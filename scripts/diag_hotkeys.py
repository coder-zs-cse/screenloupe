"""Diagnose whether global keyboard hooks work on this machine.

Run:  py -3.13 scripts/diag_hotkeys.py

Tests Alt+M and Alt+N within 10 seconds each.
"""

from __future__ import annotations

import sys
import time

import keyboard

print("ScreenLoupe hotkey diagnostic")
print(f"listener active: {keyboard._listener.listening}")
print()

results: dict[str, bool] = {"alt+m": False, "alt+n": False}


def on_m() -> None:
    results["alt+m"] = True
    print("SUCCESS: Alt+M fired.")


def on_n() -> None:
    results["alt+n"] = True
    print("SUCCESS: Alt+N fired.")


keyboard.add_hotkey("alt+m", on_m, suppress=False)
keyboard.add_hotkey("alt+n", on_n, suppress=False)

print("Press Alt+M, then Alt+N (10 seconds)...")
deadline = time.time() + 10
while time.time() < deadline and not all(results.values()):
    time.sleep(0.1)

ok = True
for combo, fired in results.items():
    if fired:
        print(f"  {combo}: OK")
    else:
        print(f"  {combo}: FAIL")
        ok = False

if not ok:
    print("\nCommon causes:")
    print("  - Run PowerShell as Administrator")
    print("  - Windows Store Python may block low-level hooks; try python.org install")
    sys.exit(1)

print("\nHooks work on this machine.")
sys.exit(0)
