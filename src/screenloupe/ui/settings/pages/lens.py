"""Lens settings page (stored for when lens hotkey ships)."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QButtonGroup, QLabel, QRadioButton, QVBoxLayout, QWidget

from screenloupe.core.config import AppConfig, LensShape
from screenloupe.core.constants import LENS_HOTKEY_ENABLED
from screenloupe.ui.settings.widgets.labeled_slider import LabeledSlider


class LensPage(QWidget):
    changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        title = QLabel("Lens")
        title.setProperty("title", True)

        note = QLabel(
            "Cursor lens (Alt+N) is disabled in v0.1. Settings here apply when the feature ships."
            if not LENS_HOTKEY_ENABLED
            else ""
        )
        note.setProperty("secondary", True)
        note.setWordWrap(True)

        self._rounded = QRadioButton("Rounded rectangle")
        self._circle = QRadioButton("Circle")
        group = QButtonGroup(self)
        group.addButton(self._rounded)
        group.addButton(self._circle)
        self._rounded.toggled.connect(lambda _: self.changed.emit())

        self._radius = LabeledSlider("Lens radius", 100, 500, 220, " px")
        self._zoom = LabeledSlider("Lens zoom", 120, 500, 200, " %")
        self._refresh = LabeledSlider("Refresh rate", 15, 120, 60, " Hz")
        for slider in (self._radius, self._zoom, self._refresh):
            slider.value_changed.connect(lambda _: self.changed.emit())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)
        layout.addWidget(title)
        if note.text():
            layout.addWidget(note)
        layout.addWidget(self._rounded)
        layout.addWidget(self._circle)
        layout.addWidget(self._radius)
        layout.addWidget(self._zoom)
        layout.addWidget(self._refresh)
        layout.addStretch()

    def load(self, cfg: AppConfig) -> None:
        lens = cfg.lens
        self._rounded.setChecked(lens.shape == LensShape.ROUNDED)
        self._circle.setChecked(lens.shape == LensShape.CIRCLE)
        self._radius.set_value(lens.radius)
        self._zoom.set_value(lens.zoom)
        self._refresh.set_value(lens.refresh_hz)

    def apply_to(self, cfg: AppConfig) -> None:
        lens = cfg.lens
        lens.shape = LensShape.ROUNDED if self._rounded.isChecked() else LensShape.CIRCLE
        lens.radius = self._radius.value()
        lens.zoom = self._zoom.value()
        lens.refresh_hz = self._refresh.value()
