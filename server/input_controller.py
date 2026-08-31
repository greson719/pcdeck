import sys
import time
from typing import List, Union

_IS_WIN32 = sys.platform == "win32"

if _IS_WIN32:
    import ctypes
    import ctypes.wintypes
    user32 = ctypes.windll.user32
else:
    ctypes = None
    user32 = None

# Mouse flags
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x01000
MOUSEEVENTF_ABSOLUTE = 0x8000
WHEEL_DELTA = 120

# Keyboard flags & types
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008

# Virtual Key Codes
VK_MAP = {
    # Modifiers
    'ctrl': 0x11,
    'control': 0x11,
    'shift': 0x10,
    'alt': 0x12,
    'win': 0x5B,
    'windows': 0x5B,
    'cmd': 0x5B,
    # Navigation & Edit
    'enter': 0x0D,
    'return': 0x0D,
    'backspace': 0x08,
    'tab': 0x09,
    'space': 0x20,
    'escape': 0x1B,
    'esc': 0x1B,
    'delete': 0x2E,
    'del': 0x2E,
    'insert': 0x2D,
    'ins': 0x2D,
    'home': 0x24,
    'end': 0x23,
    'pageup': 0x21,
    'pgup': 0x21,
    'pagedown': 0x22,
    'pgdn': 0x22,
    'left': 0x25,
    'up': 0x26,
    'right': 0x27,
    'down': 0x28,
    'capslock': 0x14,
    'numlock': 0x90,
    'scrolllock': 0x91,
    'printscreen': 0x2C,
    'prtsc': 0x2C,
    # Numpad Virtual Keys
    'numpad0': 0x60, 'numpad1': 0x61, 'numpad2': 0x62, 'numpad3': 0x63, 'numpad4': 0x64,
    'numpad5': 0x65, 'numpad6': 0x66, 'numpad7': 0x67, 'numpad8': 0x68, 'numpad9': 0x69,
    'num0': 0x60, 'num1': 0x61, 'num2': 0x62, 'num3': 0x63, 'num4': 0x64,
    'num5': 0x65, 'num6': 0x66, 'num7': 0x67, 'num8': 0x68, 'num9': 0x69,
    'numpad_multiply': 0x6A, 'num_mul': 0x6A, 'num_mult': 0x6A,
    'numpad_add': 0x6B, 'num_add': 0x6B, 'num_plus': 0x6B,
    'numpad_separator': 0x6C,
    'numpad_subtract': 0x6D, 'num_sub': 0x6D, 'num_minus': 0x6D,
    'numpad_decimal': 0x6E, 'num_dot': 0x6E, 'num_dec': 0x6E,
    'numpad_divide': 0x6F, 'num_div': 0x6F, 'num_slash': 0x6F,
    'numpad_enter': 0x0D, 'num_enter': 0x0D,
    # Media Keys
    'play_pause': 0xB3,
    'prev': 0xB1,
    'next': 0xB0,
    'stop': 0xB2,
    'vol_mute': 0xAD,
    'vol_down': 0xAE,
    'vol_up': 0xAF,
    # Function Keys
    'f1': 0x70,
    'f2': 0x71,
    'f3': 0x72,
    'f4': 0x73,
    'f5': 0x74,
    'f6': 0x75,
    'f7': 0x76,
    'f8': 0x77,
    'f9': 0x78,
    'f10': 0x79,
    'f11': 0x7A,
    'f12': 0x7B,
}

