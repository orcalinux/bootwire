# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

BootWire is a UART firmware-update protocol (v0.2) for Cortex-M bootloaders. The repo holds the specification and its diagrams (`docs/protocol/`) and the whole host side in Python (`desktop/`): a library, the `bootwire` CLI, a PySide6/QML desktop app, and a simulated target. The C target bootloader does not exist yet; `SimTarget` is its reference behaviour.

## Commands

All Python work runs from `desktop/` (pytest config and `pythonpath = ["src"]` live in `desktop/pyproject.toml`).

The root `Makefile` wraps the common tasks and creates `desktop/.venv` on first use (`make help` lists everything):

```bash
make cli ARGS="-p sim info"   # run the CLI from source
make gui                      # open the desktop app
make test                     # full test suite
make man                      # read desktop/man/bootwire.1
make deb                      # build dist/bootwire_<version>_all.deb (packaging/build-deb.sh)
```

The same things by hand:

```bash
cd desktop
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[gui,dev]'          # '.[dev]' alone is enough for library + CLI work

pytest -q                             # everything
pytest -q tests/test_client.py        # one file
pytest -q tests/test_client.py::test_name          # one test
pytest -q tests/gui/test_controller.py -k batch    # by keyword

bootwire -p sim info                  # CLI against the in-process simulator
bootwire -p sim flash app.bin
python -m bootwire.sim                # simulator on a pty; prints the /dev/pts/N to pass to -p
bootwire-gui                          # desktop app (or: python -m bootwire_gui)

python -m pip wheel --no-deps . -w dist   # the build step CI runs
```

- There is no linter, formatter or type checker configured.
- Qt tests set `QT_QPA_PLATFORM=offscreen` and `QT_QUICK_BACKEND=software` themselves and are skipped (`pytest.importorskip`) when PySide6 or pyte is missing, so a green run without the `gui` extra has not exercised the GUI.
- CI (`.github/workflows/desktop.yml`) runs on Ubuntu and Windows with Python 3.11. `tests/gui/test_windowing.py` has a Windows-only part that needs `QT_QPA_PLATFORM=windows`.
- Screenshots of every workspace in both themes, written to `.impeccable/review/` (git-ignored):
  `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python ../scripts/preview_gui.py`
- Diagrams: `docs/protocol/render.sh` regenerates every SVG under `docs/protocol/image/` from `py/`, `dot/` and `puml/`. It needs Graphviz and PlantUML (Java). The SVGs are generated; edit the sources, never the SVGs.
- `scripts/render_icons.py` regenerates the PNG/ICO icons from the SVG mark.
- The manual pages in `desktop/man/` are hand-written roff. A change to a CLI option or command in `bootwire_cli/main.py` needs the same change in `bootwire.1`.
- `packaging/build-deb.sh` builds the package with `dpkg-deb` directly (no debhelper). It ships the sources under `/usr/lib/python3/dist-packages` and depends on Debian's Python packages; the Qt packages are Recommends so the CLI installs without them. A new runtime dependency in `pyproject.toml` must also be added to the control fields in that script.

## Architecture

Three packages under `desktop/src/`, layered strictly in one direction:

```
bootwire_gui  ─┐
               ├─▶  bootwire  (protocol/, transport/, client.py, sim/)
bootwire_cli  ─┘
```

**`bootwire` (library, Python ≥ 3.9, no Qt).** `protocol/` builds frames bottom-up: `crc.py` → `frame.py` (request `SEQ CMD PAYLOAD CRC16`, response `SEQ CMD|0x80 STATUS PAYLOAD CRC16`, little-endian) → `slip.py` (`C0`-delimited framing, `SlipReader` for streams). `client.py` (`BootWireClient`) is stop-and-wait: one request in flight, resend the same SEQ on silence, error statuses are final and never retried. `connect()` must come first; it stores `client.info` (`DeviceInfo`), and every later size, region and alignment decision comes from what the target reported, never from host constants.

**Transports are duck-typed**: anything with `write(bytes)`, `read(timeout) -> bytes`, `reset_input()`, `close()`. `transport/uart.py` wraps pyserial (so `socket://host:port` URLs work); `sim/target.py` provides `LoopbackTransport` + `SimTarget`, with fault injection (dropped and corrupted frames) used throughout `tests/test_client.py`. The port name `sim` selects the simulator in both the CLI and the GUI.

**`SimTarget` is the executable specification of the target.** It implements the reply cache (same SEQ + CMD is answered from cache and not executed twice; CONNECT clears it), region protection, alignment checks, read-back on WRITE and the vector-table check on RUN. A protocol change must land in the spec, the client and `SimTarget` together.

**`bootwire_cli`.** `main.py` is the Typer app, `ops.py` has one function per action, `session.py` owns settings, port choice, the mapping from errors to exit codes (0 ok, 1 target refused or silent, 2 usage/file/port) and progress bars. Global options go before the subcommand.

**`bootwire_gui` (Python ≥ 3.10, optional `gui` extra).** The threading rule is the main constraint:

- `session.py` (`DeviceSession`) is Qt-free: image inspection, validation, cooperative cancellation between commands, simulator lifetime. It is tested without Qt in `tests/gui/test_session.py`.
- `controller.py` holds `Worker` (a QObject on one QThread that owns the `DeviceSession`) and `Controller` (GUI thread). QML calls `Controller.perform(action, options)`; the request is queued to the worker; results come back as signals. All device access and file hashing happen on the worker. No QML touches a port.
- `Controller` is exposed to QML as the context property `backend`, with one `state` dict property. Frame, log and progress updates mutate state immediately but notify QML at most every 40 ms. Inspector rows live in `TraceModel` (a `QAbstractListModel`) so lists keep their scroll position.
- `TraceTransport` wraps the real transport to feed the frame inspector; RX wire hex is re-encoded after decoding, not a raw capture.
- `console.py` + `commands.py` implement the developer panel's BootWire tab: an argparse-based parser that drives the **existing** GUI session rather than spawning the CLI. `terminal.py` + `terminal_host.py` run a local shell in a helper process (ptyprocess on POSIX, pywinpty on Windows) rendered through pyte.
- `windowing.py` is the Windows-only native frame filter for the custom title bar.
- `qml/Main.qml` holds the seven workspaces; the other QML files are shared controls, and `Theme.qml` holds the tokens for both themes.
- Persistence is `QSettings("BootWire", "Desktop")`. Tests and preview scripts pass their own `QSettings` ini file to `Controller(settings=...)`; do the same in new tests so they never touch real user settings.

## Conventions specific to this repo

- Adding a protocol command touches, in order: an ID in `protocol/commands.py`, a method in `client.py`, handling in `sim/target.py`, a CLI command in `bootwire_cli/main.py` + `ops.py`, tests, then the spec (`docs/protocol/README.md`) and its diagrams via `render.sh`. The GUI command parser (`bootwire_gui/commands.py`) is separate from the Typer CLI and needs its own entry.
- Keep `bootwire` and `bootwire_cli` importable without PySide6, and compatible with Python 3.9.
- The `gui` extra excludes PySide6 6.12.0 on Python < 3.12 (it aborts the interpreter after about a thousand signal emits). Do not loosen that pin.
- User command IDs are `0x40`–`0x7F`; `0x00`–`0x13` are the bootloader's own.
- `tests/test_frame.py` contains golden vectors meant for the future firmware; they change only when the spec changes.
- GUI design direction is recorded in `PRODUCT.md` and `DESIGN.md` (colours, typography, the existing logo are to be preserved). Read them before visual changes.
