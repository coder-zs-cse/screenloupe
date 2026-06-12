"""Unit tests for config schema, round-trip, clamping, and corrupt-file recovery."""

from __future__ import annotations

import json
from pathlib import Path

from screenloupe.core.config import (
    ConfigStore,
    LensShape,
    ZoomMode,
    config_from_dict,
    config_to_dict,
    default_config,
)


def test_default_config_values() -> None:
    cfg = default_config()
    assert cfg.config_version == 1
    assert cfg.enabled is True
    assert cfg.run_at_startup is True
    assert cfg.hotkeys.magnify == "alt+m"
    assert cfg.hotkeys.dismiss == "esc"
    assert cfg.hotkeys.lens == "alt+n"
    assert cfg.hotkeys.master_toggle == "ctrl+alt+m"
    assert cfg.magnifier.zoom_mode == ZoomMode.FIT
    assert cfg.magnifier.zoom_percent == 200
    assert cfg.magnifier.max_zoom == 400
    assert cfg.magnifier.opacity == 92
    assert cfg.magnifier.refresh_hz == 30
    assert cfg.lens.radius == 220
    assert cfg.lens.zoom == 200
    assert cfg.lens.refresh_hz == 60
    assert cfg.lens.shape == LensShape.ROUNDED


def test_config_round_trip() -> None:
    original = default_config()
    original.magnifier.zoom_mode = ZoomMode.FIXED
    original.magnifier.zoom_percent = 350
    original.lens.shape = LensShape.CIRCLE
    original.enabled = False

    data = config_to_dict(original)
    restored = config_from_dict(data)

    assert restored.enabled == original.enabled
    assert restored.magnifier.zoom_mode == ZoomMode.FIXED
    assert restored.magnifier.zoom_percent == 350
    assert restored.lens.shape == LensShape.CIRCLE


def test_clamping_out_of_range_values() -> None:
    cfg = config_from_dict(
        {
            "magnifier": {
                "zoom_percent": 50,
                "max_zoom": 999,
                "opacity": 10,
                "refresh_hz": 5,
            },
            "lens": {"radius": 50, "zoom": 999, "refresh_hz": 200},
        }
    )
    assert cfg.magnifier.zoom_percent == 120
    assert cfg.magnifier.max_zoom == 800
    assert cfg.magnifier.opacity == 50
    assert cfg.magnifier.refresh_hz == 10
    assert cfg.lens.radius == 100
    assert cfg.lens.zoom == 500
    assert cfg.lens.refresh_hz == 120


def test_unknown_keys_ignored() -> None:
    cfg = config_from_dict({"unknown_field": True, "magnifier": {"extra": 1}})
    assert cfg.magnifier.zoom_percent == 200


def test_invalid_enum_falls_back_to_defaults() -> None:
    cfg = config_from_dict(
        {"magnifier": {"zoom_mode": "bogus"}, "lens": {"shape": "triangle"}}
    )
    assert cfg.magnifier.zoom_mode == ZoomMode.FIT
    assert cfg.lens.shape == LensShape.ROUNDED


def test_config_store_save_and_load(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    store = ConfigStore(path)
    store.load()

    store.config.magnifier.opacity = 75
    store.save()

    store2 = ConfigStore(path)
    store2.load()
    assert store2.config.magnifier.opacity == 75


def test_corrupt_file_recovery(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text("{ not valid json", encoding="utf-8")

    store = ConfigStore(path)
    cfg = store.load()

    assert cfg.magnifier.zoom_percent == 200
    assert path.with_suffix(".json.bak").exists()
    assert json.loads(path.read_text(encoding="utf-8"))["config_version"] == 1


def test_missing_file_uses_defaults(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    store = ConfigStore(path)
    cfg = store.load()
    assert cfg.hotkeys.magnify == "alt+m"
    assert not path.exists()
