"""SetWindowDisplayAffinity — exclude overlay windows from screen capture."""

from __future__ import annotations

import ctypes

from screenloupe.core.constants import WDA_EXCLUDEFROMCAPTURE


def set_capture_excluded(hwnd: int) -> bool:
    """Exclude hwnd from BitBlt/DXGI capture. Call after QWidget.show()."""
    return bool(ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE))
