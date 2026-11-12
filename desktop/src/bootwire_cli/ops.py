# src/bootwire_cli/ops.py
"""One function per CLI action. Used by both the commands and the interactive menu."""

from __future__ import annotations

import time
import zlib
from typing import Optional

import typer
from rich.table import Table

from bootwire_cli.session import Settings, console, open_client, progress_bar, read_file
from bootwire.client import DeviceInfo
from bootwire.errors import BootWireStatusError, BootWireTimeout
from bootwire.protocol.commands import Status, status_name


def show_info(info: DeviceInfo) -> None:
    table = Table(title="Target", show_header=False, title_justify="left")
    table.add_column(style="info")
    table.add_column()
    table.add_row("Protocol version", str(info.protocol_version))
    table.add_row("Bootloader version", ".".join(map(str, info.bootloader_version)))
    table.add_row("Device ID", f"0x{info.device_id:08X}")
    table.add_row("Application region", f"0x{info.app_start:08X} .. 0x{info.app_end:08X} ({info.app_size // 1024} KiB)")
    table.add_row("Erase block", f"{info.erase_block} bytes")
    table.add_row("Write alignment", f"{info.write_align} bytes")
    table.add_row("Max payload", f"{info.max_payload} bytes")
    console.print(table)


def do_info(settings: Settings) -> None:
    with open_client(settings) as client:
        show_info(client.connect())


def do_ping(settings: Settings, data: bytes, count: int) -> None:
    with open_client(settings) as client:
        client.connect()
        for i in range(1, count + 1):
            start = time.perf_counter()
            client.ping(data)
            ms = (time.perf_counter() - start) * 1000
            console.print(f"[success]reply {i}/{count}[/success]: {len(data)} bytes echoed in {ms:.1f} ms")


def do_erase(settings: Settings, address: Optional[int], length: Optional[int]) -> None:
    with open_client(settings) as client:
        info = client.connect()
        start = info.app_start if address is None else address
        size = info.app_end - start if length is None else length
        console.print(f"[info]Erasing 0x{start:08X} .. 0x{start + size:08X}[/info]")
        with progress_bar() as progress:
            client.erase_region(start, size, progress)
        console.print("[success]Erase done[/success]")


def do_write(settings: Settings, path: str, address: Optional[int]) -> None:
    data = read_file(path)
    with open_client(settings) as client:
        info = client.connect()
        start = info.app_start if address is None else address
        console.print(f"[info]Writing {len(data)} bytes at 0x{start:08X} (region must be erased first)[/info]")
        with progress_bar() as progress:
            client.write_image(data, start, progress)
        console.print("[success]Write done[/success]")


def do_verify(settings: Settings, path: str, address: Optional[int]) -> None:
    data = read_file(path)
    with open_client(settings) as client:
        info = client.connect()
        start = info.app_start if address is None else address
        padded = client.pad_image(data)
        expected = zlib.crc32(padded)
        try:
            client.verify_image(data, start)
        except BootWireStatusError as e:
            if e.status == Status.VERIFY and len(e.payload) == 4:
                actual = int.from_bytes(e.payload, "little")
                console.print(f"[error]Flash does not match {path}: CRC-32 of file 0x{expected:08X}, "
                              f"flash 0x{actual:08X}[/error]")
                raise typer.Exit(1)
            raise
        console.print(f"[success]Flash matches {path}[/success] (CRC-32 0x{expected:08X}, {len(padded)} bytes)")


def do_run(settings: Settings) -> None:
    with open_client(settings) as client:
        client.connect()
        _run(client)


def _run(client) -> None:
    try:
        client.run()
    except BootWireTimeout:
        console.print("[status]RUN sent but not confirmed. The application may already be running.[/status]")
        return
    console.print("[success]Application started[/success]")


def do_flash(settings: Settings, path: str, address: Optional[int], run: bool) -> None:
    data = read_file(path)
    with open_client(settings) as client:
        info = client.connect()
        show_info(info)
        start = info.app_start if address is None else address
        console.print(f"[info]Flashing {path} ({len(data)} bytes) at 0x{start:08X}[/info]")
        with progress_bar() as progress:
            client.erase_region(start, len(client.pad_image(data)), progress)
            client.write_image(data, start, progress)
            crc = client.verify_image(data, start)
            size = len(client.pad_image(data))
            progress("verify", size, size)
        console.print(f"[success]Image written and verified[/success] (CRC-32 0x{crc:08X})")
        if run:
            _run(client)


def do_send(settings: Settings, cmd: int, payload: bytes) -> None:
    with open_client(settings) as client:
        client.connect()
        try:
            reply = client.send(cmd, payload)
        except BootWireStatusError as e:
            console.print(f"[error]status {status_name(e.status)} (0x{e.status:02X})[/error]"
                          + (f" payload {e.payload.hex(' ')}" if e.payload else ""))
            raise typer.Exit(1)
        console.print(f"[success]status OK[/success], {len(reply)} bytes: {reply.hex(' ') if reply else '(none)'}")
        if reply and all(32 <= b < 127 for b in reply):
            console.print(f"  as text: {reply.decode('ascii')!r}")
