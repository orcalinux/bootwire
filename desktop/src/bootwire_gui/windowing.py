"""Preserve native window management beneath the custom Windows title bar.

Linux/Wayland window management uses the normal Qt window flags directly. No
application shortcuts intercept the desktop's configurable tiling commands.
"""
from __future__ import annotations

import sys

from PySide6.QtCore import QAbstractNativeEventFilter


def install_native_frame(app, window):
    if sys.platform != "win32":
        return None
    frame = _WindowsFrame(app, window)
    window.destroyed.connect(frame.detach)
    return frame  # The caller retains the native event filter for the window lifetime.


class _WindowsFrame(QAbstractNativeEventFilter):
    def __init__(self, app, window):
        super().__init__()
        import ctypes
        from ctypes import wintypes

        self._ctypes = ctypes
        self._types = wintypes
        self._app = app
        self._hwnd = int(window.winId())
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        pointer_type = ctypes.c_ssize_t
        # Get/SetWindowLongPtr are aliases of Get/SetWindowLong on 32-bit Windows.
        suffix = "PtrW" if ctypes.sizeof(ctypes.c_void_p) == 8 else "W"
        self._get_style = getattr(self._user32, "GetWindowLong" + suffix)
        self._get_style.argtypes = [wintypes.HWND, ctypes.c_int]
        self._get_style.restype = pointer_type
        self._set_style = getattr(self._user32, "SetWindowLong" + suffix)
        self._set_style.argtypes = [wintypes.HWND, ctypes.c_int, pointer_type]
        self._set_style.restype = pointer_type
        self._user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND,
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
        self._user32.SetWindowPos.restype = wintypes.BOOL
        self._user32.IsZoomed.argtypes = [wintypes.HWND]
        self._user32.IsZoomed.restype = wintypes.BOOL
        self._user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
        self._user32.MonitorFromWindow.restype = wintypes.HANDLE

        class MonitorInfo(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                        ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]

        self._monitor_info = MonitorInfo
        self._user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MonitorInfo)]
        self._user32.GetMonitorInfoW.restype = wintypes.BOOL
        # Qt's FramelessWindowHint removes WS_THICKFRAME. Restore normal shell
        # capabilities, then suppress only the painted frame via WM_NCCALCSIZE.
        self._original_style = self._get_style(self._hwnd, -16)
        style = self._original_style | 0x00C00000 | 0x00040000 | 0x00080000 | 0x00030000
        app.installNativeEventFilter(self)
        ctypes.set_last_error(0)
        self._set_style(self._hwnd, -16, style)
        if ctypes.get_last_error():
            app.removeNativeEventFilter(self)
            raise ctypes.WinError(ctypes.get_last_error())
        # FRAMECHANGED | NOMOVE | NOSIZE | NOZORDER | NOACTIVATE
        if not self._user32.SetWindowPos(self._hwnd, None, 0, 0, 0, 0, 0x0037):
            app.removeNativeEventFilter(self)
            self._set_style(self._hwnd, -16, self._original_style)
            raise ctypes.WinError(ctypes.get_last_error())

    def nativeEventFilter(self, event_type, message):
        if bytes(event_type) not in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
            return False, 0
        msg = self._types.MSG.from_address(int(message))
        if msg.hWnd != self._hwnd or msg.message != 0x0083:  # WM_NCCALCSIZE
            return False, 0
        if msg.wParam and self._user32.IsZoomed(self._hwnd):
            # A maximized custom client area must exclude the taskbar on this
            # monitor. RECT is the first member of NCCALCSIZE_PARAMS.
            info = self._monitor_info()
            info.cbSize = self._ctypes.sizeof(info)
            monitor = self._user32.MonitorFromWindow(self._hwnd, 2)
            if self._user32.GetMonitorInfoW(monitor, self._ctypes.byref(info)):
                rect = self._types.RECT.from_address(msg.lParam)
                rect.left, rect.top = info.rcWork.left, info.rcWork.top
                rect.right, rect.bottom = info.rcWork.right, info.rcWork.bottom
        return True, 0

    def detach(self, *_):
        self._app.removeNativeEventFilter(self)
