# src/bootwire/sim/target.py
"""
A model of the target side of BootWire v0.2.

It is the reference for the firmware: `SimTarget.feed()` does, in Python, what
the bootloader must do in C. It is also the partner the tests and the CLI talk
to when no board is connected.
"""

from __future__ import annotations

import struct
import time
import zlib
from typing import Callable, Dict, Optional, Tuple

from bootwire.client import DeviceInfo
from bootwire.protocol import slip
from bootwire.protocol.commands import (
    CMD_CONNECT, CMD_ERASE, CMD_PING, CMD_RUN, CMD_USER_FIRST, CMD_USER_LAST,
    CMD_VERIFY, CMD_WRITE, PROTOCOL_VERSION, Status,
)
from bootwire.protocol.frame import (
    REQUEST_OVERHEAD, FrameError, build_response, parse_request,
)

Reply = Tuple[int, bytes]                      # (status, payload)
UserHandler = Callable[[bytes], Reply]

RAM_START = 0x20000000


class SimTarget:
    def __init__(
        self,
        app_start: int = 0x08008000,
        app_size: int = 0x00038000,
        erase_block: int = 0x800,
        write_align: int = 4,
        max_payload: int = 260,
        device_id: int = 0x51D0C0DE,
        ram_size: int = 0x00010000,
        bootloader_version: Tuple[int, int, int] = (0, 2, 0),
    ):
        self.info = DeviceInfo(
            protocol_version=PROTOCOL_VERSION,
            bootloader_version=bootloader_version,
            max_payload=max_payload,
            device_id=device_id,
            app_start=app_start,
            app_size=app_size,
            erase_block=erase_block,
            write_align=write_align,
        )
        self.ram_size = ram_size
        self.flash = bytearray(b"\xFF" * app_size)
        self.running = False                    # True once RUN handed control to the application
        self.executed = 0                       # commands really executed (retries served from cache do not count)
        self.user_handlers: Dict[int, UserHandler] = {}

        # RX buffer: a frame longer than this cannot be a valid request and is dropped.
        self._reader = slip.SlipReader(max_size=max_payload + REQUEST_OVERHEAD)
        # Reply cache: one entry, enough because the host sends one request at a time.
        self._last_key: Optional[Tuple[int, int]] = None
        self._last_reply = b""

    # ── wire level ───────────────────────────────────────────────────────────

    def feed(self, data: bytes) -> bytes:
        """Take bytes from the wire, return the bytes the target sends back."""
        out = bytearray()
        for raw in self._reader.feed(data):
            reply = self.handle_frame(raw)
            if reply is not None:
                out += slip.encode(reply)
        return bytes(out)

    def handle_frame(self, raw: bytes) -> Optional[bytes]:
        """One decoded frame in, one response frame out (or None to stay silent)."""
        if self.running:
            return None                          # the application owns the UART now
        try:
            req = parse_request(raw)
        except FrameError:
            return None                          # corrupted: say nothing, the host will resend

        key = (req.seq, req.cmd)
        if req.cmd != CMD_CONNECT and key == self._last_key:
            return self._last_reply              # a retry: answer again, do not execute again

        status, payload = self._execute(req.cmd, req.payload)
        self.executed += 1
        reply = build_response(req.seq, req.cmd, status, payload)
        self._last_key, self._last_reply = key, reply
        if req.cmd == CMD_RUN and status == Status.OK:
            self.running = True                  # firmware: wait for TX to finish, then jump
        return reply

    # ── commands ─────────────────────────────────────────────────────────────

    def _execute(self, cmd: int, payload: bytes) -> Reply:
        if cmd == CMD_CONNECT:
            return self._connect(payload)
        if cmd == CMD_PING:
            return Status.OK, payload
        if cmd == CMD_ERASE:
            return self._erase(payload)
        if cmd == CMD_WRITE:
            return self._write(payload)
        if cmd == CMD_VERIFY:
            return self._verify(payload)
        if cmd == CMD_RUN:
            return self._run(payload)
        if CMD_USER_FIRST <= cmd <= CMD_USER_LAST and cmd in self.user_handlers:
            return self.user_handlers[cmd](payload)
        return Status.UNKNOWN_CMD, b""

    def _in_region(self, address: int, length: int) -> bool:
        return length > 0 and address >= self.info.app_start and address + length <= self.info.app_end

    def _connect(self, payload: bytes) -> Reply:
        if len(payload) != 1:
            return Status.BAD_LENGTH, b""
        return Status.OK, self.info.pack()

    def _erase(self, payload: bytes) -> Reply:
        if len(payload) != 8:
            return Status.BAD_LENGTH, b""
        address, length = struct.unpack("<II", payload)
        block = self.info.erase_block
        if not self._in_region(address, length) or (address - self.info.app_start) % block or length % block:
            return Status.BAD_PARAM, b""
        offset = address - self.info.app_start
        self.flash[offset:offset + length] = b"\xFF" * length
        return Status.OK, b""

    def _write(self, payload: bytes) -> Reply:
        if len(payload) <= 4:
            return Status.BAD_LENGTH, b""
        address = struct.unpack_from("<I", payload)[0]
        data = payload[4:]
        align = self.info.write_align
        if not self._in_region(address, len(data)) or address % align or len(data) % align:
            return Status.BAD_PARAM, b""
        offset = address - self.info.app_start
        # NOR flash can only turn 1 bits into 0 bits; writing over old data leaves garbage.
        for i, byte in enumerate(data):
            self.flash[offset + i] &= byte
        if self.flash[offset:offset + len(data)] != data:
            return Status.VERIFY, b""
        return Status.OK, b""

    def _verify(self, payload: bytes) -> Reply:
        if len(payload) != 12:
            return Status.BAD_LENGTH, b""
        address, length, expected = struct.unpack("<III", payload)
        if not self._in_region(address, length):
            return Status.BAD_PARAM, b""
        offset = address - self.info.app_start
        actual = zlib.crc32(bytes(self.flash[offset:offset + length]))
        status = Status.OK if actual == expected else Status.VERIFY
        return status, struct.pack("<I", actual)

    def _run(self, payload: bytes) -> Reply:
        if payload:
            return Status.BAD_LENGTH, b""
        return (Status.OK, b"") if self.app_is_valid() else (Status.NO_APP, b"")

    def app_is_valid(self) -> bool:
        """Cortex-M vector table check: stack pointer in RAM, reset vector in the app, Thumb bit set."""
        sp, reset = struct.unpack_from("<II", self.flash)
        sp_ok = RAM_START < sp <= RAM_START + self.ram_size and sp % 4 == 0
        reset_ok = bool(reset & 1) and self.info.app_start <= (reset & ~1) < self.info.app_end
        return sp_ok and reset_ok


