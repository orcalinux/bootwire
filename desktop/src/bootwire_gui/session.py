"""Serialized device operations. This module has no Qt dependency."""
from __future__ import annotations

import hashlib
import tempfile
import struct
import threading
import time
import zlib
from dataclasses import asdict
from pathlib import Path

from bootwire.client import BootWireClient
from bootwire.errors import BootWireError, BootWireTimeout
from bootwire.protocol.commands import command_name
from bootwire.sim import LoopbackTransport, SimTarget
from bootwire.transport.uart import UARTTransport


class OperationCancelled(BootWireError):
    pass


def inspect_image(path):
    path = Path(path).expanduser().resolve()
    data = path.read_bytes()
    if not data:
        raise BootWireError("The image is empty. Choose a raw .bin firmware image.")
    return data, {
        "path": str(path), "name": path.name, "size": len(data),
        "sizeLabel": f"{len(data):,} bytes", "crc32": f"{zlib.crc32(data):08X}",
        "sha256": hashlib.sha256(data).hexdigest(),
        "stackPointer": f"0x{struct.unpack_from('<I', data)[0]:08X}" if len(data) >= 4 else "Unavailable",
        "resetVector": f"0x{struct.unpack_from('<I', data, 4)[0]:08X}" if len(data) >= 8 else "Unavailable",
    }


def parse_number(text, label, default=None):
    """Read a decimal or 0x-prefixed number typed by the user."""
    text = str(text if text is not None else "").strip()
    if not text and default is not None:
        return default
    try:
        return int(text, 0)
    except ValueError:
        raise BootWireError(f"{label} must be a number such as 0x08008000 or 4096.") from None


