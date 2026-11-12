# desktop/tests/test_client.py
"""The host client against the simulated target, with faults injected on the wire."""

import struct
import zlib

import pytest

from bootwire.client import BootWireClient
from bootwire.errors import BootWireError, BootWireStatusError, BootWireTimeout
from bootwire.protocol import slip
from bootwire.protocol.commands import CMD_CONNECT, CMD_PING, CMD_WRITE, PROTOCOL_VERSION, Status
from bootwire.protocol.frame import build_request, build_response, parse_request, parse_response
from bootwire.sim import LoopbackTransport, SimTarget

APP_START = 0x08008000


def make_image(size: int = 3000) -> bytes:
    """A minimal Cortex-M image: initial SP in RAM, reset handler (Thumb) inside the app."""
    vectors = struct.pack("<II", 0x20008000, APP_START + 0x101)
    body = bytes((i * 7) & 0xFF for i in range(size - len(vectors)))
    return vectors + body


@pytest.fixture
def link():
    return LoopbackTransport(SimTarget(app_start=APP_START))


@pytest.fixture
def client(link):
    c = BootWireClient(link, timeout=0.02, erase_timeout=0.02, max_retries=3)
    c.connect()
    return c


def flash_bytes(link, length, offset=0):
    return bytes(link.target.flash[offset:offset + length])


# ── normal operation ─────────────────────────────────────────────────────────

def test_connect_reports_target_layout(client):
    info = client.info
    assert info.protocol_version == PROTOCOL_VERSION
    assert info.app_start == APP_START
    assert info.erase_block == 0x800
    assert info.write_align == 4
    assert info.max_payload == 260


def test_ping_echo(client):
    assert client.ping(b"\xC0\xDB hello") == b"\xC0\xDB hello"


def test_flash_full_flow(client, link):
    image = make_image(5001)                       # not a multiple of 4: gets padded with 0xFF
    client.flash(image)
    padded = image + b"\xFF" * 3
    assert flash_bytes(link, len(padded)) == padded
    assert link.target.running


def test_flash_at_offset(client, link):
    image = make_image(1024)
    client.flash(image, address=APP_START + 0x1000, run=False)
    assert flash_bytes(link, 1024, 0x1000) == image
    assert not link.target.running


def test_erase_rounds_out_to_blocks(client, link):
    link.target.flash[0:0x2000] = b"\x00" * 0x2000
    client.erase_region(APP_START + 0x900, 0x10)       # touches only block 1
    assert flash_bytes(link, 0x800, 0x800) == b"\xFF" * 0x800
    assert flash_bytes(link, 0x800, 0) == b"\x00" * 0x800
    assert flash_bytes(link, 0x800, 0x1000) == b"\x00" * 0x800


def test_write_chunks_use_max_payload(client, link):
    client.erase_region(APP_START, 0x800)
    writes_before = link.writes
    client.write_image(bytes(512))
    assert link.writes - writes_before == 2           # 256 data bytes per WRITE


def test_verify_returns_crc(client):
    image = make_image(600)
    client.flash(image, run=False)
    assert client.verify_image(image) == zlib.crc32(image)


def test_user_command(client, link):
    link.target.user_handlers[0x40] = lambda payload: (Status.OK, payload[::-1])
    assert client.send(0x40, b"abc") == b"cba"


# ── target-side checks ───────────────────────────────────────────────────────

def test_verify_mismatch_reports_target_crc(client, link):
    image = make_image(600)
    client.flash(image, run=False)
    link.target.flash[10] ^= 0xFF                    # a bit flipped in flash after writing
    with pytest.raises(BootWireStatusError) as err:
        client.verify_image(image)
    assert err.value.status == Status.VERIFY
    assert err.value.payload != struct.pack("<I", zlib.crc32(image))


def test_write_over_unerased_flash_fails_readback(client, link):
    link.target.flash[0:4] = b"\x00\x00\x00\x00"
    with pytest.raises(BootWireStatusError) as err:
        client.write(APP_START, b"\xFF\xFF\xFF\xFF")
    assert err.value.status == Status.VERIFY


@pytest.mark.parametrize("address, data", [
    (APP_START - 4, b"\x00" * 4),                  # below the application region (bootloader)
    (APP_START + 0x38000 - 4, b"\x00" * 8),        # runs past the end of the region
    (APP_START + 2, b"\x00" * 4),                  # not aligned
    (APP_START, b"\x00" * 3),                      # length not aligned
])
def test_target_rejects_bad_write(client, address, data):
    with pytest.raises(BootWireStatusError) as err:
        client.write(address, data)
    assert err.value.status == Status.BAD_PARAM


def test_target_rejects_unaligned_erase(client):
    with pytest.raises(BootWireStatusError) as err:
        client.erase(APP_START + 0x100, 0x800)
    assert err.value.status == Status.BAD_PARAM


