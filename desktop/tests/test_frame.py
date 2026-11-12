# desktop/tests/test_frame.py

import struct

import pytest

from bootwire.protocol.commands import CMD_CONNECT, CMD_ERASE, CMD_PING, CMD_WRITE, Status
from bootwire.protocol.frame import (
    FrameError, Request, Response, build_request, build_response, parse_request, parse_response,
)
from bootwire.protocol.slip import encode

# Golden vectors. The firmware must produce and accept exactly these bytes.
GOLDEN = [
    (build_request(0x01, CMD_PING), "01 01 1f 3e"),
    (build_response(0x01, CMD_PING, Status.OK), "01 81 00 05 d3"),
    (build_request(0x00, CMD_CONNECT, bytes([2])), "00 00 02 de ec"),
    (build_request(0x03, CMD_ERASE, struct.pack("<II", 0x08008000, 0x800)), "03 10 00 80 00 08 00 08 00 00 7d 03"),
    (build_response(0x03, CMD_ERASE, Status.BAD_PARAM), "03 90 04 a3 cd"),
    (build_request(0x05, CMD_WRITE, struct.pack("<I", 0x08008000) + bytes([0xC0, 0xDB, 0x11, 0x22])),
     "05 11 00 80 00 08 c0 db 11 22 e3 20"),
]


@pytest.mark.parametrize("frame, expected", GOLDEN)
def test_golden_vectors(frame, expected):
    assert frame.hex(" ") == expected


def test_golden_wire_bytes_with_escapes():
    frame = build_request(0x05, CMD_WRITE, struct.pack("<I", 0x08008000) + bytes([0xC0, 0xDB, 0x11, 0x22]))
    assert encode(frame).hex(" ") == "c0 05 11 00 80 00 08 db dc db dd 11 22 e3 20 c0"


def test_request_roundtrip():
    raw = build_request(0xFF, 0x41, b"\x00\x01\x02")
    assert parse_request(raw) == Request(seq=0xFF, cmd=0x41, payload=b"\x00\x01\x02")


def test_response_roundtrip():
    raw = build_response(0x10, CMD_WRITE, Status.FLASH, b"\xAA")
    assert parse_response(raw) == Response(seq=0x10, cmd=CMD_WRITE, status=Status.FLASH, payload=b"\xAA")


def test_response_sets_bit_7_of_cmd():
    assert build_response(0, 0x12, 0)[1] == 0x92


@pytest.mark.parametrize("index", range(4))
def test_any_flipped_bit_is_detected(index):
    raw = bytearray(build_request(7, CMD_PING))
    raw[index] ^= 0x10
    with pytest.raises(FrameError):
        parse_request(bytes(raw))


def test_too_short():
    with pytest.raises(FrameError):
        parse_request(b"\x01\x02\x03")
    with pytest.raises(FrameError):
        parse_response(b"\x01\x81\x00\x00")


def test_kind_is_checked():
    with pytest.raises(FrameError):
        parse_request(build_response(1, CMD_PING, 0))
    with pytest.raises(FrameError):
        parse_response(build_request(1, CMD_PING))


def test_command_id_must_fit_7_bits():
    with pytest.raises(ValueError):
        build_request(1, 0x80)
