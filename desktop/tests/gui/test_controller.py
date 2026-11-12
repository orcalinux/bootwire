"""Optional Qt integration checks, including the actual QML engine."""
import json
import os
import time
from pathlib import Path

import pytest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_QUICK_BACKEND', 'software')
pytest.importorskip('PySide6')
from PySide6.QtCore import QSettings, QUrl, QCoreApplication
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from bootwire_gui.controller import Controller


@pytest.fixture(scope='module')
def app():
    QQuickStyle.setStyle('Basic')
    app = QGuiApplication.instance() or QGuiApplication([])
    return app


@pytest.fixture
def controller(app, tmp_path):
    c = Controller(settings=QSettings(str(tmp_path/'settings.ini'), QSettings.IniFormat))
    yield c
    c.shutdown()


def wait_for(app, predicate, timeout=5):
    end = time.monotonic() + timeout
    while not predicate() and time.monotonic() < end:
        app.processEvents()
        time.sleep(.002)
    assert predicate(), 'Qt operation did not finish'


def run(app, c, action, options):
    c.perform(action, options)
    wait_for(app, lambda: not c.state['busy'])


def connect(app, c):
    run(app, c, 'connect', {'port':'sim', 'timeout':.05, 'eraseTimeout':.05, 'retries':1})
    assert c.state['connected']


def test_controller_flash_trace_and_persistence(app, controller, tmp_path):
    c = controller
    connect(app,c)
    run(app,c,'demo',{})
    image = c.state['image']
    c.addRelease('1.0.0','Demo build')
    c.saveProfile('Bench',{'port':'sim','baud':115200})
    run(app,c,'flash',dict(image,run=False))
    assert c.state['severity'] == 'success'
    assert any(frame['direction']=='TX' for frame in c.traces.items)
    assert any(frame['direction']=='RX' for frame in c.traces.items)
    assert c.state['history'][0]['action']=='flash'
    c.export(QUrl.fromLocalFile(str(tmp_path/'history.json')).toString(),'history')
    assert json.loads((tmp_path/'history.json').read_text())[0]['action']=='flash'
    assert c._load('library',[])[0]['version']=='1.0.0'
    assert c._load('profiles',[])[0]['name']=='Bench'


def test_target_error_preserves_session(app,controller):
    connect(app,controller)
    run(app,controller,'send',{'command':'0x40'})
    assert controller.state['severity']=='error'
    assert controller.state['connected']


def test_double_submission_is_ignored(app,controller):
    controller.perform('connect',{'port':'sim'})
    controller.perform('disconnect',{})
    wait_for(app,lambda:not controller.state['busy'])
    assert controller.state['connected']


def test_batch_records_partial_failure(app,controller):
    run(app,controller,'demo',{})
    options=dict(controller.state['image'],profiles=[{'name':'Bench','port':'sim'}, {'name':'Invalid','port':''}])
    run(app,controller,'batch',options)
    assert not controller.state['connected']
    assert controller.state['severity']=='warning'
    assert [j['success'] for j in controller.state['batchResults']]==[True,False]


def test_run_timeout_is_not_false_success(app,controller):
    connect(app,controller)
    run(app,controller,'demo',{})
    run(app,controller,'flash',controller.state['image'])
    run(app,controller,'fault',{'kind':'drop_responses'})
    run(app,controller,'run',{})
    assert not controller.state['connected']
    assert 'without confirmation' in controller.state['detail']


def test_qml_loads_and_renders_all_workspaces(app,controller):
    engine=QQmlApplicationEngine()
    warnings=[]
    engine.warnings.connect(lambda items:warnings.extend(item.toString() for item in items))
    engine.rootContext().setContextProperty('backend',controller)
    qml=Path(__file__).parents[2]/'src/bootwire_gui/qml/Main.qml'
    engine.load(QUrl.fromLocalFile(str(qml)))
    assert engine.rootObjects(), warnings
    window=engine.rootObjects()[0]
    for width,height in [(1380,900),(1000,720)]:
        window.setWidth(width);window.setHeight(height)
        for page in range(7):
            window.setProperty('page',page)
            for _ in range(3):app.processEvents()
            assert not window.grabWindow().isNull()
    assert not warnings, warnings
    window.close()
    engine.deleteLater()
    QCoreApplication.sendPostedEvents(None,0)
    app.processEvents()


