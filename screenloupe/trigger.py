"""
trigger.py — what gesture turns the loupe on, and whether to suppress it.

Two families:

  * KeyTrigger   — passive. Reads a key/button with GetAsyncKeyState each tick.
                   Holding it does nothing harmful (e.g. Right Ctrl), so we
                   don't need to consume the event. Cheap and safe.

  * MouseTrigger — active. Installs a WH_MOUSE_LL low-level hook so it can
                   *consume* the button (return non-zero) and stop the app
                   underneath from acting on it. For the "smart middle" mode it
                   tells a tap from a hold by time: a quick tap is replayed as a
                   real click (so closing tabs still works), a hold magnifies.

The golden rule of low-level hooks: the callback must be lean and fast, or
Windows skips it. So the callback only flips flags / timestamps; the hold-vs-tap
decision and any work happen back on the main loop via update()/active().
"""

import ctypes
import time
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

LRESULT = ctypes.c_ssize_t
ULONG_PTR = ctypes.c_size_t

WH_MOUSE_LL = 14
WM_MBUTTONDOWN = 0x0207
WM_MBUTTONUP = 0x0208
WM_XBUTTONDOWN = 0x020B
WM_XBUTTONUP = 0x020C
LLMHF_INJECTED = 0x00000001
XBUTTON1 = 0x0001
XBUTTON2 = 0x0002

VK_MBUTTON = 0x04
VK_XBUTTON1 = 0x05
VK_XBUTTON2 = 0x06
VK_RCONTROL = 0xA3
VK_RSHIFT = 0xA1

INPUT_MOUSE = 0
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", wintypes.POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("mi", MOUSEINPUT)]


HOOKPROC = ctypes.WINFUNCTYPE(
    LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
)

user32.SetWindowsHookExW.restype = wintypes.HHOOK
user32.SetWindowsHookExW.argtypes = [
    ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD
]
user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
user32.CallNextHookEx.restype = LRESULT
user32.CallNextHookEx.argtypes = [
    wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
]
user32.SendInput.restype = wintypes.UINT
user32.SendInput.argtypes = [wintypes.UINT, ctypes.c_void_p, ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]


def _down(vk):
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


class KeyTrigger:
    """Hold a benign key/button; no suppression needed."""

    def __init__(self, vk):
        self.vk = vk

    def install(self):
        pass

    def uninstall(self):
        pass

    def update(self):
        pass

    def active(self):
        return _down(self.vk)


class MouseTrigger:
    """Hold a mouse button, consuming it so the app below doesn't react.

    button: 'middle' | 'x1' | 'x2'
    tap_through: if True, a quick tap is replayed as a real click (middle only).
    """

    def __init__(self, button, tap_through=False, hold_ms=160):
        self.button = button
        self.tap_through = tap_through and button == "middle"
        self.hold = max(0.02, hold_ms / 1000.0)

        if button == "x1":
            self._msg_down, self._msg_up, self._xbtn = (
                WM_XBUTTONDOWN, WM_XBUTTONUP, XBUTTON1)
            self._vk = VK_XBUTTON1
        elif button == "x2":
            self._msg_down, self._msg_up, self._xbtn = (
                WM_XBUTTONDOWN, WM_XBUTTONUP, XBUTTON2)
            self._vk = VK_XBUTTON2
        else:
            self._msg_down, self._msg_up, self._xbtn = (
                WM_MBUTTONDOWN, WM_MBUTTONUP, None)
            self._vk = VK_MBUTTON

        self._hook = None
        self._proc = None  # keep the HOOKPROC alive
        self._down = False
        self._pending = False  # tap_through: undecided press
        self._down_t = 0.0
        self._active = False

    # -- hook lifecycle -----------------------------------------------------
    def install(self):
        self._proc = HOOKPROC(self._callback)
        hmod = kernel32.GetModuleHandleW(None)
        self._hook = user32.SetWindowsHookExW(WH_MOUSE_LL, self._proc, hmod, 0)
        # If the hook fails to install, active() silently falls back to polling.

    def uninstall(self):
        if self._hook:
            user32.UnhookWindowsHookEx(self._hook)
        self._hook = None
        self._proc = None

    # -- the lean callback --------------------------------------------------
    def _callback(self, nCode, wParam, lParam):
        if nCode < 0:
            return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

        ms = ctypes.cast(
            ctypes.c_void_p(lParam), ctypes.POINTER(MSLLHOOKSTRUCT)).contents

        # Never touch injected events (incl. our own replayed clicks).
        if ms.flags & LLMHF_INJECTED:
            return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

        matches = (self._xbtn is None or
                   ((ms.mouseData >> 16) & 0xFFFF) == self._xbtn)

        if wParam == self._msg_down and matches:
            self._down = True
            self._down_t = time.perf_counter()
            if self.tap_through:
                self._pending = True   # decide tap vs hold later
            else:
                self._active = True
            return 1  # swallow

        if wParam == self._msg_up and matches:
            self._down = False
            if self.tap_through:
                if self._active:        # it was a hold -> just end magnify
                    self._active = False
                    self._pending = False
                elif self._pending:     # it was a tap -> replay a real click
                    self._pending = False
                    self._replay_middle_click()
            else:
                self._active = False
            return 1  # swallow the real up

        return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

    def _replay_middle_click(self):
        arr = (INPUT * 2)()
        arr[0].type = INPUT_MOUSE
        arr[0].mi.dwFlags = MOUSEEVENTF_MIDDLEDOWN
        arr[1].type = INPUT_MOUSE
        arr[1].mi.dwFlags = MOUSEEVENTF_MIDDLEUP
        user32.SendInput(2, ctypes.byref(arr), ctypes.sizeof(INPUT))

    # -- main-loop side -----------------------------------------------------
    def update(self):
        # Promote a still-held pending press into an active magnify once it
        # crosses the hold threshold.
        if self.tap_through and self._pending and self._down:
            if (time.perf_counter() - self._down_t) >= self.hold:
                self._pending = False
                self._active = True

    def active(self):
        if self._hook:
            return self._active
        return _down(self._vk)  # fallback if the hook didn't install


def make(name, hold_ms=160):
    name = (name or "middle_smart").lower()
    if name == "middle_only":
        return MouseTrigger("middle", tap_through=False, hold_ms=hold_ms)
    if name == "xbutton1":
        return MouseTrigger("x1", tap_through=False, hold_ms=hold_ms)
    if name == "xbutton2":
        return MouseTrigger("x2", tap_through=False, hold_ms=hold_ms)
    if name == "rctrl":
        return KeyTrigger(VK_RCONTROL)
    if name == "rshift":
        return KeyTrigger(VK_RSHIFT)
    return MouseTrigger("middle", tap_through=True, hold_ms=hold_ms)  # default
