import os
import time
import pytest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QT_QUICK_BACKEND','software')
pytest.importorskip('PySide6')
from PySide6.QtCore import QSettings
from PySide6.QtGui import QGuiApplication
from bootwire_gui.controller import Controller

OPTIONS={'port':'sim','baud':115200,'timeout':.05,'eraseTimeout':.05,'retries':1}


@pytest.fixture
def app():
    return QGuiApplication.instance() or QGuiApplication([])


@pytest.fixture
def controller(app,tmp_path):
    c=Controller(settings=QSettings(str(tmp_path/'console.ini'),QSettings.IniFormat))
    yield c
    c.shutdown()


def wait(app,predicate):
    deadline=time.monotonic()+5
    while not predicate() and time.monotonic()<deadline:
        app.processEvents();time.sleep(.002)
    assert predicate()


def submit(app,c,line):
    c.console.submit(line,OPTIONS)
    wait(app,lambda:not c.console.state['executing'] and not c.state['busy'])


def test_console_connect_ping_and_raw_command_share_session(app,controller):
    c=controller
    submit(app,c,'bootwire -p sim info')
    assert c.state['connected']
    target=c.worker.session.target
    submit(app,c,'ping -n 3 -d "C0 DB" --hex')
    assert c.worker.session.target is target
    assert any(e['source']=='protocol' and 'PING' in e['message'] for e in c.console.state['entries'])
    submit(app,c,'send 0x01 -d "C0 DB" --hex')
    assert any('c0 db' in e['message'] for e in c.console.state['entries'] if e['source']=='command')


def test_destructive_console_command_does_not_execute_before_confirmation(app,controller):
    c=controller
    submit(app,c,'info')
    before=c.worker.session.target.executed
    submit(app,c,'erase -l 0x800')
    assert c.console.state['pending']
    assert c.worker.session.target.executed==before
    c.console.reject()
    assert c.worker.session.target.executed==before
    submit(app,c,'erase -l 0x800')
    c.console.confirm()
    wait(app,lambda:not c.state['busy'] and not c.console.state['executing'])
    assert c.worker.session.target.executed==before+1


def test_console_flash_uses_inspected_image_and_verifies(app,controller,tmp_path):
    c=controller
    c.perform('demo',{})
    wait(app,lambda:not c.state['busy'])
    path=c.state['image']['path']
    submit(app,c,f'flash "{path}" --no-run')
    assert c.console.state['pending']
    assert c.state['image']['simulatorOnly']
    c.console.confirm()
    wait(app,lambda:not c.state['busy'] and not c.console.state['executing'])
    assert c.state['severity']=='success'
    assert c.worker.session.target.app_is_valid()
    assert not c.worker.session.target.running
    assert any('Image verified' in e['message'] for e in c.console.state['entries'])


def test_invalid_console_command_and_unknown_target_command_are_recoverable(app,controller):
    c=controller
    submit(app,c,'not-a-command')
    assert c.console.state['entries'][-1]['level']=='error'
    submit(app,c,'send 0x40')
    assert c.state['connected']
    assert not c.console.state['executing']
    assert any('UNKNOWN_CMD' in e['message'] for e in c.console.state['entries'])
    submit(app,c,'ping')
    assert c.state['severity']=='success'
