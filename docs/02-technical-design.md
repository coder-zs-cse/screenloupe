# 02 — Technical Design

> The five mechanisms that make ScreenLoupe possible, with the exact API calls. Get these right and everything else is plumbing.

## 1. The feedback-loop problem & capture exclusion (CRITICAL)

The magnifier overlay covers a large screen area **including (usually) its own capture source**. Naively capturing the screen captures the overlay → which displays the capture → infinite recursive mirror within ~3 frames.

**Solution:** exclude every overlay window from screen capture:

```python
# capture/exclusion.py
import ctypes
WDA_EXCLUDEFROMCAPTURE = 0x00000011  # Windows 10 2004+ (build 19041)

def set_capture_excluded(hwnd: int) -> bool:
    """Window stays visible on the physical display but is invisible
    to BitBlt / PrintWindow / DXGI duplication. Returns False on
    unsupported OS (caller must have gated on build >= 19041)."""
    return bool(ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE))
```

Call **after** the QWidget is shown (needs a real hwnd: `int(widget.winId())`). Apply to: magnifier overlay, lens overlay, and the selector overlay (selector shows a frozen frame, but excluding it is free insurance). Side effect to document: ScreenLoupe overlays won't appear in the user's own screenshots/screen-shares — for this product that's a feature.

**Verification spike (Phase 1, before anything else):** show a red translucent excluded window over a region, capture that region with mss, assert no red pixels. If this fails on the dev machine, stop and reassess.

## 2. Click-through, no-steal, always-on-top overlay windows

Every overlay needs four properties: topmost, frameless, never takes focus, lets all mouse input pass through.

```python
# overlay/win32_window.py
import ctypes
from PyQt6.QtCore import Qt

GWL_EXSTYLE       = -20
WS_EX_LAYERED     = 0x00080000
WS_EX_TRANSPARENT = 0x00000020   # mouse events pass to the window below
WS_EX_NOACTIVATE  = 0x08000000   # never steals keyboard focus
WS_EX_TOOLWINDOW  = 0x00000080   # no taskbar button, no Alt+Tab entry

def make_overlay(widget) -> None:
    """Call AFTER widget.show(). Qt flags handle the Qt side;
    Win32 ex-styles handle the OS side. Both are required."""
    widget.setWindowFlags(Qt.WindowType.FramelessWindowHint
                          | Qt.WindowType.WindowStaysOnTopHint
                          | Qt.WindowType.Tool)
    widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
    widget.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

    hwnd = int(widget.winId())
    u32 = ctypes.windll.user32
    ex = u32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    u32.SetWindowLongW(hwnd, GWL_EXSTYLE,
        ex | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW)
```