class DeviceSession:
    """Owned exclusively by one worker; the simulator survives disconnects."""
    def __init__(self, log=lambda *args: None, progress=lambda *args: None, wrap_transport=lambda transport: transport):
        self.log = log
        self.progress = progress
        self.wrap_transport = wrap_transport
        self.client = None
        self.target = SimTarget()
        self.cancelled = threading.Event()
        self.simulated = False

    def close(self):
        if self.client:
            self.client.close()
            self.client = None

    def connect(self, options):
        self.close()
        port = options.get("port", "sim").strip()
        if not port:
            raise BootWireError("Choose a serial port or the simulator.")
        try:
            timeout = float(options.get("timeout", .5))
            erase_timeout = float(options.get("eraseTimeout", 5))
            retries = int(options.get("retries", 3))
            baud = int(options.get("baud", 115200))
        except (TypeError, ValueError, OverflowError):
            raise BootWireError("Timeouts, retries, and baud rate must be numbers. Check the connection bar and Preferences.") from None
        if not .05 <= timeout <= 60 or not .05 <= erase_timeout <= 120 or not 0 <= retries <= 10 or baud <= 0:
            raise BootWireError("Use positive timeouts, 0–10 retries, and a positive baud rate.")
        self.simulated = port == "sim"
        transport = LoopbackTransport(self.target) if self.simulated else UARTTransport(port, baud)
        try:
            self.client = BootWireClient(self.wrap_transport(transport), timeout=timeout, erase_timeout=erase_timeout,
                                        max_retries=retries, on_retry=self._retry)
            info = self.client.connect()
            self._validate_info(info)
        except Exception:
            self.close()
            raise
        self.log("success", f"Connected to {'simulator' if self.simulated else port}.")
        result = asdict(info)
        result.update(port=port, simulated=self.simulated, version=".".join(map(str, info.bootloader_version)),
                      startLabel=f"0x{info.app_start:08X}", endLabel=f"0x{info.app_end:08X}",
                      sizeLabel=f"{info.app_size / 1024:g} KiB", idLabel=f"0x{info.device_id:08X}")
        return result

    @staticmethod
    def _validate_info(info):
        if (info.app_size < 8 or info.erase_block <= 0 or info.write_align <= 0
                or info.app_size % info.erase_block or info.app_start % info.write_align
                or info.app_size % info.write_align or info.app_end > 2**32
                or info.max_payload < max(23, info.write_align + 4)):
            raise BootWireError("The target reported an unsupported flash layout or payload limit.")

    def _retry(self, cmd, attempt, attempts):
        self.check_cancelled()
        self.log("warning", f"No valid reply to {command_name(cmd)}. Retry {attempt - 1} of {attempts - 1}.")

    def check_cancelled(self):
        if self.cancelled.is_set():
            raise OperationCancelled("Stopped between commands. The image may be incomplete; flash it again before running.")

    def _progress(self, stage, done, total):
        self.progress(stage, done, total)
        self.check_cancelled()

    def _image(self, options):
        data, image = inspect_image(options["path"])
        if options.get("simulatorOnly") and not self.simulated:
            raise BootWireError("The demonstration image is for the simulator only. Choose firmware built for your board.")
        if options.get("sha256") and image["sha256"] != options["sha256"]:
            raise BootWireError("The image changed on disk. Choose it again to review the new file.")
        address = parse_number(options.get("address", ""), "Load address", self.client.info.app_start)
        padded = self.client.pad_image(data)
        self.client._check_range(address, len(padded))
        if address % self.client.info.write_align:
            raise BootWireError("The load address must match the target's write alignment.")
        block = self.client.info.erase_block
        rounded_end = address + len(padded)
        rounded_end += -(rounded_end - self.client.info.app_start) % block
        if rounded_end > self.client.info.app_end:
            raise BootWireError("The image's erase blocks extend past the application region.")
        return padded, address

    def execute(self, action, options):
        self.check_cancelled()
        if action == "inspect":
            image = inspect_image(options["path"])[1]
            if options.get("sha256") and image["sha256"] != options["sha256"]:
                raise BootWireError("This library image has changed on disk. Add the updated file as a new release.")
            image["simulatorOnly"] = options.get("simulatorOnly", False)
            return image
        if action == "demo":
            path = Path(tempfile.mkdtemp(prefix="bootwire-demo-")) / "simulator-demo.bin"
            path.write_bytes(struct.pack("<II", 0x20010000, 0x08008009) + bytes(range(256)) * 16)
            image = inspect_image(path)[1]
            image["simulatorOnly"] = True
            return image
        if action == "connect":
            return self.connect(options)
        if action == "disconnect":
            self.close()
            return {}
        if action == "reset_simulator":
            if not self.simulated:
                raise BootWireError("Simulator reset is available only in simulation mode.")
            self.close()
            self.target = SimTarget()
            return {}
        if not self.client:
            raise BootWireError("Connect to a device first.")
        if action == "fault":
            if not self.simulated:
                raise BootWireError("Fault injection is available only in simulation mode.")
            allowed = {"drop_requests", "drop_responses", "corrupt_requests", "corrupt_responses"}
            if options["kind"] not in allowed:
                raise BootWireError("Unknown fault type.")
            setattr(self.client.transport, options["kind"], 1)
            return {"message": "The next frame will be affected. Run a ping to test recovery."}
        if action == "ping":
            payload = self._payload(options)
            if len(payload) > self.client.info.max_payload:
                raise BootWireError("Payload exceeds the target's maximum payload size.")
            results = []
            count = int(options.get("count", 5))
            if not 1 <= count <= 100:
                raise BootWireError("Choose between 1 and 100 pings.")
            for i in range(count):
                self.check_cancelled()
                start = time.monotonic()
                self.client.ping(payload)
                ms = (time.monotonic() - start) * 1000
                results.append(ms)
                self.log("success", f"PING {i+1}/{count}: {len(payload)} bytes echoed in {ms:.2f} ms.")
                self._progress("ping", i+1, count)
            return {"message": f"{count}/{count} replies · average {sum(results)/count:.2f} ms"}
        if action in {"send", "raw_send"}:
            cmd = parse_number(options.get("command", ""), "Command ID")
            if action == "send" and not 0x40 <= cmd <= 0x7F:
                raise BootWireError("The command console accepts user commands 0x40–0x7F. Use the dedicated tools for flash operations.")
            if not 0 <= cmd <= 0x7F:
                raise BootWireError("Command ID must be 0x00–0x7F.")
            payload = self._payload(options)
            if len(payload) > self.client.info.max_payload:
                raise BootWireError("Payload exceeds the target's maximum payload size.")
            try:
                reply = self.client.send(cmd, payload)
            except BootWireTimeout:
                if cmd != 0x13:
                    raise
                self.close()
                return {"message":"RUN sent without confirmation. The application may be running.","disconnected":True,"unconfirmed":True}
            result = {"message": f"OK · {len(reply)} bytes", "hex": reply.hex(" ") or "(empty)",
                      "text": reply.decode("utf-8", errors="replace")}
            if cmd == 0x13:
                self.close()
                result['disconnected'] = True
            return result
        if action in {"flash", "write", "verify"}:
            data, address = self._image(options)
            if action == "flash":
                self.client.erase_region(address, len(data), self._progress)
            if action in {"flash", "write"}:
                self.client.write_image(data, address, self._progress)
            self.check_cancelled()
            crc = self.client.verify_image(data, address)
            self._progress("verify", len(data), len(data))
            result = {"message": f"Image verified · CRC-32 {crc:08X}", "crc32": f"{crc:08X}"}
            if action == "flash" and options.get("run", False):
                result.update(self._run())
            return result
        if action == "erase":
            info = self.client.info
            address = parse_number(options.get("address", ""), "Erase address", info.app_start)
            length = parse_number(options.get("length", ""), "Erase length", info.app_end - address)
            self.client.erase_region(address, length, self._progress)
            return {"message": "Application region erased."}
        if action == "run":
            return self._run()
        raise BootWireError(f"Unknown operation: {action}")

    def _run(self):
        self.check_cancelled()
        unconfirmed = False
        try:
            self.client.run()
            message = "Application started. Re-enter bootloader mode to reconnect."
        except BootWireTimeout:
            unconfirmed = True
            message = "RUN sent without confirmation. The application may be running; re-enter bootloader mode to reconnect."
        self.close()
        return {"message": message, "disconnected": True, "unconfirmed": unconfirmed}

    @staticmethod
    def _payload(options):
        text = options.get("payload", "")
        if not options.get("hex", False):
            return text.encode("utf-8")
        try:
            return bytes.fromhex(text.replace(":", " ").replace(",", " ").replace("0x", " "))
        except ValueError:
            raise BootWireError('Hex payload must be byte pairs such as "C0 DB 11". Untick Hex to send text.') from None