class LoopbackTransport:
    """
    In-memory transport wired straight to a SimTarget, with fault injection.

    Set a counter to N to break the next N frames:
      drop_requests / corrupt_requests    host -> target
      drop_responses / corrupt_responses  target -> host
    """

    def __init__(self, target: Optional[SimTarget] = None):
        self.target = target or SimTarget()
        self.drop_requests = 0
        self.corrupt_requests = 0
        self.drop_responses = 0
        self.corrupt_responses = 0
        self.writes = 0
        self._rx = bytearray()

    @staticmethod
    def _corrupt(wire: bytes) -> bytes:
        damaged = bytearray(wire)
        damaged[len(damaged) // 2] ^= 0x01
        return bytes(damaged)

    def write(self, data: bytes) -> None:
        self.writes += 1
        if self.drop_requests:
            self.drop_requests -= 1
            return
        if self.corrupt_requests:
            self.corrupt_requests -= 1
            data = self._corrupt(data)
        reply = self.target.feed(data)
        if not reply:
            return
        if self.drop_responses:
            self.drop_responses -= 1
            return
        if self.corrupt_responses:
            self.corrupt_responses -= 1
            reply = self._corrupt(reply)
        self._rx += reply

    def read(self, timeout: float) -> bytes:
        if not self._rx:
            time.sleep(max(timeout, 0))
            return b""
        data = bytes(self._rx)
        self._rx.clear()
        return data

    def reset_input(self) -> None:
        self._rx.clear()

    def close(self) -> None:
        pass
