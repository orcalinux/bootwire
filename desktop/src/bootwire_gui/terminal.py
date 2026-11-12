"""Asynchronous PTY/ConPTY shell sessions and a bounded ANSI terminal screen."""
from __future__ import annotations

import html
import json
import os
import shutil
import sys
from pathlib import Path

from PySide6.QtCore import QObject, Property, QProcess, QProcessEnvironment, QTimer, Signal, Slot
from PySide6.QtGui import QGuiApplication


ANSI = {'black':'#243447', 'red':'#F27887', 'green':'#7BD6AE', 'brown':'#E8C878',
        'blue':'#7EB5FF', 'magenta':'#D2A2F7', 'cyan':'#78D3DF', 'white':'#E7EDF7',
        'brightblack':'#91A2B7', 'brightred':'#FF9DA7', 'brightgreen':'#A2E8BD',
        'brightbrown':'#F9DF9F', 'brightblue':'#A8CFFF', 'brightmagenta':'#E5C1FF',
        'brightcyan':'#A0EAF1', 'brightwhite':'#FFFFFF'}


def shell_profiles(platform=None, which=None, environ=None):
    platform = platform or os.name
    which = which or shutil.which
    environ = os.environ if environ is None else environ
    result = []
    if platform == 'nt':
        for name, label, args in [('pwsh','PowerShell', ['-NoLogo']),
                                  ('powershell','Windows PowerShell', ['-NoLogo']),
                                  ('cmd','Command Prompt', [])]:
            executable = which(name)
            if executable:
                result.append({'id':name, 'label':label, 'argv':[executable]+args})
    else:
        default_shell = environ.get('SHELL','')
        default_label = Path(default_shell).name.capitalize()+' (default)' if default_shell else 'Default shell'
        candidates = [(default_shell, default_label), ('bash','Bash'), ('zsh','Zsh'), ('fish','Fish'), ('sh','POSIX shell')]
        seen = set()
        for name, label in candidates:
            executable = which(name) if name else None
            if executable and executable not in seen:
                seen.add(executable)
                result.append({'id':name, 'label':label, 'argv':[executable,'-i']})
    return result


def color(value, default):
    if value == 'default':
        return default
    if value in ANSI:
        return ANSI[value]
    if len(value) == 6 and all(c in '0123456789abcdefABCDEF' for c in value):
        return '#' + value
    return default


