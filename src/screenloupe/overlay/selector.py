"""Full-screen frozen-frame selector overlay."""

from __future__ import annotations

import ctypes
import logging

from PyQt6.QtCore import QPoint, QRect, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QCursor, QFont, QGuiApplication, QImage, QPainter, QPen, QScreen
from PyQt6.QtWidgets import QApplication, QWidget

from screenloupe.capture.exclusion import set_capture_excluded
from screenloupe.core.constants import (
    GWL_EXSTYLE,
    MIN_SELECTION_PX,
    WS_EX_NOACTIVATE,
    WS_EX_TOOLWINDOW,
)
from screenloupe.platformwin.dpi import logical_to_physical

logger = logging.getLogger(__name__)

ACCENT = QColor(79, 195, 247)
VEIL_ALPHA = 140  # ~55% black veil (docs/03)
HINT_DELAY_MS = 150
HANDLE_SIZE = 6


def normalize_rect(origin: QPoint, current: QPoint) -> QRect:
    """Return a normalized QRect from two widget-local points."""
    return QRect(origin, current).normalized()


def drag_distance(origin: QPoint, current: QPoint) -> int:
    """Chebyshev distance — matches snipping-tool-style short-click cancel."""
    return max(abs(current.x() - origin.x()), abs(current.y() - origin.y()))


def is_valid_selection(rect_physical: QRect, min_px: int = MIN_SELECTION_PX) -> bool:
    """True when both dimensions meet the minimum (E1)."""
    return rect_physical.width() >= min_px and rect_physical.height() >= min_px


def widget_rect_to_physical(rect: QRect, widget: QWidget, screen: QScreen) -> QRect:
    """Map a widget-local logical rect to global physical pixels."""
    global_logical = rect.translated(widget.mapToGlobal(QPoint(0, 0)))
    return logical_to_physical(global_logical, screen)


def physical_rect_to_frozen_source(
    rect_physical: QRect, mss_monitor: dict[str, int], frozen: QImage
) -> QRect:
    """Map a global physical rect to pixel coordinates inside the frozen frame."""
    x = rect_physical.x() - mss_monitor["left"]
    y = rect_physical.y() - mss_monitor["top"]
    x = max(0, min(x, frozen.width() - 1))
    y = max(0, min(y, frozen.height() - 1))
    w = min(rect_physical.width(), frozen.width() - x)
    h = min(rect_physical.height(), frozen.height() - y)
    return QRect(x, y, max(0, w), max(0, h))


def _apply_selector_win32(hwnd: int) -> None:
    """Topmost tool window without click-through (docs/02 § 2 exception)."""
    user32 = ctypes.windll.user32
    ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW)


