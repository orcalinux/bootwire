"""Qt boundary: the UI never accesses a device or reads firmware directly."""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

import serial
from serial.tools import list_ports
from PySide6.QtCore import QAbstractListModel, QModelIndex, QObject, Property, QSettings, QThread, QTimer, QUrl, Signal, Slot, Qt

from bootwire.config import load_config
from bootwire.errors import BootWireStatusError, BootWireTimeout
from bootwire.protocol import slip
from bootwire.protocol.commands import command_name, status_name
from bootwire.protocol.frame import parse_request, parse_response
from bootwire_gui.session import DeviceSession, OperationCancelled
from bootwire_gui.console import ConsoleService


class TraceTransport:
    def __init__(self, transport, emit):
        self.inner, self.emit = transport, emit
        self.reader = slip.SlipReader()

    def write(self, data):
        try:
            frame = parse_request(slip.decode(data))
            self.emit("TX", frame.seq, frame.cmd, -1, frame.payload.hex(" "), data.hex(" "))
        except ValueError:
            pass
        self.inner.write(data)

    def read(self, timeout):
        data = self.inner.read(timeout)
        for raw in self.reader.feed(data):
            try:
                frame = parse_response(raw)
                self.emit("RX", frame.seq, frame.cmd, frame.status, frame.payload.hex(" "), slip.encode(raw).hex(" "))
            except ValueError:
                self.emit("BAD", -1, -1, -1, raw.hex(" "), "CRC or frame validation failed")
        return data

    def reset_input(self):
        self.reader.reset()
        self.inner.reset_input()

    def close(self):
        self.inner.close()


class Worker(QObject):
    completed = Signal(str, object, str, str)
    progress = Signal(str, int, int)
    log = Signal(str, str)
    trace = Signal(str, int, int, int, str, str)
    targetStarted = Signal(str)

    def __init__(self):
        super().__init__()
        self.session = DeviceSession(self.log.emit, self.progress.emit,
                                     lambda transport: TraceTransport(transport, self.trace.emit))

    def connect_device(self, options):
        result = self.session.connect(options)
        return result

    @Slot(str, object)
    def dispatch(self, action, options):
        result, error, category = {}, "", ""
        try:
            if action == "shutdown":
                self.session.close()
                QThread.currentThread().quit()
                return
            if action == "connect":
                result = self.connect_device(options)
            elif action == "batch":
                self.session.close()
                jobs = []
                result = {"jobs": jobs, "disconnected": True}
                for profile in options["profiles"]:
                    self.session.check_cancelled()
                    self.targetStarted.emit(profile["name"])
                    self.log.emit("info", f"Batch target: {profile['name']}")
                    try:
                        self.connect_device(profile)
                        image_options = dict(options, run=options.get("run", False))
                        result = self.session.execute("flash", image_options)
                        jobs.append({"name": profile["name"], "success": True, "message": result["message"]})
                    except OperationCancelled:
                        raise
                    except Exception as exc:
                        jobs.append({"name": profile["name"], "success": False, "message": str(exc)})
                        self.log.emit("error", f"{profile['name']}: {exc}")
                    finally:
                        self.session.close()
                passed = sum(job["success"] for job in jobs)
                result = {"message": f"Batch complete: {passed}/{len(jobs)} targets verified.",
                          "jobs": jobs, "disconnected": True, "partial": passed != len(jobs)}
            else:
                # Fault injection needs the underlying simulator transport.
                if action == "fault" and self.session.client:
                    traced = self.session.client.transport
                    self.session.client.transport = getattr(traced, "inner", traced)
                    try:
                        result = self.session.execute(action, options)
                    finally:
                        self.session.client.transport = traced
                else:
                    result = self.session.execute(action, options)
        except OperationCancelled as exc:
            error, category = str(exc), "cancelled"
        except BootWireStatusError as exc:
            error, category = str(exc), "target"
        except (BootWireTimeout, serial.SerialException, OSError) as exc:
            error, category = str(exc), "connection" if action not in {"inspect"} else "file"
            if category == "connection":
                self.session.close()
        except Exception as exc:
            error, category = str(exc), "validation"
        if action == "batch" and error:
            self.session.close()
        self.completed.emit(action, result, error, category)


REFRESH_MS = 40
TRACE_LIMIT = 500


