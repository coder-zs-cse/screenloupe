"""
loupe.py — the engine.

The whole trick of this tool is that we do NOT screenshot the screen and scale
it ourselves. Instead we lean on Windows' built-in Magnification API
(magnification.dll), the same native, GPU-assisted engine that powers the OS
Magnifier accessibility tool. We just:

    1. create a transparent, click-through, always-on-top circular window,
    2. host a "Magnifier" control inside it,
    3. each frame, tell the control "magnify the screen region under the cursor",
    4. move the window so it sits centered on the cursor.

Because the expensive pixel work happens in native code, our Python loop only
makes a handful of cheap ctypes calls per frame — easily fast enough for 60+ FPS.
"""

import ctypes
from ctypes import wintypes

# --- DLL handles -----------------------------------------------------------
user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
mag = ctypes.WinDLL("magnification", use_last_error=True)

# LRESULT / pointer-sized return type (critical for correctness on 64-bit).
LRESULT = ctypes.c_ssize_t

# --- Win32 constants -------------------------------------------------------
WS_POPUP = 0x80000000
WS_VISIBLE = 0x10000000
WS_CHILD = 0x40000000

WS_EX_TOPMOST = 0x00000008
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020   # clicks pass straight through to apps below
WS_EX_TOOLWINDOW = 0x00000080   # keep us out of the taskbar / alt-tab
WS_EX_NOACTIVATE = 0x08000000   # never steal focus

LWA_ALPHA = 0x00000002

SW_HIDE = 0
SW_SHOWNOACTIVATE = 4

HWND_TOPMOST = wintypes.HWND(-1)
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010
SWP_NOREDRAW = 0x0008

CS_HREDRAW = 0x0002
CS_VREDRAW = 0x0001

PM_REMOVE = 0x0001
VK_MBUTTON = 0x04

# Magnifier control window-class name.
WC_MAGNIFIER = "Magnifier"

# --- Structures ------------------------------------------------------------
class MAGTRANSFORM(ctypes.Structure):
    """A 3x3 row-major float matrix. For uniform zoom z it's diag(z, z, 1)."""
    _fields_ = [("v", ctypes.c_float * 9)]


WNDPROC = ctypes.WINFUNCTYPE(
    LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
)


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
        ("hIconSm", wintypes.HICON),
    ]


# --- Function prototypes (set explicitly to avoid 64-bit pointer truncation) -
def _bind():
    user32.CreateWindowExW.restype = wintypes.HWND
    user32.CreateWindowExW.argtypes = [
        wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
        wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID,
    ]
    user32.DefWindowProcW.restype = LRESULT
    user32.DefWindowProcW.argtypes = [
        wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
    ]
    user32.RegisterClassExW.restype = wintypes.ATOM
    user32.RegisterClassExW.argtypes = [ctypes.POINTER(WNDCLASSEXW)]
    user32.SetLayeredWindowAttributes.argtypes = [
        wintypes.HWND, wintypes.COLORREF, wintypes.BYTE, wintypes.DWORD
    ]
    user32.SetWindowPos.argtypes = [
        wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, ctypes.c_int, wintypes.UINT
    ]
    user32.SetWindowRgn.argtypes = [wintypes.HWND, wintypes.HRGN, wintypes.BOOL]
    user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
    user32.GetAsyncKeyState.restype = ctypes.c_short
    user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.InvalidateRect.argtypes = [
        wintypes.HWND, ctypes.c_void_p, wintypes.BOOL
    ]
    user32.PeekMessageW.argtypes = [
        ctypes.c_void_p, wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.UINT
    ]
    kernel32.GetModuleHandleW.restype = wintypes.HMODULE
    kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]

    user32.GetSystemMetrics.restype = ctypes.c_int
    user32.GetSystemMetrics.argtypes = [ctypes.c_int]

    gdi32.CreateEllipticRgn.restype = wintypes.HRGN
    gdi32.CreateEllipticRgn.argtypes = [ctypes.c_int] * 4
    gdi32.CreateRectRgn.restype = wintypes.HRGN
    gdi32.CreateRectRgn.argtypes = [ctypes.c_int] * 4

    mag.MagInitialize.restype = wintypes.BOOL
    mag.MagUninitialize.restype = wintypes.BOOL
    mag.MagSetWindowSource.restype = wintypes.BOOL
    mag.MagSetWindowSource.argtypes = [wintypes.HWND, wintypes.RECT]
    mag.MagSetWindowTransform.restype = wintypes.BOOL
    mag.MagSetWindowTransform.argtypes = [
        wintypes.HWND, ctypes.POINTER(MAGTRANSFORM)
    ]


