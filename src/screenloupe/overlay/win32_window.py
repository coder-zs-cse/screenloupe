"""Win32 extended styles for click-through, no-activate overlay windows."""

from __future__ import annotations

import ctypes

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget

from screenloupe.core.constants import (
    GWL_EXSTYLE,
    HWND_TOPMOST,
    SWP_NOACTIVATE,
    SWP_NOMOVE,
    SWP_NOSIZE,
    WS_EX_LAYERED,
    WS_EX_NOACTIVATE,
    WS_EX_TOOLWINDOW,
    WS_EX_TRANSPARENT,
)


def prepare_overlay(widget: QWidget) -> None:
    """Set Qt flags and attributes. Must be called BEFORE widget.show()."""
    widget.setWindowFlags(
        Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.WindowStaysOnTopHint
        | Qt.WindowType.Tool
    )
    widget.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
    widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)


def make_overlay(widget: QWidget) -> None:
    """Apply Win32 click-through styles. Call AFTER widget.show().

    Qt flags must already be set via prepare_overlay() before show().
    Changing Qt window flags after show() recreates the native hwnd and drops
    these ex-styles — do not call prepare_overlay() here.
    """
    hwnd = int(widget.winId())
    user32 = ctypes.windll.user32
    ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    user32.SetWindowLongW(
        hwnd,
        GWL_EXSTYLE,
        ex | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW,
    )
    user32.SetWindowPos(
        hwnd,
        HWND_TOPMOST,
        0,
        0,
        0,
        0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
    )
