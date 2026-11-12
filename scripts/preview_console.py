"""Capture populated developer-panel tabs using an isolated simulator and a local PTY."""
import os
from pathlib import Path
import tempfile
import time
from PySide6.QtCore import QSettings,QUrl,QObject
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from bootwire_gui.controller import Controller
from bootwire_gui.branding import application_icon

root=Path(__file__).resolve().parents[1]
out=root/'.impeccable/review'
out.mkdir(parents=True,exist_ok=True)
QQuickStyle.setStyle('Basic');app=QGuiApplication([]);app.setWindowIcon(application_icon())
c=Controller(settings=QSettings(str(Path(tempfile.mkdtemp())/'console.ini'),QSettings.IniFormat))
e=QQmlApplicationEngine();warnings=[]
e.warnings.connect(lambda items:warnings.extend(w.toString() for w in items))
e.rootContext().setContextProperty('backend',c)
e.load(QUrl.fromLocalFile(str(root/'desktop/src/bootwire_gui/qml/Main.qml')))
assert e.rootObjects(),warnings
w=e.rootObjects()[0];panel=w.findChild(QObject,'developerPanel')

def wait(predicate):
    deadline=time.monotonic()+10
    while not predicate() and time.monotonic()<deadline:
        app.processEvents();time.sleep(.01)
    assert predicate(), (c.state['detail'],c.console.terminal.state['message'])

def settle():
    for _ in range(24):app.processEvents();time.sleep(.01)

options={'port':'sim','baud':115200,'timeout':.1,'eraseTimeout':.1,'retries':2}
c.console.submit('bootwire -p sim info',options)
wait(lambda:not c.state['busy'] and not c.console.state['executing'])
c.console.submit('ping -n 3 -d "C0 DB" --hex',options)
wait(lambda:not c.state['busy'] and not c.console.state['executing'])
panel.setProperty('expanded',True);panel.setProperty('panelHeight',340)
for theme in ['light','dark']:
    c.setTheme(theme)
    for tab,label in [(0,'verbose-output'),(1,'bootwire-console')]:
        panel.setProperty('tab',tab);settle()
        w.grabWindow().save(str(out/f'{theme}-{label}.png'))
panel.setProperty('tab',2);settle()
terminal=c.console.terminal
terminal.start('',str(root))
wait(lambda:terminal.state['running'])
command = "printf '\\033[32mBootWire local terminal ready\\033[0m\\n'; pwd" if os.name!='nt' else "Write-Output 'BootWire local terminal ready'; Get-Location"
terminal.write(command+'\r')
wait(lambda:'BootWire local terminal ready' in terminal.state['text'])
for theme in ['light','dark']:
    c.setTheme(theme);settle()
    w.grabWindow().save(str(out/f'{theme}-system-terminal.png'))
w.setWidth(1000);w.setHeight(720);settle()
w.grabWindow().save(str(out/'compact-system-terminal.png'))
assert not warnings,warnings
c.shutdown();w.close();del e
print('Captured developer output, BootWire console, and real local terminal in both themes.')
