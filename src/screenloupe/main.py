"""Entry point: DPI awareness, QApplication bootstrap, AppController."""

from __future__ import annotations

import atexit
import logging
import sys
from logging.handlers import RotatingFileHandler

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon

from screenloupe.app import AppController
from screenloupe.core.constants import LOG_PATH
from screenloupe.platformwin.dpi import set_process_dpi_aware
from screenloupe.platformwin.single_instance import (
    ShowSettingsEventFilter,
    SingleInstanceGuard,
)
from screenloupe.ui.icons import app_icon
from screenloupe.ui.settings.window import SettingsWindow
from screenloupe.ui.theme import STYLESHEET
from screenloupe.ui.tray import TrayIcon


def _configure_logging() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(LOG_PATH, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[handler],
    )


def run() -> None:
    """Bootstrap ScreenLoupe and run the event loop."""
    set_process_dpi_aware()
    _configure_logging()

    guard = SingleInstanceGuard()
    if not guard.acquire():
        guard.notify_existing()
        return

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("ScreenLoupe")
    app.setWindowIcon(app_icon())
    app.setStyleSheet(STYLESHEET)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        logging.error("System tray is not available on this platform")
        sys.exit(1)

    controller = AppController()
    controller.bootstrap()
    controller.start()

    settings = SettingsWindow(controller)

    def show_settings() -> None:
        settings.show()
        settings.raise_()
        settings.activateWindow()

    tray = TrayIcon(controller, show_settings)
    controller.set_ui_refresh(tray.refresh)
    tray.show()

    app.installNativeEventFilter(ShowSettingsEventFilter(show_settings))

    cfg = controller.config_store.config
    if not cfg.first_run_toast_shown:
        tray.show_first_run_toast()
        cfg.first_run_toast_shown = True
        controller.config_store.save()

    atexit.register(controller.shutdown)
    atexit.register(guard.release)

    logging.info("ScreenLoupe started (tray active)")
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
