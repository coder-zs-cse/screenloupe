"""Global hotkey hooks via keyboard library."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

import keyboard
from PyQt6.QtCore import QObject, pyqtSignal

from screenloupe.core.config import HotkeyConfig
from screenloupe.core.constants import LENS_HOTKEY_ENABLED

logger = logging.getLogger(__name__)

HookRemover = Callable[[], None]

# keyboard.is_pressed('alt') is unreliable on Windows — check sided names too.
_MODIFIER_ALIASES: dict[str, tuple[str, ...]] = {
    "alt": ("alt", "left alt", "right alt"),
    "ctrl": ("ctrl", "left ctrl", "right ctrl"),
    "shift": ("shift", "left shift", "right shift"),
    "win": ("win", "left windows", "right windows"),
}

_LENS_RELEASE_DEBOUNCE_S = 0.2


def _parse_combo(combo: str) -> tuple[frozenset[str], str]:
    parts = [p.strip().lower() for p in combo.replace(" ", "").split("+") if p.strip()]
    if not parts:
        return frozenset(), "n"
    return frozenset(parts[:-1]), parts[-1]


def _modifier_release_keys(modifiers: frozenset[str]) -> list[str]:
    keys: list[str] = []
    for modifier in modifiers:
        keys.extend(_MODIFIER_ALIASES.get(modifier, (modifier,)))
    return keys


class HotkeyManager(QObject):
    """Registers combos from config; emits Qt signals for AppController."""

    magnify_requested = pyqtSignal()
    lens_pressed = pyqtSignal()
    lens_released = pyqtSignal()
    escape_pressed = pyqtSignal()
    toggle_requested = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._dismiss_combo = "esc"
        self._lens_combo = "alt+n"
        self._lens_modifiers: frozenset[str] = frozenset({"alt"})
        self._lens_trigger = "n"
        self._esc_active = False
        self._lens_active = False
        self._lens_press_mono = 0.0
        self._removers: list[HookRemover] = []
        self._esc_remover: HookRemover | None = None
        self._last_hotkeys: HotkeyConfig | None = None

    def register_from_config(self, hotkeys: HotkeyConfig) -> None:
        """Register all hotkeys from HotkeyConfig."""
        self._last_hotkeys = hotkeys
        self._clear_hooks()

        self._dismiss_combo = hotkeys.dismiss
        self._lens_combo = hotkeys.lens
        self._lens_modifiers, self._lens_trigger = _parse_combo(hotkeys.lens)

        self._removers.append(
            keyboard.add_hotkey(
                hotkeys.magnify,
                self._emit_from_hook(self.magnify_requested, "magnify"),
                suppress=False,
            )
        )
        self._removers.append(
            keyboard.add_hotkey(
                hotkeys.master_toggle,
                self._emit_from_hook(self.toggle_requested, "toggle"),
                suppress=False,
            )
        )
        if LENS_HOTKEY_ENABLED:
            self._removers.append(
                keyboard.add_hotkey(
                    hotkeys.lens,
                    self._on_lens_combo_down,
                    suppress=False,
                )
            )
            self._removers.append(
                keyboard.on_release_key(
                    self._lens_trigger, self._on_lens_trigger_up, suppress=False
                )
            )
            for modifier_key in _modifier_release_keys(self._lens_modifiers):
                self._removers.append(
                    keyboard.on_release_key(
                        modifier_key, self._on_lens_modifier_up, suppress=False
                    )
                )
            logger.info("Hotkeys registered (lens=%s)", hotkeys.lens)
        else:
            logger.info("Hotkeys registered (lens disabled for v0.1)")

    def set_escape_active(self, active: bool) -> None:
        """Dynamically hook/unhook Esc suppression."""
        if active == self._esc_active:
            return
        if active:
            self._esc_remover = keyboard.add_hotkey(
                self._dismiss_combo,
                self._emit_from_hook(self.escape_pressed, "escape"),
                suppress=True,
            )
            self._esc_active = True
        else:
            _safe_remove(self._esc_remover)
            self._esc_remover = None
            self._esc_active = False

    def reset_lens_hold(self) -> None:
        """Clear lens hold tracking when AppController dismisses without a release hook."""
        self._lens_active = False

    def pause(self) -> None:
        """Unregister hooks while a hotkey recorder is active."""
        self._clear_hooks()

    def resume(self) -> None:
        """Re-register hooks after hotkey recording."""
        if self._last_hotkeys is not None:
            self.register_from_config(self._last_hotkeys)

    def unregister_all(self) -> None:
        """Remove all registered hotkeys."""
        self._clear_hooks()

    def _clear_hooks(self) -> None:
        """Remove hooks registered by this manager (avoids keyboard.unhook_all_hotkeys)."""
        self.set_escape_active(False)
        for remover in self._removers:
            _safe_remove(remover)
        self._removers.clear()
        self._lens_active = False

    def _on_lens_combo_down(self) -> None:
        if not self._lens_active:
            self._lens_active = True
            self._lens_press_mono = time.monotonic()
            self._emit_from_hook(self.lens_pressed, "lens_down")()

    def _on_lens_trigger_up(self, _event: keyboard.KeyboardEvent) -> None:
        self._maybe_release_lens("lens_trigger_up")

    def _on_lens_modifier_up(self, _event: keyboard.KeyboardEvent) -> None:
        self._maybe_release_lens("lens_modifier_up")

    def _maybe_release_lens(self, reason: str) -> None:
        if not self._lens_active:
            logger.debug("lens release ignored (not active): %s", reason)
            return
        elapsed = time.monotonic() - self._lens_press_mono
        if elapsed < _LENS_RELEASE_DEBOUNCE_S:
            logger.debug("lens release ignored (debounce %.0fms): %s", elapsed * 1000, reason)
            return
        self._release_lens(reason)

    def _release_lens(self, reason: str) -> None:
        if self._lens_active:
            self._lens_active = False
            self._emit_from_hook(self.lens_released, reason)()

    def _emit_from_hook(self, signal: pyqtSignal, name: str) -> Callable[[], None]:
        """Emit a Qt signal from the keyboard hook thread (queued to main thread)."""

        def emit() -> None:
            logger.info("hotkey hook fired: %s", name)
            signal.emit()

        return emit


def _safe_remove(remover: HookRemover | None) -> None:
    if remover is None:
        return
    try:
        remover()
    except Exception:
        logger.debug("Failed to remove keyboard hook", exc_info=True)
