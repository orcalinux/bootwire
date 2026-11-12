# src/bootwire/client.py
"""Host side of BootWire v0.2: one request, one response, retry on silence."""

from __future__ import annotations

import os
import struct
import time
import zlib
from dataclasses import dataclass
from typing import Callable, Optional, Tuple

from bootwire.errors import BootWireError, BootWireStatusError, BootWireTimeout
from bootwire.protocol import slip
from bootwire.protocol.commands import (
    CMD_CONNECT, CMD_ERASE, CMD_PING, CMD_RUN, CMD_VERIFY, CMD_WRITE,
    PROTOCOL_VERSION, Status, command_name,
)
from bootwire.protocol.frame import FrameError, build_request, parse_response

_INFO_FORMAT = "<B3BHIIIIB"
_ADDRESS_SIZE = 4

# progress(stage, done, total) with stage "erase", "write" or "verify"
ProgressFn = Callable[[str, int, int], None]
# on_retry(cmd, attempt, attempts)
RetryFn = Callable[[int, int, int], None]


@dataclass(frozen=True)
class DeviceInfo:
    """What the target reports in its CONNECT response."""
    protocol_version: int
    bootloader_version: Tuple[int, int, int]
    max_payload: int    # largest request or response payload the target accepts, in bytes
    device_id: int
    app_start: int      # first address the host may erase and write
    app_size: int       # size of that region in bytes
    erase_block: int    # ERASE address and length must be multiples of this
    write_align: int    # WRITE address and length must be multiples of this

    @classmethod
    def unpack(cls, payload: bytes) -> "DeviceInfo":
        if len(payload) != struct.calcsize(_INFO_FORMAT):
            raise BootWireError(f"CONNECT response has {len(payload)} bytes, expected {struct.calcsize(_INFO_FORMAT)}")
        proto, major, minor, patch, max_payload, dev, start, size, block, align = struct.unpack(_INFO_FORMAT, payload)
        return cls(proto, (major, minor, patch), max_payload, dev, start, size, block, align)

    def pack(self) -> bytes:
        return struct.pack(
            _INFO_FORMAT, self.protocol_version, *self.bootloader_version, self.max_payload,
            self.device_id, self.app_start, self.app_size, self.erase_block, self.write_align,
        )

    @property
    def app_end(self) -> int:
        return self.app_start + self.app_size


