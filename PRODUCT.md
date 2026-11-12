# BootWire

<!-- impeccable:product-schema 1 -->

## Platform

Cross-platform desktop application (Qt Quick), alongside a headless Python CLI.

## Stack

User accepted Python with PySide6 and Qt Quick/QML. The protocol library stays independent of Qt.

## Users

The project owner is extending an embedded firmware toolkit. The user requested all three workflows: firmware flashing, advanced protocol debugging, and managing devices and firmware releases. Production operating systems remain unconfirmed.

## Product Purpose

Update Cortex-M firmware over UART and exchange custom commands through BootWire protocol v0.2. The desktop should be easy to use, modern, and extensible.

## Capabilities and Constraints

Existing functionality: CONNECT, PING, addressed ERASE/WRITE, CRC-32 VERIFY, RUN, user commands, CRC-16/SLIP framing, retries, one-entry reply cache, simulated target. Real target bootloader is not implemented in this repository. One request may be in flight per connection. Application region and write limits come from the device.

## Brand Commitments

The user explicitly likes the existing colors and BootWire logo; preserve them. They requested custom modern control styling, useful application menus, and the existing logo as the application/window icon.

BootWire is the confirmed product name. User requested a fancy modern desktop UI with substantial functionality.

## Evidence on Hand

Protocol specification and 28 generated diagrams under docs/protocol. Python library and CLI in desktop/src. Existing simulator and 75 protocol tests.

## Product Principles

- Preserve a reusable protocol core and CLI.
- Keep device work off the interface thread.
- Make device state and recovery explicit.
- Distinguish simulator data from real hardware.

## Confirmed Interface Requirements

The user chose a clean, spacious workspace with light and dark themes and requested all three workflows. This first implementation provides saved device profiles, sequential batch flashing, a local release catalog, diagnostics, and a frame inspector. It maintains one active target connection at a time. Simultaneous device sessions and remote release hosting remain open future decisions.

## Developer Workspace

User requested a VS Code-like console panel showing verbose internals, manual BootWire commands, and a normal local terminal on Linux and Windows. Implemented as separate Output, BootWire, and System terminal tabs; device commands share the GUI connection. Local shells use a PTY helper on POSIX or pywinpty on Windows. Windows runtime coverage is configured for CI, pending execution outside this Linux workspace.
