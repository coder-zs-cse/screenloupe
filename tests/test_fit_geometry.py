"""Unit tests for magnifier fit/fixed geometry."""

from __future__ import annotations

from screenloupe.overlay.magnifier import Rect, fit_geometry, fixed_geometry


def test_fit_geometry_wide_selection() -> None:
    sel = Rect(0, 0, 200, 100)
    screen = Rect(0, 0, 1920, 1080)
    overlay, scale = fit_geometry(sel, screen, max_zoom=4.0)
    assert scale == 4.0
    assert overlay.w == 800
    assert overlay.h == 400


def test_fit_geometry_tall_selection() -> None:
    sel = Rect(0, 0, 100, 400)
    screen = Rect(0, 0, 1920, 1080)
    overlay, scale = fit_geometry(sel, screen, max_zoom=10.0)
    assert scale == 2.7
    assert overlay.w == 270
    assert overlay.h == 1080


def test_fit_geometry_near_screen_size_never_shrink() -> None:
    sel = Rect(0, 0, 1920, 1080)
    screen = Rect(0, 0, 1920, 1080)
    overlay, scale = fit_geometry(sel, screen, max_zoom=4.0)
    assert scale == 1.0
    assert overlay.w == 1920
    assert overlay.h == 1080


def test_fit_geometry_max_zoom_clamp() -> None:
    sel = Rect(0, 0, 50, 50)
    screen = Rect(0, 0, 1920, 1080)
    overlay, scale = fit_geometry(sel, screen, max_zoom=2.0)
    assert scale == 2.0
    assert overlay.w == 100
    assert overlay.h == 100


def test_fit_geometry_centered_on_screen() -> None:
    sel = Rect(0, 0, 100, 100)
    screen = Rect(100, 50, 1000, 800)
    overlay, _scale = fit_geometry(sel, screen, max_zoom=4.0)
    assert overlay.x == 100 + (1000 - 400) // 2
    assert overlay.y == 50 + (800 - 400) // 2


def test_fixed_geometry_clamped_to_screen() -> None:
    sel = Rect(0, 0, 100, 100)
    screen = Rect(0, 0, 500, 500)
    overlay, scale = fixed_geometry(sel, screen, zoom=5.0)
    assert scale == 5.0
    assert overlay.w == 500
    assert overlay.h == 500
