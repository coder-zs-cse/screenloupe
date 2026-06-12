"""Magnifier settings page."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QButtonGroup, QLabel, QRadioButton, QVBoxLayout, QWidget

from screenloupe.core.config import AppConfig, ZoomMode
from screenloupe.ui.settings.widgets.labeled_slider import LabeledSlider
from screenloupe.ui.settings.widgets.preview_tile import PreviewTile


class MagnifierPage(QWidget):
    changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        title = QLabel("Magnifier")
        title.setProperty("title", True)

        self._fit = QRadioButton("Fit to screen")
        self._fixed = QRadioButton("Fixed percent")
        self._mode_group = QButtonGroup(self)
        self._mode_group.addButton(self._fit)
        self._mode_group.addButton(self._fixed)
        self._fit.toggled.connect(lambda _: self.changed.emit())

        self._max_zoom = LabeledSlider("Max zoom", 150, 800, 400, " %")
        self._zoom_pct = LabeledSlider("Zoom percent", 120, 500, 200, " %")
        self._opacity = LabeledSlider("Overlay opacity", 50, 100, 92, " %")
        self._refresh = LabeledSlider("Refresh rate", 10, 60, 30, " Hz")
        self._preview = PreviewTile()

        for slider in (self._max_zoom, self._zoom_pct, self._opacity, self._refresh):
            slider.value_changed.connect(lambda _: self._on_slider())
            slider.value_changed.connect(lambda _: self.changed.emit())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)
        layout.addWidget(title)
        layout.addWidget(self._fit)
        layout.addWidget(self._fixed)
        layout.addWidget(self._max_zoom)
        layout.addWidget(self._zoom_pct)
        layout.addWidget(self._opacity)
        layout.addWidget(self._refresh)
        layout.addWidget(self._preview, 1)

    def load(self, cfg: AppConfig) -> None:
        mag = cfg.magnifier
        self._fit.setChecked(mag.zoom_mode == ZoomMode.FIT)
        self._fixed.setChecked(mag.zoom_mode == ZoomMode.FIXED)
        self._max_zoom.set_value(mag.max_zoom)
        self._zoom_pct.set_value(mag.zoom_percent)
        self._opacity.set_value(mag.opacity)
        self._refresh.set_value(mag.refresh_hz)
        self._on_slider()

    def apply_to(self, cfg: AppConfig) -> None:
        mag = cfg.magnifier
        mag.zoom_mode = ZoomMode.FIT if self._fit.isChecked() else ZoomMode.FIXED
        mag.max_zoom = self._max_zoom.value()
        mag.zoom_percent = self._zoom_pct.value()
        mag.opacity = self._opacity.value()
        mag.refresh_hz = self._refresh.value()

    def _on_slider(self) -> None:
        zoom = self._zoom_pct.value() if self._fixed.isChecked() else self._max_zoom.value()
        self._preview.set_zoom(zoom)
        self._preview.set_opacity(self._opacity.value())
