"""General settings page."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QCheckBox, QLabel, QVBoxLayout, QWidget

from screenloupe.core.config import AppConfig


class GeneralPage(QWidget):
    changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        title = QLabel("General")
        title.setProperty("title", True)

        self._enabled = QCheckBox("ScreenLoupe enabled")
        self._enabled.toggled.connect(lambda: self.changed.emit())
        self._startup = QCheckBox("Run ScreenLoupe at Windows startup")
        self._startup.toggled.connect(lambda: self.changed.emit())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(self._enabled)
        layout.addWidget(self._startup)
        layout.addStretch()

    def load(self, cfg: AppConfig) -> None:
        self._enabled.blockSignals(True)
        self._startup.blockSignals(True)
        self._enabled.setChecked(cfg.enabled)
        self._startup.setChecked(cfg.run_at_startup)
        self._enabled.blockSignals(False)
        self._startup.blockSignals(False)

    def apply_to(self, cfg: AppConfig) -> None:
        cfg.enabled = self._enabled.isChecked()
        cfg.run_at_startup = self._startup.isChecked()
