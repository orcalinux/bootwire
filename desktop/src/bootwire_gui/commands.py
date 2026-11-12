"""Parse BootWire console commands as data; never pass them to a shell."""
from __future__ import annotations

import argparse
import shlex
from dataclasses import dataclass, field


class CommandError(ValueError):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise CommandError(message)


@dataclass
class Command:
    action: str
    options: dict = field(default_factory=dict)
    connection: dict = field(default_factory=dict)
    reconnect: bool = False
    review: bool = False
    help: str = ""


def parser():
    p = Parser(prog='bootwire', add_help=False, description='Commands use the same device session as the desktop.')
    p.add_argument('-p', '--port')
    p.add_argument('-b', '--baud', type=int)
    p.add_argument('-t', '--timeout', type=float)
    p.add_argument('-r', '--retries', type=int)
    sub = p.add_subparsers(dest='action', parser_class=Parser)
    for name in ['connect', 'disconnect', 'info', 'run', 'clear', 'help', 'cancel', 'demo', 'reset-simulator']:
        sub.add_parser(name, add_help=False)
    ping = sub.add_parser('ping', add_help=False)
    ping.add_argument('-d', '--data', default='ping')
    ping.add_argument('--hex', action='store_true')
    ping.add_argument('-n', '--count', type=int, default=1)
    erase = sub.add_parser('erase', add_help=False)
    erase.add_argument('-a', '--address', default='')
    erase.add_argument('-l', '--length', default='')
    for name in ['flash', 'write', 'verify']:
        image = sub.add_parser(name, add_help=False)
        image.add_argument('file')
        image.add_argument('-a', '--address', default='')
        if name == 'flash':
            image.add_argument('--no-run', action='store_true')
    send = sub.add_parser('send', add_help=False)
    send.add_argument('command')
    send.add_argument('-d', '--data', default='')
    send.add_argument('--hex', action='store_true')
    return p


HELP = '''BootWire console — same connection and flash state as the GUI

connect / info                Connect or refresh target information
bootwire -p sim info          Global options before the command: -p -b -t -r
disconnect                    Close the current device session
ping -n 5 -d "C0 DB" --hex     Echo bytes and measure round-trip time
flash "app.bin" --no-run      Erase, write, and verify a raw image
write "app.bin"               Write into erased flash, then verify
verify "app.bin"              Verify the padded image CRC-32
erase [-a ADDRESS] [-l LENGTH] Erase a range, or the whole application region
run                           Start the target application
send 0x40 -d "01 02" --hex     Send a raw command (0x00–0x7F)
demo                          Load a simulator-only demonstration image
reset-simulator               Reset virtual flash and reconnect manually
cancel                        Stop device work between commands
clear / help                  Clear console output / show this guide

Addresses accept decimal or 0x hex. Quote file paths containing spaces.
Raw hex payloads must be quoted. No pipes, shell expansions, or scripts run here.
Erase, write, flash, RUN, and destructive raw commands require confirmation.
Use the System terminal tab for your operating system's shell.'''


def parse_command(line, defaults):
    lexer = shlex.shlex(line, posix=True)
    lexer.whitespace_split = True
    lexer.commenters = ''
    lexer.escape = ''  # Preserve Windows paths, including quoted C:\\ paths.
    try:
        args = list(lexer)
    except ValueError as exc:
        raise CommandError(str(exc)) from exc
    if args and args[0].lower() in {'bootwire', 'bootwire.exe'}:
        args.pop(0)
    if not args or '--help' in args or '-h' in args:
        return Command('help', help=HELP)
    ns = parser().parse_args(args)
    if not ns.action or ns.action == 'help':
        return Command('help', help=HELP)
    connection = dict(defaults)
    reconnect = False
    for key in ['port', 'baud', 'timeout', 'retries']:
        value = getattr(ns, key)
        if value is not None:
            connection[key] = value
            reconnect = True
    action = ns.action.replace('-', '_')
    options = {}
    if action in {'ping', 'send'}:
        options = {'payload': ns.data, 'hex': ns.hex}
        if ns.hex:
            try:
                bytes.fromhex(ns.data.replace(':', ' '))
            except ValueError as exc:
                raise CommandError('Invalid hex payload. Use quoted byte pairs such as "C0 DB".') from exc
    if action == 'ping':
        if not 1 <= ns.count <= 100:
            raise CommandError('Ping count must be 1–100.')
        options['count'] = ns.count
    review = action in {'erase', 'write', 'flash', 'run'}
    if action == 'send':
        try:
            cmd = int(ns.command, 0)
        except ValueError as exc:
            raise CommandError('Command ID must be a number, e.g. 0x40.') from exc
        if not 0 <= cmd <= 0x7f:
            raise CommandError('Command ID must be 0x00–0x7F.')
        action = 'raw_send'
        options['command'] = str(cmd)
        review = cmd in {0x10, 0x11, 0x13}
    if action in {'flash', 'write', 'verify'}:
        options.update(path=ns.file, address=ns.address)
        if action == 'flash':
            options['run'] = not ns.no_run
    if action == 'erase':
        options = {'address': ns.address, 'length': ns.length}
    return Command(action, options, connection, reconnect, review)
