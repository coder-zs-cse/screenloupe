"""HKCU Run registry helpers for run-at-startup."""

from __future__ import annotations

import contextlib
import logging
import winreg

from screenloupe.core.constants import APP_NAME

logger = logging.getLogger(__name__)

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def is_run_at_startup() -> bool:
    """Return True if the Run key entry exists."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except FileNotFoundError:
        return False
    except OSError:
        logger.exception("Failed to read run-at-startup registry key")
        return False


def set_run_at_startup(exe_path: str, enabled: bool) -> None:
    """Add or remove the HKCU Run key entry."""
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            if enabled:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{exe_path}" --minimized')
            else:
                with contextlib.suppress(FileNotFoundError):
                    winreg.DeleteValue(key, APP_NAME)
    except OSError:
        logger.exception("Failed to update run-at-startup registry key")
