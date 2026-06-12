"""Shortcuts settings page."""

from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from screenloupe.core.config import AppConfig, default_config
from screenloupe.core.constants import LENS_HOTKEY_ENABLED
from screenloupe.ui.settings.widgets.hotkey_recorder import HotkeyRecorder


class ShortcutsPage(QWidget):
    changed = pyqtSignal()

    def __init__(
        self,
        on_record_start: Callable[[], None],
        on_record_stop: Callable[[], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        defaults = default_config().hotkeys
        title = QLabel("Shortcuts")
        title.setProperty("title", True)

        self._magnify = HotkeyRecorder("Magnify region", defaults.magnify)
        self._dismiss = HotkeyRecorder("Dismiss overlay", defaults.dismiss)
        self._lens = HotkeyRecorder("Cursor lens (hold)", defaults.lens)
        self._toggle = HotkeyRecorder("Master toggle", defaults.master_toggle)

        self._recorders = [self._magnify, self._dismiss, self._toggle]
        if LENS_HOTKEY_ENABLED:
            self._recorders.append(self._lens)
        else:
            self._lens.setEnabled(False)
            self._lens.setToolTip("Cursor lens is disabled in v0.1")

        for rec in self._recorders:
            rec.set_record_hooks(on_record_start, on_record_stop)
            rec.combo_changed.connect(self._on_combo_changed)

        esc_btn = QPushButton('Set dismiss to "Esc"')
        esc_btn.clicked.connect(self._set_esc)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(6)
        layout.addWidget(title)
        layout.addWidget(self._magnify)
        layout.addWidget(self._dismiss)
        layout.addWidget(esc_btn)
        layout.addWidget(self._lens)
        layout.addWidget(self._toggle)
        layout.addStretch()

    def load(self, cfg: AppConfig) -> None:
        hk = cfg.hotkeys
        self._magnify.set_combo(hk.magnify)
        self._dismiss.set_combo(hk.dismiss)
        self._lens.set_combo(hk.lens)
        self._toggle.set_combo(hk.master_toggle)
        self._refresh_peers()

    def apply_to(self, cfg: AppConfig) -> None:
        hk = cfg.hotkeys
        hk.magnify = self._magnify.combo()
        hk.dismiss = self._dismiss.combo()
        hk.lens = self._lens.combo()
        hk.master_toggle = self._toggle.combo()

    def has_conflicts(self) -> bool:
        return any(r.has_conflict() for r in self._recorders)

    def _set_esc(self) -> None:
        self._dismiss.set_combo("esc")
        self.changed.emit()

    def _on_combo_changed(self, _combo: str) -> None:
        self._refresh_peers()
        self.changed.emit()

    def _refresh_peers(self) -> None:
        labels = {
            self._magnify: "Magnify region",
            self._dismiss: "Dismiss overlay",
            self._lens: "Cursor lens",
            self._toggle: "Master toggle",
        }
        combos = {labels[r]: r.combo() for r in self._recorders}
        for rec in self._recorders:
            peers = {k: v for k, v in combos.items() if k != labels[rec]}
            rec.set_peer_combos(peers)
