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
except ImportError:
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


def install_vigem_silently(msi_path: Optional[str] = None) -> Tuple[bool, str]:
    """
    Installs the bundled Microsoft WHQL-signed ViGEmBus MSI completely silently.
    Returns (success: bool, message: str).
    """
    if sys.platform != "win32":
        return False, "ViGEmBus is only supported on Windows 10/11."

    if not msi_path:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        msi_path = os.path.join(base_dir, "drivers", "ViGEmBus_x64.msi")

    if not os.path.exists(msi_path):
        return False, f"Driver installer package not found at: {msi_path}"

    try:
        cmd = [
            "msiexec.exe",
            "/i", msi_path,
            "/qn",           # Quiet mode, zero user interface
            "/norestart",    # Do not restart Windows
            "ALLUSERS=1"
        ]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        # 0 = success, 3010 = success reboot deferred
        if proc.returncode in (0, 3010):
            return True, "ViGEmBus driver installed successfully."
        else:
            return False, f"msiexec returned code {proc.returncode}: {proc.stderr}"
    except Exception as e:
        return False, f"Driver execution error: {str(e)}"


class GamepadManager:
    """
    Unified Gamepad Engine.
    Handles virtual Xbox 360 controller emulation via ViGEmBus with seamless
    fallback to SendInput keyboard/mouse mappings when drivers are missing.
    """

    def __init__(self):
        self.lock = threading.Lock()
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

        # Fallback keybindings for SendInput mode
        self.fallback_keymap = {
            "A": "space",
            "B": "c",
            "X": "r",
            "Y": "e",
            "LB": "shift",
            "RB": "f",
            "LT": "right_click",
            "RT": "left_click",
            "DPAD_UP": "up",
            "DPAD_DOWN": "down",
            "DPAD_LEFT": "left",
            "DPAD_RIGHT": "right",
            "START": "esc",
            "BACK": "tab",
            "GUIDE": "win",
            "THUMBL": "shift",
            "THUMBR": "ctrl"
        }

        self.init_backend()

    def init_backend(self) -> str:
        """Initializes ViGEmBus virtual Xbox controller or falls back to SendInput."""
        with self.lock:
            # Check ViGEmBus availability
            if _HAS_VGAMEPAD and is_vigem_installed():
                try:
                    self.x360 = vg.VX360Gamepad()
                    self.mode = "xinput"
                    self._setup_vgamepad_map()
                    print("[GamepadManager] ViGEmBus Virtual Xbox 360 Controller connected.")
                    return self.mode
                except Exception as e:
                    print(f"[GamepadManager] ViGEmBus initialization failed ({e}), falling back to SendInput.")

            self.mode = "sendinput"
            self.x360 = None
            print("[GamepadManager] Running in SendInput Keyboard/Mouse fallback mode.")
            return self.mode

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
            else:
                # SendInput fallback
                self._handle_fallback_button(btn_upper, is_down)

    def set_trigger(self, trigger: str, value: float):
        """Sets analog trigger pressure (0.0 to 1.0)."""
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
            else:
                # Fallback: trigger threshold > 0.4 triggers mouse clicks or keys
                is_pressed = val > 0.4
                btn_name = "LT" if key == "left" else "RT"
                self._handle_fallback_button(btn_name, is_pressed)

    def set_stick(self, stick: str, x: float, y: float):
        """
        Sets analog stick deflection (-1.0 to 1.0).
        x: -1.0 (left) to 1.0 (right)
        y: -1.0 (down) to 1.0 (up)
        """
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
            else:
                # Fallback: Left stick maps to WASD, Right stick maps to mouse delta
                if stick_lower in ("left", "l", "l3"):
                    self._handle_fallback_wasd(clamped_x, clamped_y)
                elif stick_lower in ("right", "r", "r3"):
                    self._handle_fallback_aim(clamped_x, clamped_y)

    def reset_all(self):
        """Resets all sticks and buttons to neutral rest state."""
        with self.lock:
            if self.mode == "xinput" and self.x360:
                try:
                    self.x360.reset()
                    self.x360.update()
                except Exception:
                    pass
            self._button_states.clear()
            self._axis_states = {"left": (0.0, 0.0), "right": (0.0, 0.0)}
            self._trigger_states = {"left": 0.0, "right": 0.0}

    # -----------------------------------------------------------------------
    # SendInput Fallback Helpers
    # -----------------------------------------------------------------------

    def _handle_fallback_button(self, btn: str, is_down: bool):
        if not kbm_controller:
            return
        mapped = self.fallback_keymap.get(btn)
        if not mapped:
            return

        if mapped == "left_click":
            if is_down:
                kbm_controller.mouse_down("left")
            else:
                kbm_controller.mouse_up("left")
        elif mapped == "right_click":
            if is_down:
                kbm_controller.mouse_down("right")
            else:
                kbm_controller.mouse_up("right")
        else:
            if is_down:
                kbm_controller.key_down(mapped)
            else:
                kbm_controller.key_up(mapped)

    def _handle_fallback_wasd(self, x: float, y: float):
        """Maps left stick deflection to WASD keys."""
        if not kbm_controller:
            return
        threshold = 0.25
        # W / S (y is positive up, negative down)
        if y > threshold:
            kbm_controller.key_down("w")
            kbm_controller.key_up("s")
        elif y < -threshold:
            kbm_controller.key_down("s")
            kbm_controller.key_up("w")
        else:
            kbm_controller.key_up("w")
            kbm_controller.key_up("s")

        # A / D
        if x > threshold:
            kbm_controller.key_down("d")
            kbm_controller.key_up("a")
        elif x < -threshold:
            kbm_controller.key_down("a")
            kbm_controller.key_up("d")
        else:
            kbm_controller.key_up("a")
            kbm_controller.key_up("d")

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
