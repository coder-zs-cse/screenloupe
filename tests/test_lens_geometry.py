"""Unit tests for lens source/overlay geometry."""

from __future__ import annotations

from screenloupe.overlay.lens import lens_geometry
from screenloupe.overlay.magnifier import Rect


def test_lens_geometry_centered() -> None:
    screen = Rect(0, 0, 1920, 1080)
    source, overlay = lens_geometry(500, 400, radius=220, zoom_percent=200, screen=screen)
    assert overlay == Rect(280, 180, 440, 440)
    assert source.w == 220
    assert source.h == 220
    assert source.x == 500 - 110
    assert source.y == 400 - 110


def test_lens_geometry_clamps_left_edge() -> None:
    screen = Rect(0, 0, 1920, 1080)
    source, overlay = lens_geometry(10, 400, radius=220, zoom_percent=200, screen=screen)
    assert source.x == 0
    assert source.w == 220
    assert overlay.x == 10 - 220


def test_lens_geometry_clamps_bottom_edge() -> None:
    screen = Rect(0, 0, 1920, 1080)
    source, _overlay = lens_geometry(500, 1070, radius=220, zoom_percent=200, screen=screen)
    assert source.y == 1080 - source.h


def test_lens_geometry_source_size_truthful_at_edge() -> None:
    screen = Rect(100, 50, 800, 600)
    source, _overlay = lens_geometry(150, 600, radius=100, zoom_percent=300, screen=screen)
    assert source.w == 67
    assert source.h == 67
