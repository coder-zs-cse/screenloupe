"""Unit tests for AppState transition table."""

from __future__ import annotations

import pytest

from screenloupe.core.state import AppState, can_transition


@pytest.mark.parametrize(
    ("from_state", "to_state", "expected"),
    [
        (AppState.IDLE, AppState.SELECTING, True),
        (AppState.IDLE, AppState.LENS, True),
        (AppState.IDLE, AppState.DISABLED, True),
        (AppState.SELECTING, AppState.MAGNIFYING, True),
        (AppState.SELECTING, AppState.IDLE, True),
        (AppState.MAGNIFYING, AppState.IDLE, True),
        (AppState.MAGNIFYING, AppState.SELECTING, True),  # E2 Alt+M restart
        (AppState.LENS, AppState.IDLE, True),
        (AppState.DISABLED, AppState.IDLE, True),
        (AppState.IDLE, AppState.MAGNIFYING, False),
        (AppState.MAGNIFYING, AppState.LENS, False),  # E3
        (AppState.SELECTING, AppState.LENS, False),
        (AppState.DISABLED, AppState.SELECTING, False),
    ],
)
def test_can_transition(from_state: AppState, to_state: AppState, expected: bool) -> None:
    assert can_transition(from_state, to_state) is expected
