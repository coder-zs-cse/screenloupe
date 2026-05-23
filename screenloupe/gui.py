"""
gui.py — the settings panel (Tkinter, ships with Python, zero extra deps).
"""
import tkinter as tk
from tkinter import ttk
from . import config, process, startup

# ── numeric sliders ──────────────────────────────────────────────────────────
# (key, label, from, to, step, is_int)
FIELDS = [
    ("zoom",       "Zoom factor",             1.1,  12.0, 0.1,  False),
    ("radius",     "Loupe radius / height (px)",40, 700,  10,   True),
    ("refresh_hz", "Refresh rate (Hz)",        15,   240,  5,    True),
    ("smoothing",  "Smoothing  (1 = locked)",  0.05, 1.0,  0.05, False),
    ("hold_ms",    "Hold threshold (ms)",      80,   600,  10,   True),
]

# ── trigger & shape choices ───────────────────────────────────────────────────
TRIGGER_CHOICES = [
    ("Middle button — tap closes tab, hold to magnify", "middle_smart"),
    ("Middle button — hold to magnify (disable normal action)",  "middle_only"),
    ("Side button (Back) — hold to magnify",            "xbutton1"),
    ("Side button (Forward) — hold to magnify",         "xbutton2"),
    ("Right Ctrl — hold to magnify",                    "rctrl"),
    ("Right Shift — hold to magnify",                   "rshift"),
]
TRIGGER_LABEL = {v: l for l, v in TRIGGER_CHOICES}
TRIGGER_VALUE = {l: v for l, v in TRIGGER_CHOICES}

SHAPE_CHOICES = [("Circle (default)", "circle"), ("Rectangle", "rect")]
SHAPE_LABEL   = {v: l for l, v in SHAPE_CHOICES}
SHAPE_VALUE   = {l: v for l, v in SHAPE_CHOICES}


