"""About settings page."""

from __future__ import annotations

import platform
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from screenloupe import __version__


def _os_ok() -> bool:
    if sys.platform != "win32":
        return False
    build = int(platform.version().split(".")[-1])
    return build >= 19041


class AboutPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        title = QLabel("About")
        title.setProperty("title", True)

        if _os_ok():
            os_status = "meets minimum (build 19041+)"
        else:
            os_status = "below minimum for capture exclusion"
        body = QLabel(
            f"ScreenLoupe {__version__}\n\n"
            f"Windows: {platform.version()} — {os_status}\n\n"
            "A live, click-through screen magnifier for Windows.\n"
            "Region magnifier: Alt+M · Master toggle: Ctrl+Alt+M"
        )
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.addWidget(title)
        layout.addWidget(body)
        layout.addStretch()

    def load(self, _cfg: object) -> None:
        return

    def apply_to(self, _cfg: object) -> None:
        return
