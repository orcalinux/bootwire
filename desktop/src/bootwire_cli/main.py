# src/bootwire_cli/main.py
"""`bootwire` command-line tool."""

from __future__ import annotations

from typing import Optional

import typer
from typer import Argument, Context, Option

from bootwire_cli import ops
from bootwire_cli.interactive import run_menu
from bootwire_cli.session import Settings, parse_bytes, parse_int
from bootwire.config import load_config
from bootwire.protocol.commands import CMD_MASK

app = typer.Typer(
    name="bootwire",
    help="BootWire toolkit: host side of the BootWire Protocol bootloader.",
    add_completion=True,
    no_args_is_help=False,
    rich_markup_mode="rich",
)


@app.callback(invoke_without_command=True)
def main(
    ctx: Context,
    port: Optional[str] = Option(None, "-p", "--port", help="Serial port, pyserial URL, or 'sim' for the built-in simulator."),
    baud: Optional[int] = Option(None, "-b", "--baud", help="Baud rate."),
    timeout: Optional[float] = Option(None, "-t", "--timeout", help="Seconds to wait for a response."),
    retries: Optional[int] = Option(None, "-r", "--retries", help="Resends after the first attempt."),
    config: Optional[str] = Option(None, "-c", "--config", help="Config file (default: ./bootwire.yaml, then ~/.bootwire.yaml)."),
    interactive: bool = Option(False, "-i", "--interactive", help="Choose the command from a menu."),
):
    cfg = load_config(config)
    ctx.obj = Settings(
        port=port or cfg["serial"]["port"],
        baud=baud or cfg["serial"]["baudrate"],
        timeout=timeout if timeout is not None else cfg["general"]["timeout"],
        erase_timeout=cfg["general"]["erase_timeout"],
        retries=retries if retries is not None else cfg["general"]["max_retries"],
        interactive=interactive,
    )
    if ctx.invoked_subcommand is None:
        if interactive:
            run_menu(ctx.obj)
        else:
            typer.echo(ctx.get_help())


@app.command()
def info(ctx: Context):
    """Connect and show what the target reports (versions, flash layout, limits)."""
    ops.do_info(ctx.obj)


@app.command()
def ping(
    ctx: Context,
    data: str = Option("ping", "-d", "--data", help="Bytes to echo (text, or hex with --hex)."),
    hex_: bool = Option(False, "--hex", help="Read --data as hex."),
    count: int = Option(1, "-n", "--count", min=1, help="Number of pings."),
):
    """Check the link: the target must echo the same bytes."""
    ops.do_ping(ctx.obj, parse_bytes(data, hex_), count)


@app.command()
def erase(
    ctx: Context,
    address: Optional[str] = Option(None, "-a", "--address", help="Start address (default: start of the application region)."),
    length: Optional[str] = Option(None, "-l", "--length", help="Bytes to erase (default: to the end of the region)."),
):
    """Erase flash, rounded out to whole erase blocks."""
    ops.do_erase(ctx.obj, parse_int(address, "address"), parse_int(length, "length"))


@app.command()
def write(
    ctx: Context,
    file: str = Argument(..., help="Binary image (.bin)."),
    address: Optional[str] = Option(None, "-a", "--address", help="Load address (default: start of the application region)."),
):
    """Write a binary image into flash that is already erased."""
    ops.do_write(ctx.obj, file, parse_int(address, "address"))


@app.command()
def verify(
    ctx: Context,
    file: str = Argument(..., help="Binary image (.bin)."),
    address: Optional[str] = Option(None, "-a", "--address", help="Load address (default: start of the application region)."),
):
    """Check with CRC-32 that flash holds exactly this image."""
    ops.do_verify(ctx.obj, file, parse_int(address, "address"))


@app.command()
def run(ctx: Context):
    """Leave the bootloader and start the application (the target checks the image first)."""
    ops.do_run(ctx.obj)


@app.command()
def flash(
    ctx: Context,
    file: str = Argument(..., help="Binary image (.bin)."),
    address: Optional[str] = Option(None, "-a", "--address", help="Load address (default: start of the application region)."),
    no_run: bool = Option(False, "--no-run", help="Stay in the bootloader after flashing."),
):
    """Full update: erase, write, verify, then run."""
    ops.do_flash(ctx.obj, file, parse_int(address, "address"), run=not no_run)


@app.command()
def send(
    ctx: Context,
    cmd: str = Argument(..., help="Command ID, 0x00-0x7F (user commands: 0x40-0x7F)."),
    data: str = Option("", "-d", "--data", help="Payload (text, or hex with --hex)."),
    hex_: bool = Option(False, "--hex", help="Read --data as hex."),
):
    """Send any command, including your own, and print the response."""
    cmd_id = parse_int(cmd, "command ID")
    if not 0 <= cmd_id <= CMD_MASK:
        typer.echo("command ID must be 0x00-0x7F", err=True)
        raise typer.Exit(2)
    ops.do_send(ctx.obj, cmd_id, parse_bytes(data, hex_))


if __name__ == "__main__":
    app()