if _IS_WIN32:
    # Win32 Structures for SendInput
    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", ctypes.c_long),
            ("dy", ctypes.c_long),
            ("mouseData", ctypes.c_ulong),
            ("dwFlags", ctypes.c_ulong),
            ("time", ctypes.c_ulong),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", ctypes.c_ushort),
            ("wScan", ctypes.c_ushort),
            ("dwFlags", ctypes.c_ulong),
            ("time", ctypes.c_ulong),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    class HARDWAREINPUT(ctypes.Structure):
        _fields_ = [
            ("uMsg", ctypes.c_ulong),
            ("wParamL", ctypes.c_short),
            ("wParamH", ctypes.c_ushort),
        ]

    class INPUT_UNION(ctypes.Union):
        _fields_ = [
            ("mi", MOUSEINPUT),
            ("ki", KEYBDINPUT),
            ("hi", HARDWAREINPUT),
        ]

    class INPUT(ctypes.Structure):
        _fields_ = [
            ("type", ctypes.c_ulong),
            ("u", INPUT_UNION),
        ]

    LPINPUT = ctypes.POINTER(INPUT)

    user32.OpenInputDesktop.restype = ctypes.wintypes.HANDLE
    user32.OpenInputDesktop.argtypes = [ctypes.wintypes.DWORD, ctypes.wintypes.BOOL, ctypes.wintypes.DWORD]

    user32.SetThreadDesktop.restype = ctypes.wintypes.BOOL
    user32.SetThreadDesktop.argtypes = [ctypes.wintypes.HANDLE]

    class POINT_STRUCT(ctypes.Structure):
        _fields_ = [("x", ctypes.wintypes.LONG), ("y", ctypes.wintypes.LONG)]

    user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT_STRUCT)]
    user32.GetCursorPos.restype = ctypes.wintypes.BOOL

    user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
    user32.SetCursorPos.restype = ctypes.wintypes.BOOL

    MOUSEEVENTF_VIRTUALDESK = 0x4000
else:
    MOUSEEVENTF_VIRTUALDESK = 0x4000

