"""Single-instance guard and show-settings broadcast."""

from __future__ import annotations

import ctypes
import logging
from collections.abc import Callable
from ctypes import wintypes

from PyQt6.QtCore import QAbstractNativeEventFilter, QByteArray

from screenloupe.core.constants import ERROR_ALREADY_EXISTS, MUTEX_NAME, SHOW_MESSAGE_NAME

logger = logging.getLogger(__name__)

_WM_SHOW_SETTINGS = ctypes.windll.user32.RegisterWindowMessageW(SHOW_MESSAGE_NAME)


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", wintypes.POINT),
    ]


class SingleInstanceGuard:
    """Hold the process mutex; release on shutdown."""

    def __init__(self) -> None:
        self._handle: int | None = None

    def acquire(self) -> bool:
        """Return True if this process is the primary instance."""
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
        self._handle = handle
        if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(handle)
            self._handle = None
            return False
        return True

    def release(self) -> None:
        if self._handle is not None:
            ctypes.windll.kernel32.CloseHandle(self._handle)
            self._handle = None

    def notify_existing(self) -> None:
        """Ask the running instance to show its settings window."""
        ctypes.windll.user32.SendNotifyMessageW(0xFFFF, _WM_SHOW_SETTINGS, 0, 0)


class ShowSettingsEventFilter(QAbstractNativeEventFilter):
    """Receive the broadcast show-settings message on the primary instance."""

    def __init__(self, on_show: Callable[[], None]) -> None:
        super().__init__()
        self._on_show = on_show

    def nativeEventFilter(  # noqa: N802
        self,
        event_type: QByteArray | bytes | bytearray,
        message: int,
    ) -> tuple[bool, int]:
        if bytes(event_type) != b"windows_generic_MSG":
            return False, 0
        msg = MSG.from_address(int(message))
        if msg.message == _WM_SHOW_SETTINGS:
            self._on_show()
            return True, 0
        return False, 0

