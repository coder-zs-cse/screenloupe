"""Full-monitor mss grab for frozen-frame selector."""

from __future__ import annotations

import mss
from PyQt6.QtGui import QImage, QScreen

from screenloupe.capture.engine import _shot_to_qimage
from screenloupe.platformwin.dpi import logical_to_physical


def mss_monitor_for_screen(sct: mss.MSS, screen: QScreen) -> dict[str, int]:
    """Map a QScreen to the matching mss monitor dict (physical pixels)."""
    target = logical_to_physical(screen.geometry(), screen)
    for mon in sct.monitors[1:]:
        if (
            mon["left"] == target.x()
            and mon["top"] == target.y()
            and mon["width"] == target.width()
            and mon["height"] == target.height()
        ):
            return mon
    return sct.monitors[1]


def grab_monitor_frame(screen: QScreen) -> tuple[QImage, dict[str, int]]:
    """Capture one frozen frame of ``screen``; returns image + mss monitor dict."""
    with mss.MSS() as sct:
        mon = mss_monitor_for_screen(sct, screen)
        shot = sct.grab(mon)
        return _shot_to_qimage(shot), mon
