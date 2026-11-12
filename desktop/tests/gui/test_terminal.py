import os
import time
import pytest
pytest.importorskip('PySide6')
pytest.importorskip('pyte')
from PySide6.QtCore import QProcess
from PySide6.QtGui import QGuiApplication
from bootwire_gui.terminal import TerminalService, shell_profiles

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QT_QUICK_BACKEND','software')


@pytest.fixture
def app():
    return QGuiApplication.instance() or QGuiApplication([])


@pytest.fixture
def terminal(app):
    service=TerminalService()
    yield service
    service.shutdown()


def wait(app,predicate,timeout=8):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline and not predicate():
        app.processEvents()
        time.sleep(.01)
    assert predicate()


def test_windows_shell_discovery_uses_real_windows_shells():
    found={'pwsh':r'C:\PowerShell\pwsh.exe','powershell':r'C:\Windows\powershell.exe','cmd':r'C:\Windows\cmd.exe'}
    profiles=shell_profiles('nt',which=found.get,environ={})
    assert [p['id'] for p in profiles]==['pwsh','powershell','cmd']
    assert profiles[0]['argv']==[found['pwsh'],'-NoLogo']
    assert profiles[-1]['argv']==[found['cmd']]


def test_ansi_screen_colors_cursor_and_html_are_safe(terminal):
    terminal._new_screen()
    terminal._stream.feed('\x1b[31m<hello>\x1b[0m\r\n世界')
    terminal._render()
    assert '<hello>' in terminal.state['text']
    assert '&lt;hello&gt;' in terminal.state['html']
    assert '#F27887' in terminal.state['html']
    assert '世界' in terminal.state['text']


def test_invalid_working_directory_reports_error(terminal):
    terminal.start('', '/this/directory/does/not/exist')
    assert not terminal.state['running']
    assert 'directory' in terminal.state['message']


@pytest.mark.skipif(os.name=='nt',reason='POSIX PTY behavior; Windows integration uses ConPTY on Windows CI')
def test_real_shell_cwd_interactive_input_resize_and_interrupt(app,terminal,tmp_path):
    terminal.start('',str(tmp_path))
    wait(app,lambda:terminal.state['running'])
    terminal.write("printf '__BOOTWIRE_PTY_OK__\\n'; pwd\r")
    wait(app,lambda:'__BOOTWIRE_PTY_OK__' in terminal.state['text'].splitlines() and str(tmp_path) in terminal.state['text'].splitlines())
    terminal.resize(90,12)
    terminal.write("stty size\r")
    wait(app,lambda:'12 90' in terminal.state['text'])
    terminal.write('sleep 20\r')
    for _ in range(10):app.processEvents();time.sleep(.01)
    terminal.interrupt()
    terminal.write("printf '__INTERRUPT_RECOVERED__\\n'\r")
    wait(app,lambda:'__INTERRUPT_RECOVERED__' in terminal.state['text'].splitlines())
    terminal.stop()
    wait(app,lambda:terminal.process.state()==QProcess.ProcessState.NotRunning)
    assert not terminal.state['running']


@pytest.mark.skipif(os.name!='nt',reason='Requires a real Windows ConPTY backend')
def test_windows_conpty_executes_a_command(app,terminal,tmp_path):
    terminal.start('',str(tmp_path))
    wait(app,lambda:terminal.state['running'])
    command = "echo __WIN_PTY_OK__" if terminal.state['shell']=='Command Prompt' else "Write-Output '__WIN_PTY_OK__'"
    terminal.write(command+'\r')
    wait(app,lambda:'__WIN_PTY_OK__' in terminal.state['text'].splitlines())
    terminal.stop()
    wait(app,lambda:terminal.process.state()==QProcess.ProcessState.NotRunning)
