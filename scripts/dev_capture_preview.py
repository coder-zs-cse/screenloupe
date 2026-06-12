"""Dev-only live capture preview — Phase 2 verify.

Run:  py -3.13 scripts/dev_capture_preview.py

Shows a 30 Hz feed of a hardcoded 600x400 region (primary monitor center).
The preview window is capture-excluded (same as production overlays) so it can
sit inside the captured region without the infinite mirror. Close to exit.
"""

from __future__ import annotations

import sys

import mss
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "src"))

from screenloupe.capture.engine import CaptureEngine
from screenloupe.capture.exclusion import set_capture_excluded
from screenloupe.overlay.magnifier import Rect
from screenloupe.platformwin.dpi import set_process_dpi_aware

PREVIEW_W = 600
PREVIEW_H = 400
REFRESH_HZ = 30


def _default_region() -> Rect:
    with mss.MSS() as sct:
        mon = sct.monitors[1]
        left = mon["left"] + max(0, (mon["width"] - PREVIEW_W) // 2)
        top = mon["top"] + max(0, (mon["height"] - PREVIEW_H) // 2)
        return Rect(left, top, PREVIEW_W, PREVIEW_H)


class PreviewWindow(QWidget):
    def __init__(self, region: Rect) -> None:
        super().__init__()
        self.setWindowTitle("ScreenLoupe capture preview (dev)")
        layout = QVBoxLayout(self)
        self._label = QLabel("Waiting for frames...")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._label)

        self._engine = CaptureEngine(self)
        self._engine.frame_ready.connect(self._on_frame)
        self._engine.start(region, REFRESH_HZ)

    def _on_frame(self, image: QImage) -> None:
        self._label.setPixmap(QPixmap.fromImage(image))

    def closeEvent(self, event) -> None:  # noqa: N802
        self._engine.stop()
        super().closeEvent(event)


def main() -> int:
    set_process_dpi_aware()
    app = QApplication(sys.argv)
    region = _default_region()
    window = PreviewWindow(region)
    window.resize(PREVIEW_W, PREVIEW_H)
    window.show()
    app.processEvents()
    if not set_capture_excluded(int(window.winId())):
        print("WARN: capture exclusion failed — move window out of capture region to avoid mirror")
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
