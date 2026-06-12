# CLAUDE.md — AI Editor Guide for ScreenLoupe

> You are implementing/extending ScreenLoupe, a Windows screen-magnifier tray app.
> **Before writing any code, read `KARPATHY.md`.** Then read `ARCHITECTURE.md` and the four docs in `docs/` in numeric order. The design docs are the source of truth; if a request conflicts with them, surface the conflict — don't silently diverge.

## Full directory tree

```
screenloupe/
├── README.md                      # overview, setup, structure
├── ARCHITECTURE.md                # system design, state machine, key decisions D1–D8
├── CLAUDE.md                      # this file
├── KARPATHY.md                    # coding behavior contract — read first
├── .cursorrules                   # Cursor mirror of this guidance
├── pyproject.toml                 # deps, entry point (screenloupe = screenloupe.main:run), ruff
├── assets/
│   ├── icon.ico                   # app icon (16–256px)
│   ├── tray_on.png / tray_off.png # tray states
│   └── wizard-banner.bmp          # Inno wizard left banner (164×314)
├── installer/
│   └── screenloupe.iss            # Inno Setup script (wizard, Start Menu, Run key, MinVersion 19041)
├── scripts/
│   ├── build.ps1                  # PyInstaller + ISCC → dist/ScreenLoupe-Setup.exe
│   └── spikes/                    # Phase-1 throwaway experiments (keep; they document feasibility)
├── src/screenloupe/
│   ├── __init__.py                # __version__
│   ├── main.py                    # DPI awareness FIRST, single-instance mutex, QApplication, boot
│   ├── app.py                     # AppController — the ONLY owner of state transitions
│   ├── core/
│   │   ├── config.py              # dataclass schema, JSON load/save, clamping, corruption recovery
│   │   ├── constants.py           # paths, app name, mutex/message names, Win32 constants
│   │   └── state.py               # AppState enum + allowed-transition table
│   ├── capture/
│   │   ├── engine.py              # CaptureEngine (QTimer, mss, frame_ready, retarget, skip-on-overrun)
│   │   └── exclusion.py           # set_capture_excluded(hwnd) — WDA_EXCLUDEFROMCAPTURE
│   ├── hotkeys/
│   │   └── manager.py             # keyboard-lib hooks → queued Qt signals; dynamic Esc registration
│   ├── overlay/
│   │   ├── win32_window.py        # make_overlay(): click-through + no-activate + toolwindow styles
│   │   ├── selector.py            # frozen-frame veil + rubber band → region_selected(Rect physical)
│   │   ├── magnifier.py           # fit_geometry() + live magnified projection
│   │   └── lens.py                # cursor-follow lens
│   ├── ui/
│   │   ├── tray.py                # tray icon, menu, first-run toast
│   │   ├── theme.py               # QSS design tokens (docs/03 § 1)
│   │   └── settings/
│   │       ├── window.py          # shell: rail + stack + Apply/Cancel + dirty tracking
│   │       ├── pages/             # general.py, shortcuts.py, magnifier.py, lens.py, about.py
│   │       └── widgets/           # hotkey_recorder.py, labeled_slider.py, preview_tile.py
│   └── platformwin/               # NOT "platform" — that shadows a stdlib module
│       ├── startup.py             # HKCU Run key add/remove/query
│       └── dpi.py                 # awareness call + logical↔physical conversion
└── tests/                         # mirrors src; pure logic only (geometry, config, state table)
```

## How to run

```powershell
pip install -e ".[dev]"
python -m screenloupe        # tray app
pytest                       # unit tests (no display required — pure logic only)
ruff check src tests
.\scripts\build.ps1          # full installer build
```

## Where new things go

- New setting → `core/config.py` schema (+ default + clamp) → relevant `ui/settings/pages/` page → consume where used. Never read JSON anywhere else.
- New hotkey action → register in `hotkeys/manager.py`, new signal → handle in `app.py` only.
- New overlay type → subclass pattern in `overlay/`, get window styles exclusively via `win32_window.make_overlay`, get capture-exclusion via `capture/exclusion.py`. Lifecycle owned by `app.py`.
- New Win32 call → constant in `core/constants.py`, wrapper in the topically-right module. Never inline magic numbers at call sites.

## Conventions

- Python 3.11+, full type hints, `ruff` (line length 100).
- Qt signal names: past/declarative facts (`region_selected`, `frame_ready`), not commands.
- **All geometry in `capture/`, `overlay/` math, and config is PHYSICAL pixels.** Convert only via `platformwin/dpi.py` at the Qt boundary. A `Rect` here is always physical — name variables `*_logical` in the rare UI spots that aren't.
- Hook-thread → Qt: queued signal connections only. Never touch widgets from the `keyboard` callback thread.
- Errors: never crash the tray app. Catch at controller boundaries, log to `%APPDATA%/ScreenLoupe/screenloupe.log` (rotating, 1 MB), degrade to IDLE.
- Tests: pure functions (`fit_geometry`, config clamping, state transitions) get unit tests. Overlay/capture behavior is verified by the phase verify-steps in `docs/04` (manual on Windows) — don't fake-mock Win32 into meaningless green tests.

## Gotchas (learned the hard way — do not rediscover)

1. **DPI awareness must be set before QApplication is created.** It's the first statement in `main()`. Setting it later silently no-ops and every coordinate is wrong at 125% scaling.
2. **`SetWindowDisplayAffinity` needs a real hwnd** — call after `widget.show()`, and re-apply if Qt recreates the native window (changing certain window flags does this — set ALL flags before show, then never touch them).
3. **Without capture exclusion you get an infinite mirror**, not an error. If you see recursion in the overlay, exclusion didn't take.
4. **`mss` is thread-affine** — create the instance on the thread that grabs. v1 grabs on the Qt main thread via QTimer; do not "optimize" into a thread without measuring first (Spike C numbers).
5. **The selector is the only overlay allowed to take focus/mouse.** If a magnifier/lens ever steals focus, the click-through styles weren't applied or were applied before show.
6. **`Esc` suppression is dynamic.** Suppressing it globally breaks every other app. Only hook it in SELECTING/MAGNIFYING.
7. **`keyboard` lib callbacks run off-thread** — see conventions. The classic crash is updating a widget from a hook callback; it works in dev 9 times then segfaults.
8. **Package dir is `platformwin/`,** because `platform` shadows the stdlib and breaks PyInstaller analysis.
9. PyInstaller: use `--onedir` (not `--onefile` — slow tray startup) and `--noconsole`; the `keyboard` and `mss` hooks are picked up automatically, but verify the built exe on a clean VM, not the dev box.
