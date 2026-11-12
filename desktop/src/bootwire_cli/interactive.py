# src/bootwire_cli/interactive.py
"""`bootwire -i`: pick a command from a menu and answer prompts for its arguments."""

from __future__ import annotations

from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt

from bootwire_cli import ops
from bootwire_cli.session import Settings, console, parse_bytes, parse_int

_MENU = ["info", "ping", "erase", "write", "verify", "run", "flash", "send"]


def _ask_address(question: str = "Address (empty = start of application region)"):
    text = Prompt.ask(question, default="")
    return parse_int(text, "address") if text.strip() else None


def run_menu(settings: Settings) -> None:
    console.print(Panel("\n".join(f"{i}. {name}" for i, name in enumerate(_MENU, 1)), title="BootWire commands"))
    try:
        choice = _MENU[int(Prompt.ask("Command", choices=[str(i) for i in range(1, len(_MENU) + 1)])) - 1]

        if choice == "info":
            ops.do_info(settings)
        elif choice == "ping":
            ops.do_ping(settings, Prompt.ask("Text to echo", default="ping").encode(), IntPrompt.ask("Count", default=1))
        elif choice == "erase":
            if Confirm.ask("Erase the whole application region?", default=True):
                ops.do_erase(settings, None, None)
            else:
                address = parse_int(Prompt.ask("Start address", default="0x08008000"), "address")
                length = parse_int(Prompt.ask("Length in bytes", default="0x800"), "length")
                ops.do_erase(settings, address, length)
        elif choice in ("write", "verify", "flash"):
            path = Prompt.ask("Path to .bin file").strip().strip("'\"")
            address = _ask_address()
            if choice == "write":
                ops.do_write(settings, path, address)
            elif choice == "verify":
                ops.do_verify(settings, path, address)
            else:
                ops.do_flash(settings, path, address, run=Confirm.ask("Run the application afterwards?", default=True))
        elif choice == "run":
            ops.do_run(settings)
        elif choice == "send":
            cmd = parse_int(Prompt.ask("Command ID (0x40-0x7F for user commands)"), "command ID")
            payload = parse_bytes(Prompt.ask("Payload as hex (empty for none)", default=""), as_hex=True)
            ops.do_send(settings, cmd, payload)
    except (KeyboardInterrupt, EOFError):
        console.print()
