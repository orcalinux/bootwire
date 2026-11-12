"""BootWire Desktop entry point; GUI dependencies remain optional."""
from __future__ import annotations

import sys
from pathlib import Path


def main():
    try:
        from PySide6.QtCore import QUrl, Qt
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtQml import QQmlApplicationEngine
        from PySide6.QtQuickControls2 import QQuickStyle
    except ImportError:
        print('Desktop dependencies are missing. Install with: pip install -e ".[gui]"', file=sys.stderr)
        return 2
    from bootwire_gui.controller import Controller
    from bootwire_gui.branding import application_icon
    from bootwire_gui.windowing import install_native_frame

    QQuickStyle.setStyle("Basic")
    QGuiApplication.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeMenuBar)
    app = QGuiApplication(sys.argv)
    app.setApplicationName("BootWire")
    app.setOrganizationName("BootWire")
    app.setDesktopFileName("bootwire")
    app.setWindowIcon(application_icon())
    controller = Controller()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", controller)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parent / "qml" / "Main.qml")))
    if not engine.rootObjects():
        controller.shutdown()
        return 1
    engine.rootObjects()[0].setIcon(app.windowIcon())
    try:
        native_frame = install_native_frame(app, engine.rootObjects()[0])
    except OSError as error:
        # A shell integration failure should not strand the device worker or
        # prevent access to firmware recovery tools.
        print(f"Native window integration is unavailable: {error}", file=sys.stderr)
        native_frame = None
    app.aboutToQuit.connect(controller.shutdown)
    result = app.exec()
    if native_frame is not None:
        native_frame.detach()
    del engine
    return result


if __name__ == "__main__":
    sys.exit(main())