class TerminalService(QObject):
    changed = Signal()
    output = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = {'running':False, 'starting':False, 'shells':shell_profiles(),
                       'shell':'', 'cwd':str(Path.cwd()), 'html':'', 'text':'',
                       'message':'Start a local shell. Commands run on this computer.', 'pid':0}
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        self.process.readyReadStandardOutput.connect(self._read)
        self.process.readyReadStandardError.connect(self._error_output)
        self.process.finished.connect(self._finished)
        self.process.errorOccurred.connect(self._process_error)
        self._buffer = b''
        self._screen = None
        self._stream = None
        self._rows, self._columns = 16, 100
        self.render_timer = QTimer(self)
        self.render_timer.setSingleShot(True)
        self.render_timer.setInterval(40)
        self.render_timer.timeout.connect(self._render)
        self.stop_timer = QTimer(self)
        self.stop_timer.setSingleShot(True)
        self.stop_timer.setInterval(4000)
        self.stop_timer.timeout.connect(self.process.kill)

    @Property('QVariantMap', notify=changed)
    def state(self):
        return self._state

    def _new_screen(self):
        import pyte
        service = self
        class Screen(pyte.HistoryScreen):
            def write_process_input(self, data):
                service._send({'type':'input', 'text':data})
        self._screen = Screen(self._columns, self._rows, history=1000)
        self._stream = pyte.Stream(self._screen)

    @Slot(str, str)
    def start(self, shell_id='', cwd=''):
        if self.process.state() != QProcess.ProcessState.NotRunning:
            return
        try:
            self._new_screen()
            profiles = self._state['shells']
            profile = next((p for p in profiles if p['id'] == shell_id), None) if shell_id else (profiles[0] if profiles else None)
            if not profile:
                raise ValueError('This shell is unavailable. Choose an installed shell.')
            directory = Path(cwd or self._state['cwd']).expanduser().resolve()
            if not directory.is_dir():
                raise ValueError('Working directory does not exist.')
            config = {'argv':profile['argv'], 'cwd':str(directory), 'rows':self._rows,'columns':self._columns}
            self._buffer = b''
            env = QProcessEnvironment.systemEnvironment()
            env.insert('PATH', str(Path(sys.executable).parent)+os.pathsep+os.environ.get('PATH',''))
            env.insert('PYTHONIOENCODING','utf-8')
            self.process.setProcessEnvironment(env)
            self.process.setWorkingDirectory(str(directory))
            self.process.setProgram(sys.executable)
            self.process.setArguments(['-u','-m','bootwire_gui.terminal_host',json.dumps(config)])
            self._state.update(starting=True, running=False, html='', text='', pid=0,
                               shell=profile['label'], cwd=str(directory), message='Starting '+profile['label']+'…')
            self.process.start()
        except Exception as exc:
            self._state.update(message=str(exc), starting=False, running=False)
        self.changed.emit()

    def _send(self, data):
        if self.process.state() == QProcess.ProcessState.Running:
            self.process.write((json.dumps(data)+'\n').encode('utf-8'))

    @Slot(str)
    def write(self, data):
        if self._state['running']:
            self._send({'type':'input','text':data})

    @Slot()
    def interrupt(self):
        self.write('\x03')

    @Slot()
    def paste(self):
        data = QGuiApplication.clipboard().text()
        if self._screen and (2004 << 5) in self._screen.mode:
            data = '\x1b[200~' + data + '\x1b[201~'
        self.write(data)

    @Slot(str)
    def copy(self, text):
        QGuiApplication.clipboard().setText(text.replace('\u2029','\n'))

    @Slot(int, int)
    def resize(self, columns, rows):
        columns, rows = max(30,min(300,columns)), max(4,min(100,rows))
        if (columns, rows) == (self._columns, self._rows):
            return
        self._columns, self._rows = columns, rows
        if self._screen:
            self._screen.resize(lines=rows, columns=columns)
            self._send({'type':'resize','rows':rows,'columns':columns})
            self._schedule_render()

    @Slot()
    def clear(self):
        if self._screen:
            self._screen.reset()
            self._render()
        # Redraw a shell prompt without starting another shell.
        self.write('\x0c')

    @Slot()
    def stop(self):
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self._send({'type':'stop'})
            self.stop_timer.start()

    def _schedule_render(self):
        if not self.render_timer.isActive():
            self.render_timer.start()

    def _read(self):
        self._buffer += bytes(self.process.readAllStandardOutput())
        while b'\n' in self._buffer:
            raw, self._buffer = self._buffer.split(b'\n',1)
            try:
                packet = json.loads(raw)
            except (ValueError, UnicodeDecodeError):
                continue
            event = packet.get('event')
            if event == 'data' and self._stream:
                self._stream.feed(packet['text'])
                self.output.emit(packet['text'])
                self._schedule_render()
            elif event == 'ready':
                self._state.update(running=True,starting=False,pid=packet['pid'],message='Local shell · '+self._state['shell'])
                self.changed.emit()
            elif event == 'error':
                self._state.update(message=packet['message'],running=False,starting=False)
                self.changed.emit()
            elif event == 'exit':
                self._state.update(message='Shell exited. Start a new session to continue.')
                self.changed.emit()

    def _error_output(self):
        text = bytes(self.process.readAllStandardError()).decode('utf-8','replace')
        if text.strip():
            self._state['message'] = text.strip()[-2000:]
            self.changed.emit()

    def _process_error(self, error):
        self._state.update(message=self.process.errorString(),running=False,starting=False)
        self.changed.emit()

    def _finished(self, code, status):
        self.stop_timer.stop()
        self._read()
        self._state.update(running=False,starting=False,pid=0)
        self._render()
        self.changed.emit()

    def _render(self):
        if not self._screen:
            return
        screen = self._screen
        rows = list(screen.history.top) + [screen.buffer[y] for y in range(screen.lines)]
        output, text_lines = [], []
        history_count = len(screen.history.top)
        for y, row in enumerate(rows):
            parts, plain, run = [], [], []
            previous = None
            def flush_run(key):
                if not run:
                    return
                fg, bg, bold, italic, underline = key
                style = f'color:{fg};background-color:{bg};'
                if bold: style += 'font-weight:600;'
                if italic: style += 'font-style:italic;'
                if underline: style += 'text-decoration:underline;'
                parts.append(f'<span style="{style}">{html.escape("".join(run))}</span>')
                run.clear()
            for x in range(screen.columns):
                cell = row[x]
                char = cell.data
                if not char:
                    continue
                fg, bg = color(cell.fg, '#E7EDF7'), color(cell.bg, '#111E2C')
                if cell.reverse:
                    fg, bg = bg, fg
                cursor = self._state['running'] and not screen.cursor.hidden and y == history_count + screen.cursor.y and x == screen.cursor.x
                if cursor:
                    fg, bg = '#111E2C', '#A8CFFF'
                key = (fg, bg, cell.bold, cell.italics, cell.underscore)
                if previous is not None and key != previous:
                    flush_run(previous)
                previous = key
                run.append(char)
                plain.append(char)
            if previous is not None:
                flush_run(previous)
            output.append(''.join(parts))
            text_lines.append(''.join(plain).rstrip())
        self._state.update(html='<pre style="margin:0;font-family:DejaVu Sans Mono;font-size:13px;">'+'\n'.join(output)+'</pre>', text='\n'.join(text_lines))
        self.changed.emit()

    def shutdown(self):
        self.render_timer.stop()
        if self.process.state() == QProcess.ProcessState.NotRunning:
            return
        self.stop()
        if not self.process.waitForFinished(5000):
            self.process.kill()
            self.process.waitForFinished(1000)
