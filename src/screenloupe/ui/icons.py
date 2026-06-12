"""Tray and window icons (programmatic fallback when assets/ is absent)."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap


def _repo_assets_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "assets"


def asset_path(name: str) -> Path | None:
    """Resolve an asset file for dev or PyInstaller bundle."""
    base = (
        Path(sys._MEIPASS) / "assets"  # type: ignore[attr-defined]
        if getattr(sys, "frozen", False)
        else _repo_assets_dir()
    )
    path = base / name
    return path if path.is_file() else None


def _draw_tray_pixmap(enabled: bool, size: int = 32) -> QPixmap:
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    rim = QColor(79, 195, 247) if enabled else QColor(130, 136, 145)
    painter.setPen(QPen(rim, max(2, size // 14)))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    margin = size // 5
    painter.drawEllipse(margin, margin, size - 2 * margin, size - 2 * margin)
    painter.drawLine(size // 2 + 2, size // 2 + 2, size - margin, size - margin)
    painter.end()
    return pix


def tray_icon(enabled: bool) -> QIcon:
    """Return tray icon for enabled/disabled state."""
    suffix = "on" if enabled else "off"
    path = asset_path(f"tray_{suffix}.png")
    if path is not None:
        return QIcon(str(path))
    return QIcon(_draw_tray_pixmap(enabled))


def app_icon() -> QIcon:
    """Return application window icon."""
    path = asset_path("icon.ico")
    if path is not None:
        return QIcon(str(path))
    return QIcon(_draw_tray_pixmap(True, 64))
