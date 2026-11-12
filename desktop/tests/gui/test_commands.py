import pytest
from bootwire_gui.commands import parse_command, CommandError

DEFAULTS = {'port':'sim','baud':115200,'timeout':.5,'eraseTimeout':5,'retries':3}


@pytest.mark.parametrize('line,action', [
    ('help','help'),('bootwire info','info'),('ping -n 5 -d "C0 DB" --hex','ping'),
    ('flash "my firmware.bin" --no-run','flash'),('write app.bin -a 0x08008000','write'),
    ('verify app.bin','verify'),('erase -a 0x08008000 -l 0x800','erase'),('run','run'),
    ('send 0x40 -d "01 02" --hex','raw_send'),('disconnect','disconnect'),('demo','demo'),
])
def test_supported_commands(line,action):
    assert parse_command(line,DEFAULTS).action == action


def test_windows_path_and_quoted_hex_are_preserved():
    command = parse_command(r'flash "C:\Firmware builds\app.bin" --no-run',DEFAULTS)
    assert command.options['path'] == r'C:\Firmware builds\app.bin'
    assert not command.options['run']


def test_global_connection_overrides():
    command=parse_command('bootwire -p COM4 -b 921600 -r 2 ping',DEFAULTS)
    assert command.connection['port']=='COM4'
    assert command.connection['baud']==921600
    assert command.reconnect


@pytest.mark.parametrize('line',['erase','write app.bin','flash app.bin','run','send 0x10','send 0x11','send 0x13'])
def test_destructive_commands_need_review(line):
    assert parse_command(line,DEFAULTS).review


@pytest.mark.parametrize('line',['send 0x80','send abc','ping -n 0','ping --hex -d XX','unknown','flash "unclosed'])
def test_invalid_commands_are_errors_not_process_exits(line):
    with pytest.raises((ValueError,CommandError)):
        parse_command(line,DEFAULTS)
