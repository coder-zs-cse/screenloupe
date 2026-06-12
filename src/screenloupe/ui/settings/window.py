"""Settings shell: tab rail, content stack, Apply/Cancel."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from screenloupe.app import AppController
from screenloupe.core.config import AppConfig, copy_config
from screenloupe.ui.icons import app_icon
from screenloupe.ui.settings.pages.about import AboutPage
from screenloupe.ui.settings.pages.general import GeneralPage
from screenloupe.ui.settings.pages.lens import LensPage
from screenloupe.ui.settings.pages.magnifier import MagnifierPage
from screenloupe.ui.settings.pages.shortcuts import ShortcutsPage


class SettingsWindow(QMainWindow):
    """Left rail + right pane settings window."""

    def __init__(self, controller: AppController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._draft = copy_config(controller.config_store.config)
        self._dirty = False

        self.setWindowTitle("ScreenLoupe Settings")
        self.setWindowIcon(app_icon())
        self.setFixedSize(760, 520)

        self._rail = QListWidget()
        self._rail.setFixedWidth(170)
        self._stack = QStackedWidget()

        self._general = GeneralPage()
        self._shortcuts = ShortcutsPage(
            on_record_start=controller.pause_hotkeys,
            on_record_stop=controller.resume_hotkeys,
        )
        self._magnifier = MagnifierPage()
        self._lens = LensPage()
        self._about = AboutPage()

        self._pages: list[tuple[str, QWidget]] = [
            ("General", self._general),
            ("Shortcuts", self._shortcuts),
            ("Magnifier", self._magnifier),
            ("Lens", self._lens),
            ("About", self._about),
        ]
        for label, page in self._pages:
            QListWidgetItem(label, self._rail)
            self._stack.addWidget(page)
            if hasattr(page, "changed"):
                page.changed.connect(self._mark_dirty)  # type: ignore[attr-defined]

        self._rail.currentRowChanged.connect(self._stack.setCurrentIndex)
        self._rail.setCurrentRow(0)

        self._apply_btn = QPushButton("Apply")
        self._apply_btn.setProperty("primary", True)
        self._apply_btn.setEnabled(False)
        self._apply_btn.clicked.connect(self._on_apply)
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self._on_cancel)

        content = QHBoxLayout()
        content.addWidget(self._rail)
        content.addWidget(self._stack, 1)

        footer = QHBoxLayout()
        footer.addStretch()
        footer.addWidget(self._cancel_btn)
        footer.addWidget(self._apply_btn)

        root = QVBoxLayout()
        root.addLayout(content, 1)
        root.addLayout(footer)

        shell = QWidget()
        shell.setLayout(root)
        self.setCentralWidget(shell)

        self._reload_draft()

    def _reload_draft(self) -> None:
        self._draft = copy_config(self._controller.config_store.config)
        self._general.load(self._draft)
        self._shortcuts.load(self._draft)
        self._magnifier.load(self._draft)
        self._lens.load(self._draft)
        self._about.load(self._draft)
        self._set_dirty(False)

    def _mark_dirty(self) -> None:
        self._set_dirty(True)

    def _set_dirty(self, dirty: bool) -> None:
        self._dirty = dirty
        self._apply_btn.setEnabled(dirty)

    def _collect_draft(self) -> AppConfig:
        cfg = copy_config(self._draft)
        self._general.apply_to(cfg)
        self._shortcuts.apply_to(cfg)
        self._magnifier.apply_to(cfg)
        self._lens.apply_to(cfg)
        cfg.clamp()
        return cfg

    def _on_apply(self) -> None:
        if self._shortcuts.has_conflicts():
            return
        cfg = self._collect_draft()
        self._controller.apply_settings(cfg)
        self._reload_draft()

    def _on_cancel(self) -> None:
        self._reload_draft()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._dirty:
            self._on_cancel()
        event.accept()
