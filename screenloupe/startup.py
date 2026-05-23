"""
startup.py — "run at login" and launching the daemon without a console.

Two responsibilities:
  1. toggle the HKEY_CURRENT_USER ...\\Run registry value (the per-user
     "start this at login" list) on and off, and read its state;
  2. work out the right command to launch ScreenLoupe in each situation —
     which differs depending on whether we're a frozen PyInstaller .exe, a
     pipx-installed console_script, or a bare source checkout.
"""

import os
import shutil
import subprocess
import sys

APP_NAME = "ScreenLoupe"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

# Launch detached + no console window so nothing flashes on screen.
DETACHED_PROCESS = 0x00000008
CREATE_NO_WINDOW = 0x08000000


def base_command():
    """list[str] that starts the background daemon (no extra args)."""
    if getattr(sys, "frozen", False):
        # PyInstaller bundle: the exe *is* the launcher.
        return [sys.executable]
    exe = shutil.which("screenloupe")
    if exe:
        return [exe]
    # Source checkout / odd install: prefer pythonw (no console) + module run.
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    python = pyw if os.path.exists(pyw) else sys.executable
    return [python, "-m", "screenloupe"]


def daemon_command():
    """list[str] that runs the silent background magnifier."""
    return base_command() + ["--background"]


def settings_command():
    """list[str] that opens the GUI (the bare command — default action)."""
    return base_command()


def _command_string(cmd):
    return " ".join(f'"{c}"' if " " in c else c for c in cmd)


def launch_daemon():
    """Spawn the background magnifier, fully detached and windowless."""
    subprocess.Popen(
        daemon_command(),
        creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW,
        close_fds=True,
    )


# --- registry "run at login" ----------------------------------------------
def is_enabled():
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, APP_NAME)
        return True
    except OSError:
        return False


def enable():
    import winreg
    cmd = _command_string(daemon_command())
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
        winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, cmd)


def disable():
    import winreg
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as k:
            winreg.DeleteValue(k, APP_NAME)
    except OSError:
        pass
