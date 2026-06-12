# ScreenLoupe — Architecture

## 1. System overview

ScreenLoupe is a **tray-resident state machine** that orchestrates three kinds of borderless, always-on-top, click-through overlay windows over a live screen-capture pipeline.

```
                ┌─────────────────────────────────────────────┐
                │                 main.py                     │
                │  single-instance guard → DPI awareness →    │
                │  QApplication → AppController → tray        │
                └──────────────────────┬──────────────────────┘
                                       │
                        ┌──────────────▼──────────────┐
                        │      AppController (app.py) │
                        │  owns the AppState machine  │
                        └──┬─────────┬─────────┬──────┘
              events       │         │         │ reads/writes
        ┌──────────────────▼──┐   ┌──▼──────┐ ┌▼──────────────┐
        │  HotkeyManager      │   │ Overlays │ │ ConfigStore   │
        │  (global hooks)     │   │ selector │ │ JSON @        │
        │  Alt+M / Alt+N /    │   │ magnifier│ │ %APPDATA%/    │
        │  Esc / master toggle│   │ lens     │ │ ScreenLoupe   │
        └─────────────────────┘   └──┬───────┘ └───────────────┘
                                     │ frames @ refresh_rate
                              ┌──────▼────────────┐
                              │ CaptureEngine     │
                              │ mss region grab   │
                              │ (overlays excluded│
                              │  from capture via │
                              │  WDA flag)        │
                              └───────────────────┘
```

## 2. The state machine (heart of the app)

All hotkey events route through one place. No overlay decides its own lifecycle.

```
                       Alt+M
        ┌──────────┐ ───────────► ┌────────────┐
        │   IDLE   │              │ SELECTING  │
        │ (tray    │ ◄─────────── │ (selector  │
        │  only)   │   Esc /      │  overlay)  │
        └───┬──▲───┘   click-     └─────┬──────┘
            │  │       cancel           │ mouse release
   hold     │  │                        ▼ (valid rect)
   Alt+N    │  │  Esc / Alt+M     ┌────────────┐
            │  └───────────────── │ MAGNIFYING │
            ▼                     │ (live      │
        ┌──────────┐              │  overlay)  │
        │   LENS   │              └────────────┘
        │ (follows │
        │  cursor) │──release Alt+N──► IDLE
        └──────────┘

   DISABLED (master toggle): all hotkeys except the toggle itself are ignored.
```

