# src/bootwire/protocol/frame.py
"""
BootWire v0.2 frames (before SLIP). All multi-byte fields are little-endian.

  Request : SEQ(1) CMD(1)             PAYLOAD(0..N) CRC16(2)
  Response: SEQ(1) CMD|0x80(1) STATUS(1) PAYLOAD(0..N) CRC16(2)

CRC16 is CRC-16/CCITT-FALSE over every byte that comes before it.
"""

from __future__ import annotations

from dataclasses import dataclass

from .commands import CMD_MASK, RESPONSE_FLAG
from .crc import crc16

REQUEST_OVERHEAD = 4    # SEQ + CMD + CRC16
RESPONSE_OVERHEAD = 5   # SEQ + CMD + STATUS + CRC16


class FrameError(ValueError):
    """The bytes are not a valid BootWire frame (too short, bad CRC, wrong kind)."""


@dataclass(frozen=True)
class Request:
    seq: int
    cmd: int
    payload: bytes = b""


@dataclass(frozen=True)
class Response:
    seq: int
    cmd: int
    status: int
    payload: bytes = b""


def _seal(body: bytes) -> bytes:
    return body + crc16(body).to_bytes(2, "little")


def _unseal(raw: bytes, min_len: int) -> bytes:
    if len(raw) < min_len:
        raise FrameError(f"frame too short ({len(raw)} bytes)")
    body, received = raw[:-2], int.from_bytes(raw[-2:], "little")
    expected = crc16(body)
    if received != expected:
        raise FrameError(f"CRC mismatch: got 0x{received:04X}, expected 0x{expected:04X}")
    return body


def build_request(seq: int, cmd: int, payload: bytes = b"") -> bytes:
    if not 0 <= cmd <= CMD_MASK:
        raise ValueError(f"command ID 0x{cmd:02X} is outside 0x00-0x7F")
    return _seal(bytes([seq & 0xFF, cmd]) + bytes(payload))


def parse_request(raw: bytes) -> Request:
    body = _unseal(raw, REQUEST_OVERHEAD)
    if body[1] & RESPONSE_FLAG:
        raise FrameError("frame is a response, not a request")
    return Request(seq=body[0], cmd=body[1], payload=body[2:])


def build_response(seq: int, cmd: int, status: int, payload: bytes = b"") -> bytes:
    return _seal(bytes([seq & 0xFF, (cmd & CMD_MASK) | RESPONSE_FLAG, status & 0xFF]) + bytes(payload))


def parse_response(raw: bytes) -> Response:
    body = _unseal(raw, RESPONSE_OVERHEAD)
    if not body[1] & RESPONSE_FLAG:
        raise FrameError("frame is a request, not a response")
    return Response(seq=body[0], cmd=body[1] & CMD_MASK, status=body[2], payload=body[3:])
