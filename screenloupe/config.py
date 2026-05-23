"""Tiny JSON config stored in %APPDATA%\\screenloupe\\config.json."""
import json, os

DEFAULTS = {
    "zoom":        2.5,
    "radius":      160,
    "refresh_hz":  90,
    "smoothing":   1.0,
    "trigger":     "middle_smart",
    "hold_ms":     160,
    "shape":       "circle",
    "rect_width":  0,       # 0 = full screen width (rect mode only)
}

TRIGGERS = ("middle_smart","middle_only","xbutton1","xbutton2","rctrl","rshift")
SHAPES   = ("circle", "rect")

# numeric clamp ranges; string keys handled by membership check below
LIMITS = {
    "zoom":       (1.1,  12.0),
    "radius":     (40,   700),
    "refresh_hz": (15,   240),
    "smoothing":  (0.05, 1.0),
    "hold_ms":    (80,   600),
    "rect_width": (0,    3840),   # 0 = full screen
}
STRING_OPTS = {"trigger": TRIGGERS, "shape": SHAPES}


def config_dir():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "screenloupe")

def config_path():
    return os.path.join(config_dir(), "config.json")


def _sanitize(raw):
    out = dict(DEFAULTS)
    for key, default in DEFAULTS.items():
        value = raw.get(key, default)
        if key in STRING_OPTS:
            out[key] = value if value in STRING_OPTS[key] else default
        elif key in LIMITS:
            try:
                v   = type(default)(value)
                lo, hi = LIMITS[key]
                out[key] = max(lo, min(hi, v))
            except (TypeError, ValueError):
                out[key] = default
    return out


def load():
    raw = dict(DEFAULTS)
    try:
        with open(config_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        raw.update({k: v for k, v in data.items() if k in DEFAULTS})
    except FileNotFoundError:
        pass
    except Exception:
        pass
    return _sanitize(raw)


def save(cfg):
    os.makedirs(config_dir(), exist_ok=True)
    clean = _sanitize(cfg)
    with open(config_path(), "w", encoding="utf-8") as f:
        json.dump(clean, f, indent=2)
    return clean
