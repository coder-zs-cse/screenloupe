"""Spike C — mss region capture must sustain 30 Hz within CPU budget.

Run:  py -3.13 scripts/spikes/spike_c_capture_perf.py

Pass: 600×1000 region at 30 Hz for 30 s → mean grab+convert < 8 ms, CPU < 10%.
"""

from __future__ import annotations

import time

import mss
from PyQt6.QtGui import QImage

REGION_W = 600
REGION_H = 1000
TARGET_HZ = 30
DURATION_S = 30
MAX_MEAN_MS = 8.0
MAX_CPU_PCT = 10.0


def _grab_to_qimage_copy(shot: object) -> QImage:
    """Fast path: mss RGB bytes → owned QImage (engine should prefer this over BGRA convert)."""
    return QImage(
        shot.rgb,
        shot.width,
        shot.height,
        shot.width * 3,
        QImage.Format.Format_RGB888,
    ).copy()


def main() -> int:
    interval = 1.0 / TARGET_HZ
    timings_ms: list[float] = []

    with mss.MSS() as sct:
        mon = sct.monitors[1]
        left = mon["left"] + max(0, (mon["width"] - REGION_W) // 2)
        top = mon["top"] + max(0, (mon["height"] - REGION_H) // 2)
        region = {"left": left, "top": top, "width": REGION_W, "height": REGION_H}

        print(f"Capturing {REGION_W}×{REGION_H} at {TARGET_HZ} Hz for {DURATION_S} s")
        print(f"Region: {region}")

        # Warmup — first grab can be slower.
        for _ in range(10):
            _grab_to_qimage_copy(sct.grab(region))

        cpu_start = time.process_time()
        wall_start = time.perf_counter()
        deadline = wall_start + DURATION_S
        next_tick = wall_start

        while time.perf_counter() < deadline:
            now = time.perf_counter()
            if now < next_tick:
                time.sleep(next_tick - now)
            next_tick += interval

            t0 = time.perf_counter()
            shot = sct.grab(region)
            _grab_to_qimage_copy(shot)
            timings_ms.append((time.perf_counter() - t0) * 1000)

    wall_elapsed = time.perf_counter() - wall_start
    cpu_pct = ((time.process_time() - cpu_start) / wall_elapsed) * 100 if wall_elapsed > 0 else 0.0
    mean_ms = sum(timings_ms) / len(timings_ms)
    p95_ms = sorted(timings_ms)[int(len(timings_ms) * 0.95)]

    print(f"Frames: {len(timings_ms)}")
    print(f"Mean grab+convert: {mean_ms:.2f} ms (limit {MAX_MEAN_MS} ms)")
    print(f"P95 grab+convert: {p95_ms:.2f} ms")
    print(f"Process CPU: {cpu_pct:.1f}% (limit {MAX_CPU_PCT}%)")

    mean_ok = mean_ms < MAX_MEAN_MS
    cpu_ok = cpu_pct < MAX_CPU_PCT

    if mean_ok and cpu_ok:
        print("PASS: Spike C — capture performance within budget.")
        return 0

    if not mean_ok:
        print(f"FAIL: mean {mean_ms:.2f} ms >= {MAX_MEAN_MS} ms")
    if not cpu_ok:
        print(f"FAIL: CPU {cpu_pct:.1f}% >= {MAX_CPU_PCT}%")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
