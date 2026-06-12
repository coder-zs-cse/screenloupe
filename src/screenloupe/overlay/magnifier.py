"""Live magnifier overlay and fit-to-screen geometry."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from PyQt6.QtCore import QRect, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen, QPixmap, QScreen
from PyQt6.QtWidgets import QWidget

from screenloupe.capture.exclusion import set_capture_excluded
from screenloupe.overlay.win32_window import make_overlay, prepare_overlay
from screenloupe.platformwin.dpi import physical_to_logical

logger = logging.getLogger(__name__)

ACCENT = QColor(79, 195, 247, 89)  # 35% alpha (docs/03)
CORNER_RADIUS = 8
BADGE_HIDE_MS = 2500


@dataclass(frozen=True)
class Rect:
    """Physical-pixel rectangle."""

    x: int
    y: int
    w: int
    h: int


def qrect_to_rect(rect: QRect) -> Rect:
    return Rect(rect.x(), rect.y(), rect.width(), rect.height())


def rect_to_qrect(rect: Rect) -> QRect:
    return QRect(rect.x, rect.y, rect.w, rect.h)


def fit_geometry(sel: Rect, screen: Rect, max_zoom: float) -> tuple[Rect, float]:
    """Largest aspect-preserving projection of sel that fits screen."""
    s = min(screen.w / sel.w, screen.h / sel.h, max_zoom)
    s = max(s, 1.0)
    w, h = round(sel.w * s), round(sel.h * s)
    x = screen.x + (screen.w - w) // 2
    y = screen.y + (screen.h - h) // 2
    return Rect(x, y, w, h), s


def fixed_geometry(sel: Rect, screen: Rect, zoom: float) -> tuple[Rect, float]:
    """Scale by exactly ``zoom``, clamped to fit on screen (never shrink below 1.0)."""
    s = max(zoom, 1.0)
    s = min(s, screen.w / sel.w, screen.h / sel.h)
    w, h = round(sel.w * s), round(sel.h * s)
    x = screen.x + (screen.w - w) // 2
    y = screen.y + (screen.h - h) // 2
    return Rect(x, y, w, h), s


class MagnifierOverlay(QWidget):
    """Live magnified projection of a screen region."""

    def __init__(
        self,
        overlay_rect: Rect,
        scale: float,
        opacity_percent: int,
        screen: QScreen,
    ) -> None:
        super().__init__()
        self._scale = scale
        self._screen = screen
        self._frame: QImage | None = None
        self._scaled: QPixmap | None = None
        self._show_badge = True

        prepare_overlay(self)
        logical = physical_to_logical(rect_to_qrect(overlay_rect), screen)
        self.setGeometry(logical)
        self.setWindowOpacity(opacity_percent / 100.0)

        self._badge_timer = QTimer(self)
        self._badge_timer.setSingleShot(True)
        self._badge_timer.timeout.connect(self._hide_badge)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        make_overlay(self)
        if not set_capture_excluded(int(self.winId())):
            logger.warning("Capture exclusion failed on magnifier overlay")
        self._badge_timer.start(BADGE_HIDE_MS)

    def set_opacity(self, opacity_percent: int) -> None:
        """Update overlay transparency (50–100)."""
        self.setWindowOpacity(opacity_percent / 100.0)

    def set_frame(self, image: QImage) -> None:
        self._frame = image
        self._scaled = QPixmap.fromImage(
            image.scaled(
                self.size(),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.update()

    def _hide_badge(self) -> None:
        self._show_badge = False
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), CORNER_RADIUS, CORNER_RADIUS)
        painter.setClipPath(path)

        if self._scaled is not None:
            painter.drawPixmap(0, 0, self._scaled)
        else:
            painter.fillRect(self.rect(), QColor(30, 33, 40))

        painter.setClipping(False)
        painter.setPen(QPen(ACCENT, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(
            0, 0, self.width() - 1, self.height() - 1, CORNER_RADIUS, CORNER_RADIUS
        )

        if self._show_badge:
            self._paint_badge(painter)

    def _paint_badge(self, painter: QPainter) -> None:
        text = f"{self._scale:.1f}x \u00b7 Esc to close"
        font = QFont("Segoe UI", 9)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        tw = metrics.horizontalAdvance(text) + 12
        th = metrics.height() + 8
        bx = self.width() - tw - 10
        by = self.height() - th - 10
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(30, 33, 40, 179))
        painter.drawRoundedRect(bx, by, tw, th, 4, 4)
        painter.setPen(QColor(232, 234, 237, 179))
        painter.drawText(bx + 6, by + metrics.ascent() + 4, text)
