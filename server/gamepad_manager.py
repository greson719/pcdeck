"""
PCDeck Pro - Console-Grade Virtual Gamepad Engine
Supports ViGEmBus Virtual Xbox 360 / DualShock Controller on Windows with SendInput Fallback.
"""

import math
import os
import subprocess
import sys
import threading
import time
from typing import Dict, Optional, Tuple, Any

# Try importing vgamepad (ViGEmBus client)
try:
    import vgamepad as vg
    _HAS_VGAMEPAD = True
except Exception:
    vg = None
    _HAS_VGAMEPAD = False

# Import local input controller for fallback mode
try:
    from server.input_controller import controller as kbm_controller
except ImportError:
    try:
        from input_controller import controller as kbm_controller
    except ImportError:
        kbm_controller = None


def is_vigem_installed() -> bool:
    """
    Checks if the ViGEmBus driver / kernel service is installed on Windows.
    Queries Windows Service Control Manager and system driver paths.
    """
    if sys.platform != "win32":
        return False
    
    # 1. Query Windows Service Control Manager
    try:
        proc = subprocess.run(
            ["sc", "query", "ViGEmBus"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        if "RUNNING" in proc.stdout or "STOPPED" in proc.stdout:
            return True
    except Exception:
        pass

    # 2. Check System32 drivers directory
    sys_dir = os.environ.get("SystemRoot", r"C:\Windows")
    driver_sys = os.path.join(sys_dir, "System32", "drivers", "ViGEmBus.sys")
    if os.path.exists(driver_sys):
        return True

    return False


def get_drivers_dir() -> str:
    """Returns safe fallback path."""
    return os.path.dirname(os.path.abspath(__file__))


def has_internet_connection() -> bool:
    """Checks if host PC has an active internet connection."""
    import socket
    try:
        sock = socket.create_connection(("1.1.1.1", 53), timeout=2.0)
        sock.close()
        return True
    except Exception:
        try:
            sock = socket.create_connection(("8.8.8.8", 53), timeout=2.0)
            sock.close()
            return True
        except Exception:
            return False


def install_vigem_silently(msi_path: Optional[str] = None) -> Tuple[bool, str]:
    """Installs ViGEmBus online via winget if requested."""
    if sys.platform != "win32":
        return False, "ViGEmBus is only supported on Windows 10/11."

    try:
        cmd = [
            "winget", "install", "--id", "Nefarius.ViGEmBus", "-e",
            "--silent", "--accept-package-agreements", "--accept-source-agreements"
        ]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        if proc.returncode in (0, 3010):
            return True, "ViGEmBus driver installed successfully via winget."
        return False, f"winget returned code {proc.returncode}"
    except Exception as e:
        return False, f"Driver execution error: {str(e)}"



# Hardware Scan Codes (Set 1 Make Codes)
SCAN_W      = 0x11
SCAN_A      = 0x1E
SCAN_S      = 0x1F
SCAN_D      = 0x20
SCAN_LSHIFT = 0x2A

DIR_W   = 1 << 0
DIR_A   = 1 << 1
DIR_S   = 1 << 2
DIR_D   = 1 << 3
DIR_RUN = 1 << 4

DIR_KEYS = (
    (DIR_W, SCAN_W, "w"),
    (DIR_A, SCAN_A, "a"),
    (DIR_S, SCAN_S, "s"),
    (DIR_D, SCAN_D, "d"),
    (DIR_RUN, SCAN_LSHIFT, "shift"),
)

# Standard Gamepad / XInput Bitmask mappings
BUTTON_BIT_MAPPINGS = (
    (1 << 0, "A"),
    (1 << 1, "B"),
    (1 << 2, "X"),
    (1 << 3, "Y"),
    (1 << 4, "LB"),
    (1 << 5, "RB"),
    (1 << 6, "THUMBL"),
    (1 << 7, "THUMBR"),
    (1 << 8, "DPAD_UP"),
    (1 << 9, "DPAD_DOWN"),
    (1 << 10, "DPAD_LEFT"),
    (1 << 11, "DPAD_RIGHT"),
    (1 << 12, "START"),
    (1 << 13, "BACK"),
    (1 << 14, "GUIDE"),
)


class WASDTranslator:
    """
    Translates raw analog stick coordinates into 8-way WASD scan code injection.
    Features radial deadzone, 45-degree sectoring, and sprint modifier (LShift).
    """
    __slots__ = ('_deadzone', '_run_threshold', '_prev_dir_mask')

    def __init__(self, deadzone: int = 5000, run_threshold: int = 24000):
        self._deadzone = deadzone
        self._run_threshold = run_threshold
        self._prev_dir_mask = 0

    def resolve(self, axis_x: int, axis_y: int):
        """
        Translates raw stick coords (x, y in -32767..32767) into WASD key presses.
        axis_y > 0 is UP, axis_y < 0 is DOWN.
        """
        mag = math.hypot(axis_x, axis_y)
        current_mask = 0

        if mag > self._deadzone:
            angle = math.degrees(math.atan2(axis_y, axis_x))

            # 8-Way Sectoring (45-degree slices)
            if 67.5 <= angle < 112.5:
                current_mask = DIR_W
            elif 22.5 <= angle < 67.5:
                current_mask = DIR_W | DIR_D
            elif -22.5 <= angle < 22.5:
                current_mask = DIR_D
            elif -67.5 <= angle < -22.5:
                current_mask = DIR_S | DIR_D
            elif -112.5 <= angle < -67.5:
                current_mask = DIR_S
            elif -157.5 <= angle < -112.5:
                current_mask = DIR_S | DIR_A
            elif angle >= 157.5 or angle < -157.5:
                current_mask = DIR_A
            elif 112.5 <= angle < 157.5:
                current_mask = DIR_W | DIR_A

            # Check Sprint / Run Threshold
            if mag >= self._run_threshold:
                current_mask |= DIR_RUN

        diff = current_mask ^ self._prev_dir_mask
        if diff:
            self._apply_diff(diff, current_mask)
            self._prev_dir_mask = current_mask

    def _apply_diff(self, diff: int, current_mask: int):
        if not kbm_controller:
            return
        is_win32 = sys.platform == "win32"
        for mask_bit, scan_code, key_name in DIR_KEYS:
            if diff & mask_bit:
                is_down = bool(current_mask & mask_bit)
                if is_win32:
                    try:
                        import ctypes
                        user32 = ctypes.windll.user32
                        flags = 0x0008 if is_down else (0x0008 | 0x0002)  # KEYEVENTF_SCANCODE
                        user32.keybd_event(0, scan_code, flags, 0)
                        continue
                    except Exception:
                        pass
                if is_down:
                    kbm_controller.key_down(key_name)
                else:
                    kbm_controller.key_up(key_name)

    def reset(self):
        if self._prev_dir_mask:
            self._apply_diff(self._prev_dir_mask, 0)
            self._prev_dir_mask = 0


class GamepadManager:
    """
    Unified Gamepad Engine.
    Handles virtual Xbox 360 controller emulation via ViGEmBus with seamless
    fallback to SendInput keyboard/mouse mappings when drivers are missing.
    """

    def __init__(self):
        self.lock = threading.RLock()
        self.mode = "none" # "xinput" or "sendinput"
        self.x360: Optional[Any] = None
        self._button_map_vg: Dict[str, Any] = {}
        self._button_states: Dict[str, bool] = {}
        self._axis_states: Dict[str, Tuple[float, float]] = {
            "left": (0.0, 0.0),
            "right": (0.0, 0.0)
        }
        self._trigger_states: Dict[str, float] = {
            "left": 0.0,
            "right": 0.0
        }
        self.wasd_translator = WASDTranslator()
        self._prev_buttons_mask = 0

        # Universal Web Game & Browser Mode: Dual-emits keyboard keystrokes for WebGL, Flash, Canvas & Native games
        self.hybrid_mode: bool = True
        self._hybrid_wasd_keys: Dict[str, bool] = {"up": False, "down": False, "left": False, "right": False}
        self._hybrid_trigger_keys: Dict[str, bool] = {"left": False, "right": False}
        self._held_fallback_keys = set()

        # Fallback & Hybrid keybindings (covers web browser games, driving simulators, and standard PC titles)
        self.fallback_keymap = {
            "A": ["space"],
            "B": ["c"],
            "X": ["r"],
            "Y": ["e"],
            "LB": ["shift", "q"],
            "RB": ["f", "e"],
            "LT": ["left", "a"],   # Brake / Reverse / Lean-Left for Web & PC Racing
            "RT": ["right", "d"],  # Gas / Accelerate / Lean-Right for Web & PC Racing
            "DPAD_UP": ["up", "w"],
            "DPAD_DOWN": ["down", "s"],
            "DPAD_LEFT": ["left", "a"],
            "DPAD_RIGHT": ["right", "d"],
            "START": ["esc"],
            "BACK": ["tab"],
            "GUIDE": ["win"],
            "THUMBL": ["shift"],
            "THUMBR": ["ctrl"],
            "1": ["1"],
            "2": ["2"],
            "3": ["3"],
            "4": ["4"],
            "TAB": ["tab"],
            "ESC": ["esc"]
        }

        self.init_backend()

    def init_backend(self) -> str:
        """Checks ViGEmBus availability and prepares driver mode without prematurely attaching controller."""
        global vg, _HAS_VGAMEPAD
        with self.lock:
            # Re-attempt import if previously failed (e.g. driver was installed after boot)
            if not _HAS_VGAMEPAD:
                try:
                    import vgamepad as _vg
                    vg = _vg
                    _HAS_VGAMEPAD = True
                except Exception:
                    vg = None
                    _HAS_VGAMEPAD = False

            # Check ViGEmBus availability
            if _HAS_VGAMEPAD and is_vigem_installed():
                self.mode = "xinput"
                self._setup_vgamepad_map()
                print("[GamepadManager] ViGEmBus Virtual Xbox 360 driver ready (Controller attaches on-demand).")
                return self.mode

            self.mode = "sendinput"
            self.x360 = None
            print("[GamepadManager] Running in SendInput Keyboard/Mouse fallback mode.")
            return self.mode

    def ensure_x360_connected(self):
        """Attaches the virtual Xbox 360 controller device only when gamepad input is actually used."""
        if self.mode == "xinput" and self.x360 is None and _HAS_VGAMEPAD and vg:
            try:
                self.x360 = vg.VX360Gamepad()
                self._setup_vgamepad_map()
                print("[GamepadManager] ViGEmBus Virtual Xbox 360 Controller connected on demand.")
            except Exception as e:
                print(f"[GamepadManager] ViGEmBus device creation failed ({e}), falling back to SendInput.")
                self.mode = "sendinput"
                self.x360 = None

    def _setup_vgamepad_map(self):
        """Maps string identifiers to vgamepad XUSB_BUTTON enums."""
        if not vg:
            return
        self._button_map_vg = {
            "A": vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
            "B": vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
            "X": vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
            "Y": vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
            "LB": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
            "RB": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
            "THUMBL": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
            "THUMBR": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
            "START": vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
            "BACK": vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
            "GUIDE": vg.XUSB_BUTTON.XUSB_GAMEPAD_GUIDE,
            "DPAD_UP": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
            "DPAD_DOWN": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
            "DPAD_LEFT": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
            "DPAD_RIGHT": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT
        }

    def set_button(self, btn: str, is_down: bool):
        """Sets digital button state with alias resolution and trigger support."""
        self.ensure_x360_connected()
        with self.lock:
            btn_upper = btn.upper().strip()

            # Normalize aliases
            alias_map = {
                "LS_CLICK": "THUMBL",
                "L3": "THUMBL",
                "THUMB_L": "THUMBL",
                "RS_CLICK": "THUMBR",
                "R3": "THUMBR",
                "THUMB_R": "THUMBR",
                "SELECT": "BACK",
                "VIEW": "BACK",
                "MAP": "BACK",
                "MENU": "START",
                "PAUSE": "START",
                "OPTIONS": "START",
                "HOME": "GUIDE"
            }
            btn_upper = alias_map.get(btn_upper, btn_upper)

            # Handle triggers if sent as digital buttons
            if btn_upper in ("LT", "L2"):
                self.set_trigger("left", 1.0 if is_down else 0.0)
                return
            elif btn_upper in ("RT", "R2"):
                self.set_trigger("right", 1.0 if is_down else 0.0)
                return

            self._button_states[btn_upper] = is_down

            if self.mode == "xinput" and self.x360:
                vg_btn = self._button_map_vg.get(btn_upper)
                if vg_btn:
                    if is_down:
                        self.x360.press_button(button=vg_btn)
                    else:
                        self.x360.release_button(button=vg_btn)
                    self.x360.update()

            # Universal Web Game & Browser Mode / SendInput Fallback
            if self.hybrid_mode or self.mode != "xinput" or not self.x360:
                self._handle_fallback_button(btn_upper, is_down)

    def set_trigger(self, trigger: str, value: float):
        """Sets analog trigger pressure (0.0 to 1.0)."""
        self.ensure_x360_connected()
        with self.lock:
            val = max(0.0, min(1.0, float(value)))
            trigger_lower = trigger.lower()
            key = "left" if trigger_lower in ("left", "lt", "l2") else "right"
            self._trigger_states[key] = val

            if self.mode == "xinput" and self.x360:
                if key == "left":
                    self.x360.left_trigger_float(value_float=val)
                else:
                    self.x360.right_trigger_float(value_float=val)
                self.x360.update()

            # Universal Web Game & Browser Mode / SendInput Fallback
            if self.hybrid_mode or self.mode != "xinput" or not self.x360:
                is_pressed = val > 0.35
                if is_pressed != self._hybrid_trigger_keys.get(key, False):
                    self._hybrid_trigger_keys[key] = is_pressed
                    btn_name = "LT" if key == "left" else "RT"
                    self._handle_fallback_button(btn_name, is_pressed)

    def set_stick(self, stick: str, x: float, y: float):
        """
        Sets analog stick deflection (-1.0 to 1.0).
        x: -1.0 (left) to 1.0 (right)
        y: -1.0 (down) to 1.0 (up)
        """
        self.ensure_x360_connected()
        with self.lock:
            clamped_x = max(-1.0, min(1.0, float(x)))
            clamped_y = max(-1.0, min(1.0, float(y)))
            stick_lower = stick.lower()
            self._axis_states[stick_lower] = (clamped_x, clamped_y)

            if self.mode == "xinput" and self.x360:
                if stick_lower in ("left", "l", "l3"):
                    self.x360.left_joystick_float(x_value_float=clamped_x, y_value_float=clamped_y)
                elif stick_lower in ("right", "r", "r3"):
                    self.x360.right_joystick_float(x_value_float=clamped_x, y_value_float=clamped_y)
                self.x360.update()

            # Universal Web Game & Browser Mode / SendInput Fallback
            if self.hybrid_mode or self.mode != "xinput" or not self.x360:
                if stick_lower in ("left", "l", "l3"):
                    self._handle_fallback_wasd(clamped_x, clamped_y)
                elif stick_lower in ("right", "r", "r3"):
                    if self.mode != "xinput" or not self.x360:
                        self._handle_fallback_aim(clamped_x, clamped_y)

    def apply_gyro_steer(self, steer_val: float):
        """
        Applies motion gyroscope steering (-1.0 left to 1.0 right).
        Blends with current left stick deflection.
        """
        self.ensure_x360_connected()
        with self.lock:
            cur_y = self._axis_states.get("left", (0.0, 0.0))[1]
            clamped_steer = max(-1.0, min(1.0, float(steer_val)))
            self._axis_states["left"] = (clamped_steer, cur_y)

            if self.mode == "xinput" and self.x360:
                self.x360.left_joystick_float(x_value_float=clamped_steer, y_value_float=cur_y)
                self.x360.update()
            else:
                self._handle_fallback_wasd(clamped_steer, cur_y)

    def apply_gyro_aim(self, aim_x: float, aim_y: float):
        """
        Applies motion gyroscope aiming (-1.0 to 1.0).
        """
        self.ensure_x360_connected()
        with self.lock:
            clamped_x = max(-1.0, min(1.0, float(aim_x)))
            clamped_y = max(-1.0, min(1.0, float(aim_y)))
            self._axis_states["right"] = (clamped_x, clamped_y)

            if self.mode == "xinput" and self.x360:
                self.x360.right_joystick_float(x_value_float=clamped_x, y_value_float=clamped_y)
                self.x360.update()
            else:
                self._handle_fallback_aim(clamped_x, clamped_y)

    def sync_button_bitmask(self, buttons_mask: int):
        """
        Synchronizes 16-bit packed button bitmask to virtual controller or fallback keys.
        Processes diff bits in sub-microsecond bitwise operations.
        """
        diff = buttons_mask ^ self._prev_buttons_mask
        if not diff:
            return
        for bit, btn_name in BUTTON_BIT_MAPPINGS:
            if diff & bit:
                is_down = bool(buttons_mask & bit)
                self.set_button(btn_name, is_down)
        self._prev_buttons_mask = buttons_mask

    def handle_hybrid_frame(self, flags: int, buttons: int, lx: int, ly: int, mdx: int, mdy: int):
        """
        Sub-millisecond processor for 12-byte OP_GAMEPAD_HYBRID frames.
        Atomic dispatch: Left Stick (WASD/XInput) + Right Thumb (Mouse Aim) + Buttons.
        """
        # 1. Sync button states
        if buttons != self._prev_buttons_mask:
            self.sync_button_bitmask(buttons)

        # 2. Locomotion & Camera
        if self.mode == "xinput" and self.x360:
            self.ensure_x360_connected()
            with self.lock:
                self.x360.left_joystick_float(x_value_float=lx / 32767.0, y_value_float=ly / 32767.0)
                self.x360.update()
            if mdx != 0 or mdy != 0:
                if kbm_controller:
                    kbm_controller.move_relative(mdx, mdy)
        else:
            # Zero-driver SendInput mode:
            # Left stick -> 8-way WASD sectoring with sprint
            self.wasd_translator.resolve(lx, ly)
            # Right swipe -> Direct relative mouse delta
            if mdx != 0 or mdy != 0:
                if kbm_controller:
                    kbm_controller.move_relative(mdx, mdy)

    def reset_all(self):
        """Resets all sticks and buttons to neutral rest state."""
        with self.lock:
            if self.mode == "xinput" and self.x360:
                try:
                    self.x360.reset()
                    self.x360.update()
                except Exception:
                    pass
            self.wasd_translator.reset()
            self._prev_buttons_mask = 0
            self._button_states.clear()
            self._axis_states = {"left": (0.0, 0.0), "right": (0.0, 0.0)}
            self._trigger_states = {"left": 0.0, "right": 0.0}

            # Release any active hybrid or fallback keystrokes
            if kbm_controller:
                for k in list(self._held_fallback_keys):
                    try:
                        kbm_controller.key_up(k)
                    except Exception:
                        pass
            self._held_fallback_keys.clear()
            self._hybrid_wasd_keys = {"up": False, "down": False, "left": False, "right": False}
            self._hybrid_trigger_keys = {"left": False, "right": False}

    def set_hybrid_mode(self, enabled: bool):
        """Toggles universal dual-emission (emits keyboard keystrokes alongside virtual controller for browser and PC games)."""
        with self.lock:
            self.hybrid_mode = bool(enabled)
            if not self.hybrid_mode:
                if kbm_controller:
                    for k in list(self._held_fallback_keys):
                        try:
                            kbm_controller.key_up(k)
                        except Exception:
                            pass
                self._held_fallback_keys.clear()
                self._hybrid_wasd_keys = {"up": False, "down": False, "left": False, "right": False}
                self._hybrid_trigger_keys = {"left": False, "right": False}

    # -----------------------------------------------------------------------
    # SendInput Fallback & Universal Web Game Helpers
    # -----------------------------------------------------------------------

    def _handle_fallback_button(self, btn: str, is_down: bool):
        if not kbm_controller:
            return
        mapped = self.fallback_keymap.get(btn)
        if not mapped:
            return

        keys = mapped if isinstance(mapped, (list, tuple)) else [mapped]
        for key in keys:
            if key == "left_click":
                if is_down:
                    kbm_controller.mouse_down("left")
                else:
                    kbm_controller.mouse_up("left")
            elif key == "right_click":
                if is_down:
                    kbm_controller.mouse_down("right")
                else:
                    kbm_controller.mouse_up("right")
            else:
                if is_down:
                    kbm_controller.key_down(key)
                    self._held_fallback_keys.add(key)
                else:
                    kbm_controller.key_up(key)
                    self._held_fallback_keys.discard(key)

    def _handle_fallback_wasd(self, x: float, y: float):
        """Maps left stick deflection to WASD keys via 8-way sectoring."""
        self.wasd_translator.resolve(int(round(x * 32767.0)), int(round(y * 32767.0)))

    def _handle_fallback_aim(self, x: float, y: float):
        """Maps right stick deflection to smooth mouse look."""
        if not kbm_controller:
            return
        if abs(x) < 0.08 and abs(y) < 0.08:
            return
        # Ballistic curve
        sens = 18.0
        dx = int(x * abs(x) * sens)
        dy = int(-y * abs(y) * sens) # Invert Y for standard mouse look
        if dx != 0 or dy != 0:
            kbm_controller.move_relative(dx, dy)


# Global Singleton Gamepad Instance
gamepad_manager = GamepadManager()
