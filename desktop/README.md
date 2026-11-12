# BootWire — host side

Python library (`bootwire`) and command-line tool (`bootwire`) for the
[BootWire Protocol v0.2](../docs/protocol/README.md): firmware update and custom commands for a
Cortex-M bootloader over UART. Includes a simulated target for working without hardware.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'        # dev adds pytest
```

Requires Python 3.9 or newer. Dependencies: `pyserial`, `typer`, `rich`, `PyYAML`.

## Desktop GUI

Requires Python 3.10+:

```bash
pip install -e '.[gui]'
bootwire-gui
```

Seven workspaces cover flashing, device profiles and sequential batches, a versioned firmware library, diagnostics/custom commands, frame inspection, job history, and preferences with light/dark themes. The resizable bottom panel adds verbose output, shared-session BootWire commands, and a PTY/ConPTY local terminal for Linux/macOS and Windows (PowerShell/cmd). Toggle it with Ctrl+J. The CLI and library do not require Qt. See the [desktop guide](../docs/desktop/README.md) for the simulator walkthrough, architecture, tests, and limitations.

## Use

```bash
bootwire --help
bootwire info                                  # what the target reports
bootwire ping -n 5                             # link test
bootwire flash build/app.bin                   # erase, write, verify, run
bootwire flash build/app.bin --no-run          # stay in the bootloader
bootwire erase                                 # whole application region
bootwire erase -a 0x08008000 -l 0x800          # one block
bootwire write app.bin -a 0x08010000           # into erased flash
bootwire verify app.bin                        # CRC-32 of file vs flash
bootwire run
bootwire send 0x40 -d "01 02 03" --hex         # your own command
bootwire -i                                    # pick from a menu
```

Global options come **before** the command: `bootwire -p /dev/ttyUSB0 -b 921600 -t 1.0 -r 5 flash app.bin`.

| Option | Meaning |
|---|---|
| `-p, --port` | device (`/dev/ttyACM0`, `COM3`), pyserial URL (`socket://host:4001`), or `sim` |
| `-b, --baud` | baud rate |
| `-t, --timeout` | seconds to wait for a response |
| `-r, --retries` | resends after the first attempt |
| `-c, --config` | settings file |
| `-i, --interactive` | menu |

Exit codes: `0` success, `1` the target refused or did not answer, `2` bad usage, file or port.

## Without hardware

```bash
bootwire -p sim flash app.bin                  # in-process simulator, one command at a time

python -m bootwire.sim --dump flash.bin   # simulator on a pseudo-terminal (Linux/macOS)
bootwire -p /dev/pts/N info                    # use the path it prints
```

The simulator reports a 224 KiB application region at `0x08008000`, 2 KiB erase blocks, 4-byte
write alignment and a 260-byte max payload. `RUN` only succeeds if the image starts with a valid
Cortex-M vector table (initial SP in `0x20000000…0x20010000`, reset handler inside the region).

## Settings

First file found: `--config`, `$BOOTWIRE_CONFIG`, `./bootwire.yaml`, `~/.bootwire.yaml`. Command-line options win.

```yaml
general:
  timeout: 0.5        # seconds to wait for a response
  erase_timeout: 5.0  # seconds to wait for one ERASE response
  max_retries: 3      # resends after the first attempt
serial:
  port:               # empty = auto; or a device, a pyserial URL, or "sim"
  baudrate: 115200
```

## Library

```python
from bootwire.client import BootWireClient
from bootwire.transport.uart import UARTTransport

client = BootWireClient(UARTTransport("/dev/ttyACM0"))
info = client.connect()
client.flash(open("app.bin", "rb").read())
client.close()
```

See the [project README](../README.md#-host-library) for every method and error type.

## Layout

```
src/bootwire/
  protocol/crc.py        CRC-16/CCITT-FALSE
  protocol/slip.py       SLIP encode/decode, SlipReader (stream)
  protocol/frame.py      request/response frames with CRC
  protocol/commands.py   command IDs, Status
  transport/uart.py      UARTTransport
  client.py              BootWireClient, DeviceInfo
  errors.py              BootWireError, BootWireTimeout, BootWireStatusError
  config.py              load_config()
  sim/                   SimTarget, LoopbackTransport, `python -m bootwire.sim`
src/bootwire_cli/
  main.py                commands
  ops.py                 one function per action
  session.py             port choice, client, errors → exit codes, progress
  interactive.py         `bootwire -i`
tests/                   pytest
```

## Develop

```bash
pytest -q
```

Adding a BootWire command: give it an ID in `protocol/commands.py`, a method in `client.py`, handling in
`sim/target.py`, a CLI command in `bootwire_cli/main.py` + `ops.py`, tests, and update the specification
and its diagrams (`docs/protocol/render.sh`).
