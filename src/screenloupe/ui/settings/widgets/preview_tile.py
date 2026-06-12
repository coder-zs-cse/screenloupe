"""Live magnifier preview tile (static sample text)."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QFrame, QSizePolicy

SAMPLE = (
    "ScreenLoupe magnifies any region into a live, see-through overlay. "
    "Your cursor and real windows stay underneath."
)


class PreviewTile(QFrame):
    """Renders sample text at the chosen zoom and opacity."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setProperty("card", True)
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._zoom_percent = 200
        self._opacity_percent = 92

    def set_zoom(self, zoom_percent: int) -> None:
        self._zoom_percent = zoom_percent
        self.update()

    def set_opacity(self, opacity_percent: int) -> None:
        self._opacity_percent = opacity_percent
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(30, 33, 40))

        scale = self._zoom_percent / 100.0
        base_pt = 11
        font = QFont("Segoe UI", max(8, int(base_pt * scale)))
        painter.setFont(font)
        painter.setPen(QPen(QColor(232, 234, 237, int(255 * self._opacity_percent / 100))))

        margin = 14
        painter.drawText(
            margin,
            margin + painter.fontMetrics().ascent(),
            self.width() - 2 * margin,
            self.height() - 2 * margin,
            int(Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap),
            SAMPLE,
        )
        painter.setPen(QPen(QColor(79, 195, 247, 90), 1))
        painter.drawRoundedRect(0, 0, self.width() - 1, self.height() - 1, 8, 8)