class WindowsInputController:
    """Ultra-fast, Jitter-Free Win32 input simulator with subpixel smoothing."""

    def __init__(self):
        self._attach_desktop()
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

        self.screen_width = user32.GetSystemMetrics(0)
        self.screen_height = user32.GetSystemMetrics(1)
        self.is_dragging = False

        # Sub-pixel accumulators for ultra-smooth non-shaking mouse glide
        self._accum_x = 0.0
        self._accum_y = 0.0
        self._accum_scroll_y = 0.0
        self._accum_scroll_x = 0.0

        # Configure ctypes argtypes for mouse_event for signed wheel data
        try:
            user32.mouse_event.argtypes = [
                ctypes.c_ulong,
                ctypes.c_ulong,
                ctypes.c_ulong,
                ctypes.c_long,
                ctypes.c_void_p
            ]
        except Exception:
            pass

    def _attach_desktop(self):
        """Ensure the thread is attached to the active interactive input desktop."""
        try:
            hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
            if hdesk:
                user32.SetThreadDesktop(hdesk)
        except Exception:
            pass

    def _send_mouse(self, flags: int, dx: int = 0, dy: int = 0, data: int = 0):
        """Hardware-level SendInput and mouse_event mouse event."""
        self._attach_desktop()
        try:
            inp = INPUT()
            inp.type = INPUT_MOUSE
            inp.u.mi.dx = int(dx)
            inp.u.mi.dy = int(dy)
            inp.u.mi.mouseData = int(data)
            inp.u.mi.dwFlags = flags
            inp.u.mi.time = 0
            inp.u.mi.dwExtraInfo = None
            res = user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
            if res == 0:
                user32.mouse_event(flags, int(dx), int(dy), int(data), 0)
        except Exception:
            try:
                user32.mouse_event(flags, int(dx), int(dy), int(data), 0)
            except Exception:
                pass

    def get_cursor_pos(self):
        """Get current mouse cursor (x, y)."""
        self._attach_desktop()
        pt = POINT_STRUCT()
        if user32.GetCursorPos(ctypes.byref(pt)):
            return int(pt.x), int(pt.y)
        return 0, 0

    def set_cursor_pos(self, x: int, y: int):
        """Set absolute cursor position in pixels."""
        self._attach_desktop()
        user32.SetCursorPos(int(x), int(y))

    def move_absolute(self, norm_x: float, norm_y: float):
        """Move cursor to normalized coordinate [0.0 - 1.0] across all displays with edge snapping."""
        self._attach_desktop()
        w = max(1, user32.GetSystemMetrics(0))
        h = max(1, user32.GetSystemMetrics(1))

        # Precision Edge Snapping: Taps near phone edges (<0.015 or >0.985) snap to exact boundary pixels
        clamped_x = max(0.0, min(1.0, float(norm_x)))
        clamped_y = max(0.0, min(1.0, float(norm_y)))
        if clamped_x > 0.985:
            clamped_x = 1.0
        elif clamped_x < 0.015:
            clamped_x = 0.0
        if clamped_y > 0.985:
            clamped_y = 1.0
        elif clamped_y < 0.015:
            clamped_y = 0.0

        px = int(round(clamped_x * (w - 1)))
        py = int(round(clamped_y * (h - 1)))
        user32.SetCursorPos(px, py)

    def set_cursor_normalized(self, norm_x: float, norm_y: float):
        """Set cursor position using normalized coordinates [0.0 - 1.0]."""
        self.move_absolute(norm_x, norm_y)

    def click_at(self, norm_x: float, norm_y: float, button: str = 'left'):
        """Move to normalized coordinates and click immediately."""
        self.move_absolute(norm_x, norm_y)
        self.click(button)

    def double_click_at(self, norm_x: float, norm_y: float, button: str = 'left'):
        """Move to normalized coordinates and double-click."""
        self.move_absolute(norm_x, norm_y)
        self.double_click(button)

    def touch_down_at(self, norm_x: float, norm_y: float, button: str = 'left'):
        """Move to position and press down mouse button (start drag)."""
        self.move_absolute(norm_x, norm_y)
        self.mouse_down(button)

    def touch_move_at(self, norm_x: float, norm_y: float):
        """Move cursor during touch drag with seamless mouse capture."""
        self.move_absolute(norm_x, norm_y)

    def touch_up_at(self, norm_x: float, norm_y: float, button: str = 'left'):
        """Release mouse button at position."""
        self.move_absolute(norm_x, norm_y)
        self.mouse_up(button)

    def scroll_at(self, norm_x: float, norm_y: float, dx: float, dy: float):
        """Move cursor to coordinate and scroll vertical & horizontal wheel with sub-pixel accumulator."""
        self.move_absolute(norm_x, norm_y)
        self.scroll(dx, dy)

    def move_relative(self, dx: float, dy: float):
        """Move cursor relatively with sub-pixel accumulator to eliminate jitter."""
        self._attach_desktop()
        self._accum_x += dx
        self._accum_y += dy

        step_x = int(self._accum_x)
        step_y = int(self._accum_y)

        if step_x != 0 or step_y != 0:
            pt = POINT_STRUCT()
            if user32.GetCursorPos(ctypes.byref(pt)):
                user32.SetCursorPos(int(pt.x + step_x), int(pt.y + step_y))
            self._send_mouse(MOUSEEVENTF_MOVE, step_x, step_y)
            self._accum_x -= step_x
            self._accum_y -= step_y

    def mouse_down(self, button: str = 'left'):
        """Press down a mouse button ('left', 'right', 'middle')."""
        button = button.lower()
        if button == 'left':
            self._send_mouse(MOUSEEVENTF_LEFTDOWN)
            self.is_dragging = True
        elif button == 'right':
            self._send_mouse(MOUSEEVENTF_RIGHTDOWN)
        elif button == 'middle':
            self._send_mouse(MOUSEEVENTF_MIDDLEDOWN)

    def mouse_up(self, button: str = 'left'):
        """Release a mouse button ('left', 'right', 'middle')."""
        button = button.lower()
        if button == 'left':
            self._send_mouse(MOUSEEVENTF_LEFTUP)
            self.is_dragging = False
        elif button == 'right':
            self._send_mouse(MOUSEEVENTF_RIGHTUP)
        elif button == 'middle':
            self._send_mouse(MOUSEEVENTF_MIDDLEUP)

    def click(self, button: str = 'left'):
        """Perform a single click."""
        self.mouse_down(button)
        time.sleep(0.01)
        self.mouse_up(button)

    def double_click(self, button: str = 'left'):
        """Perform a double click."""
        self.click(button)
        time.sleep(0.05)
        self.click(button)

    def scroll(self, dx: float, dy: float):
        """Scroll vertical or horizontal mouse wheel with high-precision sub-unit accumulator."""
        self._accum_scroll_y += dy
        self._accum_scroll_x += dx

        step_y = int(self._accum_scroll_y)
        step_x = int(self._accum_scroll_x)

        if step_y != 0:
            user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, step_y, None)
            self._accum_scroll_y -= step_y

        if step_x != 0:
            user32.mouse_event(MOUSEEVENTF_HWHEEL, 0, 0, step_x, None)
            self._accum_scroll_x -= step_x

    def key_down(self, key_name: str):
        """Press down a key."""
        k = key_name.lower()
        if k in VK_MAP:
            vk = VK_MAP[k]
            user32.keybd_event(vk, 0, 0, 0)
        elif len(k) == 1:
            vk = user32.VkKeyScanW(ord(k)) & 0xFF
            user32.keybd_event(vk, 0, 0, 0)

    def key_up(self, key_name: str):
        """Release a key."""
        k = key_name.lower()
        if k in VK_MAP:
            vk = VK_MAP[k]
            user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
        elif len(k) == 1:
            vk = user32.VkKeyScanW(ord(k)) & 0xFF
            user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)

    def key_press(self, key_name: str):
        """Press and release a key with virtual key mapping and unicode character fallback."""
        k = key_name.lower()
        if k in VK_MAP:
            self.key_down(key_name)
            time.sleep(0.01)
            self.key_up(key_name)
        elif len(key_name) == 1:
            # Single character (symbols, letters, emojis) -> direct unicode SendInput
            self.type_text(key_name)
        else:
            self.key_down(key_name)
            time.sleep(0.01)
            self.key_up(key_name)

    def hotkey(self, keys: List[str]):
        """Execute a key combination (e.g. ['ctrl', 'c'] or ['win', 'd'])."""
        for k in keys:
            self.key_down(k)
            time.sleep(0.01)
        time.sleep(0.02)
        for k in reversed(keys):
            self.key_up(k)
            time.sleep(0.01)

    def type_text(self, text: str):
        """Type Unicode string with full newline, tab, and special character Windows compatibility."""
        if not text:
            return
        for char in text:
            if char in ('\r', '\n'):
                self.key_press('enter')
                time.sleep(0.005)
            elif char == '\t':
                self.key_press('tab')
                time.sleep(0.005)
            elif char == '\b':
                self.key_press('backspace')
                time.sleep(0.005)
            else:
                code = ord(char)
                # Key down
                inp_down = INPUT()
                inp_down.type = INPUT_KEYBOARD
                inp_down.u.ki.wVk = 0
                inp_down.u.ki.wScan = code
                inp_down.u.ki.dwFlags = KEYEVENTF_UNICODE
                inp_down.u.ki.time = 0
                inp_down.u.ki.dwExtraInfo = None

                # Key up
                inp_up = INPUT()
                inp_up.type = INPUT_KEYBOARD
                inp_up.u.ki.wVk = 0
                inp_up.u.ki.wScan = code
                inp_up.u.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
                inp_up.u.ki.time = 0
                inp_up.u.ki.dwExtraInfo = None

                inputs = (INPUT * 2)(inp_down, inp_up)
                user32.SendInput(2, inputs, ctypes.sizeof(INPUT))
                time.sleep(0.002)

    def media(self, action: str):
        """Dispatch media action."""
        act = action.lower()
        if act == "play_pause":
            self.key_press("play_pause")
        elif act == "prev":
            self.key_press("prev")
        elif act == "next":
            self.key_press("next")
        elif act == "vol_up":
            self.key_press("vol_up")
        elif act == "vol_down":
            self.key_press("vol_down")
        elif act == "mute":
            self.key_press("vol_mute")


