"""Application paths, names, and Win32 constants."""

from pathlib import Path

APP_NAME = "ScreenLoupe"
CONFIG_VERSION = 1

# v0.1 release: cursor lens hotkey deferred (hold-to-release hooks unreliable on Windows).
LENS_HOTKEY_ENABLED = False

APPDATA_DIR = Path.home() / "AppData" / "Roaming" / "ScreenLoupe"
CONFIG_PATH = APPDATA_DIR / "config.json"
LOG_PATH = APPDATA_DIR / "screenloupe.log"

MUTEX_NAME = r"Global\ScreenLoupe.SingleInstance"
SHOW_MESSAGE_NAME = "SCREENLOUPE_SHOW"

# Win32 — capture exclusion (docs/02 § 1)
WDA_EXCLUDEFROMCAPTURE = 0x00000011

# Win32 — overlay extended styles (docs/02 § 2)
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080

# Win32 — SetWindowPos (overlay z-order without activation)
HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010

# Win32 — DPI (docs/02 § 3)
DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4

# Win32 — single instance
ERROR_ALREADY_EXISTS = 183

# Selection cancel threshold (docs/01 § 2)
MIN_SELECTION_PX = 8
