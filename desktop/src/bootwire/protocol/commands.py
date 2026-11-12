# src/bootwire/protocol/commands.py
"""Command IDs and status codes of BootWire v0.2."""

from enum import IntEnum

PROTOCOL_VERSION = 2

# Command IDs use 7 bits. Bit 7 is set by the target in its response.
RESPONSE_FLAG = 0x80
CMD_MASK = 0x7F

# 0x00-0x0F: link control
CMD_CONNECT = 0x00
CMD_PING = 0x01

# 0x10-0x1F: bootloader flash operations
CMD_ERASE = 0x10
CMD_WRITE = 0x11
CMD_VERIFY = 0x12
CMD_RUN = 0x13

# 0x40-0x7F: user-defined commands
CMD_USER_FIRST = 0x40
CMD_USER_LAST = 0x7F

COMMAND_NAMES = {
    CMD_CONNECT: "CONNECT",
    CMD_PING: "PING",
    CMD_ERASE: "ERASE",
    CMD_WRITE: "WRITE",
    CMD_VERIFY: "VERIFY",
    CMD_RUN: "RUN",
}


def command_name(cmd: int) -> str:
    return COMMAND_NAMES.get(cmd, f"0x{cmd:02X}")


class Status(IntEnum):
    OK = 0x00
    GENERIC = 0x01       # unspecified failure
    UNKNOWN_CMD = 0x02   # command ID not supported
    BAD_LENGTH = 0x03    # payload length wrong for this command
    BAD_PARAM = 0x04     # address out of range or not aligned
    FLASH = 0x05         # flash erase or program operation failed
    VERIFY = 0x06        # read-back or CRC-32 mismatch
    NO_APP = 0x07        # RUN refused: no valid application image


def status_name(status: int) -> str:
    try:
        return Status(status).name
    except ValueError:
        return f"0x{status:02X}"