class LinuxInputController:
    """Ultra-fast cross-platform input controller for Linux and macOS via pynput."""

    def __init__(self):
        self.is_dragging = False
        self._accum_x = 0.0
        self._accum_y = 0.0
        self._accum_scroll_y = 0.0
        self._accum_scroll_x = 0.0

        try:
            from pynput.mouse import Controller as MouseController, Button
            from pynput.keyboard import Controller as KeyboardController, Key
            self._mouse = MouseController()
            self._keyboard = KeyboardController()
            self._Button = Button
            self._Key = Key
            self._has_pynput = True
        except Exception:
            self._mouse = None
            self._keyboard = None
            self._Button = None
            self._Key = None
            self._has_pynput = False

        self.screen_width = 1920
        self.screen_height = 1080
        try:
            import mss
            with mss.mss() as sct:
                mon = sct.monitors[0]
                self.screen_width = mon.get("width", 1920)
                self.screen_height = mon.get("height", 1080)
        except Exception:
            pass

    def get_cursor_pos(self):
        if self._mouse:
            try:
                pos = self._mouse.position
                return int(pos[0]), int(pos[1])
            except Exception:
                pass
        return 0, 0

    def set_cursor_pos(self, x: int, y: int):
        if self._mouse:
            try:
                self._mouse.position = (int(x), int(y))
            except Exception:
                pass

    def move_absolute(self, norm_x: float, norm_y: float):
        nx = max(0.0, min(1.0, float(norm_x)))
        ny = max(0.0, min(1.0, float(norm_y)))
        px = int(round(nx * (self.screen_width - 1)))
        py = int(round(ny * (self.screen_height - 1)))
        self.set_cursor_pos(px, py)

    def set_cursor_normalized(self, norm_x: float, norm_y: float):
        self.move_absolute(norm_x, norm_y)

    def click_at(self, norm_x: float, norm_y: float, button: str = 'left'):
        self.move_absolute(norm_x, norm_y)
        time.sleep(0.002)
        self.click(button)

    def double_click_at(self, norm_x: float, norm_y: float, button: str = 'left'):
        self.move_absolute(norm_x, norm_y)
        time.sleep(0.002)
        self.double_click(button)

    def touch_down_at(self, norm_x: float, norm_y: float, button: str = 'left'):
        self.move_absolute(norm_x, norm_y)
        time.sleep(0.002)
        self.mouse_down(button)

    def touch_move_at(self, norm_x: float, norm_y: float):
        self.move_absolute(norm_x, norm_y)

    def touch_up_at(self, norm_x: float, norm_y: float, button: str = 'left'):
        self.move_absolute(norm_x, norm_y)
        time.sleep(0.002)
        self.mouse_up(button)

    def scroll_at(self, norm_x: float, norm_y: float, dx: float, dy: float):
        self.move_absolute(norm_x, norm_y)
        self.scroll(dx, dy)

    def move_relative(self, dx: float, dy: float):
        if not self._mouse:
            return
        self._accum_x += float(dx)
        self._accum_y += float(dy)
        step_x = int(self._accum_x)
        step_y = int(self._accum_y)
        if step_x != 0 or step_y != 0:
            self._accum_x -= step_x
            self._accum_y -= step_y
            try:
                self._mouse.move(step_x, step_y)
            except Exception:
                pass

    def _get_button(self, btn: str):
        if not self._Button:
            return None
        b = btn.lower()
        if b == "right":
            return self._Button.right
        elif b in ("middle", "mid"):
            return self._Button.middle
        return self._Button.left

    def mouse_down(self, button: str = 'left'):
        if self._mouse and self._Button:
            btn = self._get_button(button)
            if btn:
                try:
                    self._mouse.press(btn)
                except Exception:
                    pass

    def mouse_up(self, button: str = 'left'):
        if self._mouse and self._Button:
            btn = self._get_button(button)
            if btn:
                try:
                    self._mouse.release(btn)
                except Exception:
                    pass

    def click(self, button: str = 'left'):
        if self._mouse and self._Button:
            btn = self._get_button(button)
            if btn:
                try:
                    self._mouse.click(btn, 1)
                except Exception:
                    pass

    def double_click(self, button: str = 'left'):
        if self._mouse and self._Button:
            btn = self._get_button(button)
            if btn:
                try:
                    self._mouse.click(btn, 2)
                except Exception:
                    pass

    def scroll(self, dx: float, dy: float):
        if not self._mouse:
            return
        self._accum_scroll_y += float(dy)
        self._accum_scroll_x += float(dx)
        steps_y = int(self._accum_scroll_y)
        steps_x = int(self._accum_scroll_x)
        if steps_y != 0 or steps_x != 0:
            self._accum_scroll_y -= steps_y
            self._accum_scroll_x -= steps_x
            try:
                self._mouse.scroll(steps_x, steps_y)
            except Exception:
                pass

    def _map_key(self, name: str):
        if not self._Key:
            return name
        k = name.lower()
        key_map = {
            'ctrl': self._Key.ctrl, 'control': self._Key.ctrl,
            'shift': self._Key.shift, 'alt': self._Key.alt,
            'win': getattr(self._Key, 'cmd', self._Key.ctrl),
            'windows': getattr(self._Key, 'cmd', self._Key.ctrl),
            'cmd': getattr(self._Key, 'cmd', self._Key.ctrl),
            'enter': self._Key.enter, 'return': self._Key.enter,
            'backspace': self._Key.backspace, 'tab': self._Key.tab,
            'space': self._Key.space, 'esc': self._Key.esc, 'escape': self._Key.esc,
            'delete': self._Key.delete, 'del': self._Key.delete,
            'insert': self._Key.insert, 'ins': self._Key.insert,
            'home': self._Key.home, 'end': self._Key.end,
            'pageup': self._Key.page_up, 'pgup': self._Key.page_up,
            'pagedown': self._Key.page_down, 'pgdn': self._Key.page_down,
            'left': self._Key.left, 'up': self._Key.up,
            'right': self._Key.right, 'down': self._Key.down,
            'capslock': self._Key.caps_lock, 'numlock': self._Key.num_lock,
            'scrolllock': getattr(self._Key, 'scroll_lock', None),
            'printscreen': self._Key.print_screen, 'prtsc': self._Key.print_screen,
            'f1': self._Key.f1, 'f2': self._Key.f2, 'f3': self._Key.f3,
            'f4': self._Key.f4, 'f5': self._Key.f5, 'f6': self._Key.f6,
            'f7': self._Key.f7, 'f8': self._Key.f8, 'f9': self._Key.f9,
            'f10': self._Key.f10, 'f11': self._Key.f11, 'f12': self._Key.f12,
            'play_pause': getattr(self._Key, 'media_play_pause', None),
            'prev': getattr(self._Key, 'media_previous', None),
            'next': getattr(self._Key, 'media_next', None),
            'vol_mute': getattr(self._Key, 'media_volume_mute', None),
            'vol_down': getattr(self._Key, 'media_volume_down', None),
            'vol_up': getattr(self._Key, 'media_volume_up', None),
        }
        return key_map.get(k, k)

    def key_down(self, key_name: str):
        if not self._keyboard:
            return
        mapped = self._map_key(key_name)
        if mapped:
            try:
                self._keyboard.press(mapped)
            except Exception:
                pass

    def key_up(self, key_name: str):
        if not self._keyboard:
            return
        mapped = self._map_key(key_name)
        if mapped:
            try:
                self._keyboard.release(mapped)
            except Exception:
                pass

    def key_press(self, key_name: str):
        if not self._keyboard:
            return
        mapped = self._map_key(key_name)
        if mapped:
            try:
                self._keyboard.press(mapped)
                time.sleep(0.005)
                self._keyboard.release(mapped)
            except Exception:
                pass

    def hotkey(self, keys: List[str]):
        if not self._keyboard:
            return
        mapped_keys = [self._map_key(k) for k in keys if self._map_key(k) is not None]
        try:
            for k in mapped_keys:
                self._keyboard.press(k)
                time.sleep(0.002)
            time.sleep(0.01)
            for k in reversed(mapped_keys):
                self._keyboard.release(k)
                time.sleep(0.002)
        except Exception:
            pass

    def type_text(self, text: str):
        if not self._keyboard:
            return
        try:
            self._keyboard.type(text)
        except Exception:
            pass


# Select appropriate input controller based on operating system
if _IS_WIN32:
    InputController = WindowsInputController
else:
    InputController = LinuxInputController

controller = InputController()
