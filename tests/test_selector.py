"""Unit tests for selector geometry helpers."""

from __future__ import annotations

from PyQt6.QtCore import QPoint, QRect

from screenloupe.overlay.selector import (
    drag_distance,
    is_valid_selection,
    normalize_rect,
    physical_rect_to_frozen_source,
)


def test_normalize_rect() -> None:
    assert normalize_rect(QPoint(100, 80), QPoint(50, 120)) == QRect(51, 80, 49, 41)


def test_drag_distance_short_click() -> None:
    assert drag_distance(QPoint(10, 10), QPoint(14, 12)) == 4


def test_is_valid_selection() -> None:
    assert is_valid_selection(QRect(0, 0, 100, 50)) is True
    assert is_valid_selection(QRect(0, 0, 8, 8)) is True
    assert is_valid_selection(QRect(0, 0, 7, 20)) is False
    assert is_valid_selection(QRect(0, 0, 20, 7)) is False


def test_physical_rect_to_frozen_source() -> None:
    from PyQt6.QtGui import QImage

    mon = {"left": 100, "top": 50, "width": 1920, "height": 1080}
    image = QImage(1920, 1080, QImage.Format.Format_RGB888)
    src = physical_rect_to_frozen_source(QRect(200, 150, 400, 300), mon, image)
    assert src == QRect(100, 100, 400, 300)
