"""The existing BootWire mark, shared by QML and desktop window decorations."""
from pathlib import Path


def application_icon():
    from PySide6.QtCore import QSize
    from PySide6.QtGui import QIcon

    assets = Path(__file__).parent / "assets"
    icon = QIcon(str(assets / "bootwire.ico"))
    icon.addFile(str(assets / "bootwire.svg"), QSize(256, 256))
    return icon
