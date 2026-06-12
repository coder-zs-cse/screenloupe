"""Labeled horizontal slider with value readout."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QSlider, QWidget


class LabeledSlider(QWidget):
    """Slider with label and formatted value (e.g. ``92 %``)."""

    value_changed = pyqtSignal(int)

    def __init__(
        self,
        label: str,
        minimum: int,
        maximum: int,
        value: int,
        suffix: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._suffix = suffix

        self._title = QLabel(label)
        self._value_label = QLabel()
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._value_label.setMinimumWidth(56)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(minimum, maximum)
        self._slider.setValue(value)
        self._slider.valueChanged.connect(self._on_value)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self._title, 1)
        row.addWidget(self._slider, 3)
        row.addWidget(self._value_label)

        self._refresh_label(value)

    def value(self) -> int:
        return self._slider.value()

    def set_value(self, value: int) -> None:
        self._slider.blockSignals(True)
        self._slider.setValue(value)
        self._slider.blockSignals(False)
        self._refresh_label(value)

    def _on_value(self, value: int) -> None:
        self._refresh_label(value)
        self.value_changed.emit(value)

    def _refresh_label(self, value: int) -> None:
        self._value_label.setText(f"{value}{self._suffix}")