class TraceModel(QAbstractListModel):
    """Decoded frames for the inspector.

    Rows are inserted and trimmed in place, so the list keeps its scroll
    position while frames arrive. Each row is exposed to QML as ``modelData``.
    """
    countChanged = Signal()
    ROLE = Qt.ItemDataRole.UserRole + 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = []

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.items)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if role == self.ROLE and index.isValid() and 0 <= index.row() < len(self.items):
            return self.items[index.row()]
        return None

    def roleNames(self):
        return {self.ROLE: b"modelData"}

    @Property(int, notify=countChanged)
    def count(self):
        return len(self.items)

    def extend(self, rows):
        rows = rows[-TRACE_LIMIT:]
        if not rows:
            return
        first = len(self.items)
        self.beginInsertRows(QModelIndex(), first, first + len(rows) - 1)
        self.items.extend(rows)
        self.endInsertRows()
        extra = len(self.items) - TRACE_LIMIT
        if extra > 0:
            self.beginRemoveRows(QModelIndex(), 0, extra - 1)
            del self.items[:extra]
            self.endRemoveRows()
        self.countChanged.emit()

    def clear(self):
        self.beginResetModel()
        self.items = []
        self.endResetModel()
        self.countChanged.emit()


class Controller(QObject):
    changed = Signal()
    requested = Signal(str, object)

    def __init__(self, parent=None, settings=None):
        super().__init__(parent)
        self.settings = settings or QSettings("BootWire", "Desktop")
        cfg = load_config()
        self._state = {
            "busy": False, "connected": False, "device": {}, "image": {}, "ports": [],
            "status": "Ready to connect", "severity": "info", "progress": 0.0,
            "stage": "idle", "detail": "Connect a device or try the built-in simulator.",
            "completedStages": [], "batchTarget": "",
            "logs": [], "history": self._load("history", []),
            "profiles": self._load("profiles", []), "library": self._load("library", []),
            "theme": self.settings.value("theme", "light"),
            "preferences": self._load("preferences", {
                "port": cfg["serial"]["port"] or "sim", "baud": cfg["serial"]["baudrate"],
                "timeout": cfg["general"]["timeout"], "eraseTimeout": cfg["general"]["erase_timeout"],
                "retries": cfg["general"]["max_retries"],
            }), "reply": {}, "batchResults": [],
        }
        # Frames, log lines and progress can arrive thousands of times per second.
        # The state is updated at once; the UI is told at most once per interval.
        self._refresh = QTimer(self)
        self._refresh.setSingleShot(True)
        self._refresh.setInterval(REFRESH_MS)
        self._refresh.timeout.connect(self._flush)
        self._traces = TraceModel(self)
        self._pending_traces = []
        self._console = ConsoleService(self)
        self.thread = QThread(self)
        self.worker = Worker()
        self.worker.moveToThread(self.thread)
        self.requested.connect(self.worker.dispatch, Qt.ConnectionType.QueuedConnection)
        self.worker.completed.connect(self._completed)
        self.worker.progress.connect(self._progress)
        self.worker.log.connect(self._log)
        self.worker.trace.connect(self._trace)
        self.worker.targetStarted.connect(self._target_started)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.start()
        self._started = 0
        self._operation = ""
        self._closed = False
        self.refreshPorts()

    def _load(self, key, default):
        try:
            value = json.loads(self.settings.value(key, json.dumps(default)))
            return value if isinstance(value, type(default)) else default
        except (ValueError, TypeError):
            return default

    def _flush(self):
        """Hand buffered frames to the inspector, then refresh the UI."""
        self._refresh.stop()
        if self._pending_traces:
            rows, self._pending_traces = self._pending_traces, []
            self._traces.extend(rows)
        self.changed.emit()

    def _changed_soon(self):
        if not self._refresh.isActive():
            self._refresh.start()

    def _save(self, key):
        self.settings.setValue(key, json.dumps(self._state[key]))

    @Property("QVariantMap", notify=changed)
    def state(self):
        return self._state

    @Property(QObject, constant=True)
    def traces(self):
        return self._traces

    @Property(QObject, constant=True)
    def console(self):
        return self._console

    @Slot()
    def refreshPorts(self):
        try:
            self._state["ports"] = [{"port": "sim", "label": "Built-in simulator"}] + [
                {"port": p.device, "label": f"{p.device} · {p.description}"} for p in list_ports.comports()]
        except Exception as exc:
            self._log("error", f"Port discovery failed: {exc}")
        self.changed.emit()

    @Slot(str, "QVariantMap")
    def perform(self, action, options):
        if self._state["busy"] or self._closed:
            return
        if action not in {"connect", "disconnect", "inspect", "demo", "flash", "write", "verify", "erase", "run", "ping", "send", "raw_send", "fault", "reset_simulator", "batch"}:
            return
        if action == "batch":
            profiles = options.get("profiles", [])
            if not profiles:
                self.notify("Choose at least one device profile for the batch.", "error")
                return
        self.worker.session.cancelled.clear()
        self._started = time.monotonic()
        self._operation = action
        self._job_target = options.get("port", self._state["device"].get("port", "—"))
        if action == "send":
            self._state["reply"] = {}
        self._state.update(busy=True, status=f"{action.replace('_', ' ').capitalize()} in progress",
                           severity="info", stage=action, progress=0.0, completedStages=[], batchTarget="",
                           detail="Working in the background. You can keep exploring the workspace.")
        self._log("info", f"Started {action.replace('_', ' ')}.")
        self.requested.emit(action, dict(options))
        self.changed.emit()

    @Slot()
    def cancel(self):
        if self._state["busy"]:
            self.worker.session.cancelled.set()
            self.notify("Stopping after the current command…", "warning")

    @Slot(str, int, int)
    def _progress(self, stage, done, total):
        fraction = done / max(total, 1)
        if self._operation in {"flash", "batch"}:
            fraction = {"erase": 0, "write": .15, "verify": .9}.get(stage, 0) + fraction * {"erase": .15, "write": .75, "verify": .1}.get(stage, 1)
        if total > 0 and done >= total and stage not in self._state["completedStages"]:
            self._state["completedStages"] = self._state["completedStages"] + [stage]
        prefix = self._state["batchTarget"] + " · " if self._state["batchTarget"] else ""
        self._state.update(stage=stage, progress=fraction, detail=f"{prefix}{stage.capitalize()} · {done:,} / {total:,}")
        if done >= total:
            self._console.append_event('debug','device',self._state['detail'])
        self._changed_soon()

    @Slot(str)
    def _target_started(self, name):
        self._state.update(batchTarget=name, completedStages=[], progress=0.0,
                           detail=f"Connecting to batch target: {name}")
        self.changed.emit()

    @Slot(str, object, str, str)
    def _completed(self, action, result, error, category):
        self._state["busy"] = False
        if action == "connect" and not error:
            self._state.update(connected=True, device=result)
        if action in {"disconnect", "reset_simulator", "batch"} or result.get("disconnected") or category == "connection" or action == "connect":
            if action != "connect" or error:
                self._state.update(connected=False, device={})
        if action in {"inspect", "demo"} and not error:
            self._state["image"] = result
        if action == "send" and not error:
            self._state["reply"] = result
        if action == "batch":
            self._state["batchResults"] = result.get("jobs", [])
            if error or result.get("partial"):
                self._state["completedStages"] = []
        message = error or result.get("message") or {
            "connect": "Device connected. Ready for firmware and diagnostics.",
            "disconnect": "Disconnected.", "inspect": "Firmware image ready. Review its details before flashing.",
            "reset_simulator": "Simulator reset. Connect again to start a fresh session.",
        }.get(action, "Operation complete.")
        severity = "warning" if category == "cancelled" or result.get("partial") or result.get("unconfirmed") else "error" if error else "success"
        self._state.update(status="Stopped" if category == "cancelled" else "Operation failed" if error else "Ready",
                           detail=message, severity=severity, stage="idle",
                           progress=1 if not error and not result.get("partial") and action in {"flash", "write", "verify", "erase", "batch"} else 0)
        self._log(severity, message)
        if action not in {"inspect", "demo", "fault", "disconnect"}:
            item = {"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "action": action,
                    "target": "Batch" if action == "batch" else self._job_target,
                    "image": self._state["image"].get("name", "—"), "message": message,
                    "result": severity, "duration": f"{time.monotonic()-self._started:.2f} s"}
            self._state["history"] = [item] + self._state["history"][:99]
            self._save("history")
        self._console.completed(action,result,error,category)
        self._flush()

    @Slot(str, str)
    def _log(self, level, message):
        self._state["logs"] = self._state["logs"][-499:] + [{"time": datetime.now().strftime("%H:%M:%S"), "level": level, "message": message}]
        self._changed_soon()
        self._console.append_event(level,'device',message)

    @Slot(str, int, int, int, str, str)
    def _trace(self, direction, seq, cmd, status, payload, wire):
        decoded = cmd >= 0
        name = command_name(cmd) if decoded else "INVALID FRAME"
        self._pending_traces.append({
            "time": datetime.now().strftime("%H:%M:%S.%f")[:-3], "direction": direction,
            "seq": seq, "seqLabel": f"0x{seq:02X}" if decoded else "—",
            "command": f"0x{cmd:02X}" if decoded else "—", "name": name,
            "status": status, "statusName": status_name(status) if status >= 0 else "",
            "length": len(payload.split()) if decoded else 0,
            "payload": payload[:4096], "wire": wire[:8192],
        })
        self._changed_soon()
        summary = f"{direction} SEQ=0x{seq:02X} {name}" if decoded else f"{direction} {name}"
        if status >= 0:
            summary += ' STATUS='+status_name(status)
        self._console.append_event('debug','protocol',summary+'\nPAYLOAD '+(payload or '(empty)')+'\nWIRE '+wire)

    @Slot(str, str)
    def notify(self, message, severity="info"):
        self._state.update(detail=message, severity=severity)
        self.changed.emit()

    @Slot(str)
    def inspectUrl(self, url):
        qurl = QUrl(url)
        path = qurl.toLocalFile() if qurl.isLocalFile() else url
        self.perform("inspect", {"path": path})

    @Slot(str, str, bool)
    def loadRelease(self, path, checksum, simulator_only):
        self.perform("inspect", {"path": path, "sha256": checksum, "simulatorOnly": simulator_only})

    @Slot(str)
    def setTheme(self, theme):
        if theme in {"light", "dark"}:
            self._state["theme"] = theme
            self.settings.setValue("theme", theme)
            self.changed.emit()

    @Slot("QVariantMap")
    def savePreferences(self, options):
        self._state["preferences"] = dict(options)
        self._save("preferences")
        self.changed.emit()

    @Slot(str, "QVariantMap")
    def saveProfile(self, name, options):
        name = name.strip()
        if not name:
            self.notify("Give the device profile a name.", "error")
            return
        profile = dict(options, name=name)
        self._state["profiles"] = [p for p in self._state["profiles"] if p["name"] != name] + [profile]
        self._save("profiles")
        self.notify(f"Saved device profile: {name}", "success")

    @Slot(str)
    def removeProfile(self, name):
        self._state["profiles"] = [p for p in self._state["profiles"] if p["name"] != name]
        self._save("profiles")
        self.changed.emit()

    @Slot(str, str)
    def addRelease(self, version, notes):
        image = self._state["image"]
        if not image or not version.strip():
            self.notify("Choose a firmware image and enter a version label first.", "error")
            return
        item = dict(image, version=version.strip(), notes=notes.strip())
        self._state["library"] = [p for p in self._state["library"] if p["sha256"] != item["sha256"]] + [item]
        self._save("library")
        self.notify("Firmware added to the local library. Its checksum will be checked before flashing.", "success")

    @Slot(str)
    def removeRelease(self, checksum):
        self._state["library"] = [p for p in self._state["library"] if p["sha256"] != checksum]
        self._save("library")
        self.changed.emit()

    @Slot(str)
    def clear(self, kind):
        if kind == "traces":
            self._pending_traces = []
            self._traces.clear()
        elif kind in {"logs", "history"}:
            self._state[kind] = []
            if kind == "history": self._save(kind)
            self.changed.emit()

    @Slot(str, str)
    def export(self, url, kind):
        if kind not in {"logs", "traces", "history", "library", "profiles"}:
            return
        try:
            path = QUrl(url).toLocalFile()
            data = self._traces.items if kind == "traces" else self._state[kind]
            Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")
            self.notify(f"Exported {kind} to {path}", "success")
        except (OSError, ValueError) as exc:
            self.notify(f"Could not export: {exc}", "error")

    @Slot()
    def shutdown(self):
        if self._closed:
            return
        self._closed = True
        self._console.shutdown()
        self.worker.session.cancelled.set()
        self.requested.emit("shutdown", {})
        # Normal window closing is allowed only when idle. Tests also use this method.
        if not self.thread.wait(5000):
            self.thread.wait()
