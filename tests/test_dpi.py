"""Unit tests for logical <-> physical coordinate conversion."""

from __future__ import annotations

from PyQt6.QtCore import QRect

from screenloupe.platformwin.dpi import logical_to_physical, physical_to_logical


class _FakeScreen:
    """Minimal QScreen stand-in for pure math tests."""

    def __init__(self, dpr: float) -> None:
        self._dpr = dpr

    def devicePixelRatio(self) -> float:  # noqa: N802 — mirrors QScreen API
        return self._dpr


def test_logical_to_physical_dpr_1() -> None:
    screen = _FakeScreen(1.0)
    rect = QRect(100, 50, 200, 150)
    phys = logical_to_physical(rect, screen)
    assert phys == QRect(100, 50, 200, 150)


def test_logical_to_physical_dpr_125() -> None:
    screen = _FakeScreen(1.25)
    rect = QRect(100, 80, 200, 160)
    phys = logical_to_physical(rect, screen)
    assert phys == QRect(125, 100, 250, 200)


def test_logical_to_physical_dpr_150() -> None:
    screen = _FakeScreen(1.5)
    rect = QRect(10, 20, 100, 80)
    phys = logical_to_physical(rect, screen)
    assert phys == QRect(15, 30, 150, 120)


def test_physical_to_logical_dpr_125() -> None:
    screen = _FakeScreen(1.25)
    rect = QRect(125, 100, 250, 200)
    logical = physical_to_logical(rect, screen)
    assert logical == QRect(100, 80, 200, 160)


def test_round_trip_dpr_150() -> None:
    screen = _FakeScreen(1.5)
    original = QRect(40, 60, 300, 200)
    restored = physical_to_logical(logical_to_physical(original, screen), screen)
    assert restored == original
