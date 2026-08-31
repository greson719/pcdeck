import ctypes
from ctypes import wintypes, byref, sizeof, Structure, c_void_p, c_int

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

user32.OpenInputDesktop.restype = wintypes.HANDLE
user32.OpenInputDesktop.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]

user32.SetThreadDesktop.restype = wintypes.BOOL
user32.SetThreadDesktop.argtypes = [wintypes.HANDLE]

hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
if hdesk:
    user32.SetThreadDesktop(hdesk)

class POINT(Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

class CURSORINFO(Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("hCursor", wintypes.HANDLE),
        ("ptScreenPos", POINT),
    ]

ci = CURSORINFO()
ci.cbSize = sizeof(CURSORINFO)
user32.GetCursorInfo.argtypes = [ctypes.POINTER(CURSORINFO)]
user32.GetCursorInfo.restype = wintypes.BOOL

res = user32.GetCursorInfo(byref(ci))
print("Attached desktop res:", res, f"flags: {ci.flags}, hCursor: {ci.hCursor}, pos: ({ci.ptScreenPos.x}, {ci.ptScreenPos.y})")
