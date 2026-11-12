# src/bootwire_cli/session.py
"""Shared CLI plumbing: settings, port choice, client creation, error reporting, progress."""

from __future__ import annotations

import sys
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, Optional

import serial
import typer
from rich.console import Console
from rich.progress import BarColumn, DownloadColumn, Progress, TextColumn, TimeRemainingColumn
from rich.prompt import Prompt
from rich.theme import Theme
from serial.tools import list_ports

from bootwire.client import BootWireClient
from bootwire.errors import BootWireError, BootWireStatusError, BootWireTimeout

console = Console(theme=Theme({
    "info": "bold cyan",
    "status": "yellow",
    "success": "bold green",
    "error": "bold red",
}))

SIM_PORT = "sim"   # in-process simulated target, handy without hardware


@dataclass
class Settings:
    port: Optional[str]
    baud: int
    timeout: float
    erase_timeout: float
    retries: int
    interactive: bool = False


def parse_int(text: Optional[str], what: str) -> Optional[int]:
    """Accept 1234, 0x4D2, 0o2322 or 0b...; None stays None."""
    if text is None:
        return None
    try:
        return int(str(text).replace("_", ""), 0)
    except ValueError:
        console.print(f"[error]{what} must be a number (decimal or 0x hex), got {text!r}[/error]")
        raise typer.Exit(2)


def parse_bytes(text: str, as_hex: bool) -> bytes:
    if not as_hex:
        return text.encode("utf-8")
    try:
        return bytes.fromhex(text.replace(" ", "").replace(":", ""))
    except ValueError:
        console.print("[error]Invalid hex data: use pairs of 0-9 A-F, for example 'DE AD BE EF'[/error]")
        raise typer.Exit(2)


def read_file(path: str) -> bytes:
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError as e:
        console.print(f"[error]Cannot read {path}: {e.strerror}[/error]")
        raise typer.Exit(2)
    if not data:
        console.print(f"[error]{path} is empty[/error]")
        raise typer.Exit(2)
    return data


def choose_port(settings: Settings) -> str:
    if settings.port:
        return settings.port
    ports = sorted(list_ports.comports(), key=lambda p: p.device)
    if not ports:
        console.print("[error]No serial port found. Connect the board or pass --port.[/error]")
        raise typer.Exit(2)
    if len(ports) == 1:
        return ports[0].device
    if not (settings.interactive or sys.stdin.isatty()):
        names = ", ".join(p.device for p in ports)
        console.print(f"[error]Several serial ports found ({names}). Choose one with --port.[/error]")
        raise typer.Exit(2)
    for i, p in enumerate(ports, 1):
        console.print(f"  {i}. {p.device}  [dim]{p.description}[/dim]")
    choice = Prompt.ask("Port number", choices=[str(i) for i in range(1, len(ports) + 1)], default="1")
    return ports[int(choice) - 1].device


def _on_retry(cmd: int, attempt: int, attempts: int) -> None:
    from bootwire.protocol.commands import command_name
    console.print(f"[status]{command_name(cmd)}: no valid response, resending ({attempt}/{attempts})[/status]")


@contextmanager
def open_client(settings: Settings) -> Iterator[BootWireClient]:
    """Open the port, yield a client, and turn every failure into a clean message and exit code."""
    port = choose_port(settings)
    try:
        if port == SIM_PORT:
            from bootwire.sim import LoopbackTransport
            transport = LoopbackTransport()
            console.print("[info]Using the in-process simulated target[/info]")
        else:
            from bootwire.transport.uart import UARTTransport
            transport = UARTTransport(port, settings.baud)
            console.print(f"[info]Using {port} at {settings.baud} bps[/info]")
    except (serial.SerialException, OSError) as e:
        console.print(f"[error]Cannot open {port}: {e}[/error]")
        raise typer.Exit(2)

    client = BootWireClient(
        transport,
        timeout=settings.timeout,
        erase_timeout=settings.erase_timeout,
        max_retries=settings.retries,
        on_retry=_on_retry,
    )
    try:
        yield client
    except BootWireStatusError as e:
        console.print(f"[error]{e}[/error]")
        raise typer.Exit(1)
    except BootWireTimeout as e:
        console.print(f"[error]Timeout: {e}. Is the board in bootloader mode and the port right?[/error]")
        raise typer.Exit(1)
    except BootWireError as e:
        console.print(f"[error]{e}[/error]")
        raise typer.Exit(1)
    except serial.SerialException as e:
        console.print(f"[error]Serial port error: {e}[/error]")
        raise typer.Exit(2)
    finally:
        client.close()


@contextmanager
def progress_bar() -> Iterator:
    """Yield a progress(stage, done, total) callback that draws one bar per stage."""
    with Progress(
        TextColumn("[info]{task.description:<7}[/info]"),
        BarColumn(),
        DownloadColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=False,
    ) as prog:
        tasks = {}

        def update(stage: str, done: int, total: int) -> None:
            if stage not in tasks:
                tasks[stage] = prog.add_task(stage, total=total)
            prog.update(tasks[stage], completed=done, total=total)

        yield update