def _set_dpi_awareness():
    """Per-monitor DPI awareness so screen coordinates are real pixels.
    Without this, the magnified region is offset/scaled on HiDPI displays."""
    try:
        user32.SetProcessDpiAwarenessContext.restype = wintypes.BOOL
        user32.SetProcessDpiAwarenessContext.argtypes = [wintypes.HANDLE]
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 == (HANDLE)-4
        if user32.SetProcessDpiAwarenessContext(wintypes.HANDLE(-4)):
            return
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
        return
    except Exception:
        pass
    try:
        user32.SetProcessDPIAware()
    except Exception:
        pass


class Loupe:
    """A circular cursor-following magnifier."""

    CLASS_NAME = "ScreenLoupeHost"

    def __init__(self, zoom=2.5, radius=160, refresh_hz=90, smoothing=1.0,
                 trigger="middle_smart", hold_ms=160,
                 shape="circle", rect_width=0):
        self.zoom = float(zoom)
        self.radius = int(radius)
        self.refresh_hz = int(refresh_hz)
        self.smoothing = max(0.05, min(1.0, float(smoothing)))
        self.shape = shape if shape in ("circle", "rect") else "circle"
        self.rect_width = int(rect_width)  # 0 = full screen width

        from . import trigger as _trigger
        self._trigger = _trigger.make(trigger, hold_ms)

        self._host = None
        self._mag = None
        self._wndproc_ref = None
        self._visible = False
        self._fx = self._fy = None
        self._win_w = 0        # actual window pixel width (set in setup)
        self._win_h = 0

    # -- lifecycle ----------------------------------------------------------
    def setup(self):
        _set_dpi_awareness()
        _bind()

        if not mag.MagInitialize():
            raise OSError("MagInitialize failed — is magnification.dll available?")

        hinst = kernel32.GetModuleHandleW(None)

        # Register the transparent host window class.
        def _proc(hwnd, msg, wparam, lparam):
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        self._wndproc_ref = WNDPROC(_proc)

        wc = WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wc.style = CS_HREDRAW | CS_VREDRAW
        wc.lpfnWndProc = self._wndproc_ref
        wc.hInstance = hinst
        wc.lpszClassName = self.CLASS_NAME
        if not user32.RegisterClassExW(ctypes.byref(wc)):
            # class may already be registered if re-run in same process; ignore 1410
            err = ctypes.get_last_error()
            if err not in (0, 1410):
                raise ctypes.WinError(err)

        SM_CXSCREEN, SM_CYSCREEN = 0, 1
        screen_w = user32.GetSystemMetrics(SM_CXSCREEN)

        self._win_h = self.radius * 2
        if self.shape == "rect":
            self._win_w = (screen_w if self.rect_width <= 0
                           else min(self.rect_width, screen_w))
        else:
            self._win_w = self.radius * 2

        w, h = self._win_w, self._win_h

        ex_style = (WS_EX_TOPMOST | WS_EX_LAYERED | WS_EX_TRANSPARENT
                    | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)
        self._host = user32.CreateWindowExW(
            ex_style, self.CLASS_NAME, "ScreenLoupe", WS_POPUP,
            0, 0, w, h, None, None, hinst, None,
        )
        if not self._host:
            raise ctypes.WinError(ctypes.get_last_error())

        user32.SetLayeredWindowAttributes(self._host, 0, 255, LWA_ALPHA)

        # Clip to shape: ellipse for circle, plain rect for rectangle.
        if self.shape == "circle":
            rgn = gdi32.CreateEllipticRgn(0, 0, w, h)
        else:
            rgn = gdi32.CreateRectRgn(0, 0, w, h)
        user32.SetWindowRgn(self._host, rgn, True)

        # The magnifier control fills the host's client area.
        self._mag = user32.CreateWindowExW(
            0, WC_MAGNIFIER, "MagnifierControl",
            WS_CHILD | WS_VISIBLE,
            0, 0, w, h, self._host, None, hinst, None,
        )
        if not self._mag:
            raise ctypes.WinError(ctypes.get_last_error())

        self._apply_zoom()
        self._trigger.install()

    def _apply_zoom(self):
        m = MAGTRANSFORM()
        for i in range(9):
            m.v[i] = 0.0
        m.v[0] = self.zoom  # x scale
        m.v[4] = self.zoom  # y scale
        m.v[8] = 1.0
        mag.MagSetWindowTransform(self._mag, ctypes.byref(m))

    # -- per-frame work -----------------------------------------------------
    def _cursor(self):
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y

    def _update(self):
        cx, cy = self._cursor()

        if self._fx is None or self.smoothing >= 1.0:
            self._fx, self._fy = cx, cy
        else:
            s = self.smoothing
            self._fx += (cx - self._fx) * s
            self._fy += (cy - self._fy) * s
        px, py = int(round(self._fx)), int(round(self._fy))

        w, h = self._win_w, self._win_h
        # Source region: the screen patch that gets blown up to fill the window.
        src_w = max(1, int(round(w / self.zoom)))
        src_h = max(1, int(round(h / self.zoom)))
        rect = wintypes.RECT(
            px - src_w // 2, py - src_h // 2,
            px - src_w // 2 + src_w, py - src_h // 2 + src_h,
        )
        mag.MagSetWindowSource(self._mag, rect)

        # Window position: full-screen-width rect pins to left edge of screen;
        # circle and custom-width rect centre on the cursor.
        if self.shape == "rect" and self.rect_width <= 0:
            win_x = 0
        else:
            win_x = px - w // 2
        win_y = py - h // 2
        user32.SetWindowPos(
            self._host, HWND_TOPMOST, win_x, win_y, 0, 0,
            SWP_NOSIZE | SWP_NOACTIVATE,
        )
        user32.InvalidateRect(self._mag, None, False)

    def _show(self, on):
        if on and not self._visible:
            self._fx = self._fy = None  # reset smoothing on each new press
            user32.ShowWindow(self._host, SW_SHOWNOACTIVATE)
            self._visible = True
        elif not on and self._visible:
            user32.ShowWindow(self._host, SW_HIDE)
            self._visible = False

    def _pump(self):
        msg = wintypes.MSG()
        while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_REMOVE):
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    # -- main loop ----------------------------------------------------------
    def run(self, should_quit=None, verbose=False):
        import time
        self.setup()
        period = 1.0 / max(1, self.refresh_hz)
        if verbose:
            try:
                print(f"ScreenLoupe running — hold the MIDDLE mouse button to "
                      f"zoom (x{self.zoom:g}, radius {self.radius}px). Ctrl+C to quit.")
            except Exception:
                pass
        try:
            while True:
                self._pump()
                if should_quit is not None and should_quit():
                    break
                self._trigger.update()
                active = self._trigger.active()
                self._show(active)
                if active:
                    self._update()
                time.sleep(period)
        except KeyboardInterrupt:
            pass
        finally:
            self.teardown()

    def teardown(self):
        try:
            self._trigger.uninstall()
        except Exception:
            pass
        try:
            self._show(False)
        except Exception:
            pass
        try:
            mag.MagUninitialize()
        except Exception:
            pass
