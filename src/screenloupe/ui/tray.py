"""System tray icon and context menu."""

from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

from screenloupe.app import AppController
from screenloupe.ui.icons import tray_icon


class TrayIcon(QSystemTrayIcon):
    """State-reflecting tray icon with context menu."""

    def __init__(
        self,
        controller: AppController,
        on_settings: Callable[[], None],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._on_settings = on_settings

        self._menu = QMenu()
        self._magnify_action = QAction("Magnify region\tAlt+M", self._menu)
        self._magnify_action.triggered.connect(controller.begin_selection)
        self._menu.addAction(self._magnify_action)

        self._menu.addSeparator()

        self._enabled_action = QAction(self._menu)
        self._enabled_action.setCheckable(True)
        self._enabled_action.triggered.connect(self._on_enabled_toggled)
        self._menu.addAction(self._enabled_action)

        settings_action = QAction("Settings\u2026", self._menu)
        settings_action.triggered.connect(on_settings)
        self._menu.addAction(settings_action)

        self._menu.addSeparator()

        quit_action = QAction("Quit ScreenLoupe", self._menu)
        quit_action.triggered.connect(self._quit_app)
        self._menu.addAction(quit_action)

        self.setContextMenu(self._menu)
        self.activated.connect(self._on_activated)
        self.refresh()

    def refresh(self) -> None:
        """Sync icon, tooltip, and menu labels with controller state."""
        cfg = self._controller.config_store.config
        enabled = cfg.enabled
        self.setIcon(tray_icon(enabled))
        tooltip = "ScreenLoupe" if enabled else "ScreenLoupe (off)"
        self.setToolTip(tooltip)

        hotkeys = cfg.hotkeys
        self._magnify_action.setText(f"Magnify region\t{hotkeys.magnify.upper()}")
        self._enabled_action.setText(f"Enabled\t{hotkeys.master_toggle.upper()}")
        self._enabled_action.blockSignals(True)
        self._enabled_action.setChecked(enabled)
        self._enabled_action.blockSignals(False)

    def show_first_run_toast(self) -> None:
        self.showMessage(
            "ScreenLoupe is running",
            "Press Alt+M to select and magnify any screen region.",
            QSystemTrayIcon.MessageIcon.Information,
            5000,
        )

    def _on_enabled_toggled(self, checked: bool) -> None:
        self._controller.set_enabled(checked)
        self.refresh()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._on_settings()

    def _quit_app(self) -> None:
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is not None:
            app.quit()