def test_real_qml_connect_flash_confirmation_and_dark_theme(app, controller):
    from PySide6.QtCore import QObject, QPointF, Qt, QMetaObject
    from PySide6.QtTest import QTest
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty('backend', controller)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parents[2]/'src/bootwire_gui/qml/Main.qml')))
    window = engine.rootObjects()[0]
    app.processEvents()
    def click(name):
        item = window.findChild(QObject, name)
        assert item and item.property('enabled'), name
        point = item.mapToScene(QPointF(item.width()/2, item.height()/2)).toPoint()
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, point)
        app.processEvents()
    click('connectButton')
    wait_for(app, lambda: not controller.state['busy'])
    assert controller.state['connected']
    run(app, controller, 'demo', {})
    app.processEvents()
    click('flashButton')
    dialog = window.findChild(QObject, 'confirmDialog')
    assert dialog.property('visible')
    assert not controller.state['busy'] # Opening the confirmation must not erase anything.
    QMetaObject.invokeMethod(dialog, 'accept')
    wait_for(app, lambda: not controller.state['busy'])
    assert controller.state['history'][0]['action'] == 'flash'
    assert controller.state['severity'] == 'success'
    controller.setTheme('dark')
    app.processEvents()
    assert window.color().name() == '#101923'
    controller.setTheme('light')
    app.processEvents()
    assert window.color().name() == '#f3f5f8'
    window.close()
    engine.deleteLater()
    QCoreApplication.sendPostedEvents(None, 0)
    app.processEvents()


def test_phase_state_distinguishes_erase_verify_and_partial_batch(app, controller):
    connect(app, controller)
    run(app, controller, 'demo', {})
    run(app, controller, 'flash', controller.state['image'])
    assert controller.state['completedStages'] == ['erase', 'write', 'verify']
    run(app, controller, 'verify', controller.state['image'])
    assert controller.state['completedStages'] == ['verify']
    run(app, controller, 'erase', {'length':'0x800'})
    assert controller.state['completedStages'] == ['erase']
    options=dict(controller.state['image'], profiles=[{'name':'Works','port':'sim'}, {'name':'Fails','port':''}])
    run(app,controller,'batch',options)
    assert controller.state['completedStages'] == []
    assert controller.state['progress'] == 0


def test_qml_profile_fields_match_actual_connection(app, controller):
    from PySide6.QtCore import Q_ARG, QMetaObject, QObject
    restored = {'port':'sim', 'baud':250000, 'timeout':1.5, 'eraseTimeout':7, 'retries':2}
    controller.savePreferences(restored)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty('backend', controller)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parents[2]/'src/bootwire_gui/qml/Main.qml')))
    window = engine.rootObjects()[0]
    baud = window.findChild(QObject, 'baudField')
    assert baud.property('editText') == '250000'
    profile = dict(restored, baud=256000)
    assert QMetaObject.invokeMethod(window, 'applyConnection', Q_ARG('QVariant', profile))
    app.processEvents()
    baud = window.findChild(QObject, 'baudField')
    assert baud.property('editText') == '256000'
    # Exercise the same options getter used by Connect, Save Profile, and Preferences.
    from PySide6.QtQml import QQmlExpression
    value = QQmlExpression(engine.rootContext(), window, 'connectionOptions()').evaluate()[0]
    assert value.toVariant() == profile
    window.close(); engine.deleteLater(); app.processEvents()


