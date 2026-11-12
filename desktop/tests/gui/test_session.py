"""The GUI's device workflow is tested without Qt or physical hardware."""
import hashlib
import struct

import pytest

from bootwire.errors import BootWireError, BootWireStatusError
from bootwire_gui.session import DeviceSession, OperationCancelled, inspect_image


@pytest.fixture
def image(tmp_path):
    path = tmp_path / 'firmware.bin'
    path.write_bytes(struct.pack('<II', 0x20010000, 0x08008009) + bytes(range(255)) * 3)
    return path


@pytest.fixture
def session():
    session = DeviceSession()
    session.connect({'port': 'sim', 'timeout': .05, 'eraseTimeout': .05, 'retries': 1})
    yield session
    session.close()


def test_image_fingerprint_and_vectors(image):
    data, info = inspect_image(image)
    assert info['sha256'] == hashlib.sha256(data).hexdigest()
    assert info['stackPointer'] == '0x20010000'
    assert info['resetVector'] == '0x08008009'


def test_full_update_with_odd_length_and_verify(session, image):
    result = session.execute('flash', {'path': str(image)})
    assert 'verified' in result['message']
    assert bytes(session.target.flash[:image.stat().st_size]) == image.read_bytes()
    assert not session.target.running
    session.execute('verify', {'path': str(image)})


def test_run_disconnects_and_reset_allows_reconnect(session, image):
    session.execute('flash', {'path': str(image)})
    assert session.execute('run', {})['disconnected']
    assert session.client is None
    assert session.target.running
    session.execute('reset_simulator', {})
    session.connect({'port': 'sim'})
    assert not session.target.running


def test_changed_image_rejected_before_erase(session, image):
    _, info = inspect_image(image)
    image.write_bytes(image.read_bytes() + b'changed')
    before = bytes(session.target.flash)
    with pytest.raises(BootWireError, match='changed'):
        session.execute('flash', {'path': str(image), 'sha256': info['sha256']})
    assert bytes(session.target.flash) == before


def test_changed_library_release_rejected(image):
    session = DeviceSession()
    with pytest.raises(BootWireError, match='changed'):
        session.execute('inspect', {'path': str(image), 'sha256': 'incorrect'})


@pytest.mark.parametrize('address', ['0x08000000', '0x08008001', '0x0803FFFF'])
def test_invalid_image_range_does_not_erase(session, image, address):
    before = bytes(session.target.flash)
    with pytest.raises(BootWireError):
        session.execute('flash', {'path': str(image), 'address': address})
    assert bytes(session.target.flash) == before


def test_cancel_between_blocks_never_writes_or_runs(session, image):
    def stop(stage, done, total):
        if stage == 'erase': session.cancelled.set()
    session.progress = stop
    with pytest.raises(OperationCancelled):
        session.execute('flash', {'path': str(image), 'run': True})
    assert not session.target.running
    assert all(byte == 255 for byte in session.target.flash)


def test_user_console_refuses_reserved_flash_commands(session):
    before = session.target.executed
    with pytest.raises(BootWireError, match='user commands'):
        session.execute('send', {'command': '0x10'})
    assert session.target.executed == before


def test_unknown_command_is_target_error(session):
    with pytest.raises(BootWireStatusError):
        session.execute('send', {'command': '0x40', 'payload': '01 02', 'hex': True})


def test_custom_reply_and_escape_ping(session):
    session.target.user_handlers[0x40] = lambda payload: (0, payload[::-1])
    reply = session.execute('send', {'command': '0x40', 'payload': 'C0 DB', 'hex': True})
    assert reply['hex'] == 'db c0'
    assert '3/3' in session.execute('ping', {'payload': 'C0 DB', 'hex': True, 'count': 3})['message']


def test_demo_cannot_flash_real_hardware(session, image):
    session.simulated = False
    with pytest.raises(BootWireError, match='simulator only'):
        session.execute('flash', {'path': str(image), 'simulatorOnly': True})


def test_fault_recovery_uses_cache(session):
    session.execute('fault', {'kind': 'drop_responses'})
    before = session.target.executed
    assert '1/1' in session.execute('ping', {'count': 1})['message']
    assert session.target.executed == before + 1


def test_payload_limit_and_invalid_hex(session):
    with pytest.raises(BootWireError, match='maximum'):
        session.execute('ping', {'payload': 'a' * 261})
    with pytest.raises(BootWireError, match='byte pairs'):
        session.execute('ping', {'payload': 'xx', 'hex': True})


def test_hex_payload_accepts_common_separators(session):
    assert session._payload({'payload': '0xC0, 0xDB:11', 'hex': True}) == bytes([0xC0, 0xDB, 0x11])


def test_typed_numbers_report_readable_errors(session):
    with pytest.raises(BootWireError, match='Erase address must be a number'):
        session.execute('erase', {'address': 'zz'})
    with pytest.raises(BootWireError, match='Command ID must be a number'):
        session.execute('send', {'command': 'forty'})
    with pytest.raises(BootWireError, match='must be numbers'):
        DeviceSession().connect({'port': 'sim', 'timeout': ''})


def test_empty_image_rejected(tmp_path):
    path = tmp_path/'empty.bin'
    path.write_bytes(b'')
    with pytest.raises(BootWireError, match='empty'):
        inspect_image(path)