class App:
    def __init__(self):
        self.cfg  = config.load()
        self.root = tk.Tk()
        self.root.title("ScreenLoupe Settings")
        self.root.resizable(False, False)
        try: self.root.tk.call("tk", "scaling", 1.25)
        except Exception: pass

        pad = {"padx": 14, "pady": 5}
        frm = ttk.Frame(self.root, padding=16)
        frm.grid(sticky="nsew")

        # header
        ttk.Label(frm, text="ScreenLoupe",
                  font=("Segoe UI", 14, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(frm, text="Magnify the screen under your cursor.",
                  foreground="#666").grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(0, 8))

        row = 2

        # ── trigger dropdown ─────────────────────────────────────────────────
        ttk.Label(frm, text="Trigger").grid(row=row, column=0, sticky="w", **pad)
        self.trigger_var = tk.StringVar(
            value=TRIGGER_LABEL.get(self.cfg["trigger"], TRIGGER_CHOICES[0][0]))
        ttk.Combobox(frm, textvariable=self.trigger_var,
                     values=[l for l, _ in TRIGGER_CHOICES],
                     state="readonly", width=46).grid(
            row=row, column=1, columnspan=2, sticky="ew", **pad)
        row += 1

        # ── numeric sliders ──────────────────────────────────────────────────
        self.vars = {}
        for key, label, lo, hi, step, is_int in FIELDS:
            ttk.Label(frm, text=label).grid(row=row, column=0, sticky="w", **pad)
            var = tk.DoubleVar(value=float(self.cfg[key]))
            self.vars[key] = var
            val_lbl = ttk.Label(frm, width=6)
            val_lbl.grid(row=row, column=2, sticky="e", **pad)

            def _fmt(v, _is_int=is_int, _lbl=val_lbl, _step=step):
                v = round(float(v) / _step) * _step
                _lbl.config(text=str(int(round(v)) if _is_int else round(v, 2)))

            ttk.Scale(frm, from_=lo, to=hi, variable=var,
                      command=_fmt, length=250).grid(
                row=row, column=1, sticky="ew", **pad)
            _fmt(var.get())
            row += 1

        # ── shape ────────────────────────────────────────────────────────────
        ttk.Separator(frm, orient="horizontal").grid(
            row=row, column=0, columnspan=3, sticky="ew", pady=6)
        row += 1

        ttk.Label(frm, text="Loupe shape").grid(row=row, column=0, sticky="w", **pad)
        self.shape_var = tk.StringVar(
            value=SHAPE_LABEL.get(self.cfg["shape"], SHAPE_CHOICES[0][0]))
        shape_cb = ttk.Combobox(frm, textvariable=self.shape_var,
                                values=[l for l, _ in SHAPE_CHOICES],
                                state="readonly", width=20)
        shape_cb.grid(row=row, column=1, sticky="w", **pad)
        row += 1

        # rect width row (enabled only when Rectangle selected)
        ttk.Label(frm, text="Rect width (px)").grid(
            row=row, column=0, sticky="w", **pad)
        self.fullscreen_var = tk.BooleanVar(value=self.cfg["rect_width"] <= 0)
        self.rw_var = tk.DoubleVar(
            value=float(max(100, self.cfg["rect_width"]) if self.cfg["rect_width"] > 0 else 800))
        rw_lbl = ttk.Label(frm, width=6)
        rw_lbl.grid(row=row, column=2, sticky="e", **pad)

        def _rw_fmt(v, _lbl=rw_lbl):
            _lbl.config(text=str(int(round(float(v) / 10) * 10)))

        self._rw_scale = ttk.Scale(frm, from_=100, to=3840, variable=self.rw_var,
                                   command=_rw_fmt, length=160)
        self._rw_scale.grid(row=row, column=1, sticky="w", **pad)
        _rw_fmt(self.rw_var.get())

        self._fs_cb = ttk.Checkbutton(frm, text="Full screen width",
                                       variable=self.fullscreen_var,
                                       command=self._on_fullscreen)
        self._fs_cb.grid(row=row, column=2, sticky="w", padx=4)
        row += 1

        # wire shape/fullscreen enable logic
        self.shape_var.trace_add("write", lambda *_: self._on_shape())
        self._rect_widgets = [self._rw_scale, self._fs_cb, rw_lbl]
        self._on_shape()   # initialise enabled state

        # ── startup ──────────────────────────────────────────────────────────
        ttk.Separator(frm, orient="horizontal").grid(
            row=row, column=0, columnspan=3, sticky="ew", pady=6)
        row += 1

        self.startup_var = tk.BooleanVar(value=startup.is_enabled())
        ttk.Checkbutton(frm, text="Run ScreenLoupe at Windows startup",
                        variable=self.startup_var).grid(
            row=row, column=0, columnspan=3, sticky="w", padx=14, pady=(4, 8))
        row += 1

        # ── status + buttons ──────────────────────────────────────────────────
        self.status = ttk.Label(frm, foreground="#444")
        self.status.grid(row=row, column=0, columnspan=2, sticky="w", padx=14)
        self.toggle_btn = ttk.Button(frm, text="", command=self.on_toggle_run)
        self.toggle_btn.grid(row=row, column=2, sticky="e", padx=14)
        row += 1

        btns = ttk.Frame(frm)
        btns.grid(row=row, column=0, columnspan=3, sticky="e", pady=(10, 0))
        ttk.Button(btns, text="Save & Apply", command=self.on_save).grid(
            row=0, column=0, padx=6)
        ttk.Button(btns, text="Close", command=self.root.destroy).grid(
            row=0, column=1, padx=6)

        self._refresh_status()

    # ── shape enable/disable helpers ──────────────────────────────────────────
    def _on_shape(self):
        is_rect = SHAPE_VALUE.get(self.shape_var.get()) == "rect"
        state = "normal" if is_rect else "disabled"
        for w in self._rect_widgets:
            try: w.config(state=state)
            except Exception: pass
        self._on_fullscreen()

    def _on_fullscreen(self):
        is_rect = SHAPE_VALUE.get(self.shape_var.get()) == "rect"
        fs = self.fullscreen_var.get()
        try:
            self._rw_scale.config(state="disabled" if (fs or not is_rect) else "normal")
        except Exception:
            pass

    # ── collect / save ────────────────────────────────────────────────────────
    def _collect(self):
        out = {
            "trigger":    TRIGGER_VALUE.get(self.trigger_var.get(), "middle_smart"),
            "shape":      SHAPE_VALUE.get(self.shape_var.get(), "circle"),
            "rect_width": 0 if self.fullscreen_var.get()
                            else int(round(self.rw_var.get() / 10) * 10),
        }
        for key, _, lo, hi, step, is_int in FIELDS:
            v = round(self.vars[key].get() / step) * step
            out[key] = int(round(v)) if is_int else round(v, 2)
        return out

    def on_save(self):
        config.save(self._collect())
        startup.enable() if self.startup_var.get() else startup.disable()
        if process.is_running():
            process.request_quit()
            self.root.after(450, self._relaunch)
        self.status.config(text="Saved.")
        self.root.after(900, self._refresh_status)

    def _relaunch(self):
        startup.launch_daemon()
        self.root.after(500, self._refresh_status)

    def on_toggle_run(self):
        process.request_quit() if process.is_running() else startup.launch_daemon()
        self.root.after(500, self._refresh_status)

    def _refresh_status(self):
        running = process.is_running()
        self.status.config(
            text="ScreenLoupe is running." if running else "ScreenLoupe is stopped.")
        self.toggle_btn.config(text="Stop" if running else "Start")

    def run(self):
        self.root.mainloop()


def launch():
    App().run()
