"""Physical-pixel cursor position via Win32."""

from __future__ import annotations

import ctypes
from ctypes import wintypes


class _POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


def get_cursor_pos_physical() -> tuple[int, int]:
    """Return cursor (x, y) in physical screen pixels."""
    pt = _POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y
