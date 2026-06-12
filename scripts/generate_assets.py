"""Generate assets/ icons and Inno wizard banner (run before build)."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QIcon, QImage, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QApplication


def _draw_loupe(size: int, enabled: bool = True) -> QPixmap:
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    rim = QColor(79, 195, 247) if enabled else QColor(130, 136, 145)
    pen_w = max(2, size // 14)
    painter.setPen(QPen(rim, pen_w))
    margin = size // 5
    painter.drawEllipse(margin, margin, size - 2 * margin, size - 2 * margin)
    painter.drawLine(size // 2 + 2, size // 2 + 2, size - margin, size - margin)
    painter.end()
    return pix


def _write_icon(path: Path) -> None:
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(_draw_loupe(size))
    icon.pixmap(256).save(str(path), "ICO")


def _write_banner(path: Path) -> None:
    w, h = 164, 314
    image = QImage(w, h, QImage.Format.Format_RGB32)
    image.fill(QColor(22, 24, 29))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor(79, 195, 247), 3))
    painter.drawEllipse(42, 80, 80, 80)
    painter.drawLine(108, 148, 140, 180)
    painter.setPen(QColor(232, 234, 237))
    font = painter.font()
    font.setPointSize(11)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(20, 220, "ScreenLoupe")
    painter.end()
    image.save(str(path), "BMP")


def main() -> None:
    _app = QApplication(sys.argv)
    root = Path(__file__).resolve().parents[1]
    assets = root / "assets"
    assets.mkdir(exist_ok=True)
    _write_icon(assets / "icon.ico")
    _draw_loupe(32, True).save(str(assets / "tray_on.png"), "PNG")
    _draw_loupe(32, False).save(str(assets / "tray_off.png"), "PNG")
    _write_banner(assets / "wizard-banner.bmp")
    print(f"Assets written to {assets}")


if __name__ == "__main__":
    main()
