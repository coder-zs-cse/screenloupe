"""QSS design tokens (docs/03 § 1)."""

STYLESHEET = """
QWidget {
    background-color: #16181D;
    color: #E8EAED;
    font-family: "Segoe UI";
    font-size: 13px;
}
QMainWindow, QDialog {
    background-color: #16181D;
}
QLabel {
    background: transparent;
}
QLabel[secondary="true"] {
    color: #9AA0A8;
}
QLabel[title="true"] {
    font-size: 20px;
    font-weight: 600;
}
QPushButton {
    background-color: #262A33;
    border: 1px solid #262A33;
    border-radius: 6px;
    padding: 6px 14px;
    min-height: 28px;
}
QPushButton:hover {
    background-color: #2E333D;
}
QPushButton:pressed {
    background-color: #1E2128;
}
QPushButton[primary="true"] {
    background-color: #4FC3F7;
    color: #16181D;
    font-weight: 600;
}
QPushButton[primary="true"]:hover {
    background-color: #6BCFF9;
}
QPushButton:disabled {
    color: #6B7280;
    background-color: #1E2128;
}
QLineEdit, QSpinBox, QComboBox {
    background-color: #262A33;
    border: 1px solid #262A33;
    border-radius: 6px;
    padding: 4px 8px;
    min-height: 28px;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border: 1px solid #4FC3F7;
}
QCheckBox, QRadioButton {
    spacing: 8px;
}
QSlider::groove:horizontal {
    height: 4px;
    background: #262A33;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    width: 14px;
    margin: -5px 0;
    background: #4FC3F7;
    border-radius: 7px;
}
QListWidget {
    background-color: #1E2128;
    border: none;
    outline: none;
}
QListWidget::item {
    padding: 10px 12px;
    border-left: 3px solid transparent;
}
QListWidget::item:selected {
    background-color: #262A33;
    border-left: 3px solid #4FC3F7;
}
QScrollArea {
    border: none;
    background: transparent;
}
QFrame[card="true"] {
    background-color: #1E2128;
    border-radius: 10px;
}
"""
