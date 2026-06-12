"""QTimer-driven mss capture engine."""

from __future__ import annotations

import logging
from typing import Any

import mss
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtGui import QImage

from screenloupe.overlay.magnifier import Rect

logger = logging.getLogger(__name__)


def rect_to_monitor(region: Rect) -> dict[str, int]:
    """Convert a physical Rect to an mss monitor dict (reused across ticks)."""
    return {"left": region.x, "top": region.y, "width": region.w, "height": region.h}


class CaptureEngine(QObject):
    """Grabs a screen region at a target refresh rate; emits frame_ready."""

    frame_ready = pyqtSignal(QImage)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._sct: mss.MSS | None = None
        self._monitor: dict[str, int] | None = None
        self._busy = False

    def start(self, region: Rect, hz: int) -> None:
        """Begin capturing ``region`` at ``hz`` frames per second."""
        self.stop()
        self._sct = mss.MSS()
        self._monitor = rect_to_monitor(region)
        interval_ms = max(1, 1000 // hz)
        self._timer.start(interval_ms)
        logger.debug("CaptureEngine started %s @ %d Hz", region, hz)

    def retarget(self, region: Rect) -> None:
        """Move capture source without restarting the timer (lens mode)."""
        self._monitor = rect_to_monitor(region)

    def stop(self) -> None:
        """Stop capture and release resources."""
        self._timer.stop()
        if self._sct is not None:
            self._sct.close()
            self._sct = None
        self._monitor = None
        self._busy = False

    def _on_tick(self) -> None:
        if self._busy:
            return
        if self._sct is None or self._monitor is None:
            return

        self._busy = True
        try:
            shot = self._sct.grab(self._monitor)
            image = _shot_to_qimage(shot)
            self.frame_ready.emit(image)
        except Exception:
            logger.exception("Capture tick failed")
        finally:
            self._busy = False


def _shot_to_qimage(shot: Any) -> QImage:
    """mss RGB bytes -> owned QImage. Fast path validated in Spike C."""
    return QImage(
        shot.rgb,
        shot.width,
        shot.height,
        shot.width * 3,
        QImage.Format.Format_RGB888,
    ).copy()
