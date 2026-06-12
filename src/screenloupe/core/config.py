"""Typed settings schema, JSON load/save, validation, and clamping."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from screenloupe.core.constants import APPDATA_DIR, CONFIG_PATH, CONFIG_VERSION

logger = logging.getLogger(__name__)


class ZoomMode(StrEnum):
    FIT = "fit"
    FIXED = "fixed"


class LensShape(StrEnum):
    ROUNDED = "rounded"
    CIRCLE = "circle"


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))


@dataclass
class HotkeyConfig:
    magnify: str = "alt+m"
    dismiss: str = "esc"
    lens: str = "alt+n"
    master_toggle: str = "ctrl+alt+m"


@dataclass
class MagnifierConfig:
    zoom_mode: ZoomMode = ZoomMode.FIT
    zoom_percent: int = 200
    max_zoom: int = 400
    opacity: int = 92
    refresh_hz: int = 30

    def clamp(self) -> None:
        self.zoom_percent = _clamp(self.zoom_percent, 120, 500)
        self.max_zoom = _clamp(self.max_zoom, 150, 800)
        self.opacity = _clamp(self.opacity, 50, 100)
        self.refresh_hz = _clamp(self.refresh_hz, 10, 60)
        if not isinstance(self.zoom_mode, ZoomMode):
            self.zoom_mode = ZoomMode.FIT


@dataclass
class LensConfig:
    radius: int = 220
    zoom: int = 200
    refresh_hz: int = 60
    shape: LensShape = LensShape.ROUNDED

    def clamp(self) -> None:
        self.radius = _clamp(self.radius, 100, 500)
        self.zoom = _clamp(self.zoom, 120, 500)
        self.refresh_hz = _clamp(self.refresh_hz, 15, 120)
        if not isinstance(self.shape, LensShape):
            self.shape = LensShape.ROUNDED


@dataclass
class AppConfig:
    config_version: int = CONFIG_VERSION
    enabled: bool = True
    run_at_startup: bool = True
    first_run_toast_shown: bool = False
    hotkeys: HotkeyConfig = field(default_factory=HotkeyConfig)
    magnifier: MagnifierConfig = field(default_factory=MagnifierConfig)
    lens: LensConfig = field(default_factory=LensConfig)

    def clamp(self) -> None:
        self.magnifier.clamp()
        self.lens.clamp()


def default_config() -> AppConfig:
    """Return a fresh default configuration."""
    return AppConfig()


def copy_config(cfg: AppConfig) -> AppConfig:
    """Deep copy via JSON round-trip."""
    return config_from_dict(config_to_dict(cfg))


def config_to_dict(cfg: AppConfig) -> dict[str, Any]:
    """Serialize config to a JSON-compatible dict."""
    data = asdict(cfg)
    data["magnifier"]["zoom_mode"] = cfg.magnifier.zoom_mode.value
    data["lens"]["shape"] = cfg.lens.shape.value
    return data


def config_from_dict(data: dict[str, Any]) -> AppConfig:
    """Deserialize config from a dict; unknown keys are ignored."""
    hotkeys_raw = data.get("hotkeys", {})
    magnifier_raw = data.get("magnifier", {})
    lens_raw = data.get("lens", {})

    zoom_mode_raw = magnifier_raw.get("zoom_mode", ZoomMode.FIT.value)
    try:
        zoom_mode = ZoomMode(zoom_mode_raw)
    except ValueError:
        zoom_mode = ZoomMode.FIT

    shape_raw = lens_raw.get("shape", LensShape.ROUNDED.value)
    try:
        shape = LensShape(shape_raw)
    except ValueError:
        shape = LensShape.ROUNDED

    cfg = AppConfig(
        config_version=int(data.get("config_version", CONFIG_VERSION)),
        enabled=bool(data.get("enabled", True)),
        run_at_startup=bool(data.get("run_at_startup", True)),
        first_run_toast_shown=bool(data.get("first_run_toast_shown", False)),
        hotkeys=HotkeyConfig(
            magnify=str(hotkeys_raw.get("magnify", "alt+m")),
            dismiss=str(hotkeys_raw.get("dismiss", "esc")),
            lens=str(hotkeys_raw.get("lens", "alt+n")),
            master_toggle=str(hotkeys_raw.get("master_toggle", "ctrl+alt+m")),
        ),
        magnifier=MagnifierConfig(
            zoom_mode=zoom_mode,
            zoom_percent=int(magnifier_raw.get("zoom_percent", 200)),
            max_zoom=int(magnifier_raw.get("max_zoom", 400)),
            opacity=int(magnifier_raw.get("opacity", 92)),
            refresh_hz=int(magnifier_raw.get("refresh_hz", 30)),
        ),
        lens=LensConfig(
            radius=int(lens_raw.get("radius", 220)),
            zoom=int(lens_raw.get("zoom", 200)),
            refresh_hz=int(lens_raw.get("refresh_hz", 60)),
            shape=shape,
        ),
    )
    cfg.clamp()
    return cfg


class ConfigStore:
    """Load, save, and persist application settings."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or CONFIG_PATH
        self._config = default_config()

    @property
    def config(self) -> AppConfig:
        return self._config

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> AppConfig:
        """Load config from disk; corrupt/missing files recover to defaults."""
        if not self._path.exists():
            self._config = default_config()
            return self._config

        try:
            raw = self._path.read_text(encoding="utf-8")
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("config root must be an object")
            self._config = config_from_dict(data)
        except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
            logger.warning("Config corrupt or unreadable (%s); recreating defaults", exc)
            backup = self._path.with_suffix(".json.bak")
            try:
                if self._path.exists():
                    self._path.replace(backup)
            except OSError:
                logger.exception("Failed to back up corrupt config")
            self._config = default_config()
            self.save()

        return self._config

    def save(self, cfg: AppConfig | None = None) -> None:
        """Persist config to disk."""
        if cfg is not None:
            cfg.clamp()
            self._config = cfg

        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(config_to_dict(self._config), indent=2)
        self._path.write_text(payload + "\n", encoding="utf-8")


# Re-export APPDATA_DIR for tests that need an isolated path.
__all__ = [
    "APPDATA_DIR",
    "AppConfig",
    "ConfigStore",
    "HotkeyConfig",
    "LensConfig",
    "LensShape",
    "MagnifierConfig",
    "ZoomMode",
    "config_from_dict",
    "config_to_dict",
    "default_config",
]
