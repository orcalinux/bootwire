# src/bootwire/protocol/crc.py

"""Flexible CRC-16 engine supporting CCITT-False and Genibus variants."""

from typing import List

_POLY    = 0x1021
_TABLE: List[int] = []

def _build_table() -> None:
    """Populate the CRC-16/CCITT lookup table (poly=0x1021)."""
    for b in range(256):
        crc = b << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) & 0xFFFF) ^ _POLY
            else:
                crc = (crc << 1) & 0xFFFF
        _TABLE.append(crc)

# build the table once
_build_table()

def crc16(
    data:    bytes,
    seed:    int = 0xFFFF,
    xorout:  int = 0x0000
) -> int:
    """
    Compute 16-bit CRC of `data` using:
      • polynomial = 0x1021
      • init       = seed (default 0xFFFF)
      • no reflection
      • final XOR  = xorout (default 0x0000 for CCITT-False)

    To get CRC-16/Genibus, call with xorout=0xFFFF.

    :param data:   input bytes
    :param seed:   initial CRC register value
    :param xorout: final XOR value (0x0000 for CCITT-False, 0xFFFF for Genibus)
    :return:       16-bit CRC
    """
    crc = seed
    for b in data:
        tbl_idx = ((crc >> 8) ^ b) & 0xFF
        crc     = (_TABLE[tbl_idx] ^ ((crc << 8) & 0xFFFF)) & 0xFFFF
    return (crc ^ xorout) & 0xFFFF
