# 04 — Implementation Plan & Packaging

> Phased, risk-first: the two physics experiments (capture exclusion, click-through) come before any product code. Each phase has a verify step — if it can't be verified, it isn't done.

## Phase 0 — Scaffold (½ day)

Create the full directory tree, `pyproject.toml` (deps: PyQt6, mss, keyboard, pywin32; dev: pytest, ruff), empty modules with docstrings, `core/config.py` with the full schema + load/save + clamping, `tests/test_config.py`.

**Verify:** `python -m screenloupe` starts and exits cleanly; `pytest` green on config round-trip + corrupt-file recovery; `ruff check` clean.

## Phase 1 — The two physics spikes (1 day) ⚠️ DO FIRST

These two experiments validate the entire product. Write them as throwaway scripts in `scripts/spikes/` before building real modules.

**Spike A — capture exclusion:** translucent red topmost window over a known region → `SetWindowDisplayAffinity(hwnd, 0x11)` → mss-grab that region → assert zero red pixels (and visually confirm the red window IS on screen).
**Spike B — click-through:** apply the full overlay style set (`02-technical-design § 2`) to a half-screen translucent window over a browser → confirm scroll, click, and typing all reach the browser; confirm the window never takes focus.
**Spike C — capture perf:** loop mss-grabbing a 600×1000 region at 30 Hz for 30 s → assert mean grab+convert < 8 ms and process CPU < 10%.

**Verify:** all three pass on the dev machine (Windows build ≥ 19041). **If A fails, stop — the architecture needs rethink before any further code.**

## Phase 2 — Capture engine + overlay base (1 day)

`capture/engine.py` (QTimer, frame_ready signal, retarget, skip-on-overrun), `capture/exclusion.py`, `overlay/win32_window.py`, `platformwin/dpi.py` with `logical_to_physical`/inverse.

**Verify:** unit tests for geometry conversion at DPR 1.0/1.25/1.5; a dev-only debug window displays a live 30 Hz feed of a hardcoded region; engine start/stop/start leaks nothing (Task Manager handle count stable over 50 cycles).

## Phase 3 — Selector overlay (1 day)

Frozen-frame veil, torch-beam rubber band, dimension badge, hint pill, Esc/short-drag cancel, `region_selected(Rect)` in physical pixels.

**Verify:** at 125% DPI scaling, select a region around a known on-screen landmark; assert emitted rect matches a fresh mss grab of the same landmark (pixel-compare corners). Cancel paths return to IDLE with no orphan window.

## Phase 4 — Magnifier overlay + state machine (1–2 days)

`core/state.py` transitions, `app.py` controller wiring, `overlay/magnifier.py` with `fit_geometry()` (unit-tested pure function), live repaint at opacity, accent border + auto-hiding zoom badge, Esc dismiss, Alt+M restart.

**Verify:** unit tests for `fit_geometry` (wide sel, tall sel, sel near screen size, max_zoom clamp, never-shrink); end-to-end: magnify the Cursor chat column, scroll the *real* column with the overlay up → overlay text scrolls live; no feedback mirror; cursor visibly tracks through the translucent overlay; state-machine table test covers every transition incl. E2/E3.

## Phase 5 — Cursor lens (1 day)

Hold detection (down/up via `keyboard` hooks, queued signals), lens window follow at `lens_refresh_hz`, source clamping at screen edges, rounded/circle shapes.

**Verify:** hold Alt+N and trace all four screen edges → lens never shows garbage or off-screen black, zoom stays truthful; release with `Alt` first then `N` first → both dismiss; rapid press-release 20× → no stuck lens, no handle leak.

## Phase 6 — Tray + settings window (2 days)

`ui/tray.py` (state icons, menu), `ui/theme.py` QSS, settings shell (rail + pages + Apply/Cancel + dirty tracking), all five pages per spec, hotkey recorder widget with validation, live preview tile, hot-reload on Apply (re-register hotkeys, push opacity/refresh into running overlays), `platformwin/startup.py` registry toggle, single-instance mutex + focus-existing.

**Verify:** rebind magnify to Alt+Q → Alt+M inert, Alt+Q works, persists across restart; duplicate binding blocked with inline warning; Cancel discards; startup toggle verified in `regedit` and Task Manager → Startup tab; second exe launch focuses settings.

## Phase 7 — Packaging & installer (1 day)

- `scripts/build.ps1`: PyInstaller `--onedir --noconsole --icon assets/icon.ico --name ScreenLoupe`, then Inno `ISCC installer/screenloupe.iss` → `dist/ScreenLoupe-Setup.exe`.
- `installer/screenloupe.iss`: per-user install (`PrivilegesRequired=lowest`, `DefaultDirName={localappdata}\Programs\ScreenLoupe`), `MinVersion=10.0.19041`, wizard pages + options checkboxes per product spec, Start Menu entry under `{userprograms}`, optional Run-key task, uninstaller (removes Run key; asks about `%APPDATA%\ScreenLoupe`), launch-on-finish.
- First-run toast (app side: show once, flag in config).

**Verify on a clean Windows VM (not the dev machine):** install with defaults → searchable from Start, Run key present, tray appears after reboot, Alt+M works inside the installed copy; uninstall → Run key gone, Start entry gone, Apps & Features entry gone.

## Phase 8 — Hardening pass (1 day)

Walk the edge-case table (product spec § 8): display-change dismissal, corrupt config recovery, DRM-black note in README, hold-lens during magnify ignored, sub-8px selection cancel. Add `README` FAQ.

**Verify:** each E# row has either a test or a recorded manual check in the PR description.

---

## Dependency order (what blocks what)

```
P0 ──► P1 (spikes) ──► P2 (engine+base) ──► P3 (selector) ──► P4 (magnifier+state) ──► P6 (tray+settings) ──► P7 (installer) ──► P8
                                        └──────────────────► P5 (lens, needs only P2)
```

P5 can run parallel to P3/P4. Total estimate: ~8–10 focused days.

## Definition of Done (v1 release)

1. On a clean VM: install → reboot → Alt+M → select Cursor's chat column → read it full-screen → scroll it live → Esc. Zero crashes, zero mirrors, cursor always visible.
2. Hold Alt+N → smooth lens at 60 Hz following the cursor edge-to-edge.
3. Every setting in the spec table exists, applies live, and survives restart.
4. `pytest` green; `ruff` clean; all pure geometry/config/state logic covered by unit tests.
5. README quickstart accurate enough that a stranger ships a PR without asking questions.