def test_custom_dropdown_selection_menu_navigation_and_icons(app, controller):
    from PySide6.QtCore import QObject, QPointF, Qt, QMetaObject, Q_ARG
    from PySide6.QtTest import QTest
    from bootwire_gui.branding import application_icon
    icon = application_icon()
    assert not icon.isNull()
    small = icon.pixmap(16,16).toImage()
    assert not small.isNull()
    assert any(small.pixelColor(x,y).blue() > 180 and small.pixelColor(x,y).green() > 120 for x in range(16) for y in range(16)), 'Small app icon must contain the blue logo, not just its background'
    assert not icon.pixmap(256,256).isNull()
    app.setWindowIcon(icon)
    engine = QQmlApplicationEngine()
    errors = []
    engine.warnings.connect(lambda warnings: errors.extend(w.toString() for w in warnings))
    engine.rootContext().setContextProperty('backend', controller)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parents[2]/'src/bootwire_gui/qml/Main.qml')))
    window = engine.rootObjects()[0]
    app.processEvents()
    assert not window.icon().isNull()
    def click(name):
        item=window.findChild(QObject,name)
        assert item and item.property('enabled'), name
        point=item.mapToScene(QPointF(item.width()/2,item.height()/2)).toPoint()
        QTest.mouseClick(window,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,point)
        app.processEvents()
    # Clicking the arrow opens a real, keyboard-navigable popup.
    baud=window.findChild(QObject,'baudField')
    point=baud.mapToScene(QPointF(baud.width()-16,baud.height()/2)).toPoint()
    QTest.mouseClick(window,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,point)
    app.processEvents()
    popup=window.findChild(QObject,'baudFieldPopup')
    assert popup.property('visible')
    QTest.keyClick(window,Qt.Key.Key_Down)
    QTest.keyClick(window,Qt.Key.Key_Return)
    app.processEvents()
    assert not popup.property('visible')
    assert baud.property('editText') == '230400'
    click('toolsMenuButton')
    menu=window.findChild(QObject,'toolsMenu')
    assert menu.property('visible')
    item=window.findChild(QObject,'openInspectorMenuItem')
    QMetaObject.invokeMethod(item,'triggered')
    QMetaObject.invokeMethod(menu,'close')
    app.processEvents()
    assert window.property('page')==4
    click('helpMenuButton')
    item=window.findChild(QObject,'aboutMenuItem')
    QMetaObject.invokeMethod(item,'triggered')
    app.processEvents()
    about=window.findChild(QObject,'aboutDialog')
    assert about.property('visible')
    QMetaObject.invokeMethod(about,'close')
    assert not errors, errors
    window.close();engine.deleteLater();app.processEvents()


def test_dropdown_scrollbar_has_its_own_gutter(app, controller):
    from PySide6.QtCore import QObject, QPointF, Qt, QMetaObject
    from PySide6.QtTest import QTest
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda items: warnings.extend(w.toString() for w in items))
    engine.rootContext().setContextProperty('backend', controller)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parents[2]/'src/bootwire_gui/qml/Main.qml')))
    window = engine.rootObjects()[0]
    field = window.findChild(QObject, 'baudField')
    field.setProperty('model', [str(9600 * (i + 1)) for i in range(30)])
    app.processEvents()
    popup = window.findChild(QObject, 'baudFieldPopup')
    QMetaObject.invokeMethod(popup, 'open')
    app.processEvents()
    options = window.findChild(QObject, 'baudFieldOptions')
    scroll = window.findChild(QObject, 'baudFieldScrollBar')
    assert scroll.property('visible')
    row_right = options.mapToScene(QPointF(options.width(), 0)).x()
    gutter_left = scroll.mapToScene(QPointF(0, 0)).x()
    assert row_right <= gutter_left - 4
    # Every rendered row must stay inside the content area, away from the thumb.
    content = options.property('contentItem')
    rows = [item for item in content.childItems() if 'ItemDelegate' in item.metaObject().className()]
    assert rows
    assert all(item.width() <= options.width() for item in rows)
    QTest.keyClick(window, Qt.Key.Key_End)
    app.processEvents()
    assert options.property('contentY') > 0
    QMetaObject.invokeMethod(popup, 'close')
    field.setProperty('model', ['9600', '115200'])
    QMetaObject.invokeMethod(popup, 'open')
    app.processEvents()
    assert not scroll.property('visible'), 'A short list must not show a full-height thumb'
    assert abs(options.width() - popup.property('availableWidth')) < 1
    assert not warnings, warnings
    QMetaObject.invokeMethod(popup, 'close')
    window.close(); engine.deleteLater(); app.processEvents()


