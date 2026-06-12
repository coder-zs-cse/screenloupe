"""Spike A — WDA_EXCLUDEFROMCAPTURE must hide overlay from mss capture.

Run:  py -3.13 scripts/spikes/spike_a_capture_exclusion.py

Two-phase proof (avoids false pass when the window is invisible):
  1. WITHOUT exclusion: mss grab must contain saturated-red pixels (overlay visible).
  2. WITH exclusion:    same grab must contain zero saturated-red pixels.

Also holds the red window on screen 8 s for a visual sanity check.
"""

from __future__ import annotations

import ctypes
import sys

import mss
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QApplication, QWidget

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2] / "src"))

from screenloupe.capture.exclusion import set_capture_excluded
from screenloupe.platformwin.dpi import logical_to_physical, set_process_dpi_aware

MIN_BUILD = 19041
RED_THRESHOLD = 200
NON_RED_MAX = 80
MIN_RED_BEFORE_EXCLUSION = 5000  # overlay must paint a mostly-red region


def _check_os() -> None:
    build = sys.getwindowsversion().build
    if build < MIN_BUILD:
        print(f"FAIL: Windows build {build} < {MIN_BUILD} (capture exclusion unavailable)")
        sys.exit(1)
    print(f"OS build {build} OK (>= {MIN_BUILD})")


def _is_window_visible(hwnd: int) -> bool:
    return bool(ctypes.windll.user32.IsWindowVisible(hwnd))


def _count_saturated_red(bgra: bytes, width: int, height: int) -> int:
    count = 0
    stride = width * 4
    for y in range(height):
        row = y * stride
        for x in range(width):
            i = row + x * 4
            b, g, r = bgra[i], bgra[i + 1], bgra[i + 2]
            if r >= RED_THRESHOLD and g <= NON_RED_MAX and b <= NON_RED_MAX:
                count += 1
    return count


class RedOverlay(QWidget):
    """Solid red panel; opacity via setWindowOpacity (reliable on Windows)."""

    def __init__(self) -> None:
        super().__init__()
        self._fill = QColor(255, 0, 0)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), self._fill)


def main() -> int:
    _check_os()
    set_process_dpi_aware()
    app = QApplication(sys.argv)

    screen = app.primaryScreen()
    if screen is None:
        print("FAIL: no primary screen")
        return 1

    screen_geo = screen.geometry()
    overlay_w, overlay_h = 400, 300
    logical_x = screen_geo.x() + (screen_geo.width() - overlay_w) // 2
    logical_y = screen_geo.y() + (screen_geo.height() - overlay_h) // 2

    overlay = RedOverlay()
    overlay.setWindowFlags(
        Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.WindowStaysOnTopHint
        | Qt.WindowType.Tool
    )
    overlay.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
    overlay.setGeometry(logical_x, logical_y, overlay_w, overlay_h)
    overlay.setWindowOpacity(0.82)

    overlay.show()
    app.processEvents()
    overlay.repaint()
    app.processEvents()

    hwnd = int(overlay.winId())
    if not _is_window_visible(hwnd):
        print("FAIL: overlay hwnd is not visible to Win32 IsWindowVisible")
        return 1

    phys = logical_to_physical(overlay.frameGeometry(), screen)
    region = {
        "left": phys.x(),
        "top": phys.y(),
        "width": phys.width(),
        "height": phys.height(),
    }

    print(f"Overlay logical: {logical_x},{logical_y}  {overlay_w}x{overlay_h}")
    print(f"mss region (physical): {region}")
    print("You should see a RED rectangle at screen center for 8 seconds.")

    with mss.MSS() as sct:
        before = sct.grab(region)
        red_before = _count_saturated_red(before.bgra, before.width, before.height)
        print(f"Phase 1 (no exclusion): saturated-red pixels = {red_before}")

        if red_before < MIN_RED_BEFORE_EXCLUSION:
            print(
                "FAIL: overlay not visible to mss before exclusion — "
                "cannot trust a zero-pixel Phase 2 result."
            )
            QTimer.singleShot(8000, app.quit)
            app.exec()
            return 1

        if not set_capture_excluded(hwnd):
            print("FAIL: SetWindowDisplayAffinity returned False")
            return 1

        after = sct.grab(region)
        red_after = _count_saturated_red(after.bgra, after.width, after.height)
        print(f"Phase 2 (with exclusion): saturated-red pixels = {red_after}")

    QTimer.singleShot(8000, app.quit)
    app.exec()

    if red_after == 0:
        print("PASS: Spike A — visible on screen AND excluded from mss capture.")
        return 0

    print("FAIL: Spike A — red pixels still present after exclusion.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
