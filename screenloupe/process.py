"""
process.py — talking to a background daemon we can't see.

The magnifier runs with no console and no window, so we need a way for the
settings GUI (a *separate process*) to ask it to quit, and to know whether it's
even running. The clean Win32 way is named kernel objects:

  * a named MUTEX     -> single-instance guard ("am I the only daemon?")
  * a named EVENT     -> a quit flag the GUI can flip from outside

Both live in the OS kernel and are addressable by name across processes, so no
sockets, no PID files, no polling tasklist.
"""

import ctypes
from ctypes import wintypes

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

ERROR_ALREADY_EXISTS = 183
WAIT_OBJECT_0 = 0x00000000
SYNCHRONIZE = 0x00100000
EVENT_MODIFY_STATE = 0x0002

# "Local\\" scopes the name to the current user session — exactly what we want.
MUTEX_NAME = "Local\\ScreenLoupe_SingleInstance"
QUIT_EVENT_NAME = "Local\\ScreenLoupe_Quit"

kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateEventW.restype = wintypes.HANDLE
kernel32.CreateEventW.argtypes = [
    wintypes.LPVOID, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR
]
kernel32.OpenEventW.restype = wintypes.HANDLE
kernel32.OpenEventW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.SetEvent.argtypes = [wintypes.HANDLE]
kernel32.WaitForSingleObject.restype = wintypes.DWORD
kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]


def acquire_single_instance():
    """Return a handle if we're the first daemon, or None if one already runs.
    Keep the returned handle alive for the whole process lifetime."""
    h = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        if h:
            kernel32.CloseHandle(h)
        return None
    return h


def create_quit_event():
    """Daemon side: create the manual-reset quit event (initially unset)."""
    return kernel32.CreateEventW(None, True, False, QUIT_EVENT_NAME)


def quit_requested(evt):
    """Daemon side: has someone asked us to stop? (non-blocking check)"""
    return kernel32.WaitForSingleObject(evt, 0) == WAIT_OBJECT_0


def is_running():
    """GUI side: does a daemon exist? (the quit event only exists if so)"""
    h = kernel32.OpenEventW(SYNCHRONIZE, False, QUIT_EVENT_NAME)
    if h:
        kernel32.CloseHandle(h)
        return True
    return False


def request_quit():
    """GUI side: signal the daemon to stop. Returns True if one was listening."""
    h = kernel32.OpenEventW(EVENT_MODIFY_STATE, False, QUIT_EVENT_NAME)
    if not h:
        return False
    kernel32.SetEvent(h)
    kernel32.CloseHandle(h)
    return True
