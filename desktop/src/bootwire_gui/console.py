"""Developer panel state, verbose events, and shared-session command execution."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot
from bootwire_gui.commands import parse_command, HELP
from bootwire_gui.terminal import TerminalService


class ConsoleService(QObject):
    changed = Signal()
    confirmationRequested = Signal()
    connectionOptionsChanged = Signal('QVariantMap')

    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self._terminal = TerminalService(self)
        self._state = {'entries':[], 'commands':[], 'pending':{}, 'executing':False, 'generation':0}
        self._next_id = 0
        self._plan = None
        self._phase = ''
        # Protocol events arrive per frame; coalesce their notifications.
        self._refresh = QTimer(self)
        self._refresh.setSingleShot(True)
        self._refresh.setInterval(40)
        self._refresh.timeout.connect(self.changed.emit)
        self.append_event('info','console','BootWire console ready. Type help for commands. The System terminal runs a separate local shell.')

    @Property('QVariantMap', notify=changed)
    def state(self):
        return self._state

    @Property(QObject, constant=True)
    def terminal(self):
        return self._terminal

    def append_event(self, level, source, message):
        message = str(message)
        self._next_id += 1
        # 'id' only grows, so the panel can append new rows instead of rebuilding its list.
        self._state['entries'] = self._state['entries'][-1999:] + [{
            'id':self._next_id, 'time':datetime.now().strftime('%H:%M:%S.%f')[:-3], 'level':level,
            'source':source, 'message':message[:12000]+('… [truncated]' if len(message)>12000 else ''),
        }]
        if level == 'debug':
            if not self._refresh.isActive():
                self._refresh.start()
        else:
            self._refresh.stop()
            self.changed.emit()

    def _end(self):
        self._plan = None
        self._phase = ''
        self._state.update(executing=False,pending={})
        self.changed.emit()

    @Slot(str, 'QVariantMap')
    def submit(self, line, defaults):
        line = line.strip()
        if not line:
            return
        self.append_event('input','command','> '+line)
        history = self._state['commands']
        if not history or history[-1] != line:
            self._state['commands'] = (history+[line])[-100:]
        try:
            plan = parse_command(line, defaults)
            if plan.action == 'help':
                self.append_event('result','command',HELP)
                return
            if plan.action == 'clear':
                self._state['entries'] = []
                self._state['generation'] += 1
                self.changed.emit()
                return
            if plan.action == 'cancel':
                self.owner.cancel()
                return
            if self._state['executing'] or self.owner.state['busy'] or self._state['pending']:
                raise ValueError('Device work or a confirmation is pending. Finish it or use cancel first.')
            if plan.action in {'flash','write','verify'}:
                plan.options['path'] = str(Path(plan.options['path']).expanduser().resolve())
                image = self.owner.state['image']
                if image.get('path') == plan.options['path']:
                    plan.options['simulatorOnly'] = image.get('simulatorOnly',False)
            self._plan = plan
            self._state['executing'] = True
            local = {'disconnect','demo','reset_simulator'}
            if plan.action in {'connect','info'} or (plan.action not in local and (not self.owner.state['connected'] or plan.reconnect)):
                self._phase = 'connecting'
                self.connectionOptionsChanged.emit(plan.connection)
                self.owner.perform('connect', plan.connection)
            else:
                self._advance()
        except Exception as exc:
            self.append_event('error','command',str(exc))
            if not self.owner.state['busy']:
                self._end()
        self.changed.emit()

    def _advance(self):
        plan = self._plan
        if plan.action in {'connect','info'}:
            self.append_event('result','command',json.dumps(self.owner.state['device'],indent=2))
            self._end()
            return
        if plan.action in {'flash','write','verify'} and self._phase != 'inspected':
            self._phase = 'inspecting'
            self.owner.perform('inspect', plan.options)
            return
        if plan.review:
            description = {
                'flash':'Erase the touched application blocks, write the image, and verify it.',
                'write':'Write into previously erased application flash, then verify.',
                'erase':'Erase application flash in the requested region.',
                'run':'Start the target application and close the bootloader connection.',
                'raw_send':'Send a raw command that can alter flash or start the application.',
            }[plan.action]
            if plan.action == 'flash' and plan.options.get('run'):
                description += ' The application will start after verification.'
            details = json.dumps(plan.options,indent=2)
            self._state.update(executing=False,pending={'summary':description, 'details':details,
                                  'target':self.owner.state['device'].get('port','Disconnected')})
            self.confirmationRequested.emit()
            self.changed.emit()
        else:
            self._execute()

    def _execute(self):
        self._phase = 'executing'
        self._state.update(executing=True,pending={})
        self.owner.perform(self._plan.action,self._plan.options)
        self.changed.emit()

    @Slot()
    def confirm(self):
        if self._plan and self._state['pending'] and not self.owner.state['busy']:
            if self.owner.state['device'].get('port') != self._state['pending']['target']:
                self.append_event('error','command','Target changed. Enter the command again to review it.')
                self._end()
                return
            self._execute()

    @Slot()
    def reject(self):
        if self._state['pending']:
            self.append_event('warning','command','Command cancelled before execution.')
            self._end()

    def completed(self, action, result, error, category):
        if not self._plan:
            return
        if error:
            self.append_event('error','command',error)
            self._end()
            return
        if self._phase == 'connecting' and action == 'connect':
            self._advance()
        elif self._phase == 'inspecting' and action == 'inspect':
            self._plan.options.update(path=result['path'],sha256=result['sha256'],simulatorOnly=result.get('simulatorOnly',False))
            self._phase = 'inspected'
            self._advance()
        elif self._phase == 'executing':
            self.append_event('result','command',json.dumps(result,indent=2,ensure_ascii=False) if result else 'OK')
            self._end()

    @Slot(str)
    def clear(self, source):
        if source == 'all':
            self._state['entries'] = []
        elif source == 'command':
            self._state['entries'] = [e for e in self._state['entries'] if e['source'] != 'command']
        else:
            self._state['entries'] = [e for e in self._state['entries'] if e['source'] == 'command']
        self._state['generation'] += 1  # rows were removed: the panel rebuilds its list
        self.changed.emit()

    @Slot(str)
    def export(self, url):
        from PySide6.QtCore import QUrl
        try:
            Path(QUrl(url).toLocalFile()).write_text(json.dumps(self._state['entries'],indent=2),encoding='utf-8')
            self.append_event('info','console','Developer output exported.')
        except (OSError,ValueError) as exc:
            self.append_event('error','console',str(exc))

    def shutdown(self):
        self._terminal.shutdown()
