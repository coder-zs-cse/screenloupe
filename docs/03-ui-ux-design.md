# 03 — UI / UX Design

> ScreenLoupe's visual identity: a precision optical instrument, not a clip-art accessibility tool. Calm, dark, glassy. The brand metaphor is **lens and light** — everything bright is "in focus", everything dim is "at rest".

## 1. Design language

| Token | Value | Used for |
|---|---|---|
| `--bg` | `#16181D` | window backgrounds |
| `--surface` | `#1E2128` | cards, tab rail |
| `--surface-2` | `#262A33` | inputs, hover |
| `--text` | `#E8EAED` | primary text |
| `--text-dim` | `#9AA0A8` | secondary text |
| `--accent` | `#4FC3F7` (loupe-glass cyan) | borders of "focused" things: selection rubber-band, active tab indicator, primary buttons, lens rim |
| `--accent-warm` | `#FFB74D` | warnings (hotkey conflicts) |
| Radius | 10 px windows/cards, 6 px inputs | |
| Type | Segoe UI Variable; 13 px body, 20 px page titles | native Windows feel |

Implemented as one QSS stylesheet in `ui/theme.py`. Dark only in v1 (the tool exists to *reduce* eye strain).

**Logo/icon:** a minimal magnifying-glass circle with a cyan rim and a small "focus glint"; tray variants: full-color (enabled), 40%-desaturated (disabled). Deliver as `assets/icon.ico` (16→256 px) + two tray PNGs.

## 2. Setup wizard (Inno Setup, custom-skinned)

Inno's modern wizard style with custom imagery — left-side vertical banner (`assets/wizard-banner.bmp`, 164×314): deep `--bg` gradient, the loupe mark, the word *ScreenLoupe* set vertically, a faint enlarged-text motif behind it.

| Page | Content & copy |
|---|---|
| Welcome | "**Read big. Stay where you are.** ScreenLoupe magnifies any region of your screen into a live, see-through overlay — your windows, your cursor, your flow stay untouched." |
| Location | Standard dir page, default `%LOCALAPPDATA%\Programs\ScreenLoupe` |
| Options | ☑ Start Menu shortcut · ☑ Run when Windows starts · ☐ Desktop shortcut |
| Progress | standard |
| Finish | ☑ Launch ScreenLoupe — "Tip: press **Alt+M** anytime to magnify." |

First-launch experience: a tray balloon/toast — "ScreenLoupe is running here 👇 · **Alt+M** select & magnify · hold **Alt+N** for a cursor lens."

## 3. Settings window (760 × 520, fixed)

```
┌────────────────────────────────────────────────────────────┐
│  ⬤ ScreenLoupe Settings                              ─ □ ✕ │
├──────────────┬─────────────────────────────────────────────┤
│              │  Magnifier                                  │
│  ⚙ General   │  ─────────────────────────────────────────  │
│  ⌨ Shortcuts │  Zoom mode        ( • Fit to screen )       │
│ ▎🔍 Magnifier │                   (   Fixed percent  )      │
│  ◎ Lens      │  Max zoom         [——————●———]  400 %       │
│  ⓘ About     │  Overlay opacity  [————————●—]   92 %       │
│              │  Refresh rate     [——●———————]   30 Hz      │
│              │                                             │
│              │  ┌───────────────────────────────────────┐  │
│              │  │   live preview tile (sample text      │  │
│              │  │   rendered at chosen zoom & opacity)  │  │
│              │  └───────────────────────────────────────┘  │
├──────────────┴─────────────────────────────────────────────┤
│                                  [ Cancel ]  [ Apply ]     │
└────────────────────────────────────────────────────────────┘
```

- Tab rail 170 px wide; active tab gets a 3 px `--accent` left bar (`▎`) + `--surface-2` fill.
- The **preview tile** is the page's delight detail: a static paragraph re-rendered live as the user drags zoom/opacity sliders — feel before Apply. (Pure QWidget repaint, no capture involved — cheap.)
- Apply enabled only when dirty; dirty tabs show a small dot.
- Shortcuts page: four rows of `label — [hotkey recorder] — reset-to-default ↺`; conflict shows `--accent-warm` underline + "Already used by *Master toggle*".

## 4. Selection overlay (the Win+Shift+S moment)

The interaction must feel **instant and physical** — light cutting through dark:

- Frozen full-screen frame under `rgba(0,0,0,0.55)` veil; cursor → crosshair.
- A hint pill fades in top-center after 150 ms: `Drag to magnify · Esc to cancel` (12 px, `--surface` @ 85%, disappears on first mouse-down).
- During drag: the band region paints the **undimmed** frozen frame (torch-beam effect), 1 px `--accent` border, 4 corner handles (visual only), and a `1184 × 312` dimension badge tracking the cursor.
- On release: veil and band do a 120 ms fade while the magnifier overlay does a 150 ms scale-in from the selection rect toward screen center — a tiny "lens pull" animation that *teaches the spatial relationship* between the small source and the big projection. (Animations are `QPropertyAnimation`; keep total < 200 ms; honor "no animation" if it complicates Phase 3 — polish, not core.)

## 5. Magnifier overlay chrome

Content is king — chrome is nearly nothing:
- 1 px `--accent` border at 35% alpha around the projection (signals "this is the loupe, not reality").
- 8 px radius corners; subtle 24 px soft shadow.
- Bottom-right corner, 70% alpha, auto-hides after 2.5 s: `2.4× · Esc to close`.
- No buttons. No titlebar. It's glass.

Lens overlay: 2 px `--accent` rim (the "lens barrel"), rounded-rect or circle per setting, no other chrome.

## 6. Tray menu

```
🔍 Magnify region      Alt+M
──────────────────────────
✓ Enabled        Ctrl+Alt+M
   Settings…
──────────────────────────
   Quit ScreenLoupe
```

## 7. Microcopy principles

- Verbs over nouns: "Magnify region", not "Region magnification mode".
- Always show the hotkey next to the action — the hotkeys *are* the product.
- Never say "zoom in/out" for the overlay (it implies navigation); say **magnify / dismiss**.
