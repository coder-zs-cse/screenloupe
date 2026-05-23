# ScreenLoupe

A cursor-following magnifier for Windows. **Hold the middle mouse button** and a
circular loupe appears under your pointer, blowing up whatever is beneath it —
in any app: browser, VS Code, terminal, Settings, a game, anywhere. Release to
dismiss. It does **not** change your screen resolution or the OS zoom level, and
it never blocks clicks.

## Why this is fast (and not a laggy screenshot hack)

It uses the Windows **Magnification API** (`magnification.dll`) — the native,
hardware-assisted engine behind the built-in OS Magnifier. Python only:

1. creates a transparent, click-through, circular always-on-top window,
2. parents a `Magnifier` control inside it,
3. each frame sets the *source rectangle* (a small patch of screen under the
   cursor) and a *zoom transform*, then re-centers the window on the cursor.

All the pixel scaling happens in native code, so the Python loop just makes a few
cheap calls per frame.

## Install

Requires Windows + Python 3.8+. No third-party packages.

The cleanest way to install a CLI tool is **pipx** (isolated, on your PATH):

```powershell
pip install pipx
pipx install .          # run from inside the screenloupe folder
```

Or with plain pip:

```powershell
pip install .
```

Either gives you a `screenloupe` command.

## Use

```powershell
screenloupe                          # run with saved settings
screenloupe --zoom 3 --radius 220    # one-off overrides
screenloupe --zoom 3 --save          # override AND persist
```

Then hold the **middle mouse button** anywhere. `Ctrl+C` in the console to quit.

### Settings

```powershell
screenloupe config                   # show settings + file location
screenloupe config set zoom 4
screenloupe config set radius 200
screenloupe config set smoothing 0.4 # eased follow instead of locked-on
```

| Setting      | Meaning                                   | Range     |
|--------------|-------------------------------------------|-----------|
| `zoom`       | Magnification factor                      | 1.1–12    |
| `radius`     | Loupe radius in pixels                    | 40–700    |
| `refresh_hz` | Update rate (higher = smoother, more CPU) | 15–240    |
| `smoothing`  | 1.0 = locked to cursor; lower = eased lag | 0.05–1.0  |
| `trigger`    | Which gesture activates the loupe         | see below |
| `hold_ms`    | Tap-vs-hold threshold (smart middle mode) | 80–600    |

**Triggers** (pick in the GUI dropdown): `middle_smart` (a quick middle-click
still closes tabs; *holding* it magnifies), `middle_only` (hold middle, normal
action suppressed), `xbutton1`/`xbutton2` (side Back/Forward buttons),
`rctrl`/`rshift` (hold Right Ctrl / Right Shift). The mouse-button triggers use
a low-level hook so they can suppress the button's normal action; the key
triggers are passive (held alone they're harmless, so nothing is suppressed). If
a hook ever misbehaves, switch to `rctrl` — it needs no hook at all.

Config lives at `%APPDATA%\screenloupe\config.json`.

## Run on login (optional)

Drop a shortcut to `screenloupe` (or `pythonw -m screenloupe`) into
`shell:startup`. Use `pythonw` instead of `python` to launch without a console
window.

## Known limitations

- Windows only (the Magnification API is Windows-specific).
- Mixed-DPI multi-monitor setups can have minor offset; the tool requests
  per-monitor-v2 DPI awareness to minimize this.
- The real OS cursor is drawn at normal size over the magnified content (the
  magnified cursor is intentionally disabled to avoid a double cursor).

---

## Settings GUI

```powershell
screenloupe --settings
```

A small window with sliders for zoom / radius / refresh / smoothing, a
**Run ScreenLoupe at Windows startup** checkbox, and a Start/Stop button for the
background magnifier. "Save & Apply" writes the config and restarts the running
daemon so changes take effect immediately.

## How the pieces fit

One executable, two modes:

- `screenloupe` (no args, or a double-click) — opens the **settings GUI**. This
  is the friendly default, so double-clicking `ScreenLoupe.exe` always shows a
  window.
- `screenloupe --background` — the **silent daemon**: no console, no window.
  This is what runs at login and what the GUI's Start button launches. A named
  mutex keeps it single-instance.

The GUI and the daemon are separate processes, so they coordinate through two
named Windows kernel objects: a mutex (single-instance) and an event (the GUI
flips it to ask the daemon to quit). No sockets, no PID files.

## Deployment

There are two audiences. Pick the path that matches yours.

### A. People who already have Python — `pipx`

```powershell
pip install pipx
pipx install .
screenloupe --settings      # tick "Run at startup", click Start
```

The entry point is declared under `[project.gui-scripts]`, so the generated
`screenloupe.exe` is windowed — **no console window appears**. (Use
`screenloupe-debug` if you want a console + Ctrl-C for troubleshooting.)

### B. People with NO Python — bundled installer

This produces a single `ScreenLoupe-Setup.exe` anyone can double-click; it needs
no Python at all because the interpreter is bundled in.

```powershell
# 1. Build a standalone exe (bundles Python via PyInstaller):
powershell -ExecutionPolicy Bypass -File build.ps1     # -> dist\ScreenLoupe.exe

# 2. Wrap it in an installer (needs Inno Setup, free):
#    open installer.iss in Inno Setup and click Compile
#                                                  -> Output\ScreenLoupe-Setup.exe
```

The installer shows a **"Run ScreenLoupe at Windows startup"** checkbox (checked
by default), creates a Start Menu entry **"ScreenLoupe Settings"** so searching
the Start menu for *screenloupe* opens the panel, and offers to launch it
immediately. Your users' whole experience becomes: download one file,
double-click, done.

> Want a true one-liner later? Once you publish `ScreenLoupe-Setup.exe` to a
> release URL, a `winget` manifest lets anyone run `winget install ScreenLoupe`.
> That's the eventual "one command" endpoint — it just requires submitting the
> package to the winget community repo.
