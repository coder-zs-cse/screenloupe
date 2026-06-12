"""Per-monitor DPI awareness and logical↔physical coordinate conversion."""

from __future__ import annotations

import ctypes

from PyQt6.QtCore import QRect
from PyQt6.QtGui import QScreen

from screenloupe.core.constants import DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2


def set_process_dpi_aware() -> None:
    """Set Per-Monitor v2 DPI awareness. Must run before QApplication exists."""
    ctypes.windll.user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)


def logical_to_physical(rect: QRect, screen: QScreen) -> QRect:
    """Convert a Qt logical QRect to physical pixels for the given screen."""
    dpr = screen.devicePixelRatio()
    return QRect(
        round(rect.x() * dpr),
        round(rect.y() * dpr),
        round(rect.width() * dpr),
        round(rect.height() * dpr),
    )


def physical_to_logical(rect: QRect, screen: QScreen) -> QRect:
    """Convert a physical-pixel QRect to Qt logical coordinates."""
    dpr = screen.devicePixelRatio()
    return QRect(
        round(rect.x() / dpr),
        round(rect.y() / dpr),
        round(rect.width() / dpr),
        round(rect.height() / dpr),
    )
