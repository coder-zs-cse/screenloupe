"""Cursor-follow lens overlay and geometry."""

from __future__ import annotations

import logging

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen, QPixmap, QScreen
from PyQt6.QtWidgets import QWidget

from screenloupe.capture.exclusion import set_capture_excluded
from screenloupe.core.config import LensShape
from screenloupe.overlay.magnifier import Rect, rect_to_qrect
from screenloupe.overlay.win32_window import make_overlay, prepare_overlay
from screenloupe.platformwin.dpi import physical_to_logical

logger = logging.getLogger(__name__)

ACCENT = QColor(79, 195, 247)
ROUNDED_RADIUS = 12


def lens_geometry(
    cursor_x: int,
    cursor_y: int,
    radius: int,
    zoom_percent: int,
    screen: Rect,
) -> tuple[Rect, Rect]:
    """Return (source_rect, overlay_rect) in physical pixels.

    Source is a square of side ``2*radius/zoom`` centered on the cursor, clamped
    to screen bounds (position only — size stays truthful at edges).
    Overlay is ``2*radius`` square centered on the cursor.
    """
    zoom = zoom_percent / 100.0
    viewport = 2 * radius
    source_side = max(1, round(viewport / zoom))

    overlay = Rect(cursor_x - radius, cursor_y - radius, viewport, viewport)

    sx = cursor_x - source_side // 2
    sy = cursor_y - source_side // 2
    sx = max(screen.x, min(sx, screen.x + screen.w - source_side))
    sy = max(screen.y, min(sy, screen.y + screen.h - source_side))
    source = Rect(sx, sy, source_side, source_side)
    return source, overlay


class LensOverlay(QWidget):
    """Hold-to-activate lens centered on the cursor."""

    def __init__(self, shape: LensShape, screen: QScreen) -> None:
        super().__init__()
        self._shape = shape
        self._screen = screen
        self._scaled: QPixmap | None = None

        prepare_overlay(self)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        make_overlay(self)
        if not set_capture_excluded(int(self.winId())):
            logger.warning("Capture exclusion failed on lens overlay")

    def move_to(self, overlay_rect: Rect) -> None:
        """Reposition the lens viewport (physical pixels)."""
        logical = physical_to_logical(rect_to_qrect(overlay_rect), self._screen)
        self.setGeometry(logical)

    def set_frame(self, image: QImage) -> None:
        self._scaled = QPixmap.fromImage(
            image.scaled(
                self.size(),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.FastTransformation,
            )
        )
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        w, h = self.width(), self.height()
        if self._shape == LensShape.CIRCLE:
            path.addEllipse(0, 0, w, h)
        else:
            path.addRoundedRect(0, 0, w, h, ROUNDED_RADIUS, ROUNDED_RADIUS)

        painter.setClipPath(path)
        if self._scaled is not None:
            painter.drawPixmap(0, 0, self._scaled)
        else:
            painter.fillRect(self.rect(), QColor(30, 33, 40))

        painter.setClipping(False)
        painter.setPen(QPen(ACCENT, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if self._shape == LensShape.CIRCLE:
            painter.drawEllipse(1, 1, w - 2, h - 2)
        else:
            painter.drawRoundedRect(1, 1, w - 2, h - 2, ROUNDED_RADIUS, ROUNDED_RADIUS)
