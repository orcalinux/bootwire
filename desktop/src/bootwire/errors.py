# src/bootwire/errors.py

from __future__ import annotations

from bootwire.protocol.commands import command_name, status_name


class BootWireError(Exception):
    """Base class for every error the BootWire client raises."""


class BootWireTimeout(BootWireError):
    """No valid response arrived, even after all retries."""


class BootWireStatusError(BootWireError):
    """The target answered with a status other than OK. Never retried."""

    def __init__(self, cmd: int, status: int, payload: bytes = b""):
        self.cmd = cmd
        self.status = status
        self.payload = payload
        super().__init__(f"{command_name(cmd)} failed: target status {status_name(status)} (0x{status:02X})")
