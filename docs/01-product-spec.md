# 01 — Product Specification

> What ScreenLoupe does, in exact behavioral terms. If this document and the code disagree, this document wins (or this document gets amended first).

## 1. The problem

Modern IDE layouts squeeze AI chat panels into a narrow right-hand column (file tree left, editor center, chat right). Reading long AI responses there strains the eyes. Existing Windows Magnifier zooms the *whole* screen and hijacks interaction. We want a **passive magnifying glass**: enlarge one region, keep living in the real screen.

## 2. Feature 1 — Region Magnifier

### Activation
- Press `Alt+M` (default, configurable) from anywhere.
- The screen freezes into a **selection mode** visually identical in spirit to `Win+Shift+S`:
  - The whole screen dims (a frozen screenshot under a ~55% black veil).
  - Crosshair cursor.
  - As the user drags, the rubber-band region shows the **bright, undimmed** screenshot — a "torch beam" revealing exactly what will be magnified — with a 1px accent border and live `W × H px` dimension badge near the cursor.
- Cancel paths: `Esc`, or a click with no drag (< 8 px movement).

### On mouse release (valid selection)
- Selector closes instantly.
- A **magnifier overlay** appears, centered on screen, showing a live enlarged view of the selected region.
- Scaling rule (default mode `fit`): scale the region by `s = min(screen_w / sel_w, screen_h / sel_h, max_zoom)` — i.e., as large as the screen allows while preserving aspect ratio, never exceeding `max_zoom` (default 400%). Aspect ratio is **never** distorted.
- Alternate mode `fixed`: scale by exactly `zoom_percent` (clamped so the result fits on screen).

### While active (the core magic)
- The overlay is **click-through**: every click, scroll, and keypress lands on the real windows beneath, exactly as if the overlay didn't exist.
- The overlay is **semi-transparent** (default 92% opaque, configurable 50–100%) so the real screen — including the real cursor position — ghosts through.
- The view is **live**: source region recaptured at `refresh_hz` (default 30), so scrolling the real chat panel scrolls the magnified view.
- The cursor never enters the magnified projection. It stays its normal size, on the real screen. (The OS renders the cursor above everything anyway; the transparency just helps the user track it against the dimmed background.)
- The overlay never appears in its own capture (capture-exclusion — see technical design).

### Deactivation
- `Esc` (default, configurable) → overlay closes, back to normal. Esc is only intercepted while ScreenLoupe has an active overlay.
- `Alt+M` again → tear down current overlay, restart selection.

## 3. Feature 2 — Cursor Lens (hold-to-magnify)

- **Hold** `Alt+N` (default, configurable): a lens appears centered on the cursor, magnifying the area under/around it. It follows the cursor live.
- **Release** the combo: lens vanishes. No toggle, no Esc needed — the hold *is* the lifetime.
- Lens parameters (all configurable):
  - `lens_radius` — half-size of the lens viewport in px (default 220 → a 440×440 lens). Shape: rounded-rect (rectangle, soft corners; a circle is a settings option, `lens_shape`).
  - `lens_zoom` — magnification depth (default 200%, range 120–500%).
  - `lens_refresh_hz` — default 60 (lens is small, capture is cheap; smooth tracking matters more here than in region mode).
- The lens window is click-through and capture-excluded, same as the magnifier.
- Source rect = `(lens_size / lens_zoom)` square centered on the cursor — the lens shows the area *under itself*, magnified, like real glass.

## 4. Feature 3 — Master toggle

- Global hotkey (default `Ctrl+Alt+M`, configurable) flips ScreenLoupe between **Enabled / Disabled**.
- Disabled: all hooks stay registered but only the master toggle does anything; tray icon switches to a grayed variant; tray tooltip says "ScreenLoupe (off)".
- Also toggleable from the tray menu and the settings General page.

## 5. Feature 4 — System tray residence

- ScreenLoupe runs as a tray app. Closing the settings window hides it; the app keeps running.
- Tray icon states: normal (enabled), grayed (disabled).
- Tray menu: `Magnify region (Alt+M)` · `Enabled ✓` · `Settings…` · `Quit ScreenLoupe`.
- Double-click tray icon → open Settings.
- Single instance: launching the .exe again focuses the existing instance's settings window instead of spawning a second tray icon.

## 6. Feature 5 — Settings window