class BootWireClient:
    def __init__(
        self,
        transport,
        timeout: float = 0.5,
        erase_timeout: float = 5.0,
        max_retries: int = 3,
        on_retry: Optional[RetryFn] = None,
    ):
        """
        :param transport:     object with write / read(timeout) / reset_input / close
        :param timeout:       seconds to wait for a response
        :param erase_timeout: seconds to wait for an ERASE response
        :param max_retries:   resends after the first attempt
        :param on_retry:      called before each resend
        """
        self.transport = transport
        self.timeout = timeout
        self.erase_timeout = erase_timeout
        self.max_retries = max_retries
        self.on_retry = on_retry
        self.info: Optional[DeviceInfo] = None
        self._seq = os.urandom(1)[0]

    def close(self) -> None:
        self.transport.close()

    # ── transaction ──────────────────────────────────────────────────────────

    def transact(self, cmd: int, payload: bytes = b"", timeout: Optional[float] = None) -> bytes:
        """
        Send one request and return the response payload.

        The same frame (same SEQ) is resent when no valid response arrives in
        time, so the target can tell a retry from a new request. A response
        with a status other than OK raises BootWireStatusError at once.
        """
        timeout = self.timeout if timeout is None else timeout
        seq = self._seq
        self._seq = (seq + 1) & 0xFF
        wire = slip.encode(build_request(seq, cmd, payload))
        attempts = self.max_retries + 1

        for attempt in range(1, attempts + 1):
            if attempt > 1 and self.on_retry:
                self.on_retry(cmd, attempt, attempts)
            self.transport.reset_input()
            reader = slip.SlipReader()
            self.transport.write(wire)

            deadline = time.monotonic() + timeout
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                for raw in reader.feed(self.transport.read(remaining)):
                    try:
                        resp = parse_response(raw)
                    except FrameError:
                        continue                      # corrupted: keep waiting, then resend
                    if resp.seq != seq or resp.cmd != cmd:
                        continue                      # stale answer to an older request
                    if resp.status != Status.OK:
                        raise BootWireStatusError(cmd, resp.status, resp.payload)
                    return resp.payload

        raise BootWireTimeout(f"{command_name(cmd)}: no response after {attempts} attempts")

    send = transact  # raw access for user-defined commands

    # ── commands ─────────────────────────────────────────────────────────────

    def connect(self) -> DeviceInfo:
        """Start a session: the target clears its reply cache and reports its limits."""
        info = DeviceInfo.unpack(self.transact(CMD_CONNECT, bytes([PROTOCOL_VERSION])))
        if info.protocol_version != PROTOCOL_VERSION:
            raise BootWireError(
                f"target speaks BootWire protocol version {info.protocol_version}, this tool speaks {PROTOCOL_VERSION}"
            )
        self.info = info
        return info

    def ping(self, data: bytes = b"") -> bytes:
        """Send bytes and check that the target echoes exactly the same bytes."""
        echo = self.transact(CMD_PING, data)
        if echo != data:
            raise BootWireError(f"PING echo differs: sent {data.hex()}, got {echo.hex()}")
        return echo

    def erase(self, address: int, length: int) -> None:
        """Erase [address, address + length). Both must be multiples of the erase block."""
        self.transact(CMD_ERASE, struct.pack("<II", address, length), timeout=self.erase_timeout)

    def write(self, address: int, data: bytes) -> None:
        """Program `data` at `address`. The target reads it back before it answers OK."""
        self.transact(CMD_WRITE, struct.pack("<I", address) + data)

    def verify(self, address: int, length: int, crc32: int) -> int:
        """Ask the target to compare the CRC-32 of a flash range. Returns the target's CRC-32."""
        payload = self.transact(CMD_VERIFY, struct.pack("<III", address, length, crc32 & 0xFFFFFFFF))
        return struct.unpack("<I", payload)[0] if len(payload) == 4 else crc32

    def run(self) -> None:
        """Leave the bootloader and start the application."""
        self.transact(CMD_RUN)

    # ── image operations ─────────────────────────────────────────────────────

    def _require_info(self) -> DeviceInfo:
        return self.info or self.connect()

    def pad_image(self, data: bytes) -> bytes:
        """Pad with 0xFF (erased flash) up to the target's write alignment."""
        align = max(self._require_info().write_align, 1)
        return data + b"\xFF" * (-len(data) % align)

    def _check_range(self, address: int, length: int) -> None:
        info = self._require_info()
        if length <= 0:
            raise BootWireError("nothing to do: length is 0")
        if address < info.app_start or address + length > info.app_end:
            raise BootWireError(
                f"range 0x{address:08X}..0x{address + length:08X} is outside the application region "
                f"0x{info.app_start:08X}..0x{info.app_end:08X}"
            )

    def erase_region(
        self, address: Optional[int] = None, length: Optional[int] = None, progress: Optional[ProgressFn] = None
    ) -> None:
        """Erase every block that touches the range, one block per command. Default: whole application region."""
        info = self._require_info()
        address = info.app_start if address is None else address
        length = info.app_end - address if length is None else length
        self._check_range(address, length)
        block = max(info.erase_block, 1)
        start = address - (address - info.app_start) % block
        end = address + length
        end += -(end - info.app_start) % block
        total = end - start
        for addr in range(start, end, block):
            self.erase(addr, block)
            if progress:
                progress("erase", addr + block - start, total)

    def write_image(self, data: bytes, address: Optional[int] = None, progress: Optional[ProgressFn] = None) -> None:
        """Write `data` in chunks as large as the target allows."""
        info = self._require_info()
        address = info.app_start if address is None else address
        data = self.pad_image(data)
        self._check_range(address, len(data))
        align = max(info.write_align, 1)
        chunk = (info.max_payload - _ADDRESS_SIZE) // align * align
        if chunk <= 0:
            raise BootWireError(f"target max payload ({info.max_payload}) is too small to write data")
        for offset in range(0, len(data), chunk):
            part = data[offset:offset + chunk]
            self.write(address + offset, part)
            if progress:
                progress("write", offset + len(part), len(data))

    def verify_image(self, data: bytes, address: Optional[int] = None) -> int:
        """Check that flash holds exactly `data` (padded), using CRC-32. Returns the CRC-32."""
        info = self._require_info()
        address = info.app_start if address is None else address
        data = self.pad_image(data)
        self._check_range(address, len(data))
        return self.verify(address, len(data), zlib.crc32(data))

    def flash(
        self, data: bytes, address: Optional[int] = None, run: bool = True, progress: Optional[ProgressFn] = None
    ) -> None:
        """Full update: connect, erase, write, verify, and (optionally) run."""
        info = self.connect()
        address = info.app_start if address is None else address
        padded = self.pad_image(data)
        self._check_range(address, len(padded))
        self.erase_region(address, len(padded), progress)
        self.write_image(padded, address, progress)
        self.verify_image(padded, address)
        if progress:
            progress("verify", len(padded), len(padded))
        if run:
            self.run()
