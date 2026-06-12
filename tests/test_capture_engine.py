"""Unit tests for capture engine helpers and lifecycle."""

from __future__ import annotations

from screenloupe.capture.engine import rect_to_monitor
from screenloupe.overlay.magnifier import Rect


def test_rect_to_monitor() -> None:
    region = Rect(x=100, y=50, w=600, h=1000)
    assert rect_to_monitor(region) == {
        "left": 100,
        "top": 50,
        "width": 600,
        "height": 1000,
    }
