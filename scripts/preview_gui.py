"""Capture the real Qt Quick UI offscreen, including populated simulator states.

Run from desktop/:
    QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python ../scripts/preview_gui.py
"""
from pathlib import Path
import tempfile
import time

from PySide6.QtCore import QSettings, QUrl, QObject, QPointF, Qt, QMetaObject
from PySide6.QtTest import QTest
from bootwire_gui.branding import application_icon
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from bootwire_gui.controller import Controller

root = Path(__file__).resolve().parents[1]
out = root / '.impeccable/review'
out.mkdir(parents=True, exist_ok=True)
QQuickStyle.setStyle('Basic')
app = QGuiApplication([])
app.setWindowIcon(application_icon())
settings = QSettings(str(Path(tempfile.mkdtemp(prefix='bootwire-preview-'))/'settings.ini'), QSettings.IniFormat)
c = Controller(settings=settings)
engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty('backend', c)
engine.load(QUrl.fromLocalFile(str(root/'desktop/src/bootwire_gui/qml/Main.qml')))
assert engine.rootObjects(), 'QML failed to load'
window = engine.rootObjects()[0]

def settle():
    for _ in range(24):
        app.processEvents()
        time.sleep(.015)

def operation(action, options):
    c.perform(action, options)
    deadline = time.monotonic() + 10
    while c.state['busy'] and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.005)
    assert not c.state['busy'], action
    assert c.state['severity'] != 'error', c.state['detail']

# Check compact icon-only actions against their actual button centers.
for name in ['preferencesButton', 'refreshPortsButton']:
    button = window.findChild(QObject, name)
    glyph = button.findChild(QObject, 'centeredGlyph')
    settle()
    actual = glyph.mapToScene(QPointF(glyph.width()/2, glyph.height()/2))
    expected = button.mapToScene(QPointF(button.width()/2, button.height()/2))
    assert abs(actual.x()-expected.x()) < .1 and abs(actual.y()-expected.y()) < .1, name
operation('connect', {'port':'sim', 'timeout':.1, 'eraseTimeout':.1})
operation('demo', {})
operation('flash', c.state['image'])
c.saveProfile('Development bench', {'port':'sim','baud':115200,'timeout':.5,'eraseTimeout':5,'retries':3})
c.addRelease('0.1.0-demo', 'Simulator demonstration. Not firmware for a physical board.')
for theme in ['light','dark']:
    c.setTheme(theme)
    for page in range(7):
        window.setProperty('page',page)
        window.setWidth(1380);window.setHeight(900)
        settle()
        assert window.grabWindow().save(str(out/f'{theme}-{page}.png'))
window.setProperty('page',0)
window.setWidth(1000);window.setHeight(720)
settle()
window.grabWindow().save(str(out/'compact.png'))
# Popup evidence uses the actual controls and their real interactive state.
window.setWidth(1380); window.setHeight(900); window.setProperty('page',0)
operation('disconnect', {})
def click_control(name, arrow=False):
    item = window.findChild(QObject,name)
    assert item, name
    point = item.mapToScene(QPointF(item.width()-16 if arrow else item.width()/2, item.height()/2)).toPoint()
    QTest.mouseClick(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, point)
    settle()
for theme in ['light','dark']:
    c.setTheme(theme);settle()
    for name, label in [('portField','ports'),('baudField','baud'),('fileMenuButton','file-menu'),('toolsMenuButton','tools-menu')]:
        click_control(name, name in ['portField','baudField'])
        window.grabWindow().save(str(out/f'{theme}-{label}.png'))
        QTest.keyClick(window,Qt.Key.Key_Escape);settle()
    baud = window.findChild(QObject, 'baudField')
    baud.setProperty('model', [str(9600 * (i + 1)) for i in range(30)])
    click_control('baudField', True)
    window.grabWindow().save(str(out/f'{theme}-scrolling-dropdown.png'))
    QTest.keyClick(window, Qt.Key.Key_Escape); settle()
    baud.setProperty('model', ['9600','57600','115200','230400','460800','921600'])
    item=window.findChild(QObject,'aboutMenuItem')
    QMetaObject.invokeMethod(item,'triggered');settle()
    window.grabWindow().save(str(out/f'{theme}-about.png'))
    QMetaObject.invokeMethod(window.findChild(QObject,'aboutDialog'),'close');settle()
c.setTheme('light'); window.setProperty('page',6); window.setHeight(1200); settle()
window.grabWindow().save(str(out/'shortcut-alignment.png'))
window.setProperty('page',0); window.setHeight(900); settle()
click_control('themeButton')
QTest.mouseMove(window, QPointF(650,180).toPoint()); settle()
window.grabWindow().save(str(out/'icon-mouse-focus.png'))
click_control('preferencesButton')
QTest.keyClick(window, Qt.Key.Key_Tab, Qt.KeyboardModifier.ShiftModifier); settle()
window.grabWindow().save(str(out/'icon-keyboard-focus.png'))
c.shutdown()
window.close()
del engine
print(f'Captured 30 desktop and popup states under {out}')