def test_unified_titlebar_menu_switching_and_window_controls(app, controller):
    from PySide6.QtCore import QObject, QPointF, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtGui import QWindow
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda items: warnings.extend(w.toString() for w in items))
    engine.rootContext().setContextProperty('backend', controller)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parents[2]/'src/bootwire_gui/qml/Main.qml')))
    window = engine.rootObjects()[0]
    app.processEvents()
    assert window.flags() & Qt.WindowType.FramelessWindowHint
    def point(name):
        item = window.findChild(QObject, name)
        assert item, name
        return item.mapToScene(QPointF(item.width()/2,item.height()/2)).toPoint()
    def click(name):
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, point(name))
        app.processEvents()
    title_icon = window.findChild(QObject, 'titleBarIcon')
    center = title_icon.mapToScene(QPointF(title_icon.width()/2,title_icon.height()/2)).y()
    assert abs(center-point('fileMenuButton').y()) < 1
    assert abs(center-point('closeWindowButton').y()) < 1
    click('fileMenuButton')
    assert window.findChild(QObject, 'fileMenu').property('visible')
    QTest.mouseMove(window, point('toolsMenuButton'))
    app.processEvents()
    assert window.findChild(QObject, 'toolsMenu').property('visible')
    assert not window.findChild(QObject, 'fileMenu').property('visible')
    QTest.keyClick(window, Qt.Key.Key_Left)
    app.processEvents()
    assert window.findChild(QObject, 'deviceMenu').property('visible')
    QTest.keyClick(window, Qt.Key.Key_Escape)
    app.processEvents()
    QTest.mouseMove(window, point('helpMenuButton'))
    app.processEvents()
    assert not window.findChild(QObject, 'helpMenu').property('visible')
    click('maximizeWindowButton')
    assert window.visibility() == QWindow.Visibility.Maximized
    click('maximizeWindowButton')
    assert window.visibility() == QWindow.Visibility.Windowed
    click('minimizeWindowButton')
    assert window.visibility() == QWindow.Visibility.Minimized
    window.showNormal();app.processEvents()
    connect(app, controller)
    run(app, controller, 'fault', {'kind':'drop_requests'})
    controller.perform('ping', {'payload':'close guard', 'count':1})
    click('closeWindowButton')
    assert window.isVisible(), 'Closing during device work must remain guarded'
    controller.cancel()
    wait_for(app, lambda: not controller.state['busy'])
    click('closeWindowButton')
    assert not window.isVisible()
    assert not warnings, warnings
    engine.deleteLater();app.processEvents()


def test_mouse_click_does_not_leave_icon_focus_ring_but_keyboard_does(app, controller):
    from PySide6.QtCore import QObject, QPointF, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtQml import QQmlProperty
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty('backend', controller)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parents[2]/'src/bootwire_gui/qml/Main.qml')))
    window = engine.rootObjects()[0]
    app.processEvents()
    def click(name):
        item = window.findChild(QObject,name)
        p = item.mapToScene(QPointF(item.width()/2,item.height()/2)).toPoint()
        QTest.mouseClick(window,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,p)
        app.processEvents()
        return item
    theme = click('themeButton')
    assert theme.property('text') == 'Light'
    assert theme.property('glyph') == 'sun'
    QTest.mouseMove(window,QPointF(650,180).toPoint())
    app.processEvents()
    assert not theme.property('visualFocus')
    assert QQmlProperty.read(theme.property('background'),'border.width') == 0
    preferences = click('preferencesButton')
    assert QQmlProperty.read(preferences.property('background'),'border.width') == 0
    QTest.keyClick(window,Qt.Key.Key_Tab,Qt.KeyboardModifier.ShiftModifier)
    app.processEvents()
    assert theme.property('activeFocus')
    assert theme.property('visualFocus')
    assert QQmlProperty.read(theme.property('background'),'border.width') == 2
    QTest.keyClick(window,Qt.Key.Key_Space)
    app.processEvents()
    assert theme.property('text') == 'Dark'
    assert theme.property('glyph') == 'moon'
    assert QQmlProperty.read(theme.property('background'),'border.width') == 2
    click('themeButton')
    assert theme.property('text') == 'Light'
    assert theme.property('glyph') == 'sun'
    QTest.mouseMove(window,QPointF(650,180).toPoint())
    app.processEvents()
    assert QQmlProperty.read(theme.property('background'),'border.width') == 0
    window.close();engine.deleteLater();app.processEvents()


