"""AppController — sole owner of AppState and overlay lifecycle."""

from __future__ import annotations

import contextlib
import logging
import sys
from collections.abc import Callable

from PyQt6.QtCore import QRect, Qt, QTimer
from PyQt6.QtGui import QGuiApplication, QScreen
from PyQt6.QtWidgets import QApplication

from screenloupe.capture.engine import CaptureEngine
from screenloupe.capture.monitor import grab_monitor_frame
from screenloupe.core.config import AppConfig, ConfigStore, ZoomMode
from screenloupe.core.state import AppState, can_transition
from screenloupe.hotkeys.manager import HotkeyManager
from screenloupe.overlay.lens import LensOverlay, lens_geometry
from screenloupe.overlay.magnifier import (
    MagnifierOverlay,
    fit_geometry,
    fixed_geometry,
    qrect_to_rect,
)
from screenloupe.overlay.selector import SelectorOverlay, screen_at_cursor
from screenloupe.platformwin.cursor import get_cursor_pos_physical
from screenloupe.platformwin.dpi import logical_to_physical
from screenloupe.platformwin.startup import set_run_at_startup

logger = logging.getLogger(__name__)


def screen_for_physical_rect(rect: QRect) -> QScreen:
    """Return the monitor containing the center of a physical-pixel rect."""
    app = QApplication.instance()
    if app is None or not isinstance(app, QGuiApplication):
        raise RuntimeError("QApplication required")
    cx = rect.x() + rect.width() // 2
    cy = rect.y() + rect.height() // 2
    for screen in app.screens():
        phys = logical_to_physical(screen.geometry(), screen)
        if phys.contains(cx, cy):
            return screen
    primary = app.primaryScreen()
    if primary is None:
        raise RuntimeError("No primary screen")
    return primary


def screen_at_physical_point(x: int, y: int) -> QScreen:
    """Return the monitor containing physical pixel (x, y)."""
    app = QApplication.instance()
    if app is None or not isinstance(app, QGuiApplication):
        raise RuntimeError("QApplication required")
    for screen in app.screens():
        phys = logical_to_physical(screen.geometry(), screen)
        if phys.contains(x, y):
            return screen
    primary = app.primaryScreen()
    if primary is None:
        raise RuntimeError("No primary screen")
    return primary


