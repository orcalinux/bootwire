"""Native shell capabilities and narrow tiling geometry."""
import sys
from pathlib import Path

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QObject, QPointF, QSettings, QSize, Qt, QUrl
from PySide6.QtGui import QGuiApplication, QWindow
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from bootwire_gui.controller import Controller
from bootwire_gui.windowing import install_native_frame


@pytest.fixture
def app():
    return QGuiApplication.instance() or QGuiApplication([])


def test_half_screen_geometry_keeps_connection_and_firmware_accessible(app, tmp_path):
    controller = Controller(settings=QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat))
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", controller)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parents[2] / "src/bootwire_gui/qml/Main.qml")))
    window = engine.rootObjects()[0]
    try:
        flags = window.flags()
        assert flags & Qt.WindowType.WindowMaximizeButtonHint
        assert flags & Qt.WindowType.WindowMinimizeButtonHint
        for width in (640, 683, 768, 960):
            window.resize(width, 540)
            for _ in range(10):
                app.processEvents()
            assert window.width() == width
            assert window.height() == 540
            grid = window.findChild(QObject, "firmwareGrid")
            assert grid.property("columns") == 1
            for name in ("portField", "baudField", "connectButton", "closeWindowButton"):
                item = window.findChild(QQuickItem, name)
                top_left = item.mapToScene(QPointF(0, 0))
                bottom_right = item.mapToScene(QPointF(item.width(), item.height()))
                assert top_left.x() >= 0, name
                assert bottom_right.x() <= width, name
                assert bottom_right.y() <= 540, name
        window.resize(1380, 900)
        for _ in range(10):
            app.processEvents()
        assert grid.property("columns") == 2
    finally:
        controller.shutdown()
        window.close()
        engine.deleteLater()
        app.processEvents()


@pytest.mark.skipif(sys.platform == "win32", reason="Other platforms use Qt window management directly")
def test_native_frame_is_noop_outside_windows(app):
    assert install_native_frame(app, QWindow()) is None


@pytest.mark.skipif(sys.platform != "win32", reason="Requires a native Windows desktop")
def test_native_windows_frame_preserves_shell_styles_and_full_client_area(app):
    if app.platformName() != "windows":
        pytest.skip("Run with QT_QPA_PLATFORM=windows to exercise the native HWND")
    import ctypes
    from ctypes import wintypes
    window = QWindow()
    window.setFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
    window.setMinimumSize(QSize(640, 540))
    window.resize(640, 540)
    frame = install_native_frame(app, window)
    try:
        window.show()
        for _ in range(10):
            app.processEvents()
        style = frame._get_style(int(window.winId()), -16)
        for flag in (0x00040000, 0x00010000, 0x00020000, 0x00080000):
            assert style & flag
        frame._user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        rect = wintypes.RECT()
        assert frame._user32.GetClientRect(int(window.winId()), ctypes.byref(rect))
        assert rect.right - rect.left == round(window.width() * window.devicePixelRatio())
        assert rect.bottom - rect.top == round(window.height() * window.devicePixelRatio())
    finally:
        frame.detach()
        window.close()
