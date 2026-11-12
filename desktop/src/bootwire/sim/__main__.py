# src/bootwire/sim/__main__.py
"""
Run the simulated target on a pseudo-terminal (Linux / macOS):

    python -m bootwire.sim [--dump flash.bin]

It prints a device path such as /dev/pts/5. Use that path as the port of the
`bootwire` tool. The simulator stops when the host sends RUN, or on Ctrl+C.
"""

from __future__ import annotations

import argparse
import os
import sys
import tty

from bootwire.sim.target import SimTarget


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m bootwire.sim", description="Simulated BootWire target on a pty")
    parser.add_argument("--dump", metavar="FILE", help="write the application flash region to FILE on exit")
    args = parser.parse_args()

    target = SimTarget()
    master, slave = os.openpty()
    tty.setraw(slave)
    info = target.info
    print(f"BootWire simulated target on {os.ttyname(slave)}")
    print(f"application region 0x{info.app_start:08X}..0x{info.app_end:08X}, "
          f"erase block {info.erase_block}, max payload {info.max_payload}")
    sys.stdout.flush()

    try:
        while not target.running:
            reply = target.feed(os.read(master, 4096))
            if reply:
                os.write(master, reply)
        print("RUN accepted: application started, simulator stops")
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        if args.dump:
            with open(args.dump, "wb") as f:
                f.write(target.flash)
            print(f"flash written to {args.dump}")
        os.close(master)
        os.close(slave)
    return 0


if __name__ == "__main__":
    sys.exit(main())