class AppController:
    """Routes hotkey events to overlay lifecycle."""

    def __init__(self) -> None:
        self._state = AppState.IDLE
        self._config_store = ConfigStore()
        self._hotkeys = HotkeyManager()
        self._engine = CaptureEngine()
        self._selector: SelectorOverlay | None = None
        self._magnifier: MagnifierOverlay | None = None
        self._lens: LensOverlay | None = None
        self._lens_follow_timer = QTimer()
        self._lens_follow_timer.timeout.connect(self._on_lens_follow_tick)
        self._ui_refresh: Callable[[], None] | None = None

    def set_ui_refresh(self, callback: Callable[[], None]) -> None:
        self._ui_refresh = callback

    def pause_hotkeys(self) -> None:
        self._hotkeys.pause()

    def resume_hotkeys(self) -> None:
        self._hotkeys.resume()
        self._sync_escape_hook()

    @property
    def state(self) -> AppState:
        return self._state

    @property
    def config_store(self) -> ConfigStore:
        return self._config_store

    def bootstrap(self) -> None:
        """Load config and prepare subsystems."""
        self._config_store.load()
        if not self._config_store.config.enabled:
            self._state = AppState.DISABLED
        logger.info("ScreenLoupe bootstrap complete (state=%s)", self._state.name)

    def start(self) -> None:
        """Register hotkeys and display-change handlers."""
        queued = Qt.ConnectionType.QueuedConnection
        self._hotkeys.magnify_requested.connect(self._on_magnify_requested, queued)
        self._hotkeys.escape_pressed.connect(self._on_escape_pressed, queued)
        self._hotkeys.toggle_requested.connect(self._on_toggle_requested, queued)
        self._hotkeys.lens_pressed.connect(self._on_lens_pressed, queued)
        self._hotkeys.lens_released.connect(self._on_lens_released, queued)
        self._hotkeys.register_from_config(self._config_store.config.hotkeys)

        app = QApplication.instance()
        if isinstance(app, QGuiApplication):
            app.screenAdded.connect(self._on_display_changed)
            app.screenRemoved.connect(self._on_display_changed)
            app.primaryScreenChanged.connect(self._on_display_changed)

        self._sync_escape_hook()
        logger.info("AppController started (state=%s)", self._state.name)

    def shutdown(self) -> None:
        """Tear down hooks and overlays."""
        self._teardown_overlays()
        self._hotkeys.unregister_all()

    def set_enabled(self, enabled: bool) -> None:
        """Set master enabled state (tray menu / settings)."""
        cfg = self._config_store.config
        if cfg.enabled == enabled:
            return
        cfg.enabled = enabled
        self._config_store.save()
        if enabled:
            self._transition(AppState.IDLE)
        else:
            self._teardown_overlays()
            self._transition(AppState.DISABLED)
        self._sync_escape_hook()
        self._notify_ui()
        logger.info("Enabled set to %s", enabled)

    def apply_settings(self, cfg: AppConfig) -> None:
        """Persist settings, re-register hotkeys, hot-reload overlays."""
        was_enabled = self._config_store.config.enabled
        self._config_store.save(cfg)
        self._hotkeys.register_from_config(cfg.hotkeys)

        if cfg.enabled != was_enabled:
            if cfg.enabled:
                self._transition(AppState.IDLE)
            else:
                self._teardown_overlays()
                self._transition(AppState.DISABLED)

        if self._magnifier is not None:
            self._magnifier.set_opacity(cfg.magnifier.opacity)

        set_run_at_startup(sys.executable, cfg.run_at_startup)
        self._sync_escape_hook()
        self._notify_ui()
        logger.info("Settings applied")

    def begin_selection(self) -> bool:
        """Open the selector overlay. Returns False if busy or disabled."""
        if self._state == AppState.DISABLED:
            return False
        if self._state == AppState.MAGNIFYING:
            self._dismiss_magnifier()
            self._transition(AppState.IDLE)
        elif self._state != AppState.IDLE:
            logger.debug("begin_selection ignored (state=%s)", self._state.name)
            return False

        screen = screen_at_cursor()
        frozen, mss_mon = grab_monitor_frame(screen)

        selector = SelectorOverlay(frozen, screen, mss_mon)
        selector.region_selected.connect(self._on_region_selected)
        selector.selection_cancelled.connect(self._on_selection_cancelled)
        selector.destroyed.connect(self._on_selector_destroyed)

        self._selector = selector
        self._transition(AppState.SELECTING)
        selector.show()
        self._sync_escape_hook()
        logger.info("Selector opened on %s", screen.name())
        return True

    def _on_magnify_requested(self) -> None:
        logger.info("magnify_requested (state=%s)", self._state.name)
        if self._state == AppState.DISABLED:
            return
        if self._state == AppState.LENS:
            self._dismiss_lens()
            self._transition(AppState.IDLE)
            self._sync_escape_hook()
            self.begin_selection()
            return
        if self._state == AppState.MAGNIFYING:
            self.begin_selection()
            return
        if self._state == AppState.IDLE:
            self.begin_selection()

    def _on_escape_pressed(self) -> None:
        if self._state == AppState.SELECTING and self._selector is not None:
            self._selector.cancel()
        elif self._state == AppState.MAGNIFYING:
            self._dismiss_magnifier()
            self._transition(AppState.IDLE)
            self._sync_escape_hook()

    def _on_toggle_requested(self) -> None:
        cfg = self._config_store.config
        cfg.enabled = not cfg.enabled
        if cfg.enabled:
            self._transition(AppState.IDLE)
        else:
            self._teardown_overlays()
            self._transition(AppState.DISABLED)
        self._sync_escape_hook()
        self._config_store.save()
        self._notify_ui()
        logger.info("Master toggle: enabled=%s", cfg.enabled)

    def _on_lens_pressed(self) -> None:
        logger.info("lens_pressed (state=%s)", self._state.name)
        if self._state in (AppState.MAGNIFYING, AppState.SELECTING, AppState.DISABLED):
            logger.debug("lens_pressed ignored (state=%s)", self._state.name)
            return
        if self._state == AppState.IDLE:
            self._open_lens()

    def _on_lens_released(self) -> None:
        logger.info("lens_released (state=%s)", self._state.name)
        if self._state == AppState.LENS:
            self._dismiss_lens()
            self._transition(AppState.IDLE)
            self._sync_escape_hook()

    def _on_region_selected(self, rect_physical: QRect) -> None:
        logger.info(
            "region_selected physical x=%d y=%d w=%d h=%d",
            rect_physical.x(),
            rect_physical.y(),
            rect_physical.width(),
            rect_physical.height(),
        )
        self._selector = None
        self._open_magnifier(rect_physical)

    def _on_selection_cancelled(self) -> None:
        logger.info("selection_cancelled")
        self._selector = None
        self._transition(AppState.IDLE)
        self._sync_escape_hook()

    def _on_selector_destroyed(self) -> None:
        if self._selector is not None:
            self._selector = None
        if self._state == AppState.SELECTING:
            self._transition(AppState.IDLE)
            self._sync_escape_hook()

    def _on_display_changed(self, *_args: object) -> None:
        """E5: dismiss overlays on topology change."""
        if self._state in (AppState.SELECTING, AppState.MAGNIFYING, AppState.LENS):
            logger.info("Display changed — forcing IDLE")
            self._teardown_overlays()
            next_state = (
                AppState.IDLE if self._config_store.config.enabled else AppState.DISABLED
            )
            self._transition(next_state)
            self._sync_escape_hook()

    def _open_magnifier(self, source_physical: QRect) -> None:
        self._dismiss_magnifier()

        cfg = self._config_store.config.magnifier
        screen = screen_for_physical_rect(source_physical)
        screen_rect = qrect_to_rect(logical_to_physical(screen.geometry(), screen))
        source = qrect_to_rect(source_physical)

        if cfg.zoom_mode == ZoomMode.FIT:
            overlay_rect, scale = fit_geometry(source, screen_rect, cfg.max_zoom / 100.0)
        else:
            overlay_rect, scale = fixed_geometry(source, screen_rect, cfg.zoom_percent / 100.0)

        magnifier = MagnifierOverlay(overlay_rect, scale, cfg.opacity, screen)
        magnifier.show()

        self._engine.frame_ready.connect(magnifier.set_frame)
        self._engine.start(source, cfg.refresh_hz)

        self._magnifier = magnifier
        self._transition(AppState.MAGNIFYING)
        self._sync_escape_hook()
        logger.info("Magnifier opened scale=%.2f overlay=%s", scale, overlay_rect)

    def _open_lens(self) -> None:
        # Opening from lens_down just set _lens_active — do not reset hold tracking here.
        self._dismiss_lens(sync_hotkey_hold=False)

        cfg = self._config_store.config.lens
        cx, cy = get_cursor_pos_physical()
        screen = screen_at_physical_point(cx, cy)
        screen_rect = qrect_to_rect(logical_to_physical(screen.geometry(), screen))
        source, overlay = lens_geometry(cx, cy, cfg.radius, cfg.zoom, screen_rect)

        lens = LensOverlay(cfg.shape, screen)
        lens.move_to(overlay)
        lens.show()

        self._engine.frame_ready.connect(lens.set_frame)
        self._engine.start(source, cfg.refresh_hz)

        self._lens = lens
        self._transition(AppState.LENS)
        interval_ms = max(1, 1000 // cfg.refresh_hz)
        self._lens_follow_timer.start(interval_ms)
        logger.info("Lens opened at (%d, %d)", cx, cy)

    def _on_lens_follow_tick(self) -> None:
        if self._state != AppState.LENS or self._lens is None:
            return
        cfg = self._config_store.config.lens
        cx, cy = get_cursor_pos_physical()
        screen = screen_at_physical_point(cx, cy)
        screen_rect = qrect_to_rect(logical_to_physical(screen.geometry(), screen))
        source, overlay = lens_geometry(cx, cy, cfg.radius, cfg.zoom, screen_rect)
        self._lens.move_to(overlay)
        self._engine.retarget(source)

    def _dismiss_magnifier(self) -> None:
        self._engine.stop()
        if self._magnifier is not None:
            with contextlib.suppress(TypeError):
                self._engine.frame_ready.disconnect(self._magnifier.set_frame)
            self._magnifier.close()
            self._magnifier = None

    def _dismiss_lens(self, *, sync_hotkey_hold: bool = True) -> None:
        self._lens_follow_timer.stop()
        self._engine.stop()
        if self._lens is not None:
            with contextlib.suppress(TypeError):
                self._engine.frame_ready.disconnect(self._lens.set_frame)
            self._lens.close()
            self._lens = None
        if sync_hotkey_hold:
            self._hotkeys.reset_lens_hold()

    def _teardown_overlays(self) -> None:
        if self._selector is not None:
            self._selector.close()
            self._selector = None
        self._dismiss_magnifier()
        self._dismiss_lens()

    def _transition(self, new_state: AppState) -> None:
        if self._state != new_state and not can_transition(self._state, new_state):
            logger.warning("transition %s -> %s not in table", self._state.name, new_state.name)
        self._state = new_state

    def _sync_escape_hook(self) -> None:
        active = self._state in (AppState.SELECTING, AppState.MAGNIFYING)
        self._hotkeys.set_escape_active(active)

    def _notify_ui(self) -> None:
        if self._ui_refresh is not None:
            self._ui_refresh()