Layout: **left vertical tab rail** (icons + labels), **right content pane**, bottom-right `Apply` / `Cancel` buttons. `Apply` persists + hot-reloads (re-registers hotkeys, updates running overlays' opacity/refresh live where feasible). `Cancel` discards edits. Unsaved-changes dot on the tab label.

### Pages and settings inventory

| Page | Setting | Type | Default | Range/Notes |
|---|---|---|---|---|
| **General** | Run ScreenLoupe at Windows startup | bool | `true` | HKCU Run key |
| | ScreenLoupe enabled | bool | `true` | mirrors master toggle |
| **Shortcuts** | Magnify region | hotkey | `Alt+M` | recorder widget |
| | Dismiss overlay | hotkey | `Esc` | recorder widget |
| | Cursor lens (hold) | hotkey | `Alt+N` | recorder widget |
| | Master toggle | hotkey | `Ctrl+Alt+M` | recorder widget |
| **Magnifier** | Zoom mode | enum | `fit` | `fit` \| `fixed` |
| | Zoom percent (fixed mode) | int | `200` | 120–500, slider+spin |
| | Max zoom cap (fit mode) | int | `400` | 150–800 |
| | Overlay opacity | int | `92` | 50–100 (%) |
| | Refresh rate | int | `30` | 10–60 Hz |
| **Lens** | Lens radius | int | `220` | 100–500 px |
| | Lens zoom | int | `200` | 120–500 (%) |
| | Lens refresh rate | int | `60` | 15–120 Hz |
| | Lens shape | enum | `rounded` | `rounded` \| `circle` |
| **About** | version, OS check (build ≥ 19041 ✓/✗), link to repo, licenses | — | — | — |

### Hotkey recorder widget behavior
- Click → "Press a combination…" → captures next chord → displays it (`Alt+M`).
- Validation: reject bare modifiers; reject duplicates across the four bindings (inline error); `Esc` while recording cancels recording (so `Esc` itself is assigned via a small "Set to Esc" link, avoiding the capture-the-canceller paradox).

## 7. Feature 6 — Installer (setup wizard)

A single `ScreenLoupe-Setup.exe` (Inno Setup) with pages:
1. **Welcome** — branding, one-line pitch.
2. **Install location** — default `%LOCALAPPDATA%\Programs\ScreenLoupe` (per-user, no admin elevation needed).
3. **Options** — checkboxes: ☑ Create Start Menu shortcut · ☑ Run ScreenLoupe when Windows starts · ☐ Create desktop shortcut.
4. **Install** — progress.
5. **Finish** — ☑ Launch ScreenLoupe now. First launch shows a small "how to use" toast pointing at the tray icon with the two hotkeys.
- Installer enforces minimum Windows 10 build 19041 (capture exclusion requirement) and aborts with a clear message below it.
- Proper uninstaller registered in Apps & Features; uninstall removes the Run key and Start Menu entries, asks whether to delete `%APPDATA%\ScreenLoupe`.

## 8. Edge cases the implementation must handle

| # | Case | Behavior |
|---|---|---|
| E1 | Selection smaller than 8×8 px | Treat as cancel |
| E2 | `Alt+M` while MAGNIFYING | Restart selection (tear down → SELECTING) |
| E3 | Hold `Alt+N` while MAGNIFYING | Ignore (one overlay at a time, v1) |
| E4 | Hotkey conflict with another app | Ours fires too (hooks see everything); document; user can rebind |
| E5 | Display config change (monitor unplug, resolution/DPI change) mid-overlay | Dismiss overlays, return to IDLE |
| E6 | Locked screen / UAC secure desktop | Hooks silently inactive there; resume after — no special handling needed |
| E7 | Source region contains DRM-protected content (e.g., Netflix) | Region renders black — that's the OS, not a bug; note in README/FAQ |
| E8 | Config file corrupt/missing | Recreate defaults, log a warning, never crash |
| E9 | Second .exe launch | Focus existing instance (named mutex + window message) |

## 9. Explicitly out of scope (v1)

- Multi-monitor selection spanning monitors (v1: selector and overlay live on the monitor where the cursor was at activation; primary-monitor fallback).
- Interacting *inside* the magnified projection (input forwarding/remapping). The product is a loupe, not a remote-desktop.
- Multiple simultaneous magnifier overlays.
- macOS/Linux.
- Auto-update.

## 10. Open questions (defaults chosen; flag to product owner)

| # | Question | Default chosen |
|---|---|---|
| Q1 | Zoom semantics: is "zoom percentage" a cap on fit-to-screen, or an exact factor? | Both, via `zoom mode` (`fit` default + cap). Confirm. |
| Q2 | Should the magnifier overlay be repositionable/dockable (e.g., always left half)? | v1: centered, fixed. |
| Q3 | Lens shape default rounded-rect vs circle? | Rounded-rect (text reads better in a rect). |
| Q4 | Master toggle default chord `Ctrl+Alt+M` okay? | Yes until told otherwise. |
