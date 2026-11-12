# src/bootwire/protocol/slip.py
"""SLIP framing (RFC 1055) with a leading and a trailing END on every frame."""

from __future__ import annotations

from typing import List

END = 0xC0
ESC = 0xDB
ESC_END = 0xDC
ESC_ESC = 0xDD

# Kept for older imports.
_END, _ESC, _ESC_END, _ESC_ESC = END, ESC, ESC_END, ESC_ESC


def encode(raw: bytes) -> bytes:
    """
    SLIP-encode a raw byte sequence.
    - Prepends END (0xC0)
    - Escapes END -> ESC, ESC_END
    - Escapes ESC -> ESC, ESC_ESC
    - Appends END (0xC0)
    """
    buf = bytearray([END])
    for b in raw:
        if b == END:
            buf.extend([ESC, ESC_END])
        elif b == ESC:
            buf.extend([ESC, ESC_ESC])
        else:
            buf.append(b)
    buf.append(END)
    return bytes(buf)


def decode(frame: bytes) -> bytes:
    """
    Decode one complete SLIP frame (leading and trailing END included).
    Raises ValueError on a missing delimiter or a bad escape.
    """
    if len(frame) < 2 or frame[0] != END or frame[-1] != END:
        raise ValueError("Incomplete SLIP frame (missing END delimiters)")
    out = bytearray()
    esc = False
    for b in frame[1:-1]:
        if esc:
            if b == ESC_END:
                out.append(END)
            elif b == ESC_ESC:
                out.append(ESC)
            else:
                raise ValueError(f"Invalid SLIP escape: 0x{b:02X}")
            esc = False
        elif b == ESC:
            esc = True
        elif b == END:
            raise ValueError("Unexpected END inside SLIP frame")
        else:
            out.append(b)
    if esc:
        raise ValueError("SLIP frame ends with unfinished escape")
    return bytes(out)


class SlipReader:
    """
    Incremental SLIP decoder for a byte stream.

    Feed it whatever the port returns; it gives back every complete frame it
    has seen. This is the same state machine the target runs in its RX
    interrupt:

      - bytes before the first END are noise and are dropped
      - END closes the current frame; an empty frame (END END) is ignored
      - a bad escape or a frame longer than `max_size` is dropped, and the
        reader waits for the next END before it accepts data again
    """

    def __init__(self, max_size: int = 4096):
        self.max_size = max_size
        self._buf = bytearray()
        self._synced = False   # seen an END, so the bytes we hold belong to a frame
        self._esc = False

    def reset(self) -> None:
        self._buf.clear()
        self._synced = False
        self._esc = False

    def _drop(self) -> None:
        self._buf.clear()
        self._synced = False
        self._esc = False

    def feed(self, data: bytes) -> List[bytes]:
        frames: List[bytes] = []
        for b in data:
            if b == END:
                if self._synced and self._buf and not self._esc:
                    frames.append(bytes(self._buf))
                self._buf.clear()
                self._esc = False
                self._synced = True
            elif not self._synced:
                continue
            elif self._esc:
                self._esc = False
                if b == ESC_END:
                    self._buf.append(END)
                elif b == ESC_ESC:
                    self._buf.append(ESC)
                else:
                    self._drop()
            elif b == ESC:
                self._esc = True
            else:
                self._buf.append(b)
            if len(self._buf) > self.max_size:
                self._drop()
        return frames