Rules:
- Exactly **one** overlay state active at a time (v1). Entering a new state tears down the previous overlay.
- `Alt+M` while MAGNIFYING restarts selection (common flow: "let me re-frame").
- `Esc` is **only intercepted while SELECTING or MAGNIFYING** — globally swallowing Esc would break every other app on the system. In IDLE/LENS/DISABLED, Esc passes through untouched.
- LENS is hold-gated: key-down enters, key-up exits. If the hold begins while MAGNIFYING, ignore it (don't stack overlays).

## 3. Module responsibilities

| Module | Responsibility | Must NOT do |
|---|---|---|
| `main.py` | Single-instance mutex, DPI awareness call (before QApplication!), bootstrap | Business logic |
| `app.py` (AppController) | Owns AppState; routes hotkey events → overlay lifecycle; applies config changes live | Win32 calls, painting |
| `core/config.py` | Typed settings schema (dataclass), JSON load/save, validation, defaults | UI concerns |
| `core/state.py` | `AppState` enum + transition guard table | Side effects |
| `capture/engine.py` | Region capture at a target FPS on a QTimer; returns QImage | Window management |
| `capture/exclusion.py` | `set_capture_excluded(hwnd)` → `SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE)` | Anything else |
| `hotkeys/manager.py` | Register/unregister combos from config; emit Qt signals: `magnify_requested`, `lens_pressed`, `lens_released`, `escape_pressed`, `toggle_requested` | Knowing what the signals mean |
| `overlay/win32_window.py` | One helper: apply click-through + no-activate + capture-exclusion to a QWidget after `show()` | App logic |
| `overlay/selector.py` | Full-screen frozen-frame dim + rubber-band selection; emits `region_selected(QRect)` in **physical pixels** | Magnification |
| `overlay/magnifier.py` | Fit-to-screen scaling math, live repaint of captured frames at configured opacity | Capture itself, hotkeys |
| `overlay/lens.py` | Cursor-follow lens window, repositions + repaints per tick | Selection |
| `ui/tray.py` | Tray icon (state-reflecting), context menu | Overlay logic |
| `ui/settings/` | Settings window: tab rail, pages, Apply/Cancel, hotkey recorder widget | Direct config file IO (goes through ConfigStore) |
| `platformwin/startup.py` | HKCU `...\Run` registry add/remove | UI |
| `platformwin/dpi.py` | Per-Monitor-v2 awareness, logical↔physical coordinate conversion | Anything else |

## 4. Data flow: one magnification session

1. `HotkeyManager` detects `Alt+M` → emits `magnify_requested`.
2. `AppController` (IDLE) → captures one full-screen frame → opens `SelectorOverlay` with it → state SELECTING.
3. User drags; on release `SelectorOverlay` emits `region_selected(rect_physical)` and closes.
4. Controller computes the display geometry (fit-to-screen, see `docs/02 § 4`), opens `MagnifierOverlay`, marks it capture-excluded + click-through → state MAGNIFYING.
5. `CaptureEngine` QTimer fires at `refresh_hz`: grab `rect_physical` → controller hands QImage to overlay → overlay scales + paints at `opacity`.
6. User scrolls the *real* chat panel (overlay is click-through; cursor must be over the original region). Next frames reflect the scroll. The loupe is live.
7. `Esc` → engine stops, overlay closes → IDLE.

## 5. Key design decisions (and why)

**D1 — Python + PyQt6, not C#/WPF/Electron.**
The three hard problems (capture exclusion, click-through layered windows, global hold-detection hooks) are raw Win32 calls — equally one `ctypes` call away in Python as one P/Invoke away in C#. PyQt6 gives us the overlay rendering, tray, and settings UI in one framework, and a prior prototype already validated click-through overlays in PyQt6. Cost: ~80–120 MB installed footprint vs ~5 MB for C#. Accepted for v1; revisit only if footprint becomes a user complaint.

**D2 — `mss` first, `dxcam` later.**
`mss` (GDI) is dead-simple, dependency-light, and easily sustains 30–60 fps for *partial-screen regions* (our case — we capture a column, not 4K fullscreen). `dxcam` (DXGI Desktop Duplication) is faster but heavier and finicky on multi-GPU laptops (Optimus). The `CaptureEngine` interface is capture-method-agnostic so swapping is a one-file change. Do not build both in v1.

**D3 — Capture exclusion via `WDA_EXCLUDEFROMCAPTURE`, hard requirement Win10 2004+.**
The overlay sits on top of its own capture source → without exclusion, infinite feedback. This flag makes the overlay invisible to BitBlt/DXGI while visible on the physical display. We declare Windows 10 2004+ (build 19041) the minimum supported OS in the installer rather than building a fallback (a fallback would require capturing *around* the overlay or hiding-and-grabbing per frame — flicker hell). YAGNI.

**D4 — Click-through overlay = the user interacts with reality, not the projection.**
`WS_EX_TRANSPARENT | WS_EX_LAYERED` + `WS_EX_NOACTIVATE` + Qt `WA_TransparentForMouseEvents`. Consequence (intentional, per product spec): to scroll the magnified content, the cursor must be over the *original* small region. The semi-transparency exists precisely so the user can still see where their cursor is. **Do not** implement input forwarding into the magnified view in v1 — that is a different, much harder product.

**D5 — All capture/selection geometry in physical pixels.**
Qt reports logical pixels under DPI scaling (125%/150% is the laptop default). `mss` and Win32 speak physical pixels. The rule: convert at the boundary (`platformwin/dpi.py`), store and compute everything internally in physical pixels. One coordinate space inside the core, or selection rects will be wrong by exactly the scaling factor.

**D6 — `keyboard` library over `RegisterHotKey`.**
`RegisterHotKey` cannot detect key *release* — and the Lens feature is hold-to-activate. The `keyboard` lib's low-level hook gives both press and release. Tradeoff: hooks are process-global and some AV software flags keylogger-like behavior; mitigated by code-signing later and by never logging keys (hook handlers compare against configured combos only).

**D7 — Settings: JSON at `%APPDATA%/ScreenLoupe/config.json`.**
Human-readable, diffable, trivially versioned (`"config_version": 1`). Registry only for the run-on-startup entry (that's where Windows looks for it).

**D8 — Installer wizard = Inno Setup, not a custom PyQt wizard.**
"Setup wizard with steps, Start Menu shortcut, run-on-startup checkbox" is exactly what Inno Setup does natively, with correct elevation, uninstall, and upgrade handling that would take weeks to reimplement. The app itself never touches Start-Menu creation; the installer owns it.

## 6. Anti-patterns for this codebase

- ❌ No overlay may register its own hotkeys or manage its own state transitions — controller only.
- ❌ No Qt logical-pixel value may enter `capture/` or geometry math — convert first.
- ❌ No per-frame allocation churn in the capture loop (reuse buffers; this loop runs 30×/sec).
- ❌ No blocking work on the Qt main thread > 5 ms inside the repaint path.
- ❌ No global Esc interception outside SELECTING/MAGNIFYING states.
- ❌ No settings writes from UI pages directly to disk — everything through `ConfigStore` so Apply/Cancel semantics hold.
- ❌ Never call any DPI-awareness API after the first window exists — it must precede `QApplication`.