Exception: the **selector** overlay must RECEIVE mouse input (it's how the user drags a rectangle) — selector gets frameless+topmost+no-activate but **not** `WA_TransparentForMouseEvents`/`WS_EX_TRANSPARENT`. It also sets a cross cursor and grabs `Esc` via normal Qt `keyPressEvent` (it has focus by design — the one window that may take it).

Overlay opacity: `widget.setWindowOpacity(opacity / 100)` — uniform window alpha, exactly the "ghosting" the product wants, cheaper than per-pixel alpha compositing.

## 3. Coordinate spaces & DPI (the silent killer)

Three coordinate systems coexist:
- **Physical pixels** — what mss, Win32 cursor APIs, and the actual framebuffer use.
- **Qt logical pixels** — physical ÷ devicePixelRatio (1.25 at 125% scaling).
- **Per-monitor DPI** — each monitor can differ.

**Rules:**
1. First line of `main()` — before QApplication exists:
   ```python
   ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)  # PER_MONITOR_AWARE_V2
   ```
   With per-monitor-v2 awareness, Qt's devicePixelRatio behaves predictably and physical geometry is real.
2. **Everything inside `capture/`, geometry math, and config-stored rects is physical pixels.** Conversion happens only in `platformwin/dpi.py` (`logical_to_physical(qrect, screen)` / inverse), called at the Qt boundary.
3. Cursor position for the lens: `ctypes.windll.user32.GetCursorPos(byref(POINT()))` → already physical. Never use Qt's `QCursor.pos()` in the lens path (logical).

## 4. Geometry: fit-to-screen scaling

```python
# overlay/magnifier.py — pure function, unit-tested
def fit_geometry(sel: Rect, screen: Rect, max_zoom: float) -> tuple[Rect, float]:
    """Returns (overlay_rect_physical, scale).
    Largest aspect-preserving projection of `sel` that fits `screen`,
    scale clamped to max_zoom and floored at 1.0 (never shrink)."""
    s = min(screen.w / sel.w, screen.h / sel.h, max_zoom)
    s = max(s, 1.0)
    w, h = round(sel.w * s), round(sel.h * s)
    x = screen.x + (screen.w - w) // 2
    y = screen.y + (screen.h - h) // 2
    return Rect(x, y, w, h), s
```

Fixed mode: `s = clamp(zoom_percent/100, 1.0, min(screen.w/sel.w, screen.h/sel.h))`.
Scaling quality: `Qt.TransformationMode.SmoothTransformation` for region magnifier (text legibility is the entire point); lens may use `FastTransformation` if profiling shows smooth can't hold `lens_refresh_hz`.

Lens geometry: lens viewport is `2r × 2r` centered on cursor; source = square of side `2r / zoom` centered on cursor, clamped to screen bounds (clamp source position, not size, so zoom stays truthful at edges).

## 5. Capture engine

```python
# capture/engine.py — single QTimer-driven engine, one consumer at a time
class CaptureEngine(QObject):
    frame_ready = pyqtSignal(QImage)

    def start(self, region: Rect, hz: int): ...   # QTimer.start(1000 // hz)
    def retarget(self, region: Rect): ...         # lens mode: move source per tick, no restart
    def stop(self): ...
```

- Backend: `mss` — one `mss.mss()` instance created per `start()` **on the thread that uses it** (mss is thread-affine; simplest correct design: run capture on the Qt main thread via QTimer — a 500×900 region grab+convert is ~2–4 ms, well within a 33 ms frame budget at 30 Hz).
- Convert BGRA → `QImage(Format_RGB32)` referencing the buffer, then `.copy()` once. Reuse the mss monitor dict; no per-frame dict allocation.
- If a tick overruns (timer callback re-entered), skip the frame — never queue.
- Performance gate (Phase 1 spike): 600×1000 region at 30 Hz must keep app CPU < 10% on the dev laptop. If not, this is the trigger to swap the backend to `dxcam` — interface stays identical.

## 6. Global hotkeys with hold semantics

`RegisterHotKey` can't report key **release** → unusable for the hold-to-lens feature. Use the `keyboard` library (low-level WH_KEYBOARD_LL hook):

```python
# hotkeys/manager.py — emits Qt signals; knows nothing about overlays
keyboard.add_hotkey('alt+m', lambda: self.magnify_requested.emit())
keyboard.add_hotkey('ctrl+alt+m', lambda: self.toggle_requested.emit())
keyboard.on_press_key('n', self._maybe_lens_down)    # check Alt held via keyboard.is_pressed
keyboard.on_release_key('n', self._maybe_lens_up)
```

- Hook callbacks run on the hook thread → **never touch Qt objects there**; emit signals with `Qt.ConnectionType.QueuedConnection` so handlers run on the main thread.
- `Esc`: register/unregister dynamically — hooked only while state ∈ {SELECTING, MAGNIFYING}, and `suppress=True` only then (swallow it so the underlying app doesn't also react). All other combos: `suppress=False` (document E4: the chord still reaches other apps; acceptable v1).
- Rebinding (settings Apply): `keyboard.remove_all_hotkeys()` → re-register from config. Config stores combos as normalized strings (`"alt+m"`), displayed prettified (`Alt+M`).
- Lens hold edge: if the user releases `Alt` before `N`, the release handler must still fire → track lens-active as a boolean set on down, cleared on `N` up **or** `Alt` up.

## 7. Run-on-startup & single instance

```python
# platformwin/startup.py
KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
# set:    winreg.SetValueEx(k, "ScreenLoupe", 0, winreg.REG_SZ, f'"{exe_path}" --minimized')
# remove: winreg.DeleteValue(k, "ScreenLoupe")  (ignore FileNotFoundError)
```
HKCU (per-user, no elevation). The installer writes the same value when its checkbox is ticked; the settings toggle reads actual registry state on open (source of truth = registry, not config.json) so installer choice and app setting never drift.

Single instance: named mutex `Global\\ScreenLoupe.SingleInstance` via `CreateMutexW`; if `GetLastError() == ERROR_ALREADY_EXISTS`, broadcast a registered window message (`RegisterWindowMessageW("SCREENLOUPE_SHOW")`) and exit; the running instance responds by showing Settings.

## 8. Config schema (v1)

```jsonc
// %APPDATA%/ScreenLoupe/config.json
{
  "config_version": 1,
  "enabled": true,
  "run_at_startup": true,                  // mirror; registry is source of truth
  "hotkeys": { "magnify": "alt+m", "dismiss": "esc",
               "lens": "alt+n", "master_toggle": "ctrl+alt+m" },
  "magnifier": { "zoom_mode": "fit", "zoom_percent": 200, "max_zoom": 400,
                 "opacity": 92, "refresh_hz": 30 },
  "lens": { "radius": 220, "zoom": 200, "refresh_hz": 60, "shape": "rounded" }
}
```
Loaded into a typed `@dataclass` tree with validation + clamping; unknown keys ignored; missing keys defaulted; corrupt file → rename to `config.json.bak`, recreate defaults.

## 9. Failure modes to design around

| Failure | Mitigation |
|---|---|
| Capture exclusion API absent (old Win10) | Installer blocks < build 19041; app double-checks at boot and refuses with a dialog |
| AV flags keyboard hook | Document; later: code-sign the exe; never log keystrokes anywhere |
| GDI capture too slow on 4K | Engine interface allows dxcam swap (D2); also we capture regions, not full screens |
| Overlay flicker on opacity change | Set opacity before `show()`; live changes via `setWindowOpacity` only (no recreate) |
| `keyboard` lib needs admin for some hooks in elevated apps' focus | Known limitation: hotkeys don't fire while an elevated window has focus, unless ScreenLoupe is elevated. Document, don't solve in v1 |
| Display topology change mid-overlay | Subscribe to `QGuiApplication.screenAdded/Removed` + `primaryScreenChanged` → force IDLE (E5) |
