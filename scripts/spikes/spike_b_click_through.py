"""Spike B — click-through overlay must not steal focus or block input.

Run:  py -3.13 scripts/spikes/spike_b_click_through.py

Uses setWindowOpacity + paintEvent (NOT WA_TranslucentBackground/stylesheet —
that combo is invisible on Windows PyQt6). No blocking target window; your real
desktop/apps stay visible under the overlay.

Before the overlay appears you get a prompt to position a browser on the RIGHT half.
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QApplication, QWidget

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2] / "src"))

from screenloupe.core.constants import (
    GWL_EXSTYLE,
    WS_EX_LAYERED,
    WS_EX_NOACTIVATE,
    WS_EX_TOOLWINDOW,
    WS_EX_TRANSPARENT,
)
from screenloupe.platformwin.dpi import set_process_dpi_aware

HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010
HOLD_MS = 25_000


def _apply_click_through_win32(hwnd: int) -> None:
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


def _has_ex_style(hwnd: int, flag: int) -> bool:
    ex = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    return bool(ex & flag)


def _foreground_hwnd() -> int:
    return int(ctypes.windll.user32.GetForegroundWindow())


def _hwnd_at_physical(x: int, y: int) -> int:
    class POINT(ctypes.Structure):
        _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

    pt = POINT(x, y)
    return int(ctypes.windll.user32.WindowFromPoint(pt))


def _click_screen_physical(x: int, y: int) -> None:
    user32 = ctypes.windll.user32
    user32.SetCursorPos(x, y)
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    user32.mouse_event(0x0004, 0, 0, 0, 0)


class CyanOverlay(QWidget):
    """Semi-transparent cyan panel — ghost-through via setWindowOpacity."""

    def __init__(self) -> None:
        super().__init__()
        self._fill = QColor(79, 195, 247)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), self._fill)


def main() -> int:
    set_process_dpi_aware()
    app = QApplication(sys.argv)

    screen = app.primaryScreen()
    if screen is None:
        print("FAIL: no primary screen")
        return 1

    geo = screen.geometry()
    half_w = geo.width() // 2

    print()
    print("=== Spike B setup ===")
    print("1. Open a browser (or any app) on the RIGHT half of your primary screen.")
    print("2. Leave the LEFT half unobstructed for comparison.")
    print("3. Press Enter here when ready — a semi-transparent CYAN overlay")
    print("   will cover only the RIGHT half for 25 seconds.")
    print()
    input("Press Enter to show overlay...")

    overlay = CyanOverlay()
    overlay.setWindowFlags(
        Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.WindowStaysOnTopHint
        | Qt.WindowType.Tool
    )
    overlay.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
    overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
    overlay.setGeometry(geo.x() + half_w, geo.y(), geo.width() - half_w, geo.height())
    overlay.setWindowOpacity(0.38)

    overlay.show()
    app.processEvents()
    overlay.repaint()
    app.processEvents()

    overlay_hwnd = int(overlay.winId())
    _apply_click_through_win32(overlay_hwnd)

    if not _has_ex_style(overlay_hwnd, WS_EX_TRANSPARENT):
        print("FAIL: WS_EX_TRANSPARENT not set")
        return 1
    if not _has_ex_style(overlay_hwnd, WS_EX_NOACTIVATE):
        print("FAIL: WS_EX_NOACTIVATE not set")
        return 1
    print("PASS (auto): Win32 ex-styles WS_EX_TRANSPARENT + WS_EX_NOACTIVATE set.")

    if _foreground_hwnd() == overlay_hwnd:
        print("FAIL: overlay is foreground immediately after show")
        return 1
    print("PASS (auto): overlay did not take foreground on show.")

    dpr = screen.devicePixelRatio()
    click_x = int((geo.x() + half_w + (geo.width() - half_w) // 2) * dpr)
    click_y = int((geo.y() + geo.height() // 2) * dpr)

    hit_hwnd = _hwnd_at_physical(click_x, click_y)
    if hit_hwnd == overlay_hwnd:
        print("FAIL: WindowFromPoint returned overlay hwnd (not click-through)")
        return 1
    print(f"PASS (auto): WindowFromPoint through overlay -> hwnd {hit_hwnd} (not overlay).")

    _click_screen_physical(click_x, click_y)
    app.processEvents()

    if _foreground_hwnd() == overlay_hwnd:
        print("FAIL: overlay hwnd became foreground after click")
        return 1
    print("PASS (auto): overlay did not take foreground after click.")

    print()
    print("MANUAL CHECK (25 s) — under the CYAN right half:")
    print("  - You should SEE the browser/content through the tint.")
    print("  - Click a link — browser must respond.")
    print("  - Scroll — page must move.")
    print("  - Type in an input — keystrokes must land in the browser.")
    print("  - Overlay must never show a focused title bar or text caret.")
    print()

    QTimer.singleShot(HOLD_MS, app.quit)
    code = app.exec()

    print("PASS: Spike B automated checks passed.")
    print("Confirm the manual checks above succeeded before closing the Phase 1 gate.")
    return 0 if code == 0 else code


if __name__ == "__main__":
    raise SystemExit(main())
