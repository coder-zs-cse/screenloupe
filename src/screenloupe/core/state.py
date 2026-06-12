"""AppState enum and allowed-transition guard table."""

from __future__ import annotations

from enum import Enum, auto


class AppState(Enum):
    IDLE = auto()
    SELECTING = auto()
    MAGNIFYING = auto()
    LENS = auto()
    DISABLED = auto()


ALLOWED_TRANSITIONS: dict[AppState, set[AppState]] = {
    AppState.IDLE: {AppState.SELECTING, AppState.LENS, AppState.DISABLED},
    AppState.SELECTING: {AppState.IDLE, AppState.MAGNIFYING},
    AppState.MAGNIFYING: {AppState.IDLE, AppState.SELECTING},
    AppState.LENS: {AppState.IDLE},
    AppState.DISABLED: {AppState.IDLE},
}


def can_transition(from_state: AppState, to_state: AppState) -> bool:
    """Return True if ``to_state`` is allowed from ``from_state``."""
    return to_state in ALLOWED_TRANSITIONS.get(from_state, set())
