"""Dev-only selector overlay — Phase 3 verify.

Run:  py -3.13 scripts/dev_selector.py

Opens the Win+Shift+S-style selector on the monitor under the cursor.
Prints the physical-pixel rect on success, or 'cancelled' on Esc/short-click.
"""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "src"))

from screenloupe.app import AppController
from screenloupe.core.state import AppState
from screenloupe.platformwin.dpi import set_process_dpi_aware


def main() -> int:
    set_process_dpi_aware()
    app = QApplication(sys.argv)

    controller = AppController()
    controller.bootstrap()

    if not controller.begin_selection():
        print("FAIL: could not open selector")
        return 1

    def on_selected(rect) -> None:
        print(
            f"SELECTED physical: x={rect.x()} y={rect.y()} "
            f"w={rect.width()} h={rect.height()}"
        )
        app.quit()

    def on_cancelled() -> None:
        print("CANCELLED")
        app.quit()

    assert controller._selector is not None
    controller._selector.region_selected.connect(on_selected)
    controller._selector.selection_cancelled.connect(on_cancelled)

    code = app.exec()
    if controller.state != AppState.IDLE:
        print(f"WARN: final state is {controller.state.name}, expected IDLE")
    if controller._selector is not None:
        print("FAIL: selector window still referenced after close")
        return 1

    print(f"Final state: {controller.state.name}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
