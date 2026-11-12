"""PTY helper process. No Qt is imported and no fork occurs in the GUI process.

Stdin/stdout carry JSON lines; the shell itself always receives a real PTY.
"""
from __future__ import annotations

import codecs
import json
import os
import queue
import signal
import subprocess
import sys
import threading


def main():
    config = json.loads(sys.argv[1])
    lock = threading.Lock()
    stop = threading.Event()
    commands = queue.Queue()
    proc = None

    def emit(kind, **values):
        with lock:
            print(json.dumps(dict(event=kind, **values), ensure_ascii=True), flush=True)

    def read_commands():
        try:
            for line in sys.stdin:
                try:
                    commands.put(json.loads(line))
                except ValueError:
                    pass
        finally:
            stop.set()

    def read_output():
        decoder = codecs.getincrementaldecoder('utf-8')('replace')
        try:
            while not stop.is_set():
                data = proc.read(4096)
                if not data:
                    continue
                text = decoder.decode(data) if isinstance(data, bytes) else data
                if text:
                    emit('data', text=text)
        except (EOFError, OSError):
            pass
        finally:
            tail = decoder.decode(b'', final=True)
            if tail:
                emit('data', text=tail)
            stop.set()

    def cleanup():
        if proc is None:
            return
        if os.name == 'nt':
            try:
                if proc.isalive():
                    subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   timeout=3, creationflags=subprocess.CREATE_NO_WINDOW)
            except (OSError, subprocess.TimeoutExpired):
                pass
        else:
            # A foreground job can have a different process group from its shell.
            try:
                foreground = os.tcgetpgrp(proc.fd)
                if foreground > 0:
                    os.killpg(foreground, signal.SIGHUP)
            except (OSError, ProcessLookupError):
                pass
            try:
                os.killpg(proc.pid, signal.SIGHUP)
            except (OSError, ProcessLookupError):
                pass
        try:
            proc.close(force=True)
        except (OSError, EOFError):
            pass

    signal.signal(signal.SIGTERM, lambda *args: stop.set())
    try:
        if os.name == 'nt':
            from winpty import PtyProcess
        else:
            from ptyprocess import PtyProcess
        env = dict(os.environ, TERM='xterm-256color', COLORTERM='truecolor')
        proc = PtyProcess.spawn(config['argv'], cwd=config['cwd'], env=env,
                                dimensions=(config['rows'], config['columns']))
        emit('ready', pid=proc.pid)
        threading.Thread(target=read_commands, daemon=True).start()
        threading.Thread(target=read_output, daemon=True).start()
        while not stop.is_set():
            try:
                command = commands.get(timeout=.05)
            except queue.Empty:
                continue
            kind = command.get('type')
            if kind == 'stop':
                stop.set()
            elif kind == 'resize':
                proc.setwinsize(command['rows'], command['columns'])
            elif kind == 'input':
                data = command['text']
                data = data if os.name == 'nt' else data.encode('utf-8')
                # POSIX writes can be partial; do not silently truncate a paste.
                while data:
                    count = proc.write(data)
                    if not count:
                        raise OSError('The terminal input channel closed.')
                    data = data[count:]
        emit('exit', code=None)
        return 0
    except Exception as exc:
        emit('error', message=str(exc))
        return 1
    finally:
        cleanup()


if __name__ == '__main__':
    raise SystemExit(main())