class SelectorOverlay(QWidget):
    """Dimmed veil + rubber-band selection; emits region_selected in physical pixels."""

    region_selected = pyqtSignal(QRect)
    selection_cancelled = pyqtSignal()

    def __init__(
        self,
        frozen: QImage,
        screen: QScreen,
        mss_monitor: dict[str, int],
    ) -> None:
        super().__init__()
        self._frozen = frozen
        self._screen = screen
        self._mss_monitor = mss_monitor
        self._origin: QPoint | None = None
        self._current: QPoint | None = None
        self._show_hint = False

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setGeometry(screen.geometry())
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setMouseTracking(True)

        QTimer.singleShot(HINT_DELAY_MS, self._reveal_hint)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        hwnd = int(self.winId())
        _apply_selector_win32(hwnd)
        if not set_capture_excluded(hwnd):
            logger.warning("Capture exclusion failed on selector overlay")
        self.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
        self.activateWindow()
        self.raise_()

    def _reveal_hint(self) -> None:
        if self._origin is None:
            self._show_hint = True
            self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.drawImage(self.rect(), self._frozen)
        painter.fillRect(self.rect(), QColor(0, 0, 0, VEIL_ALPHA))

        if self._origin is not None and self._current is not None:
            sel = normalize_rect(self._origin, self._current)
            if sel.width() > 0 and sel.height() > 0:
                self._paint_torch(painter, sel)
                self._paint_chrome(painter, sel)

        if self._show_hint:
            self._paint_hint(painter)

    def _paint_torch(self, painter: QPainter, sel: QRect) -> None:
        phys = widget_rect_to_physical(sel, self, self._screen)
        src = physical_rect_to_frozen_source(phys, self._mss_monitor, self._frozen)
        if src.width() <= 0 or src.height() <= 0:
            return
        cropped = self._frozen.copy(src)
        painter.drawImage(sel, cropped)

    def _paint_chrome(self, painter: QPainter, sel: QRect) -> None:
        pen = QPen(ACCENT, 1)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(sel)

        hs = HANDLE_SIZE
        for cx, cy in (
            (sel.left(), sel.top()),
            (sel.right() - hs + 1, sel.top()),
            (sel.left(), sel.bottom() - hs + 1),
            (sel.right() - hs + 1, sel.bottom() - hs + 1),
        ):
            painter.fillRect(cx, cy, hs, hs, ACCENT)

        if self._current is not None:
            phys = widget_rect_to_physical(sel, self, self._screen)
            badge = f"{phys.width()} x {phys.height()} px"
            font = QFont("Segoe UI", 9)
            painter.setFont(font)
            metrics = painter.fontMetrics()
            tw = metrics.horizontalAdvance(badge) + 12
            th = metrics.height() + 8
            bx = self._current.x() + 16
            by = self._current.y() + 16
            if bx + tw > self.width():
                bx = self._current.x() - tw - 8
            if by + th > self.height():
                by = self._current.y() - th - 8
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(30, 33, 40, 217))
            painter.drawRoundedRect(bx, by, tw, th, 4, 4)
            painter.setPen(QColor(232, 234, 237))
            painter.drawText(bx + 6, by + metrics.ascent() + 4, badge)

    def _paint_hint(self, painter: QPainter) -> None:
        text = "Drag to magnify \u00b7 Esc to cancel"
        font = QFont("Segoe UI", 9)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        tw = metrics.horizontalAdvance(text) + 24
        th = metrics.height() + 12
        bx = (self.width() - tw) // 2
        by = 24
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(30, 33, 40, 217))
        painter.drawRoundedRect(bx, by, tw, th, 6, 6)
        painter.setPen(QColor(232, 234, 237))
        painter.drawText(bx + 12, by + metrics.ascent() + 6, text)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._show_hint = False
            self._origin = event.pos()
            self._current = event.pos()
            self.update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._origin is not None:
            self._current = event.pos()
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self._origin is not None:
            self._finish_selection(event.pos())
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self._cancel()
            return
        super().keyPressEvent(event)

    def _finish_selection(self, release_pos: QPoint) -> None:
        origin = self._origin
        if origin is None:
            return
        if drag_distance(origin, release_pos) < MIN_SELECTION_PX:
            self._cancel()
            return

        sel = normalize_rect(origin, release_pos)
        phys = widget_rect_to_physical(sel, self, self._screen)
        if is_valid_selection(phys):
            self.region_selected.emit(phys)
        else:
            self.selection_cancelled.emit()
        self.close()

    def cancel(self) -> None:
        """Public cancel entry (Esc hotkey from controller)."""
        self._cancel()

    def _cancel(self) -> None:
        self.selection_cancelled.emit()
        self.close()


def screen_at_cursor() -> QScreen:
    """Monitor where the cursor sits; primary-monitor fallback (docs/01 § 9)."""
    app = QApplication.instance()
    if app is None or not isinstance(app, QGuiApplication):
        raise RuntimeError("QApplication required")
    pos = QCursor.pos()
    screen = app.screenAt(pos)
    return screen if screen is not None else app.primaryScreen()
