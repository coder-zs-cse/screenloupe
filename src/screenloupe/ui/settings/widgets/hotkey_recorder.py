"""Hotkey capture widget."""

from __future__ import annotations

from collections.abc import Callable

import keyboard
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

HookRemover = Callable[[], None]


def format_hotkey_display(combo: str) -> str:
    parts = [p.strip() for p in combo.replace(" ", "").split("+") if p.strip()]
    out: list[str] = []
    for part in parts:
        if len(part) == 1:
            out.append(part.upper())
        else:
            out.append(part.title())
    return "+".join(out)


class HotkeyRecorder(QWidget):
    """Click Record, press a chord, emits normalized combo string."""

    combo_changed = pyqtSignal(str)
    conflict_changed = pyqtSignal(str)
    _combo_captured = pyqtSignal(str)

    def __init__(
        self,
        label: str,
        default_combo: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._default = default_combo
        self._combo = default_combo
        self._recording = False
        self._active_keys: set[str] = set()
        self._hook_remover: HookRemover | None = None
        self._other_combos: dict[str, str] = {}
        self._on_record_start: Callable[[], None] | None = None
        self._on_record_stop: Callable[[], None] | None = None

        self._combo_captured.connect(self._commit, Qt.ConnectionType.QueuedConnection)

        self._label = QLabel(label)
        self._label.setMinimumWidth(140)
        self._field = QLineEdit(format_hotkey_display(default_combo))
        self._field.setReadOnly(True)

        self._record_btn = QPushButton("Record")
        self._record_btn.clicked.connect(self._toggle_record)
        self._reset_btn = QPushButton("\u21ba")
        self._reset_btn.setFixedWidth(36)
        self._reset_btn.setToolTip("Reset to default")
        self._reset_btn.clicked.connect(self._reset_default)

        self._error = QLabel()
        self._error.setStyleSheet("color: #FFB74D;")

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self._label)
        row.addWidget(self._field, 1)
        row.addWidget(self._record_btn)
        row.addWidget(self._reset_btn)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 4, 0, 4)
        root.addLayout(row)
        root.addWidget(self._error)

    def set_record_hooks(self, on_start: Callable[[], None], on_stop: Callable[[], None]) -> None:
        self._on_record_start = on_start
        self._on_record_stop = on_stop

    def combo(self) -> str:
        return self._combo

    def set_combo(self, combo: str) -> None:
        self._combo = combo
        self._field.setText(format_hotkey_display(combo))
        self._validate()

    def set_peer_combos(self, peers: dict[str, str]) -> None:
        self._other_combos = peers
        self._validate()

    def has_conflict(self) -> bool:
        return bool(self._error.text())

    def _reset_default(self) -> None:
        self.set_combo(self._default)
        self.combo_changed.emit(self._combo)

    def _toggle_record(self) -> None:
        if self._recording:
            self._stop_record()
        else:
            self._start_record()

    def _start_record(self) -> None:
        self._recording = True
        self._active_keys.clear()
        self._field.setText("Press a combination\u2026")
        self._record_btn.setText("Cancel")
        if self._on_record_start:
            self._on_record_start()
        # suppress=True keeps the chord from reaching other apps while recording.
        self._hook_remover = keyboard.hook(self._on_key_event, suppress=True)

    def _stop_record(self) -> None:
        if not self._recording and self._hook_remover is None:
            return
        self._recording = False
        self._record_btn.setText("Record")
        if self._hook_remover is not None:
            self._hook_remover()
            self._hook_remover = None
        if self._on_record_stop:
            self._on_record_stop()
        self._field.setText(format_hotkey_display(self._combo))

    def _on_key_event(self, event: keyboard.KeyboardEvent) -> None:
        if not self._recording or not event.name or event.name == "unknown":
            return
        name = event.name
        if event.event_type == keyboard.KEY_DOWN:
            self._active_keys.add(name)
            return
        if event.event_type != keyboard.KEY_UP:
            return
        self._active_keys.discard(name)
        if keyboard.is_modifier(event.scan_code):
            return
        combo = keyboard.get_hotkey_name(list(self._active_keys) + [name])
        if not combo:
            return
        self._combo_captured.emit(combo)

    def _commit(self, combo: str) -> None:
        self._stop_record()
        self.set_combo(combo)
        self.combo_changed.emit(combo)

    def _validate(self) -> None:
        for label, other in self._other_combos.items():
            if other == self._combo:
                msg = f"Already used by {label}"
                self._error.setText(msg)
                self.conflict_changed.emit(msg)
                return
        self._error.clear()
        self.conflict_changed.emit("")