def test_target_rejects_wrong_length(client):
    with pytest.raises(BootWireStatusError) as err:
        client.send(0x10, b"\x00\x00")               # ERASE needs 8 bytes
    assert err.value.status == Status.BAD_LENGTH


def test_unknown_command(client):
    with pytest.raises(BootWireStatusError) as err:
        client.send(0x7F)
    assert err.value.status == Status.UNKNOWN_CMD


def test_run_refused_without_valid_image(client, link):
    with pytest.raises(BootWireStatusError) as err:
        client.run()
    assert err.value.status == Status.NO_APP
    assert not link.target.running


def test_host_refuses_range_outside_region_before_sending(client, link):
    writes_before = link.writes
    with pytest.raises(BootWireError):
        client.write_image(bytes(16), address=APP_START - 0x800)
    assert link.writes == writes_before


# ── faults on the wire ───────────────────────────────────────────────────────

def test_lost_request_is_resent(client, link):
    executed = link.target.executed
    link.drop_requests = 1
    assert client.ping(b"x") == b"x"
    assert link.target.executed == executed + 1


def test_corrupted_request_is_ignored_by_target_then_resent(client, link):
    executed = link.target.executed
    link.corrupt_requests = 2
    assert client.ping(b"y") == b"y"
    assert link.target.executed == executed + 1


def test_lost_response_is_replayed_not_executed_again(client, link):
    client.erase_region(APP_START, 0x800)
    executed = link.target.executed
    link.drop_responses = 1
    client.write(APP_START, b"\x12\x34\x56\x78")
    # Executing WRITE twice would program the same word twice; the cache prevents it.
    assert link.target.executed == executed + 1
    assert flash_bytes(link, 4) == b"\x12\x34\x56\x78"


def test_corrupted_response_is_ignored_by_host_then_replayed(client, link):
    executed = link.target.executed
    link.corrupt_responses = 1
    assert client.ping(b"z") == b"z"
    assert link.target.executed == executed + 1


def test_flash_survives_many_faults(link):
    class Noisy(LoopbackTransport):
        """Drops every 3rd request and corrupts every 5th response for the whole update."""
        def write(self, data):
            if (self.writes + 1) % 3 == 0:
                self.drop_requests = 1
            elif (self.writes + 1) % 5 == 0:
                self.corrupt_responses = 1
            super().write(data)

    noisy = Noisy(link.target)
    image = make_image(4000)
    BootWireClient(noisy, timeout=0.02, erase_timeout=0.02, max_retries=3).flash(image, run=False)
    assert flash_bytes(noisy, len(image)) == image
    assert noisy.writes > link.target.executed       # retries happened, yet each command ran once


def test_error_status_is_not_retried(client, link):
    writes_before = link.writes
    with pytest.raises(BootWireStatusError):
        client.send(0x7F)
    assert link.writes == writes_before + 1


def test_gives_up_after_retries(client, link):
    writes_before = link.writes
    link.drop_requests = 100
    with pytest.raises(BootWireTimeout):
        client.ping()
    assert link.writes == writes_before + 4          # 1 attempt + 3 retries


def test_stale_response_with_other_seq_is_ignored(link):
    class StaleFirst(LoopbackTransport):
        """A late answer to the previous request arrives just before the real one."""
        def write(self, data):
            req = parse_request(slip.decode(data))
            self._rx += slip.encode(build_response((req.seq - 1) & 0xFF, req.cmd, Status.OK, b"stale"))
            super().write(data)

    c = BootWireClient(StaleFirst(link.target), timeout=0.02, max_retries=0)
    c.connect()                                       # would fail to unpack b"stale" if accepted
    assert c.ping(b"fresh") == b"fresh"


# ── reply cache and CONNECT ──────────────────────────────────────────────────

def _exchange(target, seq, cmd, payload=b""):
    return parse_response(slip.decode(target.feed(slip.encode(build_request(seq, cmd, payload)))))


def test_same_seq_and_cmd_returns_cached_reply():
    target = SimTarget()
    assert _exchange(target, 9, CMD_PING, b"first").payload == b"first"
    assert _exchange(target, 9, CMD_PING, b"second").payload == b"first"   # treated as a retry


def test_connect_clears_the_cache():
    target = SimTarget()
    _exchange(target, 9, CMD_PING, b"old session")
    _exchange(target, 9, CMD_CONNECT, bytes([PROTOCOL_VERSION]))
    assert _exchange(target, 9, CMD_PING, b"new session").payload == b"new session"


def test_target_is_silent_after_run(client, link):
    client.flash(make_image(), run=True)
    reply = link.target.feed(slip.encode(build_request(1, CMD_PING)))
    assert reply == b""


def test_oversized_request_is_dropped():
    target = SimTarget(max_payload=16)
    assert target.feed(slip.encode(build_request(1, CMD_WRITE, bytes(40)))) == b""
    assert _exchange(target, 2, CMD_PING, b"ok").payload == b"ok"