def test_developer_panel_real_command_entry_and_confirmation(app,controller):
    from PySide6.QtCore import QObject, QPointF, Qt, QMetaObject
    from PySide6.QtTest import QTest
    engine=QQmlApplicationEngine();warnings=[]
    engine.warnings.connect(lambda items:warnings.extend(w.toString() for w in items))
    engine.rootContext().setContextProperty('backend',controller)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parents[2]/'src/bootwire_gui/qml/Main.qml')))
    window=engine.rootObjects()[0]
    app.processEvents()
    QTest.keyClick(window,Qt.Key.Key_J,Qt.KeyboardModifier.ControlModifier)
    app.processEvents()
    panel=window.findChild(QObject,'developerPanel')
    assert panel.property('expanded')
    entry=window.findChild(QObject,'bootwireCommandInput')
    entry.setProperty('text','bootwire -p sim info')
    QMetaObject.invokeMethod(entry,'accepted')
    wait_for(app,lambda:not controller.state['busy'] and not controller.console.state['executing'])
    assert controller.state['connected']
    entry.setProperty('text','erase -l 0x800')
    QMetaObject.invokeMethod(entry,'accepted')
    app.processEvents()
    dialog=window.findChild(QObject,'consoleConfirmation')
    assert dialog.property('visible')
    before=controller.worker.session.target.executed
    assert controller.console.state['pending']
    QMetaObject.invokeMethod(dialog,'reject')
    assert controller.worker.session.target.executed==before
    assert not controller.console.state['pending']
    QTest.keyClick(window,Qt.Key.Key_J,Qt.KeyboardModifier.ControlModifier)
    app.processEvents()
    assert not panel.property('expanded')
    assert not warnings,warnings
    window.close();engine.deleteLater();app.processEvents()


def test_terminal_panel_paste_and_enter_reach_real_shell(app,controller):
    import os
    if os.name=='nt':
        pytest.skip('Native Windows command execution is covered by the ConPTY integration test')
    pytest.importorskip('pyte')
    from PySide6.QtCore import QObject, Qt
    from PySide6.QtTest import QTest
    engine=QQmlApplicationEngine();warnings=[]
    engine.warnings.connect(lambda items:warnings.extend(w.toString() for w in items))
    engine.rootContext().setContextProperty('backend',controller)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parents[2]/'src/bootwire_gui/qml/Main.qml')))
    window=engine.rootObjects()[0]
    panel=window.findChild(QObject,'developerPanel')
    panel.setProperty('expanded',True);panel.setProperty('tab',2)
    app.processEvents()
    terminal=controller.console.terminal
    terminal.start('',str(Path.cwd()))
    wait_for(app,lambda:terminal.state['running'])
    text=window.findChild(QObject,'systemTerminalInput')
    text.forceActiveFocus(Qt.FocusReason.MouseFocusReason)
    app.clipboard().setText("printf '__GUI_TERMINAL_OK__\\n'")
    QTest.keyClick(window,Qt.Key.Key_V,Qt.KeyboardModifier.ControlModifier|Qt.KeyboardModifier.ShiftModifier)
    QTest.keyClick(window,Qt.Key.Key_Return)
    wait_for(app,lambda:'__GUI_TERMINAL_OK__' in terminal.state['text'].splitlines())
    assert not warnings,warnings
    terminal.stop()
    wait_for(app,lambda:not terminal.state['running'])
    window.close();engine.deleteLater();app.processEvents()


def test_traces_carry_names_hex_sequence_and_status(app, controller):
    c = controller
    connect(app, c)
    run(app, c, 'send', {'command': '0x40', 'payload': '01 02', 'hex': True})
    request, reply = c.traces.items[0], c.traces.items[1]
    assert (request['direction'], request['name'], request['command']) == ('TX', 'CONNECT', '0x00')
    assert request['seqLabel'] == f"0x{request['seq']:02X}"
    assert (reply['direction'], reply['statusName']) == ('RX', 'OK')
    refused = c.traces.items[-1]
    assert (refused['name'], refused['statusName'], refused['status']) == ('0x40', 'UNKNOWN_CMD', 2)
    assert c.traces.items[-2]['length'] == 2


