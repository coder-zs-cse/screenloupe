"""Command-line / launcher entry points for ScreenLoupe.

    screenloupe                 run the background magnifier (no window)
    screenloupe --settings      open the settings GUI
    screenloupe --zoom 3 ...    one-off overrides for a foreground run
    screenloupe-debug           same, but with a console + startup banner
    screenloupe config [set k v]  view / change saved settings (use -debug)
"""

import argparse
import sys

from . import config


def _require_windows():
    if not sys.platform.startswith("win"):
        sys.exit("ScreenLoupe only runs on Windows (it uses the "
                 "Windows Magnification API).")


def cmd_run(args):
    _require_windows()
    from . import process

    # Only one daemon at a time.
    mutex = process.acquire_single_instance()
    if mutex is None:
        return  # already running; second launch just exits quietly
    evt = process.create_quit_event()

    cfg = config.load()
    for k in ("zoom", "radius", "refresh_hz", "smoothing"):
        v = getattr(args, k, None)
        if v is not None:
            cfg[k] = v
    if getattr(args, "save", False):
        cfg = config.save(cfg)

    from .loupe import Loupe
    Loupe(zoom=cfg["zoom"], radius=cfg["radius"],
          refresh_hz=cfg["refresh_hz"], smoothing=cfg["smoothing"],
          trigger=cfg["trigger"], hold_ms=cfg["hold_ms"]).run(
        should_quit=lambda: process.quit_requested(evt),
        verbose=getattr(args, "verbose", False),
    )


def cmd_settings(_args):
    _require_windows()
    from .gui import launch
    launch()


def cmd_config(args):
    cfg = config.load()
    if args.action == "set":
        if args.key not in config.DEFAULTS:
            sys.exit(f"Unknown key '{args.key}'. Valid: "
                     f"{', '.join(config.DEFAULTS)}")
        caster = type(config.DEFAULTS[args.key])
        try:
            cfg[args.key] = caster(args.value)
        except (TypeError, ValueError):
            sys.exit(f"'{args.value}' is not a valid {caster.__name__}")
        cfg = config.save(cfg)
        print(f"Set {args.key} = {cfg[args.key]}")
    print(f"Config file: {config.config_path()}")
    for k in config.DEFAULTS:
        print(f"  {k:10} = {cfg[k]}")


def _build_parser():
    p = argparse.ArgumentParser(
        prog="screenloupe",
        description="Hold the middle mouse button to magnify the screen "
                    "under your cursor.")
    p.add_argument("--background", action="store_true",
                   help="run the magnifier silently (used at login)")
    p.add_argument("--settings", action="store_true",
                   help="open the settings window (this is also the default)")
    p.add_argument("--zoom", type=float, help="magnification factor")
    p.add_argument("--radius", type=int, help="loupe radius in pixels")
    p.add_argument("--refresh-hz", type=int, dest="refresh_hz",
                   help="update rate (15-240)")
    p.add_argument("--smoothing", type=float,
                   help="1.0 locked to cursor, <1.0 eased follow")
    p.add_argument("--save", action="store_true",
                   help="persist any overrides above")
    p.add_argument("--verbose", action="store_true", help=argparse.SUPPRESS)

    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("settings", help="open the settings window")
    c = sub.add_parser("config", help="view or change saved settings")
    c.add_argument("action", nargs="?", choices=["set"], default=None)
    c.add_argument("key", nargs="?")
    c.add_argument("value", nargs="?")
    return p


def main(argv=None):
    args = _build_parser().parse_args(argv)
    if args.cmd == "config":
        cmd_config(args)
    elif args.background:
        cmd_run(args)          # silent daemon
    else:
        cmd_settings(args)     # default: open the window


def main_console(argv=None):
    """Console entry point (screenloupe-debug): run the magnifier in the
    foreground with a banner and Ctrl+C support."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if not any(a in argv for a in ("config", "--settings", "settings")):
        if "--background" not in argv:
            argv.append("--background")
        argv.append("--verbose")
    main(argv)