def test_frame_bursts_are_coalesced_into_few_ui_refreshes(app, controller, tmp_path):
    c = controller
    connect(app, c)
    image = tmp_path/'large.bin'
    image.write_bytes(bytes(range(256)) * 256)
    run(app, c, 'inspect', {'path': str(image)})
    refreshes = []
    c.changed.connect(lambda: refreshes.append(1))
    started = time.monotonic()
    run(app, c, 'flash', dict(c.state['image'], run=False))
    assert c.state['severity'] == 'success', c.state['detail']
    assert len(c.traces.items) == 500
    # More than 500 frames were exchanged; the UI is refreshed on a timer instead.
    assert len(refreshes) < 100
    assert time.monotonic() - started < 5


def test_inspector_keeps_scroll_position_while_frames_arrive(app, controller):
    from PySide6.QtCore import QObject
    c = controller
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty('backend', c)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parents[2]/'src/bootwire_gui/qml/Main.qml')))
    window = engine.rootObjects()[0]
    window.setProperty('page', 4)
    connect(app, c)
    run(app, c, 'ping', {'payload': 'BootWire', 'count': 40})
    traces = window.findChild(QObject, 'traceList')
    follow = window.findChild(QObject, 'followTraces')
    wait_for(app, lambda: traces.property('count') == len(c.traces.items))
    for _ in range(20):
        app.processEvents()
    # Following: the newest frame is in view.
    assert traces.property('atYEnd')
    follow.setProperty('checked', False)
    traces.setProperty('contentY', traces.property('originY') + 300)
    app.processEvents()
    before = traces.property('contentY') - traces.property('originY')
    run(app, c, 'ping', {'payload': 'BootWire', 'count': 40})
    wait_for(app, lambda: traces.property('count') == len(c.traces.items))
    for _ in range(20):
        app.processEvents()
    after = traces.property('contentY') - traces.property('originY')
    assert abs(after - before) < 1, (before, after)
    assert not traces.property('atYEnd')
    c.clear('traces')
    app.processEvents()
    assert traces.property('count') == 0 and window.property('traceCount') == 0
    window.close(); engine.deleteLater(); app.processEvents()


def test_developer_output_keeps_scroll_position_and_filters(app, controller):
    from PySide6.QtCore import QObject
    from PySide6.QtQml import QQmlExpression
    c = controller
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda items: warnings.extend(w.toString() for w in items))
    engine.rootContext().setContextProperty('backend', c)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parents[2]/'src/bootwire_gui/qml/Main.qml')))
    window = engine.rootObjects()[0]
    panel = window.findChild(QObject, 'developerPanel')
    panel.setProperty('expanded', True); panel.setProperty('tab', 0)
    output = window.findChild(QObject, 'developerOutputList')

    def settle():
        for _ in range(30):
            app.processEvents(); time.sleep(.003)

    def top_row():
        return QQmlExpression(engine.rootContext(), output, 'indexAt(20, contentY + 4)').evaluate()[0]

    connect(app, c)
    run(app, c, 'ping', {'payload': 'x', 'count': 40}); settle()
    shown = output.property('count')
    assert shown > 100 and output.property('atYEnd')
    window.findChild(QObject, 'followOutput').setProperty('checked', False)
    output.setProperty('contentY', output.property('originY') + 300); settle()
    row = top_row()
    run(app, c, 'ping', {'payload': 'x', 'count': 40}); settle()
    assert output.property('count') > shown
    assert top_row() == row
    assert not output.property('atYEnd')
    # The command tab lists only console input and results; clearing empties the output tab.
    panel.setProperty('tab', 1); settle()
    assert output.property('count') == 0
    panel.setProperty('tab', 0); settle()
    c.console.clear('output'); settle()
    assert output.property('count') == 0
    assert not warnings, warnings
    window.close(); engine.deleteLater(); app.processEvents()
