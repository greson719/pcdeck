"""
PCDeck - Native Windows Desktop Application GUI
Desktop control panel for wireless PC remote control, high-speed file transfer,
live PC audio streaming, and adaptive phone screen streaming.

Visual style is driven by the design tokens below (C_* colours, F_* fonts):
neutral surfaces, one accent, saturated colour reserved for state.
"""

import asyncio
import datetime
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import traceback
from typing import Optional
import urllib.request
import webbrowser
try:
    import winreg
except ImportError:
    winreg = None



# Ensure sys.stdout and sys.stderr exist for windowed / noconsole PyInstaller executables
if sys.stdout is None:
    sys.stdout = io.StringIO()
if sys.stderr is None:
    sys.stderr = io.StringIO()

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure root directory is in sys.path so 'server.*' packages resolve
if getattr(sys, "frozen", False):
    _ROOT_DIR = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
else:
    _ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

# Suppress benign Windows connection reset exceptions (WinError 10054/10053) on abrupt mobile client disconnect
if sys.platform == "win32":
    try:
        from asyncio.proactor_events import _ProactorBasePipeTransport
        _orig_call_conn_lost = _ProactorBasePipeTransport._call_connection_lost
        def _safe_call_conn_lost(self, exc):
            try:
                _orig_call_conn_lost(self, exc)
            except (ConnectionResetError, ConnectionAbortedError, OSError):
                pass
        _ProactorBasePipeTransport._call_connection_lost = _safe_call_conn_lost
    except Exception:
        pass

from PIL import Image, ImageTk
import qrcode
import uvicorn

LOG_FILE = os.path.join(os.path.expanduser("~"), "pcdeck_pro_debug.log")
from server.license_manager import verify_license, activate_license_online, save_license

def load_pc_license() -> dict:
    return verify_license()

def is_msix_packaged() -> bool:
    """Detect if running inside an MSIX / Windows Store package identity container."""
    if sys.platform != "win32":
        return False
    # Check 1: Infallible filesystem path check. Packaged apps always execute from WindowsApps directory
    exe = (sys.executable or "").lower()
    if "windowsapps" in exe or "gresonparichha.pcdeck" in exe:
        return True
    # Check 2: Win32 Package Identity API with allocated buffer
    try:
        import ctypes
        from ctypes import wintypes
        kernel32 = ctypes.windll.kernel32
        buf_len = wintypes.UINT(256)
        buf = ctypes.create_unicode_buffer(256)
        rc = kernel32.GetCurrentPackageFullName(ctypes.byref(buf_len), buf)
        if rc == 0 or (rc != 15700 and len(buf.value) > 0):
            return True
    except (Exception, OSError):
        pass
    return False

def is_first_run_startup_prompt_done() -> bool:
    """Checks whether the first-run 'Start with Windows' prompt has already been shown."""
    if is_msix_packaged():
        return True
    if sys.platform == "win32":
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\PCDeck", 0, winreg.KEY_READ)
            val, _ = winreg.QueryValueEx(key, "StartupPromptShown")
            winreg.CloseKey(key)
            if val == 1:
                return True
        except Exception:
            pass

    try:
        config_path = os.path.join(os.path.expanduser("~"), ".pcdeck", "app_settings.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return bool(data.get("startup_prompt_shown", False))
    except Exception:
        pass

    return False


def mark_first_run_startup_prompt_done():
    """Marks the first-run 'Start with Windows' prompt as completed so it does not reappear."""
    if is_msix_packaged():
        return
    if sys.platform == "win32":
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\PCDeck")
            winreg.SetValueEx(key, "StartupPromptShown", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
        except Exception:
            pass

    try:
        cfg_dir = os.path.join(os.path.expanduser("~"), ".pcdeck")
        os.makedirs(cfg_dir, exist_ok=True)
        config_path = os.path.join(cfg_dir, "app_settings.json")
        data = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        data["startup_prompt_shown"] = True
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def open_url_in_browser(url: str):
    """Reliably open a URL in the user's default browser on Windows."""
    try:
        os.startfile(url)
        return True
    except Exception:
        pass
    try:
        import webbrowser
        if webbrowser.open(url, new=2):
            return True
    except Exception:
        pass
    try:
        import subprocess
        subprocess.Popen(["cmd", "/c", "start", "", url], shell=True)
        return True
    except Exception:
        pass
    return False


DODO_CHECKOUT_URL = "https://checkout.dodopayments.com/buy/pdt_0Np7oiRe7Art1gb9IAx8K?quantity=1&redirect_url=https://getpcdeck.com&singlePage=true"


def load_app_settings() -> dict:
    """Loads ~/.pcdeck/app_settings.json safely."""
    try:
        config_path = os.path.join(os.path.expanduser("~"), ".pcdeck", "app_settings.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_app_settings(data: dict):
    """Saves ~/.pcdeck/app_settings.json safely."""
    try:
        cfg_dir = os.path.join(os.path.expanduser("~"), ".pcdeck")
        os.makedirs(cfg_dir, exist_ok=True)
        config_path = os.path.join(cfg_dir, "app_settings.json")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def get_recent_pcs() -> list:
    """Returns list of recently connected PCs from settings."""
    try:
        cfg = load_app_settings()
        return cfg.get("recent_pcs", [])
    except Exception:
        return []


def add_recent_pc(name: str, ip: str, port: str = "8000"):
    """Adds or updates a PC entry in recent connection history."""
    try:
        cfg = load_app_settings()
        recent = cfg.get("recent_pcs", [])
        recent = [p for p in recent if p.get("ip") != ip]
        recent.insert(0, {
            "name": name or f"PC ({ip})",
            "ip": ip,
            "port": str(port),
            "time": time.strftime("%b %d, %H:%M")
        })
        cfg["recent_pcs"] = recent[:8]
        save_app_settings(cfg)
    except Exception:
        pass


def get_or_init_review_state(increment_session: bool = False) -> dict:
    """
    Retrieves or initializes the 3-day review prompt tracking state.
    Increments session count if requested (on startup).
    """
    settings = load_app_settings()
    now = time.time()
    dirty = False

    if "first_run_timestamp" not in settings:
        settings["first_run_timestamp"] = now
        dirty = True

    if "session_count" not in settings:
        settings["session_count"] = 1
        dirty = True
    elif increment_session:
        settings["session_count"] = int(settings.get("session_count", 0)) + 1
        dirty = True

    if "review_prompt_status" not in settings:
        settings["review_prompt_status"] = "pending"  # "pending", "reviewed", "dismissed"
        dirty = True

    if "review_next_prompt_time" not in settings:
        settings["review_next_prompt_time"] = 0.0
        dirty = True

    if dirty:
        save_app_settings(settings)

    return settings


def check_should_show_review_prompt(settings: Optional[dict] = None, current_time: Optional[float] = None) -> bool:
    """
    Pure evaluation rule for showing the polite 3-day review prompt:
    1. Must be on Windows.
    2. Status must be 'pending' (not already reviewed or permanently dismissed).
    3. Current time must be >= review_next_prompt_time (not currently snoozed).
    4. At least 72 hours (3 days) elapsed since first_run_timestamp.
    5. At least 3 active sessions recorded.
    """
    if sys.platform != "win32":
        return False

    if settings is None:
        settings = load_app_settings()

    if settings.get("review_prompt_status") in ("reviewed", "dismissed"):
        return False

    now = current_time if current_time is not None else time.time()
    next_prompt = float(settings.get("review_next_prompt_time", 0.0))
    if now < next_prompt:
        return False

    first_run = float(settings.get("first_run_timestamp", now))
    # 72 hours = 259,200 seconds
    if (now - first_run) < (3 * 86400):
        return False

    sessions = int(settings.get("session_count", 0))
    if sessions < 3:
        return False

    return True


def record_review_action(action: str, days: Optional[int] = None):
    """
    Records the user's action on the review prompt:
    - 'reviewed': Launches store review and permanently silences prompt.
    - 'dismissed': Permanently silences prompt ('Don't show again').
    - 'snoozed': Postpones prompt for specified days (default 7 days).
    """
    settings = load_app_settings()
    now = time.time()
    if action == "reviewed":
        settings["review_prompt_status"] = "reviewed"
    elif action == "dismissed":
        settings["review_prompt_status"] = "dismissed"
    elif action == "snoozed":
        snooze_days = days if days is not None else 7
        settings["review_next_prompt_time"] = now + (snooze_days * 86400)
    save_app_settings(settings)




# ---------------------------------------------------------------------------
# Design tokens
#
# One accent, neutral surfaces, and saturated colour reserved for state. The
# previous palette ran five neons (cyan, lime, yellow, pink, orange) at full
# saturation against near-black, which is what made the client read as generic.
# Change a value here and it applies across every screen.
# ---------------------------------------------------------------------------
def get_windows_system_theme() -> str:
    """Returns 'dark' or 'light' based on Windows Personalize registry setting."""
    if sys.platform == "win32" and winreg:
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
                0,
                winreg.KEY_READ
            )
            val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return "light" if val == 1 else "dark"
        except Exception:
            pass
    return "dark"


THEME_DARK = {
    "C_BG": "#0d0f12",
    "C_SURFACE": "#14171d",
    "C_SURFACE_2": "#1b2029",
    "C_SURFACE_3": "#222733",
    "C_INPUT": "#101217",
    "C_BORDER": "#21262d",
    "C_BORDER_STRONG": "#30363d",
    "C_TEXT": "#f0f6fc",
    "C_TEXT_DIM": "#8b949e",
    "C_ACCENT": "#3b82f6",
    "C_ACCENT_HOVER": "#2563eb",
    "C_SUCCESS": "#10b981",
    "C_WARNING": "#f59e0b",
    "C_DANGER": "#ef4444",
    "C_TAB_ACTIVE_BG": "#1b2029",
    "C_TAB_ACTIVE_FG": "#f0f6fc",
    "C_TAB_INACTIVE_BG": "#14171d",
    "C_TAB_INACTIVE_FG": "#8b949e",
}

THEME_LIGHT = {
    "C_BG": "#eaecf0",
    "C_SURFACE": "#ffffff",
    "C_SURFACE_2": "#f3f5f8",
    "C_SURFACE_3": "#e2e6ec",
    "C_INPUT": "#ffffff",
    "C_BORDER": "#cbd5e1",
    "C_BORDER_STRONG": "#94a3b8",
    "C_TEXT": "#1f2328",
    "C_TEXT_DIM": "#57606a",
    "C_ACCENT": "#2563eb",
    "C_ACCENT_HOVER": "#1d4ed8",
    "C_SUCCESS": "#059669",
    "C_WARNING": "#d97706",
    "C_DANGER": "#dc2626",
    "C_TAB_ACTIVE_BG": "#ffffff",
    "C_TAB_ACTIVE_FG": "#1f2328",
    "C_TAB_INACTIVE_BG": "#e2e6ec",
    "C_TAB_INACTIVE_FG": "#57606a",
}

C_BG = THEME_DARK["C_BG"]
C_SURFACE = THEME_DARK["C_SURFACE"]
C_SURFACE_2 = THEME_DARK["C_SURFACE_2"]
C_SURFACE_3 = THEME_DARK["C_SURFACE_3"]
C_INPUT = THEME_DARK["C_INPUT"]
C_BORDER = THEME_DARK["C_BORDER"]
C_BORDER_STRONG = THEME_DARK["C_BORDER_STRONG"]
C_TEXT = THEME_DARK["C_TEXT"]
C_TEXT_DIM = THEME_DARK["C_TEXT_DIM"]
C_BLACK = "#000000"
C_ACCENT = THEME_DARK["C_ACCENT"]
C_ACCENT_HOVER = THEME_DARK["C_ACCENT_HOVER"]
C_SUCCESS = THEME_DARK["C_SUCCESS"]
C_WARNING = THEME_DARK["C_WARNING"]
C_DANGER = THEME_DARK["C_DANGER"]         # Stop / error crimson

CURRENT_DESKTOP_VERSION_CODE = 280
CURRENT_DESKTOP_VERSION_NAME = "2.8.0"

# Typography: one family, hierarchy carried by size and weight rather than
# setting everything to 8px bold.
F_FAMILY = "Segoe UI"
F_MONO = "Consolas"
F_TITLE = (F_FAMILY, 17, "bold")
F_HEADING = (F_FAMILY, 11, "bold")
F_LABEL = (F_FAMILY, 9, "bold")      # small caps section labels
F_BODY = (F_FAMILY, 9)
F_BODY_STRONG = (F_FAMILY, 9, "bold")
F_SUBHEAD = (F_FAMILY, 10, "bold")
F_SMALL = (F_FAMILY, 8)
F_SMALL_STRONG = (F_FAMILY, 8, "bold")
F_BUTTON = (F_FAMILY, 11, "bold")
F_BUTTON_LARGE = (F_FAMILY, 12, "bold")
F_BUTTON_SMALL = (F_FAMILY, 10, "bold")

# CustomTkinter Modern Component System (WebView2 Aesthetic with Native Performance)
try:
    import customtkinter as ctk
    HAS_CUSTOMTKINTER = True
except ImportError:
    ctk = None
    HAS_CUSTOMTKINTER = False

if HAS_CUSTOMTKINTER:
    class CTkModernFrame(ctk.CTkFrame):
        def __init__(self, master=None, **kwargs):
            if "bg" in kwargs:
                kwargs["fg_color"] = kwargs.pop("bg")
            if "bd" in kwargs:
                kwargs["border_width"] = kwargs.pop("bd")
            if "highlightbackground" in kwargs:
                kwargs["border_color"] = kwargs.pop("highlightbackground")
            if "highlightthickness" in kwargs:
                kwargs["border_width"] = kwargs.pop("highlightthickness")
            kwargs.pop("relief", None)
            if "corner_radius" not in kwargs:
                kwargs["corner_radius"] = 12
            if "fg_color" not in kwargs:
                kwargs["fg_color"] = C_SURFACE
            if "border_color" not in kwargs:
                kwargs["border_color"] = C_BORDER
            if "border_width" not in kwargs:
                kwargs["border_width"] = 1
            super().__init__(master, **kwargs)

        def configure(self, *args, **kwargs):
            if "bg" in kwargs:
                kwargs["fg_color"] = kwargs.pop("bg")
            if "bd" in kwargs:
                kwargs["border_width"] = kwargs.pop("bd")
            if "highlightbackground" in kwargs:
                kwargs["border_color"] = kwargs.pop("highlightbackground")
            if "highlightthickness" in kwargs:
                kwargs["border_width"] = kwargs.pop("highlightthickness")
            kwargs.pop("relief", None)
            super().configure(*args, **kwargs)

        def config(self, *args, **kwargs):
            self.configure(*args, **kwargs)

        def cget(self, attribute_name):
            if attribute_name == "bg":
                return self._fg_color
            if attribute_name in ("border_color", "highlightbackground"):
                return self._border_color
            if attribute_name in ("border_width", "highlightthickness", "bd"):
                return self._border_width
            return super().cget(attribute_name)

    class CTkModernButton(ctk.CTkButton):
        def __init__(self, master=None, **kwargs):
            if "bg" in kwargs:
                kwargs["fg_color"] = kwargs.pop("bg")
            if "fg" in kwargs:
                kwargs["text_color"] = kwargs.pop("fg")
            if "activebackground" in kwargs:
                kwargs["hover_color"] = kwargs.pop("activebackground")
            kwargs.pop("activeforeground", None)
            kwargs.pop("padx", None)
            kwargs.pop("pady", None)
            kwargs.pop("cursor", None)
            kwargs.pop("bd", None)
            kwargs.pop("relief", None)

            # Auto-resolve text_color if not provided (prevents white-on-white text in Light Mode)
            fg_col = kwargs.get("fg_color", None)
            if "text_color" not in kwargs:
                if fg_col in ("#3b82f6", "#2563eb", "#1d4ed8", "#10b981", "#059669", "#ef4444", "#dc2626"):
                    kwargs["text_color"] = "#ffffff"
                elif fg_col in ("#eab308", "#ffd700"):
                    kwargs["text_color"] = "#000000"
                else:
                    kwargs["text_color"] = C_TEXT

            # Auto-resolve hover_color if not provided
            if "hover_color" not in kwargs:
                if fg_col in ("#3b82f6", "#2563eb"):
                    kwargs["hover_color"] = C_ACCENT_HOVER
                elif fg_col in ("#ef4444", "#dc2626"):
                    kwargs["hover_color"] = "#b91c1c"
                elif fg_col in ("#10b981", "#059669"):
                    kwargs["hover_color"] = "#047857"
                else:
                    kwargs["hover_color"] = "#d8dee6" if C_TEXT in ("#1f2328", "#0f172a") else "#282e3a"

            if "corner_radius" not in kwargs:
                kwargs["corner_radius"] = 8
            if "font" not in kwargs:
                kwargs["font"] = F_BUTTON
            super().__init__(master, **kwargs)

            # Robust click bindings: eliminate dropped clicks on trackpads, touchscreens, and rapid clicks
            self.bind("<Button-1>", self._on_robust_press, add="+")
            self.bind("<Return>", self._on_robust_invoke, add="+")
            self.bind("<space>", self._on_robust_invoke, add="+")
            if hasattr(self, "_canvas") and self._canvas:
                self._canvas.bind("<Button-1>", self._on_robust_press, add="+")
            if hasattr(self, "_text_label") and self._text_label:
                self._text_label.bind("<Button-1>", self._on_robust_press, add="+")

        def _on_robust_press(self, event=None):
            self._mouse_inside = True

        def _on_robust_invoke(self, event=None):
            if self._state != tk.DISABLED and getattr(self, "_state", "") != "disabled":
                if self._command is not None:
                    self._command()

        def _on_release(self, event=None):
            # Override CustomTkinter's default _on_release: ensure click fires even if pointer jitter occurred
            if self._state != tk.DISABLED and getattr(self, "_state", "") != "disabled":
                try:
                    self._on_leave()
                    self._click_animation_running = True
                    self.after(80, self._click_animation)
                except Exception:
                    pass
                if self._command is not None:
                    self._command()

        def configure(self, *args, **kwargs):
            if "bg" in kwargs:
                kwargs["fg_color"] = kwargs.pop("bg")
            if "fg" in kwargs:
                kwargs["text_color"] = kwargs.pop("fg")
            if "activebackground" in kwargs:
                kwargs["hover_color"] = kwargs.pop("activebackground")
            kwargs.pop("activeforeground", None)
            kwargs.pop("padx", None)
            kwargs.pop("pady", None)
            kwargs.pop("cursor", None)
            kwargs.pop("bd", None)
            kwargs.pop("relief", None)

            if "fg_color" in kwargs and "hover_color" not in kwargs:
                fg_col = kwargs["fg_color"]
                if fg_col in ("#3b82f6", "#2563eb"):
                    kwargs["hover_color"] = C_ACCENT_HOVER
                elif fg_col in ("#ef4444", "#dc2626"):
                    kwargs["hover_color"] = "#b91c1c"
                elif fg_col in ("#10b981", "#059669"):
                    kwargs["hover_color"] = "#047857"
                else:
                    kwargs["hover_color"] = "#d8dee6" if C_TEXT in ("#1f2328", "#0f172a") else "#282e3a"

            super().configure(*args, **kwargs)

            if hasattr(self, "_text_label") and self._text_label:
                self._text_label.bind("<Button-1>", self._on_robust_press, add="+")

        def config(self, *args, **kwargs):
            self.configure(*args, **kwargs)

        def cget(self, attribute_name):
            if attribute_name == "bg":
                return self._fg_color
            if attribute_name == "fg":
                return self._text_color
            if attribute_name == "state":
                return self._state
            return super().cget(attribute_name)

    class CTkModernLabel(ctk.CTkLabel):
        def __init__(self, master=None, **kwargs):
            if "bg" in kwargs:
                kwargs["fg_color"] = kwargs.pop("bg")
            if "fg" in kwargs:
                kwargs["text_color"] = kwargs.pop("fg")
            kwargs.pop("bd", None)
            kwargs.pop("relief", None)
            if "fg_color" not in kwargs:
                kwargs["fg_color"] = "transparent"
            if "text_color" not in kwargs:
                kwargs["text_color"] = C_TEXT
            super().__init__(master, **kwargs)

        def configure(self, *args, **kwargs):
            if "bg" in kwargs:
                kwargs["fg_color"] = kwargs.pop("bg")
            if "fg" in kwargs:
                kwargs["text_color"] = kwargs.pop("fg")
            kwargs.pop("bd", None)
            kwargs.pop("relief", None)
            super().configure(*args, **kwargs)

        def config(self, *args, **kwargs):
            self.configure(*args, **kwargs)

        def cget(self, attribute_name):
            if attribute_name == "bg":
                return self._fg_color
            if attribute_name == "fg":
                return self._text_color
            return super().cget(attribute_name)

else:
    class CTkModernFrame(tk.Frame):
        def __init__(self, master=None, **kwargs):
            if "fg_color" in kwargs:
                kwargs["bg"] = kwargs.pop("fg_color")
            if "border_color" in kwargs:
                kwargs["highlightbackground"] = kwargs.pop("border_color")
            if "border_width" in kwargs:
                kwargs["highlightthickness"] = kwargs.pop("border_width")
            kwargs.pop("corner_radius", None)
            super().__init__(master, **kwargs)

        def configure(self, *args, **kwargs):
            if "fg_color" in kwargs:
                kwargs["bg"] = kwargs.pop("fg_color")
            if "border_color" in kwargs:
                kwargs["highlightbackground"] = kwargs.pop("border_color")
            if "border_width" in kwargs:
                kwargs["highlightthickness"] = kwargs.pop("border_width")
            kwargs.pop("corner_radius", None)
            super().configure(*args, **kwargs)

        def config(self, *args, **kwargs):
            self.configure(*args, **kwargs)

    class CTkModernButton(tk.Button):
        def __init__(self, master=None, **kwargs):
            if "fg_color" in kwargs:
                kwargs["bg"] = kwargs.pop("fg_color")
            if "text_color" in kwargs:
                kwargs["fg"] = kwargs.pop("text_color")
            if "hover_color" in kwargs:
                kwargs["activebackground"] = kwargs.pop("hover_color")
            kwargs.pop("corner_radius", None)
            kwargs.setdefault("relief", "flat")
            super().__init__(master, **kwargs)

        def configure(self, *args, **kwargs):
            if "fg_color" in kwargs:
                kwargs["bg"] = kwargs.pop("fg_color")
            if "text_color" in kwargs:
                kwargs["fg"] = kwargs.pop("text_color")
            if "hover_color" in kwargs:
                kwargs["activebackground"] = kwargs.pop("hover_color")
            kwargs.pop("corner_radius", None)
            super().configure(*args, **kwargs)

        def config(self, *args, **kwargs):
            self.configure(*args, **kwargs)

    class CTkModernLabel(tk.Label):
        def __init__(self, master=None, **kwargs):
            if "fg_color" in kwargs:
                kwargs["bg"] = kwargs.pop("fg_color")
            if "text_color" in kwargs:
                kwargs["fg"] = kwargs.pop("text_color")
            kwargs.pop("corner_radius", None)
            super().__init__(master, **kwargs)

        def configure(self, *args, **kwargs):
            if "fg_color" in kwargs:
                kwargs["bg"] = kwargs.pop("fg_color")
            if "text_color" in kwargs:
                kwargs["fg"] = kwargs.pop("text_color")
            kwargs.pop("corner_radius", None)
            super().configure(*args, **kwargs)

        def config(self, *args, **kwargs):
            self.configure(*args, **kwargs)


CRASH_LOG_FILE = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "PCDeck", "crash.log")
try:
    os.makedirs(os.path.dirname(CRASH_LOG_FILE), exist_ok=True)
except Exception:
    pass

def log_debug(msg: str):
    line = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n"
    for p in (LOG_FILE, CRASH_LOG_FILE):
        try:
            with open(p, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass

def global_excepthook(exc_type, exc_value, exc_tb):
    header = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] UNCAUGHT EXCEPTION:\n"
    for p in (LOG_FILE, CRASH_LOG_FILE):
        try:
            with open(p, "a", encoding="utf-8") as f:
                f.write(header)
                traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
        except Exception:
            pass

sys.excepthook = global_excepthook

def thread_excepthook(args):
    try:
        global_excepthook(args.exc_type, args.exc_value, args.exc_traceback)
    except Exception:
        pass

if hasattr(threading, "excepthook"):
    threading.excepthook = thread_excepthook

# Windows High-DPI Awareness & Taskbar AppID Registration (Must be called BEFORE any Tk window is created)
if sys.platform == "win32":
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass
        # In MSIX, OS assigns AUMID automatically from AppxManifest. Calling this inside MSIX can trigger MoAppCrash!
        if not is_msix_packaged():
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("PCDeckPro.DesktopClient.Pro.v2026")
            except Exception:
                pass
    except Exception:
        pass

# Ensure search paths and working directory
if getattr(sys, "frozen", False):
    if not is_msix_packaged():
        try:
            os.chdir(os.path.dirname(sys.executable))
        except Exception:
            pass
    else:
        # MSIX Centennial sandbox: switch to user-writable directory to prevent PermissionError
        safe_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "PCDeck")
        try:
            os.makedirs(safe_dir, exist_ok=True)
            os.chdir(safe_dir)
        except Exception:
            pass
    current_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
else:
    current_dir = os.path.dirname(os.path.abspath(__file__))

parent_dir = os.path.dirname(current_dir)
for p in [current_dir, parent_dir]:
    if p and p not in sys.path:
        sys.path.insert(0, p)

try:
    from server.main import (
        LOCAL_IP,
        SERVER_PORT,
        SERVER_URL,
        TRANSFER_DIR,
        app,
        controller,
        streamer,
        get_adb_path,
        get_scrcpy_path,
        launch_scrcpy,
        get_connected_devices,
        adb_preflight,
        check_adb_connected,
        get_device_resolution,
        get_device_ip,
        switch_device_to_wireless,
        get_pairing_token,
        get_local_ip,
    )
except ImportError:
    from main import (
        LOCAL_IP,
        SERVER_PORT,
        SERVER_URL,
        TRANSFER_DIR,
        app,
        controller,
        streamer,
        get_adb_path,
        get_scrcpy_path,
        launch_scrcpy,
        get_connected_devices,
        adb_preflight,
        check_adb_connected,
        get_device_resolution,
        get_device_ip,
        switch_device_to_wireless,
        get_pairing_token,
        get_local_ip,
    )

try:
    from server.wifi_manager import (
        get_current_wifi_status,
        get_saved_profiles,
        scan_visible_networks,
        connect_to_profile,
        auto_reconnect_known_networks,
        load_wifi_config,
        save_wifi_config,
        update_wifi_config,
        start_watchdog,
        stop_watchdog,
        restore_all_wlan_autoconfig,
        ensure_wifi_radio_on,
    )
except ImportError:
    from wifi_manager import (
        get_current_wifi_status,
        get_saved_profiles,
        scan_visible_networks,
        connect_to_profile,
        auto_reconnect_known_networks,
        load_wifi_config,
        save_wifi_config,
        update_wifi_config,
        wait_for_usable_link,
        renew_dhcp,
        restore_all_wlan_autoconfig,
        ensure_wifi_radio_on,
    )

try:
    from server.wifi_latency_manager import wifi_latency_manager
except ImportError:
    try:
        from wifi_latency_manager import wifi_latency_manager
    except ImportError:
        wifi_latency_manager = None


def get_asset_search_dirs():
    """Return all valid directories where application assets might be located."""
    dirs = []
    
    # 1. PyInstaller _MEIPASS directory (extracted bundle)
    meipass = getattr(sys, "_MEIPASS", "")
    if meipass:
        dirs.append(meipass)
        dirs.append(os.path.join(meipass, "static"))
        dirs.append(os.path.join(meipass, "assets"))

    # 2. Executable directory (for frozen or standard runs)
    if getattr(sys, "frozen", False) and sys.executable:
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        dirs.append(exe_dir)
        dirs.append(os.path.join(exe_dir, "static"))
        dirs.append(os.path.join(exe_dir, "assets"))

    # 3. Source script directory & parent directory
    file_dir = os.path.dirname(os.path.abspath(__file__))
    dirs.append(file_dir)
    dirs.append(os.path.join(file_dir, "static"))
    dirs.append(os.path.join(file_dir, "assets"))

    parent = os.path.dirname(file_dir)
    dirs.append(parent)
    dirs.append(os.path.join(parent, "static"))
    dirs.append(os.path.join(parent, "assets"))

    # 4. Current working directory
    try:
        cwd = os.getcwd()
        dirs.append(cwd)
        dirs.append(os.path.join(cwd, "static"))
        dirs.append(os.path.join(cwd, "assets"))
    except Exception:
        pass

    # Deduplicate while preserving order
    seen = set()
    valid_dirs = []
    for d in dirs:
        try:
            norm = os.path.normpath(d)
            if norm not in seen and os.path.isdir(norm):
                seen.add(norm)
                valid_dirs.append(norm)
        except Exception:
            pass
    return valid_dirs


def find_asset(*candidate_names):
    """Find the first existing asset matching any of the candidate filenames."""
    for d in get_asset_search_dirs():
        for name in candidate_names:
            try:
                candidate_path = os.path.join(d, name)
                if os.path.isfile(candidate_path):
                    return os.path.abspath(candidate_path)
            except Exception:
                pass
    return None


def apply_crisp_window_icon(window):
    """
    Sets high-DPI crystal-sharp icon for Window title bar, Alt+Tab switcher, and Windows Taskbar.
    Directly interfaces with Win32 WM_SETICON, SetClassLongPtrW (with 64-bit ctypes argtypes),
    and SetWindowPos on all native HWNDs (frame + child + ancestors) to ensure Windows 11 Taskbar never shows Tk feather.
    """
    try:
        # Ensure Tkinter geometry / wrapper frame is initialized
        try:
            window.update_idletasks()
        except Exception:
            pass

        ico_file = find_asset(
            "app_icon.ico",
            "PCDeck.ico",
            "icon.ico",
            "favicon.ico",
        )
        if ico_file:
            ico_abs = os.path.abspath(ico_file)
            try:
                window.iconbitmap(default=ico_abs)
            except Exception:
                pass
            try:
                window.iconbitmap(ico_abs)
            except Exception:
                pass

        # Load multi-res PNG photos for Tkinter window iconphoto (Alt+Tab & Window manager)
        png_file = find_asset(
            "PCDeck_Mouse_Logo.png",
            "PCDeck_Master_Logo.png",
            "PCDeck_Logo.png",
            "icon-512.png",
            "icon.png",
            "favicon.png",
        )
        if png_file:
            try:
                base_img = Image.open(png_file)
                photos = []
                for s in [16, 20, 24, 32, 40, 48, 64, 128, 256]:
                    resized = base_img.resize((s, s), Image.Resampling.LANCZOS)
                    photos.append(ImageTk.PhotoImage(resized))
                window.iconphoto(True, *photos)
                window._crisp_icons = photos
            except Exception as e:
                log_debug(f"iconphoto setting error: {e}")

        if sys.platform == "win32" and ico_file:
            ico_abs = os.path.abspath(ico_file)

            def _inject_win32_icons():
                try:
                    import ctypes
                    user32 = ctypes.windll.user32

                    hwnd_child = window.winfo_id()
                    hwnd_frame = None
                    try:
                        frame_str = window.wm_frame()
                        if frame_str:
                            hwnd_frame = int(frame_str, 16)
                    except Exception:
                        hwnd_frame = None

                    hwnd_ancestor_root = None
                    hwnd_ancestor_owner = None
                    try:
                        hwnd_ancestor_root = user32.GetAncestor(hwnd_child, 2)   # GA_ROOT = 2
                    except Exception:
                        pass
                    try:
                        hwnd_ancestor_owner = user32.GetAncestor(hwnd_child, 3)  # GA_ROOTOWNER = 3
                    except Exception:
                        pass

                    hwnd_parent = None
                    try:
                        hwnd_parent = user32.GetParent(hwnd_child)
                    except Exception:
                        pass

                    hwnds = {h for h in [hwnd_frame, hwnd_child, hwnd_ancestor_root, hwnd_ancestor_owner, hwnd_parent] if h}

                    IMAGE_ICON = 1
                    LR_LOADFROMFILE = 0x00000010
                    WM_SETICON = 0x0080
                    ICON_BIG = 1
                    ICON_SMALL = 0
                    GCLP_HICON = -14
                    GCLP_HICONSM = -34
                    SWP_FLAGS = 0x0020 | 0x0002 | 0x0001 | 0x0004  # SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER

                    # Exact system icon dimensions for current monitor DPI
                    cx_big = user32.GetSystemMetrics(11) or 32     # SM_CXICON
                    cy_big = user32.GetSystemMetrics(12) or 32     # SM_CYICON
                    cx_small = user32.GetSystemMetrics(49) or 16   # SM_CXSMICON
                    cy_small = user32.GetSystemMetrics(50) or 16   # SM_CYSMICON

                    LoadImageW = user32.LoadImageW
                    LoadImageW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
                    LoadImageW.restype = ctypes.c_void_p

                    SendMessageW = user32.SendMessageW
                    SendMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
                    SendMessageW.restype = ctypes.c_void_p

                    SetClassLongPtr = getattr(user32, "SetClassLongPtrW", None) or getattr(user32, "SetClassLongW", None)
                    if SetClassLongPtr:
                        SetClassLongPtr.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
                        SetClassLongPtr.restype = ctypes.c_void_p

                    hicon_big = LoadImageW(None, ico_abs, IMAGE_ICON, cx_big, cy_big, LR_LOADFROMFILE)
                    hicon_small = LoadImageW(None, ico_abs, IMAGE_ICON, cx_small, cy_small, LR_LOADFROMFILE)

                    for h in hwnds:
                        if hicon_big:
                            SendMessageW(h, WM_SETICON, ICON_BIG, hicon_big)
                            if SetClassLongPtr:
                                try:
                                    SetClassLongPtr(h, GCLP_HICON, hicon_big)
                                except Exception:
                                    pass
                        if hicon_small:
                            SendMessageW(h, WM_SETICON, ICON_SMALL, hicon_small)
                            if SetClassLongPtr:
                                try:
                                    SetClassLongPtr(h, GCLP_HICONSM, hicon_small)
                                except Exception:
                                    pass
                        try:
                            user32.SetWindowPos(h, None, 0, 0, 0, 0, SWP_FLAGS)
                        except Exception:
                            pass
                except Exception as e:
                    log_debug(f"Win32 icon injection warning: {e}")

            _inject_win32_icons()
            window.after(10, _inject_win32_icons)
            window.after(50, _inject_win32_icons)
            window.after(200, _inject_win32_icons)
            window.after(600, _inject_win32_icons)
            try:
                window.bind("<Map>", lambda e: _inject_win32_icons(), add="+")
            except Exception:
                pass
    except Exception as e:
        log_debug(f"apply_crisp_window_icon error: {e}")


class PCDeckProGUI:
    def __init__(self, root: tk.Tk, start_minimized: bool = False):
        self.root = root
        self.start_minimized = start_minimized
        self.root.title(f"PCDeck v{CURRENT_DESKTOP_VERSION_NAME} - Wireless PC Touch Deck & Streamer")
        try:
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            rx = max(0, (sw - 960) // 2)
            ry = max(0, (sh - 640) // 2)
            self.root.geometry(f"960x640+{rx}+{ry}")
        except Exception:
            self.root.geometry("960x640")
        self.root.minsize(920, 600)
        self.root.configure(bg=C_BG)

        # Set Window Icon for Titlebar, Taskbar, and Alt-Tab
        apply_crisp_window_icon(self.root)

        master_png = find_asset(
            "PCDeck_Mouse_Logo.png",
            "PCDeck_Master_Logo.png",
            "PCDeck_Logo.png",
            "icon.png",
            "favicon.png",
        )
        if master_png:
            try:
                self.logo_img = Image.open(master_png)
                self.logo_photo = ImageTk.PhotoImage(self.logo_img.resize((36, 36), Image.Resampling.LANCZOS))
            except Exception as e:
                log_debug(f"Error loading logo_photo: {e}")
                self.logo_photo = None
        else:
            self.logo_photo = None

        # Server Handle & Telemetry
        self.server: Optional[uvicorn.Server] = None
        self.server_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.start_time = time.time()

        # State Variables
        # Theme State
        self.theme_pref = self._load_theme_pref()
        self._apply_theme_tokens()
        self.current_tab = "connect"
        self.root.configure(bg=self.c_bg)

        self.autostart_enabled = self.check_autostart_registry()
        self.start_boot_var = tk.BooleanVar(value=self.autostart_enabled)
        self.reconnect_var = tk.StringVar(value="auto")
        self.fps_var = tk.StringVar(value="30")
        self.qr_photo = None
        self.active_serial = ""
        self.active_model = ""
        self.phone_remote_win = None

        # Wi-Fi Auto-Reconnector Configuration
        self.wifi_config = load_wifi_config()
        self.auto_wifi_var = tk.BooleanVar(value=self.wifi_config.get("auto_reconnect_on_launch", False))
        self._update_prompt_shown = False

        # Pro License State
        self.license_info = load_pc_license()
        self.is_pc_pro = self.license_info.get("pro_active", False)
        if self.is_pc_pro:
            try:
                from server.main import set_pro_client
                set_pro_client(True)
            except Exception:
                pass
            self.root.title(f"PCDeck Pro v{CURRENT_DESKTOP_VERSION_NAME} - Wireless PC Touch Deck & Streamer")
        else:
            self.root.title("PCDeck - Wireless PC Touch Deck & Streamer")
            # If inactive but a stored license exists on disk, attempt silent recovery in background
            def _async_license_heal():
                try:
                    from server.license_manager import try_silent_license_recovery
                    if try_silent_license_recovery():
                        self.root.after(0, self._apply_pro_state)
                except Exception:
                    pass
            threading.Thread(target=_async_license_heal, daemon=True).start()

        # 3-Day Polite Store Review Tracking
        self.review_state = get_or_init_review_state(increment_session=True)
        self.review_card = None

        if not is_msix_packaged():
            self._cleanup_legacy_autostart()
        else:
            self._cleanup_msix_rogue_shortcuts()
        self._build_ui()
        self.start_server()

        # Non-blocking metrics cache and background worker (Zero UI thread stalls)
        self._cached_ip = getattr(self, "current_ip", LOCAL_IP)
        self._cached_wifi_status = {"state": "connected", "ssid": "", "signal": "0%"}
        self._cached_pro_active = self.is_pc_pro
        self._metrics_bg_thread = threading.Thread(
            target=self._metrics_bg_worker, daemon=True, name="PCDeck-MetricsWorker"
        )
        self._metrics_bg_thread.start()

        self._init_wifi_reconnector()
        self._start_metrics_loop()

        # Connect driver progress notifications from backend
        try:
            from server.main import set_driver_progress_callback
            set_driver_progress_callback(self.on_driver_progress)
        except Exception:
            pass

        # System Tray & Background Service Integration
        self._tray_minimized_notified = False
        self.flyout = None
        self.tray_icon = None
        self._init_tray_icon()

        # Ensure elevated autostart task is registered and synced if enabled (Win32 standalone only)
        if self.autostart_enabled and not is_msix_packaged():
            threading.Thread(target=self._ensure_autostart_task_scheduler, daemon=True).start()

        if self.start_minimized:
            self.root.withdraw()
            try:
                self.show_notification(
                    "PCDeck is running quietly in the tray. Ready to connect.",
                    "PCDeck Server Active",
                )
            except Exception:
                pass
        else:
            # First-run onboarding: Prompt user to enable Start with Windows (Win32 standalone only)
            if not is_msix_packaged():
                self.root.after(700, self._check_first_run_startup_prompt)

        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)

        # Schedule polite Windows review notification check (60s after launch)
        self.root.after(60000, self._dispatch_scheduled_review_notification)

        # Silent version/active check (daemon thread, zero UI impact, 100% offline-tolerant)
        threading.Thread(target=self._silent_update_ping, daemon=True, name="PCDeck-UpdatePing").start()

    def _silent_update_ping(self):
        if is_msix_packaged():
            # Microsoft Store automatically handles updates for Store packages
            return
        time.sleep(2.0)  # Let UI initialize completely first
        while True:
            try:
                req = urllib.request.Request(
                    "https://getpcdeck.com/api/version/",
                    headers={"User-Agent": f"PCDeck-Desktop/{CURRENT_DESKTOP_VERSION_NAME} (Windows)"}
                )
                with urllib.request.urlopen(req, timeout=4.0) as resp:
                    if resp.status == 200:
                        try:
                            raw = resp.read().decode("utf-8")
                            data = json.loads(raw)
                            remote_code = int(data.get("versionCode", 0))
                            if remote_code > CURRENT_DESKTOP_VERSION_CODE and not self._update_prompt_shown:
                                self._update_prompt_shown = True
                                self.root.after(500, lambda d=data: self._show_update_available_dialog(d))
                        except Exception:
                            pass
                        # Successful check; sleep 4 hours before checking again
                        time.sleep(14400)
                        continue
            except Exception:
                pass
            # If offline / failed, retry quietly after 3 minutes
            time.sleep(180)

    def _show_update_available_dialog(self, data: dict):
        """Shows a small, clean cyber-styled dialog notifying the user an update is available."""
        try:
            remote_name = data.get("versionName", "New Version")
            download_url = data.get("websiteUrl", "https://getpcdeck.com")
            if "#download" not in download_url:
                download_url = download_url.rstrip("/") + "/#download-cards"

            dlg = tk.Toplevel(self.root)
            dlg.withdraw()
            dlg.title("PCDeck — Update Available")
            dlg.resizable(False, False)
            dlg.configure(bg=C_SURFACE)
            if not self.start_minimized and self.root.winfo_viewable():
                dlg.transient(self.root)

            apply_crisp_window_icon(dlg)

            dw = 440
            dh = 260
            try:
                sw = self.root.winfo_screenwidth()
                sh = self.root.winfo_screenheight()
                x = max(0, (sw - dw) // 2)
                y = max(0, (sh - dh) // 2)
                dlg.geometry(f"{dw}x{dh}+{x}+{y}")
            except Exception:
                dlg.geometry(f"{dw}x{dh}")

            pad = tk.Frame(dlg, bg=C_SURFACE, padx=22, pady=18)
            pad.pack(fill="both", expand=True)

            # Top Badge
            badge_row = tk.Frame(pad, bg=C_SURFACE)
            badge_row.pack(fill="x", pady=(0, 6))
            badge = tk.Label(
                badge_row,
                text="  UPDATE AVAILABLE  ",
                font=(F_FAMILY, 8, "bold"),
                fg=C_BLACK,
                bg=C_ACCENT,
                padx=6,
                pady=2,
            )
            badge.pack(side="left")

            # Title
            title_lbl = tk.Label(
                pad,
                text=f"PCDeck v{remote_name} is Available",
                font=(F_FAMILY, 13, "bold"),
                fg=C_TEXT,
                bg=C_SURFACE,
                anchor="w",
            )
            title_lbl.pack(fill="x", pady=(4, 6))

            # Body description
            msg_text = f"A newer version of PCDeck (v{remote_name}) is ready for download.\n\nWould you like to visit the download page to update now?"
            body_lbl = tk.Label(
                pad,
                text=msg_text,
                font=F_BODY,
                fg=C_TEXT_DIM,
                bg=C_SURFACE,
                justify="left",
                wraplength=390,
            )
            body_lbl.pack(fill="x", pady=(0, 16))

            # Buttons Row
            btn_row = tk.Frame(pad, bg=C_SURFACE)
            btn_row.pack(fill="x", side="bottom")

            def _on_download():
                try:
                    webbrowser.open(download_url)
                except Exception:
                    pass
                dlg.destroy()

            def _on_later():
                dlg.destroy()

            dl_btn = tk.Button(
                btn_row,
                text="Visit Download Page →",
                font=(F_FAMILY, 9, "bold"),
                fg="#ffffff",
                bg="#1b44d8",
                activeforeground="#ffffff",
                activebackground="#1436b0",
                bd=0,
                padx=16,
                pady=7,
                cursor="hand2",
                command=_on_download,
            )
            dl_btn.pack(side="right", padx=(8, 0))

            later_btn = tk.Button(
                btn_row,
                text="Later",
                font=F_BODY,
                fg=C_TEXT_DIM,
                bg=C_SURFACE_2,
                activeforeground=C_TEXT,
                activebackground=C_SURFACE_3,
                bd=0,
                padx=14,
                pady=7,
                cursor="hand2",
                command=_on_later,
            )
            later_btn.pack(side="right")

            dlg.deiconify()
            dlg.lift()
            dlg.attributes("-topmost", True)
            dlg.after(200, lambda: dlg.attributes("-topmost", False))
            dlg.focus_force()

        except Exception as e:
            log_debug(f"Failed to display update dialog: {e}")

    def _load_theme_pref(self) -> str:
        try:
            cfg = load_app_settings()
            return cfg.get("theme", "system")
        except Exception:
            return "system"

    def _apply_theme_tokens(self):
        pref = getattr(self, "theme_pref", "system")
        if pref == "system":
            mode = get_windows_system_theme()
            tokens = THEME_LIGHT if mode == "light" else THEME_DARK
        elif pref == "light":
            tokens = THEME_LIGHT
        else:
            tokens = THEME_DARK

        self.c_bg = tokens["C_BG"]
        self.c_surface = tokens["C_SURFACE"]
        self.c_surface_2 = tokens["C_SURFACE_2"]
        self.c_surface_3 = tokens["C_SURFACE_3"]
        self.c_input = tokens["C_INPUT"]
        self.c_border = tokens["C_BORDER"]
        self.c_border_strong = tokens["C_BORDER_STRONG"]
        self.c_text = tokens["C_TEXT"]
        self.c_text_dim = tokens["C_TEXT_DIM"]
        self.c_accent = tokens["C_ACCENT"]
        self.c_accent_hover = tokens["C_ACCENT_HOVER"]
        self.c_success = tokens["C_SUCCESS"]
        self.c_warning = tokens["C_WARNING"]
        self.c_danger = tokens["C_DANGER"]
        self.c_tab_active_bg = tokens["C_TAB_ACTIVE_BG"]
        self.c_tab_active_fg = tokens["C_TAB_ACTIVE_FG"]
        self.c_tab_inactive_bg = tokens["C_TAB_INACTIVE_BG"]
        self.c_tab_inactive_fg = tokens["C_TAB_INACTIVE_FG"]

        # Synchronize module-level design token globals so all cards, badges, and dialogs adapt cleanly
        global C_BG, C_SURFACE, C_SURFACE_2, C_SURFACE_3, C_INPUT, C_BORDER, C_BORDER_STRONG, C_TEXT, C_TEXT_DIM, C_ACCENT, C_ACCENT_HOVER, C_SUCCESS, C_WARNING, C_DANGER
        C_BG = self.c_bg
        C_SURFACE = self.c_surface
        C_SURFACE_2 = self.c_surface_2
        C_SURFACE_3 = self.c_surface_3
        C_INPUT = self.c_input
        C_BORDER = self.c_border
        C_BORDER_STRONG = self.c_border_strong
        C_TEXT = self.c_text
        C_TEXT_DIM = self.c_text_dim
        C_ACCENT = self.c_accent
        C_ACCENT_HOVER = self.c_accent_hover
        C_SUCCESS = self.c_success
        C_WARNING = self.c_warning
        C_DANGER = self.c_danger

        if HAS_CUSTOMTKINTER:
            try:
                ctk.set_appearance_mode("Light" if tokens == THEME_LIGHT else "Dark")
            except Exception:
                pass

    def set_theme(self, pref: str):
        """Sets the color theme preference ('system', 'dark', 'light') and rebuilds UI cleanly."""
        if pref not in ("system", "dark", "light"):
            pref = "system"
        self.theme_pref = pref
        cfg = load_app_settings()
        cfg["theme"] = pref
        save_app_settings(cfg)
        self._apply_theme_tokens()
        # Reset CustomTkinter master.configure monkeypatch to prevent dead widget callbacks
        self.root.configure = tk.Tk.configure.__get__(self.root, tk.Tk)
        self.root.config = tk.Tk.config.__get__(self.root, tk.Tk)
        tk.Tk.configure(self.root, bg=self.c_bg)

        if hasattr(self, "theme_combo_var") and self.theme_combo_var:
            self.theme_combo_var.set("Light Mode" if pref == "light" else ("Dark Mode" if pref == "dark" else "Follow Windows (Auto)"))

        # Release any active mouse/event grab before rebuilding widgets
        try:
            self.root.grab_release()
        except Exception:
            pass

        curr_tab = getattr(self, "current_tab", "settings")
        self.root.after(30, lambda: self._rebuild_ui_for_theme(curr_tab))

    def on_theme_change(self, event=None):
        val = getattr(self, "theme_combo_var", None)
        if not val:
            return
        v = val.get()
        if "Auto" in v or "Follow" in v:
            pref = "system"
        elif "Light" in v:
            pref = "light"
        else:
            pref = "dark"
        self.set_theme(pref)

    def _rebuild_ui_for_theme(self, curr_tab: str):
        try:
            self.root.grab_release()
        except Exception:
            pass
        # Unhook CustomTkinter monkeypatch before destroying children
        self.root.configure = tk.Tk.configure.__get__(self.root, tk.Tk)
        self.root.config = tk.Tk.config.__get__(self.root, tk.Tk)
        for child in list(self.root.winfo_children()):
            if isinstance(child, tk.Toplevel):
                continue
            try:
                child.destroy()
            except Exception:
                pass
        # Unhook CustomTkinter monkeypatch after destroying dead widgets
        self.root.configure = tk.Tk.configure.__get__(self.root, tk.Tk)
        self.root.config = tk.Tk.config.__get__(self.root, tk.Tk)
        tk.Tk.configure(self.root, bg=self.c_bg)
        self._build_ui()
        self._switch_tab(curr_tab)

    def toggle_audio_stream(self):
        try:
            try:
                from server.main import audio_streamer
            except ImportError:
                from main import audio_streamer
            curr = getattr(audio_streamer, "is_running", False)
            if curr:
                audio_streamer.stop()
                if hasattr(self, "audio_status_lbl") and self.audio_status_lbl and self.audio_status_lbl.winfo_exists():
                    self.audio_status_lbl.config(text="OFF", fg=self.c_text_dim, bg=self.c_surface_3)
                if hasattr(self, "btn_toggle_audio") and self.btn_toggle_audio and self.btn_toggle_audio.winfo_exists():
                    self.btn_toggle_audio.config(text="START AUDIO STREAM", bg=self.c_surface_3, fg=self.c_text)
            else:
                audio_streamer.start()
                if hasattr(self, "audio_status_lbl") and self.audio_status_lbl and self.audio_status_lbl.winfo_exists():
                    self.audio_status_lbl.config(text="ACTIVE", fg=self.c_success, bg=self.c_surface_3)
                if hasattr(self, "btn_toggle_audio") and self.btn_toggle_audio and self.btn_toggle_audio.winfo_exists():
                    self.btn_toggle_audio.config(text="STOP AUDIO STREAM", bg=self.c_danger, fg="#ffffff")
        except Exception as e:
            log_debug(f"toggle_audio_stream error: {e}")

    def _configure_ttk_styles(self):
        try:
            style = ttk.Style()
            style.theme_use("clam")
            style.configure(
                "Deck.TCombobox",
                fieldbackground=self.c_input,
                background=self.c_surface_3,
                foreground=self.c_text,
                darkcolor=self.c_input,
                lightcolor=self.c_border,
                selectbackground=self.c_accent,
                selectforeground="#ffffff",
                arrowcolor=self.c_accent,
                bordercolor=self.c_border,
                padding=4,
            )
            style.map(
                "Deck.TCombobox",
                fieldbackground=[("readonly", self.c_input), ("active", self.c_surface_2), ("!disabled", self.c_input)],
                background=[("readonly", self.c_surface_3), ("active", self.c_border), ("!disabled", self.c_surface_3)],
                foreground=[("readonly", self.c_text), ("active", self.c_text), ("!disabled", self.c_text)],
                selectbackground=[("readonly", self.c_accent)],
                selectforeground=[("readonly", "#ffffff")],
            )
            self.root.option_add("*TCombobox*Listbox.background", self.c_input)
            self.root.option_add("*TCombobox*Listbox.foreground", self.c_text)
            self.root.option_add("*TCombobox*Listbox.selectBackground", self.c_accent)
            self.root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
        except Exception:
            pass

    def _switch_tab(self, tab_key: str):
        self.current_tab = tab_key
        for t in [getattr(self, "tab_connect", None), getattr(self, "tab_tools", None), getattr(self, "tab_settings", None)]:
            if t and t.winfo_exists():
                t.pack_forget()

        if hasattr(self, "tab_buttons"):
            for k, btn in self.tab_buttons.items():
                if not btn.winfo_exists():
                    continue
                if k == tab_key:
                    btn.config(
                        bg=self.c_tab_active_bg,
                        fg=self.c_tab_active_fg,
                        activebackground=self.c_tab_active_bg,
                        activeforeground=self.c_tab_active_fg,
                    )
                else:
                    btn.config(
                        bg=self.c_tab_inactive_bg,
                        fg=self.c_tab_inactive_fg,
                        activebackground=self.c_tab_inactive_bg,
                        activeforeground=self.c_tab_inactive_fg,
                    )

        if tab_key == "connect" and hasattr(self, "tab_connect") and self.tab_connect.winfo_exists():
            self.tab_connect.pack(fill="both", expand=True)
        elif tab_key == "tools" and hasattr(self, "tab_tools") and self.tab_tools.winfo_exists():
            self.tab_tools.pack(fill="both", expand=True)
        elif tab_key == "settings" and hasattr(self, "tab_settings") and self.tab_settings.winfo_exists():
            self.tab_settings.pack(fill="both", expand=True)

    def _build_ui(self):
        self._configure_ttk_styles()

        # 1. Top Modern Header Bar
        header = CTkModernFrame(
            self.root,
            bg=self.c_surface,
            corner_radius=12,
            highlightbackground=self.c_border,
            highlightthickness=1,
            height=58,
        )
        header.pack(fill="x", padx=16, pady=(12, 6))
        self.header_frame = header

        brand_frame = tk.Frame(header, bg=self.c_surface)
        brand_frame.pack(side="left", padx=14, pady=10)

        # Brand Icon Badge
        if not getattr(self, "logo_photo", None):
            master_png = find_asset(
                "PCDeck_Mouse_Logo.png",
                "PCDeck_Master_Logo.png",
                "PCDeck_Logo.png",
                "icon.png",
                "favicon.png",
            )
            if master_png:
                try:
                    self.logo_img = Image.open(master_png)
                    self.logo_photo = ImageTk.PhotoImage(self.logo_img.resize((36, 36), Image.Resampling.LANCZOS))
                except Exception:
                    self.logo_photo = None

        if hasattr(self, "logo_photo") and self.logo_photo:
            self.logo_lbl = tk.Label(brand_frame, image=self.logo_photo, bg=self.c_surface)
            self.logo_lbl.image = self.logo_photo
            self.logo_lbl.pack(side="left", padx=(0, 10))

        title_box = tk.Frame(brand_frame, bg=self.c_surface)
        title_box.pack(side="left")

        title_row = tk.Frame(title_box, bg=self.c_surface)
        title_row.pack(anchor="w")

        tk.Label(
            title_row,
            text="PC",
            font=F_TITLE,
            fg=self.c_text,
            bg=self.c_surface,
        ).pack(side="left")

        tk.Label(
            title_row,
            text="Deck",
            font=F_TITLE,
            fg=self.c_accent,
            bg=self.c_surface,
        ).pack(side="left")

        self.title_pro_badge = CTkModernLabel(
            title_row,
            text="PRO",
            font=(F_FAMILY, 9, "bold"),
            fg="#000000",
            bg="#eab308",
            corner_radius=6,
            padx=5,
            pady=1,
        )
        if self.is_pc_pro:
            self.title_pro_badge.pack(side="left", padx=(6, 0))

        # Subtle, discreet version label in top header (tiny 7pt regular, muted dim, no distracting bubble)
        self.header_version_badge = tk.Label(
            title_row,
            text=f"v{CURRENT_DESKTOP_VERSION_NAME}",
            font=(F_FAMILY, 7),
            fg=self.c_text_dim,
            bg=self.c_surface,
        )
        self.header_version_badge.pack(side="left", padx=(5, 0), pady=(6, 0))

        sub_lbl = tk.Label(
            title_box,
            text="WIRELESS PC TOUCH DECK & STREAMER",
            font=F_SMALL_STRONG,
            fg=self.c_text_dim,
            bg=self.c_surface,
        )
        sub_lbl.pack(anchor="w")

        # Right Header Stats
        header_right = tk.Frame(header, bg=self.c_surface)
        header_right.pack(side="right", padx=14, pady=10)

        self.status_pill = CTkModernLabel(
            header_right,
            text=f"● SERVER: [ONLINE] ({LOCAL_IP}:{SERVER_PORT})",
            font=F_BODY_STRONG,
            fg="#ffffff",
            bg=self.c_success,
            corner_radius=20,
            padx=12,
            pady=4,
        )
        self.status_pill.pack(side="right", padx=(8, 0))

        self.client_badge = CTkModernLabel(
            header_right,
            text="0 Clients",
            font=F_BODY_STRONG,
            fg=self.c_accent,
            bg=self.c_surface_3,
            corner_radius=6,
            padx=10,
            pady=3,
        )
        self.client_badge.pack(side="right")

        self.pro_badge = CTkModernLabel(
            header_right,
            text="★ PRO ACTIVE",
            font=F_SMALL_STRONG,
            fg="#ffd700",
            bg="#221e10",
            corner_radius=6,
            padx=8,
            pady=3,
        )
        if self.is_pc_pro:
            self.pro_badge.pack(side="right", padx=(0, 6))

        # 2. Segmented 3-Tab Navigation Bar
        tab_bar = tk.Frame(self.root, bg=self.c_bg)
        tab_bar.pack(fill="x", padx=16, pady=(0, 6))
        self.tab_bar = tab_bar

        tab_seg_frame = CTkModernFrame(
            tab_bar,
            bg=self.c_surface,
            corner_radius=8,
            highlightbackground=self.c_border,
            highlightthickness=1,
        )
        tab_seg_frame.pack(side="left")

        self.tab_buttons = {}
        tabs = [
            ("connect", "Connect"),
            ("tools", "Tools & Audio"),
            ("settings", "Settings")
        ]
        for key, label in tabs:
            btn = CTkModernButton(
                tab_seg_frame,
                text=label,
                font=F_BUTTON_LARGE,
                corner_radius=6,
                height=36,
                command=lambda k=key: self._switch_tab(k),
            )
            btn.pack(side="left", padx=2, pady=2)
            self.tab_buttons[key] = btn

        # 3. Content Area with 3 Tab Frames
        content_container = tk.Frame(self.root, bg=self.c_bg)
        content_container.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        self.content_container = content_container
        self.content_frame = content_container

        self.tab_connect = tk.Frame(content_container, bg=self.c_bg)
        self.tab_tools = tk.Frame(content_container, bg=self.c_bg)
        self.tab_settings = tk.Frame(content_container, bg=self.c_bg)

        # Build each tab view
        self._build_tab_connect()
        self._build_tab_tools()
        self._build_tab_settings()

        # Switch to active tab
        initial_tab = getattr(self, "current_tab", "connect")
        self._switch_tab(initial_tab)

        # Start live uptime ticker
        self._start_uptime_ticker()

    def _build_tab_connect(self):
        container = self.tab_connect

        # LEFT PANEL: Pairing Gateway (Width ~ 320px)
        left_col = CTkModernFrame(
            container,
            bg=self.c_surface,
            corner_radius=12,
            highlightbackground=self.c_border,
            highlightthickness=1,
            width=320,
        )
        left_col.pack(side="left", fill="both", padx=(0, 8), pady=0)
        left_col.pack_propagate(False)

        # Header: Pairing gateway
        qr_hdr = tk.Frame(left_col, bg=self.c_surface)
        qr_hdr.pack(fill="x", padx=14, pady=(12, 6))

        tk.Label(
            qr_hdr,
            text="Pairing gateway",
            font=F_HEADING,
            fg=self.c_text,
            bg=self.c_surface,
        ).pack(side="left")

# Pairing gateway header is kept clean without redundant status labels

        # QR Code Card
        qr_card = CTkModernFrame(
            left_col,
            bg="#ffffff",
            corner_radius=10,
            highlightbackground=self.c_border,
            highlightthickness=1,
        )
        qr_card.pack(padx=14, pady=4)

        self.qr_label = tk.Label(qr_card, bg="#ffffff", bd=0)
        self.qr_label.pack(padx=6, pady=6)
        self._generate_qr_image()

        # IP Address Bar with Copy
        ip_box = CTkModernFrame(
            left_col,
            bg=self.c_input,
            corner_radius=8,
            highlightbackground=self.c_border,
            highlightthickness=1,
            height=38,
        )
        ip_box.pack(fill="x", padx=14, pady=(4, 6))
        ip_box.pack_propagate(False)

        self.ip_entry = tk.Entry(
            ip_box,
            font=(F_MONO, 10, "bold"),
            fg=self.c_accent,
            bg=self.c_input,
            readonlybackground=self.c_input,
            selectbackground=self.c_accent,
            selectforeground="#ffffff",
            bd=0,
            justify="center",
        )
        self.ip_entry.insert(0, f"http://{LOCAL_IP}:{SERVER_PORT}")
        self.ip_entry.config(state="readonly")
        self.ip_entry.pack(side="left", fill="x", expand=True, padx=(8, 4), pady=4)

        copy_btn = CTkModernButton(
            ip_box,
            text="Copy",
            font=F_BUTTON_SMALL,
            fg=self.c_text,
            bg=self.c_surface_3,
            corner_radius=6,
            width=58,
            height=28,
            command=self.copy_ip,
        )
        copy_btn.pack(side="right", padx=4, pady=4)

        # Diagnostics & Resolution Card
        diag_box = CTkModernFrame(
            left_col,
            bg=self.c_surface_2,
            corner_radius=8,
            highlightbackground=self.c_border,
            highlightthickness=1,
        )
        diag_box.pack(fill="x", padx=14, pady=(4, 8))

        self.phone_status_lbl = tk.Label(
            diag_box,
            text=f"● Wi-Fi: {LOCAL_IP}",
            font=F_SMALL_STRONG,
            fg=self.c_success,
            bg=self.c_surface_2,
            anchor="w",
        )
        self.phone_status_lbl.pack(fill="x", padx=10, pady=(6, 2))

        self.screen_lbl = tk.Label(
            diag_box,
            text=f"Display: {controller.screen_width} x {controller.screen_height} @ 60 Hz",
            font=(F_MONO, 8),
            fg=self.c_text_dim,
            bg=self.c_surface_2,
            anchor="w",
        )
        self.screen_lbl.pack(fill="x", padx=10, pady=(0, 6))

        self.btn_help_conn = CTkModernButton(
            left_col,
            text="Troubleshoot & allow in firewall",
            font=F_BUTTON,
            fg=self.c_accent,
            bg=self.c_surface_2,
            corner_radius=8,
            height=36,
            command=self.open_how_to_connect_dialog,
        )
        self.btn_help_conn.pack(fill="x", padx=14, pady=(0, 8))

        # RIGHT PANEL: Actions & Live Connection Center
        right_col = CTkModernFrame(
            container,
            bg=self.c_surface,
            corner_radius=12,
            highlightbackground=self.c_border,
            highlightthickness=1,
        )
        right_col.pack(side="right", fill="both", expand=True, padx=(0, 0), pady=0)
        self.right_col = right_col

        # 1. TOP STATUS BAR (Uptime, Network, Latency)
        top_status_card = CTkModernFrame(
            right_col,
            bg=self.c_surface_2,
            corner_radius=8,
            highlightbackground=self.c_border,
            highlightthickness=1,
        )
        top_status_card.pack(fill="x", padx=14, pady=(12, 6))

        self.uptime_lbl = tk.Label(
            top_status_card,
            text="Uptime: 00:00:00",
            font=F_SMALL_STRONG,
            fg=self.c_text,
            bg=self.c_surface_2,
            padx=10,
            pady=5,
        )
        self.uptime_lbl.pack(side="left")

        self.network_health_lbl = tk.Label(
            top_status_card,
            text="Network: Ready",
            font=F_SMALL_STRONG,
            fg=self.c_text_dim,
            bg=self.c_surface_2,
            padx=10,
            pady=5,
        )
        self.network_health_lbl.pack(side="left", padx=8)

        self.latency_lbl = tk.Label(
            top_status_card,
            text="Latency: Standby",
            font=F_SMALL_STRONG,
            fg=self.c_text_dim,
            bg=self.c_surface_2,
            padx=10,
            pady=5,
        )
        self.latency_lbl.pack(side="right")

        # 2. HERO CARD: REMOTE CONTROLLERS (Phone Controller & Control Another PC)
        hero_card = CTkModernFrame(
            right_col,
            bg=self.c_surface,
            corner_radius=10,
            highlightbackground=self.c_border,
            highlightthickness=1,
        )
        hero_card.pack(fill="x", padx=14, pady=4)

        hero_hdr = tk.Frame(hero_card, bg=self.c_surface)
        hero_hdr.pack(fill="x", padx=12, pady=(10, 4))

        tk.Label(
            hero_hdr,
            text="Remote controllers",
            font=F_HEADING,
            fg=self.c_text,
            bg=self.c_surface,
        ).pack(side="left")

        self.stream_status_badge = CTkModernLabel(
            hero_hdr,
            text="● READY",
            font=F_SMALL_STRONG,
            fg="#ffffff",
            bg=self.c_success,
            corner_radius=6,
            padx=8,
            pady=2,
        )
        self.stream_status_badge.pack(side="right")

        # Two Side-by-Side Controller Action Tiles
        hero_tiles = tk.Frame(hero_card, bg=self.c_surface)
        hero_tiles.pack(fill="x", padx=12, pady=(0, 12))

        # Tile 1: Phone Controller
        t1 = CTkModernFrame(
            hero_tiles,
            bg=self.c_surface_2,
            corner_radius=10,
            highlightbackground=self.c_border,
            highlightthickness=1,
        )
        t1.pack(side="left", fill="both", expand=True, padx=(0, 6), pady=2)

        tk.Label(
            t1,
            text="Phone controller",
            font=F_HEADING,
            fg=self.c_text,
            bg=self.c_surface_2,
        ).pack(anchor="w", padx=12, pady=(10, 2))

        tk.Label(
            t1,
            text="Mirror screen (60 FPS), touch trackpad & media gestures.",
            font=F_SMALL,
            fg=self.c_text_dim,
            bg=self.c_surface_2,
            justify="left",
            wraplength=210,
        ).pack(anchor="w", padx=12, pady=(0, 8))

        self.btn_primary_stream = CTkModernButton(
            t1,
            text="Launch phone controller",
            font=F_BUTTON_LARGE,
            fg="#ffffff",
            bg=self.c_accent,
            corner_radius=8,
            height=38,
            command=self.open_phone_remote,
        )
        self.btn_primary_stream.pack(fill="x", padx=12, pady=(0, 10))

        # Tile 2: Control Another PC
        t2 = CTkModernFrame(
            hero_tiles,
            bg=self.c_surface_2,
            corner_radius=10,
            highlightbackground=self.c_border,
            highlightthickness=1,
        )
        t2.pack(side="right", fill="both", expand=True, padx=(6, 0), pady=2)

        tk.Label(
            t2,
            text="Control another PC",
            font=F_HEADING,
            fg=self.c_text,
            bg=self.c_surface_2,
        ).pack(anchor="w", padx=12, pady=(10, 2))

        tk.Label(
            t2,
            text="Pilot secondary PC or laptop via browser with 1-click reconnect.",
            font=F_SMALL,
            fg=self.c_text_dim,
            bg=self.c_surface_2,
            justify="left",
            wraplength=210,
        ).pack(anchor="w", padx=12, pady=(0, 8))

        self.btn_control_pc = CTkModernButton(
            t2,
            text="Connect to PC",
            font=F_BUTTON_LARGE,
            fg=self.c_text,
            bg=self.c_surface_3,
            corner_radius=8,
            height=38,
            command=self.open_control_another_pc_dialog,
        )
        self.btn_control_pc.pack(fill="x", padx=12, pady=(0, 10))

        # 3. CONNECTED CLIENTS & MULTI-PC CARD
        conn_card = CTkModernFrame(
            right_col,
            bg=self.c_surface,
            corner_radius=10,
            highlightbackground=self.c_border,
            highlightthickness=1,
        )
        conn_card.pack(fill="both", expand=True, padx=14, pady=4)

        conn_hdr = tk.Frame(conn_card, bg=self.c_surface)
        conn_hdr.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(
            conn_hdr,
            text="Connected clients",
            font=F_HEADING,
            fg=self.c_text,
            bg=self.c_surface,
        ).pack(side="left")

        tk.Label(
            conn_hdr,
            text="0 active",
            font=F_SMALL,
            fg=self.c_text_dim,
            bg=self.c_surface,
        ).pack(side="right")

        self.conn_clients_box = CTkModernFrame(
            conn_card,
            bg=self.c_surface_2,
            corner_radius=8,
            highlightbackground=self.c_border,
            highlightthickness=1,
        )
        self.conn_clients_box.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        self.lbl_no_clients = tk.Label(
            self.conn_clients_box,
            text="Waiting for mobile device to connect... Open PCDeck on your phone and point camera at the QR code.",
            font=F_BODY,
            fg=self.c_text_dim,
            bg=self.c_surface_2,
            wraplength=440,
            justify="left",
            pady=12,
        )
        self.lbl_no_clients.pack(anchor="w", padx=10)

        # 4. POLITE 3-DAY STORE REVIEW CARD
        if check_should_show_review_prompt(self.review_state):
            self._build_review_card(right_col)

    def _build_tab_tools(self):
        container = self.tab_tools

        # Main Card 1: FAST WIRELESS FILE TRANSFER
        file_card = CTkModernFrame(
            container,
            bg=self.c_surface,
            corner_radius=12,
            highlightbackground=self.c_border,
            highlightthickness=1,
        )
        file_card.pack(fill="x", padx=0, pady=(0, 8))

        f_hdr = tk.Frame(file_card, bg=self.c_surface)
        f_hdr.pack(fill="x", padx=14, pady=(12, 2))
        tk.Label(
            f_hdr,
            text="Fast wireless file transfer",
            font=F_HEADING,
            fg=self.c_text,
            bg=self.c_surface,
        ).pack(side="left")

        tk.Label(
            file_card,
            text="Transfer high-resolution photos, 4K videos, documents, and APKs directly over local Wi-Fi with zero data caps.",
            font=F_SMALL,
            fg=self.c_text_dim,
            bg=self.c_surface,
            justify="left",
        ).pack(anchor="w", padx=14, pady=(0, 8))

        # Two Side-by-side Action Tiles
        file_tiles = tk.Frame(file_card, bg=self.c_surface)
        file_tiles.pack(fill="x", padx=14, pady=(0, 12))

        # Tile 1: Send Files
        tile_send = CTkModernFrame(
            file_tiles,
            bg=self.c_surface_2,
            corner_radius=10,
            highlightbackground=self.c_border,
            highlightthickness=1,
        )
        tile_send.pack(side="left", fill="both", expand=True, padx=(0, 6))

        tk.Label(
            tile_send,
            text="Send files to phone",
            font=F_LABEL,
            fg=self.c_text,
            bg=self.c_surface_2,
        ).pack(anchor="w", padx=12, pady=(10, 2))

        tk.Label(
            tile_send,
            text="Pick files from your PC to send instantly to your phone's Downloads folder.",
            font=F_SMALL,
            fg=self.c_text_dim,
            bg=self.c_surface_2,
            justify="left",
            wraplength=280,
        ).pack(anchor="w", padx=12, pady=(0, 8))

        CTkModernButton(
            tile_send,
            text="Select files",
            font=F_BUTTON,
            fg="#ffffff",
            bg=self.c_accent,
            corner_radius=8,
            height=36,
            command=self.send_files_to_phone,
        ).pack(fill="x", padx=12, pady=(0, 10))

        # Tile 2: Open Transfers Folder
        tile_recv = CTkModernFrame(
            file_tiles,
            bg=self.c_surface_2,
            corner_radius=10,
            highlightbackground=self.c_border,
            highlightthickness=1,
        )
        tile_recv.pack(side="right", fill="both", expand=True, padx=(6, 0))

        tk.Label(
            tile_recv,
            text="Received files",
            font=F_LABEL,
            fg=self.c_text,
            bg=self.c_surface_2,
        ).pack(anchor="w", padx=12, pady=(10, 2))

        tk.Label(
            tile_recv,
            text="View and manage photos, videos, and files received from connected phones.",
            font=F_SMALL,
            fg=self.c_text_dim,
            bg=self.c_surface_2,
            justify="left",
            wraplength=280,
        ).pack(anchor="w", padx=12, pady=(0, 8))

        CTkModernButton(
            tile_recv,
            text="Open transfers folder",
            font=F_BUTTON,
            fg=self.c_text,
            bg=self.c_surface_3,
            corner_radius=8,
            height=36,
            command=self.open_transfers_folder,
        ).pack(fill="x", padx=12, pady=(0, 10))

        # Main Card 2: PC AUDIO & HARDWARE STREAMING
        audio_card = CTkModernFrame(
            container,
            bg=self.c_surface,
            corner_radius=12,
            highlightbackground=self.c_border,
            highlightthickness=1,
        )
        audio_card.pack(fill="both", expand=True, padx=0, pady=(0, 0))

        a_hdr = tk.Frame(audio_card, bg=self.c_surface)
        a_hdr.pack(fill="x", padx=14, pady=(12, 2))
        tk.Label(
            a_hdr,
            text="Audio streaming & hardware sensors",
            font=F_HEADING,
            fg=self.c_text,
            bg=self.c_surface,
        ).pack(side="left")

        tk.Label(
            audio_card,
            text="WASAPI loopback audio capture, phone microphone sink, and virtual gamepad integration.",
            font=F_SMALL,
            fg=self.c_text_dim,
            bg=self.c_surface,
            justify="left",
        ).pack(anchor="w", padx=14, pady=(0, 8))

        # Two Side-by-side Audio/Hardware Tiles
        audio_tiles = tk.Frame(audio_card, bg=self.c_surface)
        audio_tiles.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        # Tile A: PC Audio Stream Loopback
        tile_audio = CTkModernFrame(
            audio_tiles,
            bg=self.c_surface_2,
            corner_radius=10,
            highlightbackground=self.c_border,
            highlightthickness=1,
        )
        tile_audio.pack(side="left", fill="both", expand=True, padx=(0, 6))

        a_row = tk.Frame(tile_audio, bg=self.c_surface_2)
        a_row.pack(fill="x", padx=12, pady=(10, 2))
        tk.Label(a_row, text="PC audio loopback", font=F_LABEL, fg=self.c_text, bg=self.c_surface_2).pack(side="left")

        self.audio_status_lbl = CTkModernLabel(
            a_row,
            text="OFF",
            font=F_SMALL_STRONG,
            fg=self.c_text_dim,
            bg=self.c_surface_3,
            corner_radius=6,
            padx=8,
            pady=2,
        )
        self.audio_status_lbl.pack(side="right")

        tk.Label(
            tile_audio,
            text="Stream PC sound (games, Spotify, calls) directly to your mobile headphones. Zero lag WASAPI loopback on port 8003.",
            font=F_SMALL,
            fg=self.c_text_dim,
            bg=self.c_surface_2,
            justify="left",
            wraplength=280,
        ).pack(anchor="w", padx=12, pady=(0, 8))

        self.btn_toggle_audio = CTkModernButton(
            tile_audio,
            text="Start audio stream",
            font=F_BUTTON,
            fg=self.c_text,
            bg=self.c_surface_3,
            corner_radius=8,
            height=36,
            command=self.toggle_audio_stream,
        )
        self.btn_toggle_audio.pack(fill="x", padx=12, pady=(0, 10))

        # Tile B: Sinks & Screen Settings
        tile_hw = CTkModernFrame(
            audio_tiles,
            bg=self.c_surface_2,
            corner_radius=10,
            highlightbackground=self.c_border,
            highlightthickness=1,
        )
        tile_hw.pack(side="right", fill="both", expand=True, padx=(6, 0))

        tk.Label(
            tile_hw,
            text="Sensors & refresh rate",
            font=F_LABEL,
            fg=self.c_text,
            bg=self.c_surface_2,
        ).pack(anchor="w", padx=12, pady=(10, 2))

        chips_frame = tk.Frame(tile_hw, bg=self.c_surface_2)
        chips_frame.pack(fill="x", padx=12, pady=(4, 6))

        CTkModernLabel(
            chips_frame,
            text="Mic Sink: Port 8002 · Ready",
            font=F_SMALL_STRONG,
            fg=self.c_success,
            bg=self.c_surface_3,
            corner_radius=6,
            padx=8,
            pady=3,
        ).pack(side="left", padx=(0, 6))

        CTkModernLabel(
            chips_frame,
            text="Cam Stream: Port 8000 · Ready",
            font=F_SMALL_STRONG,
            fg=self.c_accent,
            bg=self.c_surface_3,
            corner_radius=6,
            padx=8,
            pady=3,
        ).pack(side="left")

        tk.Label(
            tile_hw,
            text="Target Screen Stream Frame Rate:",
            font=F_SMALL,
            fg=self.c_text_dim,
            bg=self.c_surface_2,
        ).pack(anchor="w", padx=12, pady=(6, 2))

        fps_row = tk.Frame(tile_hw, bg=self.c_surface_2)
        fps_row.pack(anchor="w", padx=12, pady=(0, 10))

        tk.Radiobutton(
            fps_row,
            text="30 FPS (Power Saver)",
            variable=self.fps_var,
            value="30",
            font=F_SMALL,
            fg=self.c_text,
            bg=self.c_surface_2,
            selectcolor=self.c_bg,
            activebackground=self.c_surface_2,
            command=self.update_fps,
        ).pack(side="left", padx=(0, 8))

        tk.Radiobutton(
            fps_row,
            text="60 FPS (Ultra Smooth) • PRO",
            variable=self.fps_var,
            value="60",
            font=F_SMALL,
            fg=self.c_text,
            bg=self.c_surface_2,
            selectcolor=self.c_bg,
            activebackground=self.c_surface_2,
            command=self.update_fps,
        ).pack(side="left")

    def _build_tab_settings(self):
        container = self.tab_settings

        # Card 1: WI-FI & HOTSPOTS AUTO-RECONNECTOR
        wifi_card = CTkModernFrame(
            container,
            bg=self.c_surface,
            corner_radius=12,
            highlightbackground=self.c_border,
            highlightthickness=1,
        )
        wifi_card.pack(fill="x", padx=0, pady=(0, 6))

        wifi_hdr = tk.Frame(wifi_card, bg=self.c_surface)
        wifi_hdr.pack(fill="x", padx=14, pady=(10, 2))

        tk.Label(
            wifi_hdr,
            text="Wi-Fi & hotspots auto-reconnector",
            font=F_HEADING,
            fg=self.c_text,
            bg=self.c_surface,
        ).pack(side="left")

        self.wifi_status_badge = CTkModernLabel(
            wifi_hdr,
            text="● Ready",
            font=F_SMALL_STRONG,
            fg="#ffffff",
            bg=self.c_success,
            corner_radius=6,
            padx=8,
            pady=2,
        )
        self.wifi_status_badge.pack(side="right")

        wifi_body = tk.Frame(wifi_card, bg=self.c_surface)
        wifi_body.pack(fill="x", padx=14, pady=(4, 10))

        self.wifi_select_var = tk.StringVar()
        self.wifi_combo = ttk.Combobox(
            wifi_body,
            textvariable=self.wifi_select_var,
            font=F_BODY,
            style="Deck.TCombobox",
            state="readonly",
        )
        self.wifi_combo.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.btn_wifi_connect = CTkModernButton(
            wifi_body,
            text="Connect",
            font=F_BUTTON,
            fg="#ffffff",
            bg=self.c_accent,
            corner_radius=8,
            height=34,
            command=self._on_wifi_connect_clicked,
        )
        self.btn_wifi_connect.pack(side="left", padx=(0, 6))

        self.btn_wifi_scan = CTkModernButton(
            wifi_body,
            text="Scan",
            font=F_BUTTON,
            fg=self.c_text,
            bg=self.c_surface_3,
            corner_radius=8,
            height=34,
            command=self._on_wifi_scan_clicked,
        )
        self.btn_wifi_scan.pack(side="left", padx=(0, 10))

        tk.Checkbutton(
            wifi_body,
            text="Auto-reconnect on launch",
            variable=self.auto_wifi_var,
            font=F_SMALL,
            fg=self.c_text_dim,
            bg=self.c_surface,
            selectcolor=self.c_bg,
            activebackground=self.c_surface,
            command=self._on_auto_wifi_toggle,
        ).pack(side="left")

        # Card 2: SYSTEM APPEARANCE & STARTUP
        app_card = CTkModernFrame(
            container,
            bg=self.c_surface,
            corner_radius=12,
            highlightbackground=self.c_border,
            highlightthickness=1,
        )
        app_card.pack(fill="x", padx=0, pady=(0, 6))

        app_hdr = tk.Frame(app_card, bg=self.c_surface)
        app_hdr.pack(fill="x", padx=14, pady=(10, 2))
        tk.Label(
            app_hdr,
            text="Appearance & system preferences",
            font=F_HEADING,
            fg=self.c_text,
            bg=self.c_surface,
        ).pack(side="left")

        app_body = tk.Frame(app_card, bg=self.c_surface)
        app_body.pack(fill="x", padx=14, pady=(4, 10))

        tk.Label(
            app_body,
            text="Color Theme:",
            font=F_BODY,
            fg=self.c_text,
            bg=self.c_surface,
        ).pack(side="left", padx=(0, 8))

        current_theme_text = "Follow Windows (Auto)"
        if self.theme_pref == "light":
            current_theme_text = "Light Mode"
        elif self.theme_pref == "dark":
            current_theme_text = "Dark Mode"
        self.theme_combo_var = tk.StringVar(value=current_theme_text)

        # 3-button segmented theme selector: 1-click instant switching, zero dropdown popdown grab issues
        theme_btn_box = tk.Frame(app_body, bg=self.c_surface)
        theme_btn_box.pack(side="left", padx=(0, 16))

        for mode_key, mode_title in [("system", "Follow Windows"), ("dark", "Dark Mode"), ("light", "Light Mode")]:
            is_active = (self.theme_pref == mode_key)
            CTkModernButton(
                theme_btn_box,
                text=mode_title,
                font=F_BODY,
                fg_color=self.c_accent if is_active else self.c_surface_2,
                text_color="#ffffff" if is_active else self.c_text,
                hover_color=self.c_accent_hover if is_active else self.c_surface_3,
                corner_radius=6,
                height=30,
                command=lambda m=mode_key: self.set_theme(m),
            ).pack(side="left", padx=(0, 6))

        tk.Checkbutton(
            app_body,
            text="Start PCDeck with Windows",
            variable=self.start_boot_var,
            font=F_BODY,
            fg=self.c_text,
            bg=self.c_surface,
            selectcolor=self.c_bg,
            activebackground=self.c_surface,
            command=self.save_settings,
        ).pack(side="left")

        # Card 3: PCDECK PRO LICENSE & SUPPORT
        lic_card = CTkModernFrame(
            container,
            bg=self.c_surface,
            corner_radius=12,
            highlightbackground=self.c_border,
            highlightthickness=1,
        )
        lic_card.pack(fill="x", padx=0, pady=(0, 6))

        lic_hdr = tk.Frame(lic_card, bg=self.c_surface)
        lic_hdr.pack(fill="x", padx=14, pady=(10, 2))

        tk.Label(
            lic_hdr,
            text="PCDeck Pro & support",
            font=F_HEADING,
            fg=self.c_text,
            bg=self.c_surface,
        ).pack(side="left")

        self.lic_status_lbl = CTkModernLabel(
            lic_hdr,
            text="PRO ACTIVE" if self.is_pc_pro else "FREE EDITION",
            font=F_SMALL_STRONG,
            fg="#ffd700" if self.is_pc_pro else self.c_text_dim,
            bg=self.c_surface_3 if self.is_pc_pro else self.c_surface,
            corner_radius=6,
            padx=8,
            pady=2,
        )
        self.lic_status_lbl.pack(side="right")

        # Row 1: Primary actions (Guide, Pro, Website)
        lic_row1 = tk.Frame(lic_card, bg=self.c_surface)
        lic_row1.pack(fill="x", padx=14, pady=(4, 6))

        self.guide_btn = CTkModernButton(
            lic_row1,
            text="How to connect guide",
            font=F_BUTTON,
            fg="#ffffff",
            bg=self.c_accent,
            corner_radius=8,
            height=34,
            command=self.open_how_to_connect_dialog,
        )
        self.guide_btn.pack(side="left", padx=(0, 8))

        self.lic_btn = CTkModernButton(
            lic_row1,
            text="Manage Pro" if self.is_pc_pro else "Upgrade to Pro ($3.99)",
            font=F_BUTTON,
            fg="#ffd700" if self.is_pc_pro else "#000000",
            bg=self.c_surface_3 if self.is_pc_pro else "#eab308",
            corner_radius=8,
            height=34,
            command=self.open_license_dialog,
        )
        self.lic_btn.pack(side="left", padx=(0, 8))

        btn_docs = CTkModernButton(
            lic_row1,
            text="Official website & docs",
            font=F_BUTTON,
            fg=self.c_text,
            bg=self.c_surface_3,
            corner_radius=8,
            height=34,
            command=lambda: open_url_in_browser("https://getpcdeck.com"),
        )
        btn_docs.pack(side="left")

        # Row 2: Community & Store Reviews
        lic_row2 = tk.Frame(lic_card, bg=self.c_surface)
        lic_row2.pack(fill="x", padx=14, pady=(0, 10))

        btn_review = CTkModernButton(
            lic_row2,
            text="★ Rate PCDeck on Microsoft Store",
            font=F_BUTTON,
            fg="#000000",
            bg="#ffd700",
            activebackground="#facc15",
            corner_radius=8,
            height=34,
            command=self._on_review_rate,
        )
        btn_review.pack(side="left", padx=(0, 8))

        btn_show_prompt = CTkModernButton(
            lic_row2,
            text="Show Review Card on Dashboard",
            font=F_BUTTON,
            fg=self.c_text,
            bg=self.c_surface_3,
            corner_radius=8,
            height=34,
            command=self._force_show_review_card,
        )
        btn_show_prompt.pack(side="left")

        # 4. SYSTEM POWER BAR & VERSION FOOTER
        pwr_bar = CTkModernFrame(
            container,
            bg=self.c_surface,
            corner_radius=12,
            highlightbackground=self.c_border,
            highlightthickness=1,
        )
        self.pwr_bar = pwr_bar
        pwr_bar.pack(fill="x", padx=0, pady=(0, 0))

        pwr_inner = tk.Frame(pwr_bar, bg=self.c_surface)
        pwr_inner.pack(fill="x", padx=14, pady=8)

        CTkModernButton(
            pwr_inner,
            text="Restart server",
            font=F_BUTTON,
            fg="#ffffff",
            bg=self.c_accent,
            corner_radius=8,
            height=36,
            command=self.restart_server,
        ).pack(side="left", padx=(0, 8))

        CTkModernButton(
            pwr_inner,
            text="Stop server",
            font=F_BUTTON,
            fg="#ffffff",
            bg=self.c_danger,
            corner_radius=8,
            height=36,
            command=self.stop_server,
        ).pack(side="left")

        self.version_lbl = None


    def _build_review_card(self, parent: tk.Widget):
        """Constructs an elegant, non-intrusive review card in the desktop window."""
        try:
            if hasattr(self, "review_card") and self.review_card and self.review_card.winfo_exists():
                return

            self.review_card = tk.Frame(
                parent,
                bg=self.c_surface_2,
                bd=0,
                relief="solid",
                highlightbackground="#ffd700",
                highlightthickness=1,
            )
            # Packed before pwr_bar if pwr_bar exists, or appended
            if hasattr(self, "pwr_bar") and self.pwr_bar and self.pwr_bar.winfo_exists():
                self.review_card.pack(fill="x", padx=14, pady=4, before=self.pwr_bar)
            else:
                self.review_card.pack(fill="x", padx=14, pady=4)

            # Header row: Title + Close Button
            rev_hdr = tk.Frame(self.review_card, bg=C_SURFACE_2)
            rev_hdr.pack(fill="x", padx=10, pady=(6, 2))

            tk.Label(
                rev_hdr,
                text="ENJOYING PCDECK?",
                font=F_LABEL,
                fg="#ffd700",
                bg=C_SURFACE_2,
            ).pack(side="left")

            close_btn = tk.Button(
                rev_hdr,
                text="✕",
                font=(F_FAMILY, 9),
                fg=C_TEXT_DIM,
                bg=C_SURFACE_2,
                activeforeground=C_TEXT,
                activebackground=C_SURFACE_2,
                bd=0,
                cursor="hand2",
                command=self._on_review_dismiss,
            )
            close_btn.pack(side="right")

            # Body description: indie developer sympathetic review
            rev_msg = (
                "PCDeck is built by an indie developer. If the app has been useful to you "
                "over the past few days, a quick rating on the Microsoft Store helps an "
                "indie developer like me a lot."
            )
            tk.Label(
                self.review_card,
                text=rev_msg,
                font=F_SMALL,
                fg=C_TEXT,
                bg=C_SURFACE_2,
                justify="left",
                wraplength=480,
            ).pack(anchor="w", padx=10, pady=(0, 6))

            # Action button row
            rev_actions = tk.Frame(self.review_card, bg=C_SURFACE_2)
            rev_actions.pack(fill="x", padx=10, pady=(0, 8))

            # Button 1: Rate on Microsoft Store
            tk.Button(
                rev_actions,
                text="Rate on Microsoft Store",
                font=F_SMALL_STRONG,
                fg="#000000",
                bg="#ffd700",
                activebackground="#facc15",
                bd=0,
                cursor="hand2",
                padx=10,
                pady=4,
                command=self._on_review_rate,
            ).pack(side="left", padx=(0, 6))

            # Button 2: Remind in 7 days
            tk.Button(
                rev_actions,
                text="Remind in 7 days",
                font=F_SMALL,
                fg=C_TEXT_DIM,
                bg=C_SURFACE_3,
                activeforeground=C_TEXT,
                activebackground=C_BORDER,
                bd=0,
                cursor="hand2",
                padx=8,
                pady=4,
                command=self._on_review_snooze,
            ).pack(side="left", padx=(0, 6))

            # Button 3: Don't show again
            tk.Button(
                rev_actions,
                text="Don't show again",
                font=F_SMALL,
                fg=C_TEXT_DIM,
                bg=C_SURFACE_2,
                activeforeground=C_TEXT,
                activebackground=C_SURFACE_2,
                bd=0,
                cursor="hand2",
                padx=6,
                pady=4,
                command=self._on_review_dismiss,
            ).pack(side="left")

        except Exception as e:
            log_debug(f"Error creating review card: {e}")

    def _force_show_review_card(self):
        """Forces immediate display of the review card on the connect tab."""
        self._switch_tab("connect")
        if hasattr(self, "right_col"):
            self._build_review_card(self.right_col)

    def _on_review_rate(self):
        """User clicked Rate on Microsoft Store."""
        record_review_action("reviewed")
        try:
            if sys.platform == "win32":
                open_url_in_browser("ms-windows-store://review/?ProductId=9P4BK16LBGLS")
            else:
                import webbrowser
                webbrowser.open("https://apps.microsoft.com/detail/9P4BK16LBGLS")
        except Exception:
            pass
        if hasattr(self, "review_card") and self.review_card:
            try:
                self.review_card.destroy()
            except Exception:
                pass
            self.review_card = None

    def _on_review_snooze(self):
        """User clicked Remind in 7 days."""
        record_review_action("snoozed")
        if hasattr(self, "review_card") and self.review_card:
            try:
                self.review_card.destroy()
            except Exception:
                pass
            self.review_card = None

    def _on_review_dismiss(self):
        """User clicked Don't show again or closed the card."""
        record_review_action("dismissed")
        if hasattr(self, "review_card") and self.review_card:
            try:
                self.review_card.destroy()
            except Exception:
                pass
            self.review_card = None

    def _dispatch_scheduled_review_notification(self):
        """
        Dispatches polite desktop notification 60s after launch if review criteria are met.
        Snoozes for 5 days so the user is not spammed on subsequent launches.
        Re-schedules periodically (every 1 hour) if criteria are not yet met.
        """
        try:
            self.review_state = load_app_settings()
            if not check_should_show_review_prompt(self.review_state):
                # Re-check in 1 hour if status is still pending (handles long-running sessions)
                status = self.review_state.get("review_prompt_status", "pending")
                if status not in ("reviewed", "dismissed"):
                    if hasattr(self, "root") and self.root:
                        self.root.after(3600000, self._dispatch_scheduled_review_notification)
                return
            record_review_action("snoozed", days=5)
            self.review_state = load_app_settings()

            # 1. Native Windows 10/11 interactive toast banner with direct store button
            toast_sent = self.show_toast_notification(
                title="Enjoying PCDeck?",
                message="A quick rating on the Microsoft Store helps an indie developer like me a lot.",
                action_url="ms-windows-store://review/?ProductId=9P4BK16LBGLS",
                action_label="Rate on Microsoft Store",
            )
            # 2. Tray balloon fallback
            if not toast_sent:
                self.show_notification(
                    "A quick rating on the Microsoft Store helps an indie developer like me a lot.",
                    "Enjoying PCDeck?",
                )
        except Exception as e:
            log_debug(f"Failed to dispatch review notification: {e}")


    def _start_uptime_ticker(self):
        self._update_uptime_tick()

    def _update_uptime_tick(self):
        try:
            if hasattr(self, "uptime_lbl") and self.uptime_lbl and self.uptime_lbl.winfo_exists():
                elapsed = int(time.time() - getattr(self, "start_time", time.time()))
                hrs, rem = divmod(elapsed, 3600)
                mins, secs = divmod(rem, 60)
                self.uptime_lbl.config(text=f"Uptime: {hrs:02d}:{mins:02d}:{secs:02d}")
            self._update_network_health()
            self.root.after(1000, self._update_uptime_tick)
        except Exception:
            pass

    def _update_network_health(self):
        """Updates network quality, latency, hardware band (2.4G/5G/6G), and link speed dynamically."""
        try:
            from server.wifi_latency_manager import wifi_latency_manager

            health = wifi_latency_manager.get_network_health() if wifi_latency_manager else {"active": False}
            hw = health.get("hardware", {})
            band = hw.get("band", "Wi-Fi")
            speed = hw.get("speed_mbps", 0.0)
            speed_str = f" · {speed:.0f} Mbps" if speed > 0 else ""

            if health.get("active"):
                rtt = health.get("rtt_ms", 0)
                status = health.get("status", "Good")
                score = health.get("score_pct", 80)
                color = health.get("color", C_SUCCESS)

                if hasattr(self, "network_health_lbl") and self.network_health_lbl.winfo_exists():
                    self.network_health_lbl.config(
                        text=f"{band}{speed_str}: {status} ({score}%)",
                        fg=color
                    )
                if hasattr(self, "latency_lbl") and self.latency_lbl.winfo_exists():
                    self.latency_lbl.config(
                        text=f"Latency: {int(rtt)} ms",
                        fg=color
                    )
            else:
                sig_pct = hw.get("signal_pct", 70)
                quality_label = "Excellent" if sig_pct >= 80 else ("Good" if sig_pct >= 60 else "Fair")
                q_color = C_SUCCESS if sig_pct >= 60 else C_WARNING

                if hasattr(self, "network_health_lbl") and self.network_health_lbl.winfo_exists():
                    self.network_health_lbl.config(
                        text=f"{band}{speed_str}: {quality_label} ({sig_pct}%)",
                        fg=q_color
                    )
                if hasattr(self, "latency_lbl") and self.latency_lbl.winfo_exists():
                    self.latency_lbl.config(text="Latency: Standby", fg=C_TEXT_DIM)
        except Exception:
            pass

    def _get_gateway_qr_url(self) -> str:
        """Constructs the local pairing URL for lightning-fast camera QR scanning."""
        url = getattr(self, "server_url", None)
        if not url:
            try:
                ip = get_local_ip()
            except Exception:
                ip = LOCAL_IP
            self.server_url = f"http://{ip}:{SERVER_PORT}"
            url = self.server_url
        clean_ip = url.replace("http://", "").replace("https://", "").rstrip("/")
        try:
            tok = get_pairing_token()
            compact_tok = tok[:12] if len(tok) >= 12 else tok
            return f"http://{clean_ip}/connect?t={compact_tok}"
        except Exception:
            return f"http://{clean_ip}/connect"

    def _generate_qr_image(self):
        """Generate and display Tk PhotoImage QR with maximum contrast and ultra-fast scan latency."""
        gateway_url = self._get_gateway_qr_url()
        # Compact URL yields chunky Version 3 (29x29) modules with solid white quiet border
        # that scan in < 20ms off computer monitors without camera glare or moire interference.
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=6,
            border=3,
        )
        qr.add_data(gateway_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#000000", back_color="#ffffff")

        self.qr_photo = ImageTk.PhotoImage(img)
        self.qr_label.config(image=self.qr_photo, bg="#ffffff")



    def copy_ip(self):
        url = getattr(self, "server_url", SERVER_URL)
        clean_ip = url.replace("http://", "").replace("https://", "").rstrip("/")
        try:
            tok = get_pairing_token()
            compact_tok = tok[:12] if len(tok) >= 12 else tok
            clean_url = f"http://{clean_ip}/?tab=screen&t={compact_tok}"
        except Exception:
            clean_url = f"http://{clean_ip}/?tab=screen"
        self.root.clipboard_clear()
        self.root.clipboard_append(clean_url)
        messagebox.showinfo("PCDeck", f"Copied Web Remote address to clipboard:\n{clean_url}")

    def refresh_discovered_pcs(self):
        """Scans local subnet for other PCDeck host instances via UDP port 8001 daemon."""
        def scan_worker():
            import socket
            discovered = []
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                s.settimeout(1.2)
                for bcast in ["255.255.255.255", "127.0.0.1"]:
                    try:
                        s.sendto(b"PCDECK_DISCOVER:gui", (bcast, 8001))
                    except Exception:
                        pass
                start_t = time.time()
                while time.time() - start_t < 1.3:
                    try:
                        data, addr = s.recvfrom(1024)
                        txt = data.decode("utf-8", errors="ignore")
                        if "PCDECK_BEACON" in txt:
                            parts = txt.split(":")
                            h_ip = parts[1] if len(parts) > 1 else addr[0]
                            h_port = parts[2] if len(parts) > 2 else "8000"
                            h_name = parts[3] if len(parts) > 3 else "PCDeck Host"
                            entry = f"{h_name} ({h_ip}:{h_port})"
                            if entry not in discovered:
                                discovered.append(entry)
                    except socket.timeout:
                        break
                    except Exception:
                        break
                s.close()
            except Exception:
                pass

            def apply_vals():
                if hasattr(self, "p2p_combo") and self.p2p_combo.winfo_exists():
                    if discovered:
                        self.p2p_combo['values'] = discovered
                        if self.p2p_var.get() in ("Select PC or enter IP address...", "", "Searching Wi-Fi..."):
                            self.p2p_var.set(discovered[0])
                    else:
                        self.p2p_combo['values'] = ["Local PC (127.0.0.1:8000)", "Enter PC IP manually..."]

            if hasattr(self, "root") and self.root.winfo_exists():
                self.root.after(0, apply_vals)

        threading.Thread(target=scan_worker, daemon=True).start()

    def control_pc_in_browser(self):
        """Extracts host IP from dropdown or manual entry and opens browser remote."""
        val = self.p2p_var.get().strip() if hasattr(self, "p2p_var") else ""
        if not val or val in ("Select PC or enter IP address...", "Searching Wi-Fi...", "Enter PC IP manually..."):
            val = "127.0.0.1:8000"

        import re
        m = re.search(r"(\d{1,3}(?:\.\d{1,3}){3})(?::(\d+))?", val)
        if m:
            ip = m.group(1)
            port = m.group(2) or "8000"
            target_url = f"http://{ip}:{port}/?tab=screen"
        elif "localhost" in val.lower():
            target_url = "http://127.0.0.1:8000/?tab=screen"
        elif val.startswith("http://") or val.startswith("https://"):
            target_url = val
            if "/?tab=screen" not in target_url:
                target_url = target_url.rstrip("/") + "/?tab=screen"
        else:
            clean = val.replace("http://", "").replace("https://", "").strip()
            if ":" not in clean:
                clean = f"{clean}:8000"
            target_url = f"http://{clean}/?tab=screen"

        open_url_in_browser(target_url)

    def open_web_controller(self):
        """Open local web controller directly in default browser."""
        url = getattr(self, "server_url", SERVER_URL)
        clean_ip = url.replace("http://", "").replace("https://", "").rstrip("/")
        try:
            tok = get_pairing_token()
            compact_tok = tok[:12] if len(tok) >= 12 else tok
            target_url = f"http://{clean_ip}/?tab=screen&t={compact_tok}"
        except Exception:
            target_url = f"http://{clean_ip}/?tab=screen"
        open_url_in_browser(target_url)

    def open_control_another_pc_dialog(self):
        """Open modal dialog showing recent history, active discovered hosts, and manual connection."""
        dlg = tk.Toplevel(self.root)
        dlg.withdraw()
        dlg.title("PCDeck — Control Another PC (Client Mode)")
        dlg.resizable(False, False)
        dlg.configure(bg=C_SURFACE)
        dlg.transient(self.root)
        apply_crisp_window_icon(dlg)

        dw = 500
        dh = 510
        try:
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            x = max(0, (sw - dw) // 2)
            y = max(0, (sh - dh) // 2)
            dlg.geometry(f"{dw}x{dh}+{x}+{y}")
        except Exception:
            dlg.geometry(f"{dw}x{dh}")

        pad = tk.Frame(dlg, bg=C_SURFACE, padx=18, pady=14)
        pad.pack(fill="both", expand=True)

        tk.Label(
            pad,
            text="CLIENT MODE",
            font=(F_FAMILY, 8, "bold"),
            fg=C_BLACK,
            bg=C_ACCENT,
            padx=6,
            pady=2,
        ).pack(anchor="w", pady=(0, 4))

        tk.Label(
            pad,
            text="Control Another PC Over Wi-Fi",
            font=(F_FAMILY, 13, "bold"),
            fg=C_TEXT,
            bg=C_SURFACE,
            anchor="w",
        ).pack(fill="x", pady=(2, 2))

        tk.Label(
            pad,
            text="Open a live remote session in your browser to control another PC running PCDeck. No client software needed.",
            font=F_SMALL,
            fg=C_TEXT_DIM,
            bg=C_SURFACE,
            justify="left",
            wraplength=460,
        ).pack(anchor="w", pady=(0, 10))

        def do_connect(ip: str, port: str = "8000", name: str = ""):
            if not ip:
                return
            add_recent_pc(name or f"PC ({ip})", ip, port)
            dlg.destroy()
            open_url_in_browser(f"http://{ip}:{port}/?tab=screen")

        # 1. Recently Connected PCs Section
        recent_list = get_recent_pcs()
        if recent_list:
            recent_frame = tk.Frame(pad, bg=C_SURFACE_2, bd=1, relief="solid")
            recent_frame.pack(fill="x", pady=(0, 8))

            recent_hdr = tk.Frame(recent_frame, bg=C_SURFACE_2)
            recent_hdr.pack(fill="x", padx=10, pady=(6, 3))
            tk.Label(recent_hdr, text="RECENT COMPUTERS", font=F_LABEL, fg=C_TEXT, bg=C_SURFACE_2).pack(side="left")

            for p_info in recent_list[:3]:
                p_name = p_info.get("name", "PCDeck Host")
                p_ip = p_info.get("ip", "")
                p_port = p_info.get("port", "8000")
                p_time = p_info.get("time", "")

                r_row = tk.Frame(recent_frame, bg=C_SURFACE_3, bd=0)
                r_row.pack(fill="x", padx=8, pady=2)

                lbl_box = tk.Frame(r_row, bg=C_SURFACE_3)
                lbl_box.pack(side="left", padx=6, pady=3)

                tk.Label(
                    lbl_box,
                    text=f"{p_name}",
                    font=F_BODY_STRONG,
                    fg=C_TEXT,
                    bg=C_SURFACE_3,
                    anchor="w",
                ).pack(anchor="w")

                tk.Label(
                    lbl_box,
                    text=f"{p_ip}:{p_port}  •  {p_time}",
                    font=(F_FAMILY, 8),
                    fg=C_TEXT_DIM,
                    bg=C_SURFACE_3,
                    anchor="w",
                ).pack(anchor="w")

                def make_conn_handler(h_ip=p_ip, h_port=p_port, h_name=p_name):
                    return lambda: do_connect(h_ip, h_port, h_name)

                tk.Button(
                    r_row,
                    text="CONNECT →",
                    font=(F_FAMILY, 8, "bold"),
                    fg=C_BG,
                    bg=C_ACCENT,
                    activeforeground=C_BG,
                    activebackground=C_ACCENT_HOVER,
                    bd=0,
                    cursor="hand2",
                    padx=8,
                    pady=2,
                    command=make_conn_handler(p_ip, p_port, p_name),
                ).pack(side="right", padx=6, pady=3)

        # 2. Discovered Hosts on Wi-Fi Section
        disc_frame = tk.Frame(pad, bg=C_SURFACE_2, bd=1, relief="solid")
        disc_frame.pack(fill="x", pady=(0, 8))

        disc_hdr = tk.Frame(disc_frame, bg=C_SURFACE_2)
        disc_hdr.pack(fill="x", padx=10, pady=(6, 3))
        tk.Label(disc_hdr, text="DISCOVERED ON WI-FI", font=F_LABEL, fg=C_TEXT, bg=C_SURFACE_2).pack(side="left")

        disc_status = tk.Label(disc_hdr, text="● Scanning...", font=F_SMALL_STRONG, fg=C_ACCENT, bg=C_SURFACE_2)
        disc_status.pack(side="right")

        hosts_container = tk.Frame(disc_frame, bg=C_SURFACE_2)
        hosts_container.pack(fill="x", padx=10, pady=(0, 6))

        loading_lbl = tk.Label(hosts_container, text="Searching local network for PCDeck instances...", font=F_SMALL, fg=C_TEXT_DIM, bg=C_SURFACE_2)
        loading_lbl.pack(pady=4)

        # 3. Manual IP Input Section
        manual_frame = tk.Frame(pad, bg=C_SURFACE_2, bd=1, relief="solid")
        manual_frame.pack(fill="x", pady=(0, 8))

        tk.Label(manual_frame, text="MANUAL HOST ADDRESS OR IP", font=F_LABEL, fg=C_TEXT, bg=C_SURFACE_2).pack(anchor="w", padx=10, pady=(5, 3))

        in_row = tk.Frame(manual_frame, bg=C_SURFACE_2)
        in_row.pack(fill="x", padx=10, pady=(0, 6))

        ip_var = tk.StringVar(value="")
        manual_entry = tk.Entry(
            in_row,
            textvariable=ip_var,
            font=(F_MONO, 10),
            fg=C_ACCENT,
            bg=C_INPUT,
            insertbackground=C_ACCENT,
            bd=0,
            relief="solid",
            highlightbackground=C_BORDER,
            highlightthickness=1,
        )
        manual_entry.pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=3)

        def connect_manual():
            val = ip_var.get().strip()
            if not val:
                messagebox.showwarning("PCDeck", "Please enter a valid Host IP address (e.g. 192.168.1.50).", parent=dlg)
                return
            import re
            m = re.search(r"(\d{1,3}(?:\.\d{1,3}){3})(?::(\d+))?", val)
            if m:
                ip = m.group(1)
                port = m.group(2) or "8000"
                do_connect(ip, port, f"PC ({ip})")
            elif "localhost" in val.lower():
                do_connect("127.0.0.1", "8000", "Local PC")
            else:
                do_connect(val, "8000", f"Host ({val})")

        btn_conn = tk.Button(
            in_row,
            text="CONNECT IN BROWSER",
            font=F_SMALL_STRONG,
            fg=C_BG,
            bg=C_ACCENT,
            activeforeground=C_BG,
            activebackground=C_ACCENT_HOVER,
            bd=0,
            cursor="hand2",
            padx=10,
            pady=3,
            command=connect_manual,
        )
        btn_conn.pack(side="right")
        manual_entry.bind("<Return>", lambda e: connect_manual())

        # Footer Row (Help note + Close)
        footer_row = tk.Frame(pad, bg=C_SURFACE)
        footer_row.pack(fill="x", pady=(4, 0))

        tk.Label(
            footer_row,
            text="Both PCs must be on the same local Wi-Fi or phone hotspot.",
            font=(F_FAMILY, 8),
            fg=C_TEXT_DIM,
            bg=C_SURFACE,
        ).pack(side="left")

        tk.Button(
            footer_row,
            text="CLOSE",
            font=F_SMALL_STRONG,
            fg=C_TEXT,
            bg=C_SURFACE_2,
            activeforeground=C_TEXT,
            activebackground=C_SURFACE_3,
            bd=0,
            cursor="hand2",
            padx=14,
            pady=4,
            command=dlg.destroy,
        ).pack(side="right")

        # Run background UDP scan for active hosts
        def run_udp_scan():
            import socket
            discovered = []
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                s.settimeout(1.2)
                for target_ip in ["255.255.255.255", "127.0.0.1"]:
                    try:
                        s.sendto(b"PCDECK_DISCOVER:client", (target_ip, 8001))
                    except Exception:
                        pass
                start_t = time.time()
                while time.time() - start_t < 1.3:
                    try:
                        data, addr = s.recvfrom(1024)
                        txt = data.decode("utf-8", errors="ignore")
                        if "PCDECK_BEACON" in txt:
                            parts = txt.split(":")
                            host_ip = parts[1] if len(parts) > 1 else addr[0]
                            host_port = parts[2] if len(parts) > 2 else "8000"
                            host_name = parts[3] if len(parts) > 3 else "PCDeck Host"
                            entry = (host_ip, host_port, host_name)
                            if entry not in discovered:
                                discovered.append(entry)
                    except socket.timeout:
                        break
                    except Exception:
                        break
                s.close()
            except Exception:
                pass

            def update_ui():
                if not dlg.winfo_exists():
                    return
                for widget in hosts_container.winfo_children():
                    widget.destroy()
                if not discovered:
                    disc_status.config(text="● No other hosts found", fg=C_TEXT_DIM)
                    tk.Label(
                        hosts_container,
                        text="No other PCDeck instances auto-detected. Enter IP manually below.",
                        font=F_SMALL,
                        fg=C_TEXT_DIM,
                        bg=C_SURFACE_2,
                    ).pack(pady=4)
                else:
                    disc_status.config(text=f"● Found {len(discovered)} Host(s)", fg=C_SUCCESS)
                    for h_ip, h_port, h_name in discovered:
                        h_row = tk.Frame(hosts_container, bg=C_SURFACE_3, bd=0)
                        h_row.pack(fill="x", pady=2, padx=2)
                        tk.Label(
                            h_row,
                            text=f"{h_name} ({h_ip}:{h_port})",
                            font=F_SMALL_STRONG,
                            fg=C_TEXT,
                            bg=C_SURFACE_3,
                            padx=6,
                        ).pack(side="left")

                        def make_launch(ip=h_ip, port=h_port, name=h_name):
                            return lambda: do_connect(ip, port, name)

                        tk.Button(
                            h_row,
                            text="CONNECT →",
                            font=(F_FAMILY, 8, "bold"),
                            fg=C_BG,
                            bg=C_ACCENT,
                            activeforeground=C_BG,
                            activebackground=C_ACCENT_HOVER,
                            bd=0,
                            cursor="hand2",
                            padx=8,
                            pady=2,
                            command=make_launch(h_ip, h_port, h_name),
                        ).pack(side="right", padx=4, pady=3)

            dlg.after(0, update_ui)

        threading.Thread(target=run_udp_scan, daemon=True).start()
        dlg.deiconify()

    def refresh_network_ip(self):
        """Manually force detect local Wi-Fi, USB Tethering, or Hotspot IP address."""
        try:
            try:
                from server.main import get_local_ip
            except ImportError:
                from main import get_local_ip
            new_ip = get_local_ip()
            self.current_ip = new_ip
            self.server_url = f"http://{new_ip}:{SERVER_PORT}"
            self.ip_entry.config(state="normal")
            self.ip_entry.delete(0, tk.END)
            self.ip_entry.insert(0, self.server_url)
            self.ip_entry.config(state="readonly", readonlybackground=C_INPUT, fg=C_ACCENT)
            self._generate_qr_image()
            if hasattr(self, "phone_status_lbl") and self.phone_status_lbl.winfo_exists():
                if new_ip.startswith("192.168.42."):
                    mode = "USB Tethered"
                elif new_ip.startswith("192.168.43.") or new_ip.startswith("172."):
                    mode = "Phone Hotspot"
                elif not new_ip.startswith("127."):
                    mode = "Wi-Fi Ready"
                else:
                    mode = "Waiting for Network (Localhost)"
                self.phone_status_lbl.config(
                    text=f"● {mode}: {new_ip}",
                    fg=C_SUCCESS if not new_ip.startswith("127.") else C_WARNING,
                )
        except Exception:
            pass

    def open_transfers_folder(self):
        try:
            os.startfile(TRANSFER_DIR)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {e}")

    def send_files_to_phone(self):
        files = filedialog.askopenfilenames(title="Select files to share with phone")
        if files:
            copied = 0
            for f in files:
                try:
                    dest = os.path.join(TRANSFER_DIR, os.path.basename(f))
                    shutil.copy2(f, dest)
                    copied += 1
                except Exception:
                    pass
            messagebox.showinfo("PCDeck Pro", f"{copied} file(s) ready for download on phone.")

    def update_fps(self):
        try:
            val = int(self.fps_var.get())
            if val == 60 and not self.is_pc_pro:
                self.fps_var.set("30")
                self.open_license_dialog()
                return
            streamer.fps_limit = val
        except Exception:
            pass

    def _get_autostart_exe_path(self) -> str:
        """Returns the absolute path to the main PCDeck executable."""
        if getattr(sys, "frozen", False) and sys.executable:
            exe_dir = os.path.dirname(os.path.abspath(sys.executable))
            root_exe = os.path.abspath(os.path.join(exe_dir, "..", "PCDeck.exe"))
            if os.path.basename(exe_dir).lower() in ("website", "dist") and os.path.exists(root_exe):
                return root_exe
            return os.path.abspath(sys.executable)
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pcdeck_exe = os.path.join(parent_dir, "PCDeck.exe")
        if os.path.exists(pcdeck_exe):
            return os.path.abspath(pcdeck_exe)
        return os.path.abspath(sys.executable)

    def _get_autostart_cmd(self) -> str:
        exe_path = self._get_autostart_exe_path()
        return f'"{exe_path}" --tray'

    def _cleanup_run_key_entry(self, delete_current: bool = False):
        """Cleans up obsolete Run registry keys from older naming conventions."""
        if sys.platform != "win32":
            return
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE,
            )
            obsolete_names = ["PCDeck_Pro", "NeonTrack", "PCDeckPro", "PCDeck_Server"]
            if delete_current:
                obsolete_names.append("PCDeck")
            for kname in obsolete_names:
                try:
                    winreg.DeleteValue(key, kname)
                except Exception:
                    pass
            winreg.CloseKey(key)
        except Exception:
            pass

    def _cleanup_msix_rogue_shortcuts(self):
        r"""
        In MSIX package installations, Windows manages the Start Menu and autostart natively.
        Purges any broken raw Win32 .lnk files in Start Menu / Startup created by previous versions
        that point directly into C:\Program Files\WindowsApps (which causes Windows to abort/crash on launch).
        """
        if sys.platform != "win32":
            return
        try:
            appdata = os.environ.get("APPDATA", "")
            if not appdata:
                return
            target_shortcuts = [
                "PCDeck.lnk",
                "PCDeck Pro.lnk",
                "PCDeck_Pro.lnk",
                "PCDeckPro.lnk",
                "NeonTrack.lnk",
            ]
            import stat
            for folder in [
                os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs"),
                os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs\Startup"),
            ]:
                for s_name in target_shortcuts:
                    lnk_file = os.path.join(folder, s_name)
                    if os.path.exists(lnk_file):
                        try:
                            try:
                                os.chmod(lnk_file, stat.S_IWRITE)
                            except Exception:
                                pass
                            os.remove(lnk_file)
                            log_debug(f"[MSIX Cleanup] Removed conflicting shortcut: {lnk_file}")
                        except Exception as e:
                            log_debug(f"[MSIX Cleanup] Error removing {lnk_file}: {e}")
        except Exception as e:
            log_debug(f"[MSIX Cleanup] Exception: {e}")

    def _ensure_start_menu_shortcut(self):
        """Ensures a valid Start Menu shortcut exists with AppUserModelID and icon for Windows 10/11 Action Center."""
        if sys.platform != "win32" or is_msix_packaged():
            return
        try:
            exe_path = self._get_autostart_exe_path()
            if not os.path.exists(exe_path):
                return
            appdata = os.environ.get("APPDATA", "")
            if not appdata:
                return
            programs_dir = os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs")
            if not os.path.exists(programs_dir):
                return
            shortcut_path = os.path.join(programs_dir, "PCDeck.lnk")
            app_dir = os.path.dirname(exe_path)

            ps_script = (
                f"$ws = New-Object -ComObject WScript.Shell; "
                f"$s = $ws.CreateShortcut('{shortcut_path}'); "
                f"$s.TargetPath = '{exe_path}'; "
                f"$s.WorkingDirectory = '{app_dir}'; "
                f"$s.IconLocation = '{exe_path},0'; "
                f"$s.Description = 'PCDeck Pro - Wireless PC Touch Deck & Streamer'; "
                f"$s.Save()"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                timeout=5
            )
        except Exception as e:
            log_debug(f"Failed to create Start Menu shortcut: {e}")

    def _cleanup_legacy_autostart(self):
        """Purges any obsolete Run registry entries and scheduled tasks from previous versions."""
        if sys.platform != "win32" or is_msix_packaged():
            return
        # 1. Clean legacy registry Run keys (HKCU & HKLM)
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE,
            )
            for kname in ["PCDeck", "PCDeck_Pro", "NeonTrack", "PCDeckPro", "PCDeck_Server"]:
                try:
                    winreg.DeleteValue(key, kname)
                except Exception:
                    pass
            winreg.CloseKey(key)
        except Exception:
            pass

        try:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE,
            )
            for kname in ["PCDeck", "PCDeck_Pro", "NeonTrack", "PCDeckPro", "PCDeck_Server"]:
                try:
                    winreg.DeleteValue(key, kname)
                except Exception:
                    pass
            winreg.CloseKey(key)
        except Exception:
            pass

        # 2. Clean legacy scheduled tasks
        try:
            subprocess.run(
                ["schtasks", "/delete", "/tn", "PCDeck", "/f"],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                timeout=3
            )
        except Exception:
            pass

    def _update_task_scheduler_autostart(self, enabled: bool):
        """
        Manages PCDeck autostart using a single authoritative standard-user launcher:
        Windows Startup Folder Shortcut (%APPDATA%\\...\\Startup\\PCDeck.lnk).
        Prevents triple-launching, UAC blocks, and UIPI privilege isolation issues.
        """
        if sys.platform != "win32" or is_msix_packaged():
            return
        startup_dir = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup")
        startup_shortcut = os.path.join(startup_dir, "PCDeck.lnk") if startup_dir else ""

        # Always purge duplicate/legacy registry Run keys and scheduled tasks
        self._cleanup_legacy_autostart()

        if enabled:
            exe_path = self._get_autostart_exe_path()
            if not os.path.exists(exe_path):
                return
            app_dir = os.path.dirname(exe_path)

            if startup_dir and os.path.exists(startup_dir):
                try:
                    ps_startup = (
                        f"$ws = New-Object -ComObject WScript.Shell; "
                        f"$s = $ws.CreateShortcut('{startup_shortcut}'); "
                        f"$s.TargetPath = '{exe_path}'; "
                        f"$s.Arguments = '--tray'; "
                        f"$s.WorkingDirectory = '{app_dir}'; "
                        f"$s.IconLocation = '{exe_path},0'; "
                        f"$s.Description = 'PCDeck Pro - Wireless PC Touch Deck & Streamer'; "
                        f"$s.Save()"
                    )
                    subprocess.run(
                        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_startup],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                        timeout=5
                    )
                    log_debug(f"[Autostart] Authoritative startup shortcut configured: {startup_shortcut}")
                except Exception as e:
                    log_debug(f"[Autostart] Failed to create startup shortcut: {e}")

            self._ensure_start_menu_shortcut()
        else:
            if startup_shortcut and os.path.exists(startup_shortcut):
                try:
                    os.remove(startup_shortcut)
                    log_debug(f"[Autostart] Removed startup shortcut: {startup_shortcut}")
                except Exception as e:
                    log_debug(f"[Autostart] Failed to remove startup shortcut: {e}")

    def _ensure_autostart_task_scheduler(self):
        """Verifies and ensures the authoritative startup shortcut is in sync on launch."""
        if sys.platform != "win32" or is_msix_packaged():
            return
        try:
            self._ensure_start_menu_shortcut()
            if getattr(self, "autostart_enabled", False):
                self._update_task_scheduler_autostart(True)
            else:
                self._cleanup_legacy_autostart()
        except Exception as e:
            log_debug(f"Error ensuring autostart synchronization: {e}")

    def check_autostart_registry(self) -> bool:
        """
        Checks if autostart is enabled.
        Primary source of truth: Windows Startup folder shortcut.
        Migrates legacy Run registry entries or scheduled tasks if found.
        """
        if sys.platform != "win32" or is_msix_packaged():
            return False

        # 1. Authoritative check: Windows Startup Folder Shortcut
        startup_dir = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup")
        if startup_dir and os.path.exists(os.path.join(startup_dir, "PCDeck.lnk")):
            return True

        # 2. Legacy Migration Check: HKCU Run registry
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_READ,
            )
            val, _ = winreg.QueryValueEx(key, "PCDeck")
            winreg.CloseKey(key)
            if val:
                # Migrate to authoritative Startup shortcut and purge registry key
                self._update_task_scheduler_autostart(True)
                return True
        except Exception:
            pass

        # 3. Legacy Migration Check: Task Scheduler
        try:
            res = subprocess.run(
                ["schtasks", "/query", "/tn", "PCDeck"],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                timeout=3
            )
            if res.returncode == 0:
                # Migrate to authoritative Startup shortcut and purge task
                self._update_task_scheduler_autostart(True)
                return True
        except Exception:
            pass

        return False

    def save_settings(self):
        autostart = self.start_boot_var.get()
        self.autostart_enabled = bool(autostart)

        # Update elevated Windows Task Scheduler task (zero UAC popup on boot)
        self._update_task_scheduler_autostart(self.autostart_enabled)

        if getattr(self, "tray_icon", None):
            try:
                self.tray_icon.update_menu()
            except Exception:
                pass

    def _check_first_run_startup_prompt(self):
        """Checks if this is the first run and prompts user to enable Start with Windows."""
        try:
            if not self.root or not self.root.winfo_exists():
                return
            if is_first_run_startup_prompt_done():
                return
            # If autostart is already active, register as handled so prompt isn't shown
            if self.check_autostart_registry():
                mark_first_run_startup_prompt_done()
                return

            self.show_startup_onboarding_dialog()
        except Exception as e:
            log_debug(f"Error checking first-run startup prompt: {e}")

    def show_startup_onboarding_dialog(self):
        """
        Presents a centered, simple popup on first launch asking the user to
        enable Start with Windows so they don't have to manually re-run PCDeck.
        """
        dlg = tk.Toplevel(self.root)
        dlg.withdraw()  # Prevent top-left flashing during construction
        dlg.title("PCDeck — Start with Windows")
        dlg.resizable(False, False)
        dlg.configure(bg=C_SURFACE)
        dlg.transient(self.root)

        apply_crisp_window_icon(dlg)

        # Center dead-middle on user's screen
        dw = 460
        dh = 295
        try:
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            x = max(0, (sw - dw) // 2)
            y = max(0, (sh - dh) // 2)
            dlg.geometry(f"{dw}x{dh}+{x}+{y}")
        except Exception:
            dlg.geometry(f"{dw}x{dh}")

        pad = tk.Frame(dlg, bg=C_SURFACE, padx=20, pady=16)
        pad.pack(fill="both", expand=True)

        # Header Badge
        top_hdr = tk.Frame(pad, bg=C_SURFACE)
        top_hdr.pack(fill="x", pady=(0, 2))

        tk.Label(
            top_hdr,
            text="STARTUP SETTINGS",
            font=F_LABEL,
            fg=C_ACCENT,
            bg=C_SURFACE,
        ).pack(anchor="w")

        # Title
        tk.Label(
            pad,
            text="Start PCDeck with Windows?",
            font=F_TITLE,
            fg=C_TEXT,
            bg=C_SURFACE,
        ).pack(anchor="w", pady=(2, 4))

        # Easy to understand description
        tk.Label(
            pad,
            text="Enable PCDeck to run in the background when your computer starts. Your mobile device can connect immediately without needing to open the app manually.",
            font=F_BODY,
            fg=C_TEXT_DIM,
            bg=C_SURFACE,
            wraplength=420,
            justify="left",
        ).pack(anchor="w", pady=(0, 10))

        # Simple benefits box
        box = tk.Frame(pad, bg=C_SURFACE_2, bd=1, relief="solid", highlightbackground=C_BORDER, highlightthickness=1)
        box.pack(fill="x", pady=(0, 12), ipady=5, ipadx=8)

        bullets = [
            ("Always Available", "Connect your phone anytime while your PC is on"),
            ("Silent Startup", "Runs quietly in the system tray on Windows boot"),
            ("Low Resource Usage", "Minimal background footprint without impacting performance")
        ]

        for title, desc in bullets:
            row = tk.Frame(box, bg=C_SURFACE_2)
            row.pack(fill="x", padx=8, pady=2)
            tk.Label(
                row,
                text=title,
                font=F_BODY_STRONG,
                fg=C_ACCENT,
                bg=C_SURFACE_2,
                width=18,
                anchor="w"
            ).pack(side="left")
            tk.Label(
                row,
                text=desc,
                font=F_SMALL,
                fg=C_TEXT,
                bg=C_SURFACE_2,
                anchor="w"
            ).pack(side="left", fill="x", expand=True)

        # Action Buttons Row
        btn_row = tk.Frame(pad, bg=C_SURFACE)
        btn_row.pack(fill="x", side="bottom", pady=(4, 0))

        def _on_enable():
            self.start_boot_var.set(True)
            self.save_settings()
            mark_first_run_startup_prompt_done()
            dlg.destroy()

        def _on_skip():
            mark_first_run_startup_prompt_done()
            dlg.destroy()

        dlg.protocol("WM_DELETE_WINDOW", _on_skip)

        # Secondary Button ("Not Now")
        tk.Button(
            btn_row,
            text="Not Now",
            font=F_BODY,
            fg=C_TEXT_DIM,
            bg=C_SURFACE_2,
            activeforeground=C_TEXT,
            activebackground=C_SURFACE_3,
            bd=0,
            relief="flat",
            cursor="hand2",
            padx=14,
            pady=6,
            command=_on_skip,
        ).pack(side="right", padx=(10, 0))

        # Primary Button ("Enable Start with Windows")
        tk.Button(
            btn_row,
            text="Enable Start with Windows",
            font=F_BODY_STRONG,
            fg=C_BLACK,
            bg=C_ACCENT,
            activeforeground=C_BLACK,
            activebackground="#06b6d4",
            bd=0,
            relief="flat",
            cursor="hand2",
            padx=16,
            pady=6,
            command=_on_enable,
        ).pack(side="right")

        dlg.update_idletasks()
        dlg.deiconify()
        dlg.grab_set()

    def on_driver_progress(self, driver_name: str, percent: int, stage_text: str, status: str = "running"):
        """Driverless architecture - no-op."""
        pass

    def _update_driver_progress_ui(self, driver_name: str, percent: int, stage_text: str, status: str = "running"):
        pass

    def open_how_to_connect_dialog(self):
        """Displays quick connection steps for iPhone/Android and 1-click Windows Firewall authorization."""
        dlg = tk.Toplevel(self.root)
        dlg.withdraw()
        dlg.title("PCDeck — How to Connect & Troubleshoot")
        dlg.resizable(False, False)
        dlg.configure(bg=C_SURFACE)
        dlg.transient(self.root)
        apply_crisp_window_icon(dlg)

        dw = 500
        dh = 410
        try:
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            x = max(0, (sw - dw) // 2)
            y = max(0, (sh - dh) // 2)
            dlg.geometry(f"{dw}x{dh}+{x}+{y}")
        except Exception:
            dlg.geometry(f"{dw}x{dh}")

        pad = tk.Frame(dlg, bg=C_SURFACE, padx=20, pady=16)
        pad.pack(fill="both", expand=True)

        tk.Label(
            pad,
            text="HOW TO CONNECT",
            font=(F_FAMILY, 8, "bold"),
            fg=C_BLACK,
            bg=C_ACCENT,
            padx=6,
            pady=2,
        ).pack(anchor="w", pady=(0, 6))

        tk.Label(
            pad,
            text="Zero-Install Wireless Connection",
            font=(F_FAMILY, 13, "bold"),
            fg=C_TEXT,
            bg=C_SURFACE,
            anchor="w",
        ).pack(fill="x", pady=(2, 6))

        steps = [
            "1. Same Wi-Fi: Connect PC and phone to the same Wi-Fi router (or phone hotspot).",
            "2. Turn off PC VPN: If using NordVPN, ExpressVPN or work VPN, pause it or allow LAN traffic.",
            "3. iPhone, iPad & Android: Open phone Camera, scan QR code, and tap 'Launch Web Remote'.",
            "4. Instant Control: Trackpad, keyboard, and screen mirror load in browser (no app needed).",
        ]
        for step in steps:
            tk.Label(
                pad,
                text=step,
                font=F_BODY,
                fg=C_TEXT_DIM,
                bg=C_SURFACE,
                justify="left",
                anchor="w",
                wraplength=450,
            ).pack(fill="x", pady=1)

        # Troubleshooting / Firewall Box
        fw_box = tk.Frame(pad, bg=C_SURFACE_2, bd=1, relief="solid", padx=12, pady=8)
        fw_box.pack(fill="x", pady=(10, 0))

        tk.Label(
            fw_box,
            text="CANNOT CONNECT / CONNECTION TIMEOUT?",
            font=(F_FAMILY, 8, "bold"),
            fg=C_WARNING,
            bg=C_SURFACE_2,
            anchor="w",
        ).pack(fill="x", pady=(0, 2))

        tk.Label(
            fw_box,
            text="If your network profile is set to Public or connection times out, Windows Firewall may be blocking Port 8000.",
            font=(F_FAMILY, 8),
            fg=C_TEXT_DIM,
            bg=C_SURFACE_2,
            justify="left",
            anchor="w",
            wraplength=440,
        ).pack(fill="x", pady=(0, 6))

        def _elevate_firewall():
            try:
                import ctypes
                cmd = 'netsh advfirewall firewall add rule name="PCDeck Pro Port 8000" dir=in action=allow protocol=TCP localport=8000 profile=any & netsh advfirewall firewall add rule name="PCDeck Pro UDP Discovery" dir=in action=allow protocol=UDP localport=8001 profile=any'
                ctypes.windll.shell32.ShellExecuteW(None, "runas", "cmd.exe", f"/c {cmd}", None, 0)
                self.show_toast("Windows Firewall rule requested (Check UAC prompt)", "info")
            except Exception as ex:
                self.show_toast(f"Firewall error: {ex}", "error")

        tk.Button(
            fw_box,
            text="Allow PCDeck in Windows Firewall (Port 8000)",
            font=(F_FAMILY, 8, "bold"),
            fg=C_BG,
            bg=C_ACCENT,
            activeforeground=C_BG,
            activebackground=C_ACCENT_HOVER,
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2",
            command=_elevate_firewall,
        ).pack(anchor="w")

        btn_row = tk.Frame(pad, bg=C_SURFACE)
        btn_row.pack(fill="x", side="bottom", pady=(12, 0))

        tk.Button(
            btn_row,
            text="Visit Web Guide →",
            font=(F_FAMILY, 9, "bold"),
            fg="#ffffff",
            bg="#1b44d8",
            activeforeground="#ffffff",
            activebackground="#1436b0",
            bd=0,
            padx=14,
            pady=6,
            cursor="hand2",
            command=lambda: webbrowser.open("https://getpcdeck.com/guides/"),
        ).pack(side="left")

        tk.Button(
            btn_row,
            text="Close",
            font=F_BODY,
            fg=C_TEXT_DIM,
            bg=C_SURFACE_2,
            activeforeground=C_TEXT,
            activebackground=C_SURFACE_3,
            bd=0,
            padx=14,
            pady=6,
            cursor="hand2",
            command=dlg.destroy,
        ).pack(side="right")

        dlg.deiconify()
        dlg.lift()
        dlg.focus_force()

    def open_license_dialog(self):
        """Open native license activation and management dialog."""
        self.license_info = load_pc_license()
        self.is_pc_pro = self.license_info.get("pro_active", False)

        dlg = tk.Toplevel(self.root)
        dlg.withdraw()  # Prevent top-left flash
        dlg.title("PCDeck Pro - License Activation")
        dlg.resizable(False, False)
        dlg.configure(bg=C_SURFACE)
        dlg.transient(self.root)

        apply_crisp_window_icon(dlg)

        # Center on parent window
        try:
            x = self.root.winfo_x() + max(0, (self.root.winfo_width() // 2) - 230)
            y = self.root.winfo_y() + max(0, (self.root.winfo_height() // 2) - 155)
            dlg.geometry(f"460x310+{x}+{y}")
        except Exception:
            dlg.geometry("460x310")

        pad = tk.Frame(dlg, bg=C_SURFACE, padx=20, pady=16)
        pad.pack(fill="both", expand=True)

        tk.Label(
            pad,
            text="PCDeck Pro License",
            font=F_TITLE,
            fg=C_TEXT,
            bg=C_SURFACE,
        ).pack(anchor="w")

        status_text = "Status: Lifetime Pro License Active" if self.is_pc_pro else "Status: Free Edition (30 FPS & Standard LAN)"
        status_color = "#ffd700" if self.is_pc_pro else C_TEXT_DIM
        tk.Label(
            pad,
            text=status_text,
            font=F_BODY_STRONG,
            fg=status_color,
            bg=C_SURFACE,
        ).pack(anchor="w", pady=(2, 8))

        tk.Label(
            pad,
            text="Pay once: $3.99 — No subscriptions, no ads, free updates forever.\nEnables 60/120 FPS screen streaming, 1080p 60fps webcam, uncapped LAN transfers, and custom themes across all devices.",
            font=F_SMALL,
            fg=C_TEXT_DIM,
            bg=C_SURFACE,
            wraplength=420,
            justify="left",
        ).pack(anchor="w", pady=(0, 10))

        tk.Label(pad, text="LICENSE KEY:", font=F_LABEL, fg=C_TEXT, bg=C_SURFACE).pack(anchor="w")
        key_entry = tk.Entry(
            pad,
            font=(F_MONO, 10),
            bg=C_INPUT,
            fg=C_TEXT,
            insertbackground=C_ACCENT,
            bd=1,
            relief="solid",
        )
        key_entry.pack(fill="x", pady=(4, 12), ipady=4)
        initial_key = ""
        if self.is_pc_pro and self.license_info.get("key"):
            initial_key = self.license_info["key"]
        if not initial_key:
            try:
                from server.license_manager import get_stored_license_record
                stored = get_stored_license_record()
                if stored.get("key"):
                    initial_key = stored["key"]
            except Exception:
                pass
        if not initial_key:
            try:
                import re
                clip = (self.root.clipboard_get() or "").strip().lower()
                if re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", clip):
                    initial_key = clip
            except Exception:
                pass
        if initial_key:
            key_entry.insert(0, initial_key)

        btn_row = tk.Frame(pad, bg=C_SURFACE)
        btn_row.pack(fill="x", pady=(4, 0))

        def on_activate():
            k = key_entry.get().strip()
            if not k:
                messagebox.showwarning("PCDeck License", "Please enter a license key.", parent=dlg)
                return
            if k.lower().startswith("pay_"):
                messagebox.showwarning("Payment ID Detected", "You entered a Payment ID (starts with 'pay_').\n\nPlease enter the 36-character License Key (UUID) sent in your Dodo Payments confirmation email or receipt.", parent=dlg)
                return
            if k.lower().startswith("lic_"):
                messagebox.showwarning("License ID Detected", "You entered a License ID (starts with 'lic_').\n\nPlease enter the 36-character License Key (UUID) sent in your Dodo Payments confirmation email or receipt.", parent=dlg)
                return

            ok, msg, _ = activate_license_online(k)
            if ok:
                self.is_pc_pro = True
                self.license_info = load_pc_license()
                self._apply_pro_state()
                messagebox.showinfo("PCDeck Pro", msg, parent=dlg)
                dlg.destroy()
            else:
                messagebox.showerror("Activation Failed", msg, parent=dlg)

        tk.Button(
            btn_row,
            text="Activate License Key",
            font=F_BODY_STRONG,
            fg="#000000",
            bg="#eab308",
            bd=0,
            cursor="hand2",
            padx=12,
            pady=6,
            command=on_activate,
        ).pack(side="left", fill="x", expand=True, padx=(0, 6))

        tk.Button(
            btn_row,
            text="Get Pro ($3.99)",
            font=F_BODY_STRONG,
            fg=C_TEXT,
            bg=C_SURFACE_3,
            bd=0,
            cursor="hand2",
            padx=12,
            pady=6,
            command=lambda: open_url_in_browser(DODO_CHECKOUT_URL),
        ).pack(side="right", padx=(6, 0))

        # Regional PPP check for developing / non-Western markets
        show_ppp = True
        try:
            if sys.platform == "win32":
                import ctypes
                geo = ctypes.windll.kernel32.GetUserGeoID(16)
                buf = ctypes.create_unicode_buffer(10)
                ctypes.windll.kernel32.GetGeoInfoW(geo, 4, buf, 10, 0)
                code = buf.value.strip().upper()
                western_countries = {"US", "CA", "GB", "AU", "NZ", "DE", "FR", "IT", "ES", "NL", "SE", "NO", "DK", "FI", "CH", "AT", "BE", "IE", "LU", "JP"}
                if code in western_countries:
                    show_ppp = False
                elif not code:
                    import time
                    tz_offset_hours = -time.timezone / 3600
                    if -10 <= tz_offset_hours <= 2 and any(z in time.tzname[0].upper() for z in ("EST", "EDT", "CST", "CDT", "MST", "MDT", "PST", "PDT", "GMT", "BST", "CET", "CEST", "WET")):
                        show_ppp = False
        except Exception:
            pass

        if show_ppp:
            ppp_lbl = tk.Label(
                pad,
                text="Check your local price at checkout (PPP enabled) →",
                font=(F_BODY, 8, "underline"),
                fg=C_ACCENT,
                bg=C_SURFACE,
                cursor="hand2"
            )
            ppp_lbl.pack(pady=(8, 0))
            ppp_lbl.bind("<Button-1>", lambda e: open_url_in_browser(DODO_CHECKOUT_URL))

        dlg.update_idletasks()
        dlg.deiconify()
        dlg.grab_set()

    def _apply_pro_state(self):
        self.is_pc_pro = True
        self.license_info = load_pc_license()
        try:
            from server.main import set_pro_client
            set_pro_client(True)
        except Exception:
            pass

        self.root.title(f"PCDeck Pro v{CURRENT_DESKTOP_VERSION_NAME} - Wireless PC Touch Deck & Streamer")
        if hasattr(self, "title_pro_badge") and self.title_pro_badge.winfo_exists():
            self.title_pro_badge.pack(side="left", padx=(6, 0))

        if hasattr(self, "lic_status_lbl") and self.lic_status_lbl.winfo_exists():
            self.lic_status_lbl.config(text="PRO ACTIVE", fg="#ffd700")

        if hasattr(self, "lic_btn") and self.lic_btn.winfo_exists():
            self.lic_btn.config(
                text="Manage Pro",
                fg="#ffd700",
                bg=C_SURFACE_3,
            )

        self.update_fps()

    def start_server(self):
        if self.is_running and self.server_thread and self.server_thread.is_alive():
            return

        def run_uvicorn():
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                config = uvicorn.Config(
                    app=app,
                    host="0.0.0.0",
                    port=SERVER_PORT,
                    log_level="error",
                    access_log=False,
                    loop="asyncio",
                    ws_ping_interval=10.0,
                    ws_ping_timeout=10.0,
                )
                self.server = uvicorn.Server(config)
                log_debug(f"Starting uvicorn server on port {SERVER_PORT}...")
                self.server.run()
                log_debug("Uvicorn server finished.")
            except BaseException as e:
                log_debug(f"Uvicorn server exited or failed: {e}")
            finally:
                self.is_running = False
                try:
                    if hasattr(self, "root") and self.root:
                        self.root.after(0, lambda: hasattr(self, "status_pill") and self.status_pill.winfo_exists() and self.status_pill.config(text="● SERVER STOPPED", bg=C_DANGER, fg=C_TEXT))
                except Exception:
                    pass

        self.is_running = True
        self.server_thread = threading.Thread(target=run_uvicorn, daemon=True)
        self.server_thread.start()
        if hasattr(self, "status_pill") and self.status_pill.winfo_exists():
            self.status_pill.config(text="● SERVER ONLINE", bg=C_SUCCESS, fg=C_BG)

    def restart_server(self):
        if self.server:
            self.server.should_exit = True
            time.sleep(0.5)
        self.is_running = False
        self.start_server()
        self.refresh_network_ip()
        self.status_pill.config(
            text=f"● SERVER: [ONLINE] ({getattr(self, 'current_ip', LOCAL_IP)}:{SERVER_PORT})",
            bg=C_SUCCESS,
            fg=C_BG,
        )
        messagebox.showinfo("PCDeck", "Server restarted successfully!")

    def stop_server(self):
        if self.server:
            self.server.should_exit = True
        self.is_running = False
        self.status_pill.config(text="● SERVER: [OFFLINE]", bg=C_DANGER, fg=C_TEXT)
        messagebox.showinfo("PCDeck", "Server stopped. Click Restart Server to resume.")

    def _init_wifi_reconnector(self):
        """Initializes Wi-Fi scanning and startup auto-reconnection in background."""
        threading.Thread(target=self._startup_wifi_worker, daemon=True).start()

    def _startup_wifi_worker(self):
        """Passive background thread for startup Wi-Fi detection without channel sweeps."""
        try:
            # Auto-heal: ensure Windows WLAN autoconfig and Wi-Fi radio are switched on
            try:
                restore_all_wlan_autoconfig()
                ensure_wifi_radio_on()
            except Exception:
                pass

            current = get_current_wifi_status()
            if current["state"] == "connected" and current["ssid"]:
                self.root.after(0, lambda: self._update_wifi_status_ui(
                    f"● {current['ssid']} ({current['signal']})", C_SUCCESS, C_BG
                ))
            else:
                self.root.after(0, lambda: self._update_wifi_status_ui("● LAN Active", C_SUCCESS, C_BG))

            # Populate combo dropdown with active connection & saved profiles
            self._do_wifi_scan_sync()
        except Exception:
            pass

    def _start_wifi_watchdog(self):
        """Begin continuous link monitoring only if explicitly enabled by user."""
        if not self.auto_wifi_var.get():
            return
        try:
            start_watchdog(on_event=self._on_wifi_event)
        except Exception:
            pass

    def _on_wifi_event(self, event: dict):
        """Watchdog callback. Runs on the watchdog thread - marshal to Tk."""
        try:
            if not (hasattr(self, "root") and self.root and self.root.winfo_exists()):
                return
            kind = event.get("type", "")
            health = event.get("health") or (event.get("report") or {}).get("health") or {}

            if kind == "repairing":
                text, bg, fg = "● Reconnecting...", C_WARNING, C_BG
            elif kind == "repaired":
                ssid = health.get("ssid") or "Wi-Fi"
                text, bg, fg = f"● {ssid} ({health.get('signal', '')})", C_SUCCESS, C_BG
            elif kind == "repair_failed":
                text, bg, fg = "● No network in range", C_DANGER, C_TEXT
            elif health.get("status") == "ok":
                ssid = health.get("ssid") or "Wi-Fi"
                text, bg, fg = f"● {ssid} ({health.get('signal', '')})", C_SUCCESS, C_BG
            elif health.get("status") == "no_lease":
                text, bg, fg = "● No IP address", C_WARNING, C_BG
            elif health.get("status") == "adapter_disabled":
                text, bg, fg = "● Adapter disabled", C_DANGER, C_TEXT
            elif health.get("status") == "no_radio":
                text, bg, fg = "● No Wi-Fi adapter", C_DANGER, C_TEXT
            else:
                text, bg, fg = "● Disconnected", C_DANGER, C_TEXT

            self.root.after(0, lambda: self._update_wifi_status_ui(text, bg, fg))

            # The LAN IP changes when we land on a different network, and every
            # QR code and pairing URL is built from it.
            if kind == "repaired" or health.get("status") == "ok":
                self.root.after(0, self.refresh_network_ip)
        except Exception:
            pass

    def _update_wifi_status_ui(self, text: str, bg: str, fg: str):
        try:
            if hasattr(self, "wifi_status_badge") and self.wifi_status_badge.winfo_exists():
                self.wifi_status_badge.config(text=text, bg=bg, fg=fg)
        except tk.TclError:
            # Window was destroyed between the after() call and this callback.
            pass

    def _on_wifi_scan_clicked(self):
        self._update_wifi_status_ui("● Scanning...", C_WARNING, C_BG)
        threading.Thread(target=self._do_wifi_scan_async, daemon=True).start()

    def _do_wifi_scan_async(self):
        try:
            self._do_wifi_scan_sync()
            current = get_current_wifi_status()
            if current["state"] == "connected" and current["ssid"]:
                self.root.after(0, lambda: self._update_wifi_status_ui(
                    f"● {current['ssid']} ({current['signal']})", C_SUCCESS, C_BG
                ))
            else:
                self.root.after(0, lambda: self._update_wifi_status_ui("● Disconnected", C_DANGER, C_TEXT))
        except Exception:
            pass

    def _do_wifi_scan_sync(self):
        try:
            nets = scan_visible_networks()
            current = get_current_wifi_status()
            active_ssid = current.get("ssid", "")

            if not nets and active_ssid:
                nets = [{"ssid": active_ssid, "signal": current.get("signal", "100%"), "is_saved": True}]

            display_items = []
            selected_idx = 0

            for i, n in enumerate(nets):
                saved_tag = " [Saved]" if n.get("is_saved") else ""
                sig = f" ({n['signal']})" if n.get("signal") and n["signal"] != "Saved" else ""
                label = f"{n['ssid']}{saved_tag}{sig}"
                display_items.append(label)
                if active_ssid and n["ssid"].lower() == active_ssid.lower():
                    selected_idx = i

            def update_combo():
                if hasattr(self, "wifi_combo") and self.wifi_combo.winfo_exists():
                    self.wifi_combo["values"] = display_items
                    if display_items:
                        self.wifi_combo.current(selected_idx)
                        self.wifi_select_var.set(display_items[selected_idx])

            self.root.after(0, update_combo)
        except Exception:
            pass

    def _on_wifi_connect_clicked(self):
        val = self.wifi_select_var.get()
        if not val:
            messagebox.showinfo("Wi-Fi Connect", "Please select a Wi-Fi network from the list first.")
            return

        # Extract clean SSID
        clean_ssid = re.sub(r"^[^\w\s-]+\s*", "", val)
        clean_ssid = re.sub(r"\s*\[Saved\].*", "", clean_ssid)
        clean_ssid = re.sub(r"\s*\(\d+%\).*", "", clean_ssid).strip()

        self._update_wifi_status_ui(f"● Connecting to {clean_ssid[:12]}...", C_WARNING, C_BG)

        def worker():
            ok, msg = connect_to_profile(clean_ssid)
            if ok:
                for _ in range(6):
                    time.sleep(1)
                    st = get_current_wifi_status()
                    if st["state"] == "connected" and st["ssid"]:
                        self.root.after(0, lambda: self._update_wifi_status_ui(
                            f"● {st['ssid']} ({st['signal']})", C_SUCCESS, C_BG
                        ))
                        self.root.after(0, self.refresh_network_ip)
                        return
                st = get_current_wifi_status()
                if st["state"] == "connected":
                    self.root.after(0, lambda: self._update_wifi_status_ui(
                        f"● {st['ssid']}", C_SUCCESS, "#ffffff"
                    ))
                    self.root.after(0, self.refresh_network_ip)
                else:
                    self.root.after(0, lambda: self._update_wifi_status_ui("● Connect Timeout", C_DANGER, "#ffffff"))
            else:
                self.root.after(0, lambda: self._update_wifi_status_ui("● Connect Failed", C_DANGER, "#ffffff"))

        threading.Thread(target=worker, daemon=True).start()

    def _on_auto_wifi_toggle(self):
        enabled = bool(self.auto_wifi_var.get())
        update_wifi_config(auto_reconnect_on_launch=enabled, auto_heal=enabled)
        # Take effect immediately instead of waiting for the next launch.
        try:
            if enabled:
                start_watchdog(on_event=self._on_wifi_event)
            else:
                stop_watchdog()
        except Exception:
            pass

    def _metrics_bg_worker(self):
        """Dedicated background thread for heavy metrics, subprocesses, and network queries.
        Keeps Tkinter UI thread 100% responsive and free of blocking calls (netsh, ipconfig, disk I/O, crypto).
        """
        tick = 0
        while True:
            try:
                # 1. Non-blocking IP detection
                ip = get_local_ip()
                self._cached_ip = ip

                # 2. Wi-Fi status check (netsh wlan show interfaces & ipconfig)
                # Query on startup, when IP changes, or every 45s (netsh runs completely off the UI thread!)
                ip_changed = (ip != getattr(self, "_last_bg_ip", ""))
                if ip_changed or (tick % 15 == 0):
                    self._last_bg_ip = ip
                    try:
                        self._cached_wifi_status = get_current_wifi_status(force=ip_changed)
                    except Exception:
                        pass

                # 3. License disk check (only once every 30s)
                if tick % 10 == 0:
                    try:
                        lic = load_pc_license()
                        self._cached_pro_active = lic.get("pro_active", False)
                    except Exception:
                        pass

                tick += 1
            except Exception as e:
                log_debug(f"_metrics_bg_worker error: {e}")
            time.sleep(3.0)

    def _start_metrics_loop(self):
        def update_metrics():
            try:
                # 1. Update active client count (deduplicated by unique device IP)
                try:
                    from server.main import get_unique_client_count, get_connected_client_ips
                except ImportError:
                    from main import get_unique_client_count, get_connected_client_ips

                count = get_unique_client_count()
                client_ips = list(get_connected_client_ips())
                if hasattr(self, "client_badge") and self.client_badge.winfo_exists():
                    self.client_badge.config(text=f"{count} Client{'s' if count != 1 else ''}")

                # Update Connected Clients box
                if hasattr(self, "lbl_no_clients") and self.lbl_no_clients.winfo_exists():
                    if count > 0:
                        ip_display = ", ".join(client_ips) if client_ips else "1 Device"
                        self.lbl_no_clients.config(
                            text=f"● Connected: {ip_display} ({count} active device{'s' if count != 1 else ''})",
                            fg=self.c_accent,
                        )
                    else:
                        self.lbl_no_clients.config(
                            text="Waiting for mobile device to connect... Open PCDeck on your phone and point camera at the QR code.",
                            fg=self.c_text_dim,
                        )

                # Pro License Badge sync (from in-memory cache)
                self.is_pc_pro = getattr(self, "_cached_pro_active", self.is_pc_pro)
                try:
                    try:
                        from server.main import is_pro_client, set_pro_client
                    except ImportError:
                        from main import is_pro_client, set_pro_client
                    pro_active = is_pro_client()
                    if not self.is_pc_pro and pro_active:
                        set_pro_client(False)
                        pro_active = False
                except Exception:
                    pro_active = False

                if hasattr(self, "root") and self.root.winfo_exists():
                    target_title = "PCDeck Pro - Wireless PC Touch Deck & Streamer" if (self.is_pc_pro or pro_active) else "PCDeck - Wireless PC Touch Deck & Streamer"
                    if self.root.title() != target_title:
                        self.root.title(target_title)

                if hasattr(self, "pro_badge") and self.pro_badge.winfo_exists():
                    if (self.is_pc_pro or pro_active) and count > 0:
                        if not self.pro_badge.winfo_ismapped():
                            self.pro_badge.pack(side="right", padx=(0, 6))
                    else:
                        if self.pro_badge.winfo_ismapped():
                            self.pro_badge.pack_forget()

                if hasattr(self, "title_pro_badge") and self.title_pro_badge.winfo_exists():
                    if self.is_pc_pro or pro_active:
                        if not self.title_pro_badge.winfo_ismapped():
                            self.title_pro_badge.pack(side="left", padx=(6, 0))
                    else:
                        if not self.is_pc_pro and self.title_pro_badge.winfo_ismapped():
                            self.title_pro_badge.pack_forget()

                # Dynamic Pro license button & label update
                is_currently_pro = self.is_pc_pro or pro_active
                if is_currently_pro:
                    if hasattr(self, "lic_status_lbl") and self.lic_status_lbl.winfo_exists():
                        if self.lic_status_lbl.cget("text") != "PRO ACTIVE":
                            self.lic_status_lbl.config(text="PRO ACTIVE", fg="#ffd700")
                    if hasattr(self, "lic_btn") and self.lic_btn.winfo_exists():
                        if self.lic_btn.cget("text") != "Manage Pro":
                            self.lic_btn.config(text="Manage Pro", fg="#ffd700", bg=C_SURFACE_3)
                else:
                    if hasattr(self, "lic_status_lbl") and self.lic_status_lbl.winfo_exists():
                        if self.lic_status_lbl.cget("text") != "FREE EDITION":
                            self.lic_status_lbl.config(text="FREE EDITION", fg=C_TEXT_DIM)
                    if hasattr(self, "lic_btn") and self.lic_btn.winfo_exists():
                        if self.lic_btn.cget("text") != "Upgrade to Pro ($3.99)":
                            self.lic_btn.config(text="Upgrade to Pro ($3.99)", fg="#000000", bg="#eab308")

                # 2. Dynamic Hotspot / Wi-Fi IP auto-detection (from in-memory cache)
                latest_ip = getattr(self, "_cached_ip", getattr(self, "current_ip", LOCAL_IP))
                if not hasattr(self, "current_ip") or self.current_ip != latest_ip:
                    self.current_ip = latest_ip
                    self.server_url = f"http://{latest_ip}:{SERVER_PORT}"
                    if hasattr(self, "ip_entry") and self.ip_entry.winfo_exists():
                        self.ip_entry.config(state="normal")
                        self.ip_entry.delete(0, tk.END)
                        self.ip_entry.insert(0, self.server_url)
                        self.ip_entry.config(state="readonly", readonlybackground=C_INPUT, fg=C_ACCENT)
                    self._generate_qr_image()

                # 3. Connection status indicator
                if hasattr(self, "phone_status_lbl") and self.phone_status_lbl.winfo_exists():
                    if latest_ip.startswith("127."):
                        self.phone_status_lbl.config(
                            text="● Connect USB Tethering or Phone Wi-Fi",
                            fg=C_WARNING,
                        )
                    elif latest_ip.startswith("192.168.42."):
                        self.phone_status_lbl.config(
                            text=f"● USB Tethered ({latest_ip})",
                            fg=C_SUCCESS,
                        )
                    elif latest_ip.startswith("192.168.43.") or latest_ip.startswith("172."):
                        self.phone_status_lbl.config(
                            text=f"● Phone Hotspot ({latest_ip})",
                            fg=C_SUCCESS,
                        )
                    else:
                        self.phone_status_lbl.config(
                            text=f"● Network Online ({latest_ip})",
                            fg=C_SUCCESS,
                        )

                # 4. Wi-Fi Status Badge update (instant in-memory cache read, zero subprocess calls)
                st = getattr(self, "_cached_wifi_status", {"state": "connected", "ssid": "", "signal": "0%"})
                if hasattr(self, "wifi_status_badge") and self.wifi_status_badge.winfo_exists():
                    current_badge = self.wifi_status_badge.cget("text")
                    if "Connecting" not in current_badge and "Scanning" not in current_badge:
                        if st.get("state") == "connected" and st.get("ssid"):
                            self.wifi_status_badge.config(
                                text=f"● {st['ssid']} ({st.get('signal', '')})",
                                bg=C_SUCCESS,
                                fg="#ffffff",
                            )
                        elif st.get("state") != "connected":
                            self.wifi_status_badge.config(
                                text="● Disconnected",
                                bg=C_DANGER,
                                fg="#ffffff",
                            )

                # 5. Audio streaming status
                if hasattr(self, "audio_status_lbl") and self.audio_status_lbl.winfo_exists():
                    try:
                        try:
                            from server.audio_streamer import audio_streamer
                        except ImportError:
                            from audio_streamer import audio_streamer

                        listeners = getattr(audio_streamer, "active_listeners", 0)
                        capturing = bool(
                            audio_streamer.is_running
                            and audio_streamer.capture_thread
                            and audio_streamer.capture_thread.is_alive()
                        )

                        if listeners > 0:
                            self.audio_status_lbl.config(
                                text=f"● Streaming to {listeners} phone{'s' if listeners != 1 else ''}",
                                fg=C_SUCCESS,
                            )
                        elif capturing:
                            self.audio_status_lbl.config(text="● Ready", fg=C_ACCENT)
                        else:
                            self.audio_status_lbl.config(text="● Off", fg=C_TEXT_DIM)
                    except Exception:
                        self.audio_status_lbl.config(text="● Unavailable", fg=C_WARNING)

                # 6. Auto-revive Uvicorn Server Watchdog
                if not self.is_running or not (self.server_thread and self.server_thread.is_alive()):
                    log_debug("[Watchdog] Uvicorn server thread is inactive, auto-starting server...")
                    self.is_running = False
                    self.start_server()
            except Exception:
                pass
            finally:
                if hasattr(self, "root") and self.root.winfo_exists():
                    self.root.after(3000, update_metrics)

        self.root.after(1000, update_metrics)

    def open_phone_remote(self):
        """Open the Tkinter Adaptive Phone Remote Controller window."""
        try:
            if hasattr(self, "phone_remote_win") and self.phone_remote_win and self.phone_remote_win.win.winfo_exists():
                self.phone_remote_win.win.lift()
                self.phone_remote_win.win.focus_force()
                return
            self.phone_remote_win = PhoneRemoteWindow(self.root, self)
        except Exception as e:
            messagebox.showerror("Phone Controller Error", f"Could not open Phone Controller: {e}")

    def quick_wireless_connect(self):
        """Switch USB to wireless mode or open pairing dialog."""
        devs = get_connected_devices()
        active = [d for d in devs if d["state"] == "device"]
        if active and not active[0]["is_wifi"]:
            serial = active[0]["serial"]
            ok, msg = switch_device_to_wireless(serial)
            if ok:
                messagebox.showinfo("Wireless Mode", f"{msg}\n\nYou can now unplug the USB cable.")
                return

        # Open wireless pairing dialog
        if hasattr(self, "phone_remote_win") and self.phone_remote_win and self.phone_remote_win.win.winfo_exists():
            self.phone_remote_win.open_wireless_dialog()
        else:
            self.open_phone_remote()
            if hasattr(self, "phone_remote_win") and self.phone_remote_win:
                self.phone_remote_win.open_wireless_dialog()

    # ---------------------------------------------------------------------------
    # System Tray & Quick-Access Taskbar Flyout Card
    # ---------------------------------------------------------------------------
    def _init_tray_icon(self):
        """Initializes the Windows System Tray icon using pystray."""
        try:
            import pystray
            icon_image = self._get_tray_icon_image()
            menu = pystray.Menu(
                pystray.MenuItem(
                    "Quick Connect (QR Code)",
                    lambda: self.root.after(0, self.toggle_quick_flyout),
                    default=True,
                ),
                pystray.MenuItem(
                    "Open Full Dashboard",
                    lambda: self.root.after(0, self.open_dashboard),
                ),
                pystray.MenuItem(
                    "Copy Web Remote Link",
                    lambda: self.root.after(0, self.copy_ip),
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    "Start with Windows",
                    lambda: self.root.after(0, self.toggle_autostart_from_tray),
                    checked=lambda item: bool(getattr(self, "autostart_enabled", False)),
                ),
                pystray.MenuItem(
                    "Rate on Microsoft Store",
                    lambda: self.root.after(0, self._on_review_rate),
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    "Exit PCDeck",
                    lambda: self.root.after(0, self.quit_application),
                ),
            )
            self.tray_icon = pystray.Icon(
                "PCDeck",
                icon_image,
                f"PCDeck v{CURRENT_DESKTOP_VERSION_NAME} — {getattr(self, 'current_ip', '127.0.0.1')}:{SERVER_PORT}",
                menu=menu,
            )
            self.tray_icon.run_detached()
        except Exception as e:
            log_debug(f"Failed to initialize system tray icon: {e}")
            self.tray_icon = None

    def _get_tray_icon_image(self):
        """Loads or renders a crisp 64x64 icon for the Windows taskbar tray."""
        master_png = find_asset(
            "PCDeck_Mouse_Logo.png",
            "PCDeck_Master_Logo.png",
            "PCDeck_Logo.png",
            "icon.png",
            "favicon.png",
        )
        if master_png:
            try:
                img = Image.open(master_png).convert("RGBA")
                return img.resize((64, 64), Image.Resampling.LANCZOS)
            except Exception:
                pass
        fallback = Image.new("RGBA", (64, 64), (24, 24, 27, 255))
        from PIL import ImageDraw
        d = ImageDraw.Draw(fallback)
        d.rounded_rectangle([8, 8, 56, 56], radius=12, fill=(56, 189, 248, 255))
        return fallback

    @staticmethod
    def _get_msix_aumid() -> Optional[str]:
        """
        Returns PackageFamilyName!ApplicationId if running inside an MSIX package, else None.
        When unpackaged (e.g. standalone portable PCDeck.exe), returns None to avoid
        branding notifications with Windows PowerShell's AUMID.
        """
        if sys.platform != "win32":
            return None
        try:
            buf_len = ctypes.c_uint32(0)
            res = ctypes.windll.kernel32.GetCurrentPackageFamilyName(ctypes.byref(buf_len), None)
            if res == 122:  # ERROR_INSUFFICIENT_BUFFER
                buf = ctypes.create_unicode_buffer(buf_len.value)
                if ctypes.windll.kernel32.GetCurrentPackageFamilyName(ctypes.byref(buf_len), buf) == 0:
                    return f"{buf.value}!PCDeck"
        except Exception:
            pass
        return None

    def show_toast_notification(self, title: str, message: str, action_url: Optional[str] = None, action_label: Optional[str] = None) -> bool:
        """Dispatches a native Windows 10/11 interactive toast notification banner asynchronously without blocking UI."""
        if sys.platform != "win32":
            return False

        # Only use Windows Runtime Toast Notification if running inside an MSIX package (Microsoft Store).
        # Unpackaged/portable apps do not have a registered AUMID, so return False and fall back
        # to PCDeck's own tray balloon notification to avoid displaying 'Windows PowerShell' branding.
        aumid = self._get_msix_aumid()
        if not aumid:
            return False

        def _dispatch():
            try:
                import subprocess
                action_xml = ""
                if action_url and action_label:
                    action_xml = f'<actions><action content="{action_label}" arguments="{action_url}" activationType="protocol"/></actions>'

                ps_script = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
$template = @"
<toast duration="long">
    <visual>
        <binding template="ToastGeneric">
            <text>{title}</text>
            <text>{message}</text>
        </binding>
    </visual>
    {action_xml}
</toast>
"@
$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($template)
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("{aumid}")
$notifier.Show($toast)
"""
                subprocess.Popen(
                    ["powershell", "-ExecutionPolicy", "Bypass", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_script],
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
                )
            except Exception as e:
                log_debug(f"show_toast_notification error: {e}")

        threading.Thread(target=_dispatch, daemon=True, name="PCDeck-ToastWorker").start()
        return True

    def show_notification(self, message: str, title: str = "PCDeck"):
        """Displays a desktop notification asynchronously without blocking the UI thread."""
        def _dispatch():
            if not getattr(self, "tray_icon", None):
                return
            try:
                if sys.platform == "win32":
                    import pystray._win32 as w
                    hicon = getattr(self.tray_icon, "_icon_handle", None)
                    # dwInfoFlags: NIIF_USER (0x04) | NIIF_LARGE_ICON (0x20) = 0x24 (36)
                    flags = 0x24 if hicon else 0x01
                    kwargs = {
                        "szInfo": message,
                        "szInfoTitle": title or "PCDeck",
                        "dwInfoFlags": flags,
                    }
                    if hicon:
                        kwargs["hBalloonIcon"] = hicon
                    self.tray_icon._message(
                        w.win32.NIM_MODIFY,
                        w.win32.NIF_INFO,
                        **kwargs
                    )
                    return
            except Exception as e:
                log_debug(f"Custom notification icon dispatch error: {e}")
            try:
                self.tray_icon.notify(message, title)
            except Exception:
                pass

        threading.Thread(target=_dispatch, daemon=True, name="PCDeck-NotifyWorker").start()

    def toggle_autostart_from_tray(self):
        """Toggles the 'Start with Windows' setting from the system tray context menu."""
        cur = not getattr(self, "autostart_enabled", False)
        self.autostart_enabled = cur
        self.start_boot_var.set(cur)
        self.save_settings()
        if self.tray_icon:
            try:
                self.tray_icon.update_menu()
            except Exception:
                pass

    def minimize_to_tray(self):
        """Minimizes the main window to the system tray so the server remains active."""
        try:
            if hasattr(self, "flyout") and self.flyout and self.flyout.winfo_exists():
                self.flyout.withdraw()
            self.root.withdraw()
            if not getattr(self, "_tray_minimized_notified", False):
                self._tray_minimized_notified = True
                self.show_notification(
                    "PCDeck is running in the background. Click icon to view QR code or dashboard.",
                    "PCDeck Server Active",
                )
        except Exception as e:
            log_debug(f"minimize_to_tray error: {e}")

    def open_dashboard(self):
        """Brings the main window to the foreground and deiconifies from tray."""
        try:
            if hasattr(self, "flyout") and self.flyout and self.flyout.winfo_exists():
                self.flyout.withdraw()
            self.root.deiconify()
            self.root.state("normal")
            self.root.lift()
            self.root.attributes("-topmost", True)
            self.root.after(250, lambda: self.root.attributes("-topmost", False))
            self.root.focus_force()

            # Dynamically build review card if eligible and not already shown
            if hasattr(self, "right_col") and (not hasattr(self, "review_card") or self.review_card is None):
                self.review_state = load_app_settings()
                if check_should_show_review_prompt(self.review_state):
                    self._build_review_card(self.right_col)
        except Exception as e:
            log_debug(f"open_dashboard error: {e}")

    def quit_application(self):
        """Clean non-blocking shutdown of background server, tray icon, and application."""
        # CRITICAL INVARIANT: Never explicitly CloseHandle or ReleaseMutex the single-instance
        # mutex here. Retaining the mutex handle until OS kernel process teardown prevents
        # a rapid re-launch race while sockets, threads, and UI resources are unmapping.
        if getattr(self, "tray_icon", None):
            tray = self.tray_icon
            self.tray_icon = None
            try:
                tray.visible = False
            except Exception:
                pass
            threading.Thread(target=tray.stop, daemon=True, name="PCDeck-TrayStop").start()
        try:
            if self.server:
                self.server.should_exit = True
        except Exception:
            pass
        try:
            if hasattr(self, "flyout") and self.flyout and self.flyout.winfo_exists():
                self.flyout.destroy()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def toggle_quick_flyout(self):
        """Toggles the clean, modern taskbar flyout card above the Windows system tray."""
        if hasattr(self, "flyout") and self.flyout and self.flyout.winfo_exists():
            if self.flyout.winfo_viewable():
                self.flyout.withdraw()
                return
            else:
                self.flyout.withdraw()
                self._update_flyout_content()
                self._position_flyout()
                self.flyout.deiconify()
                self.flyout.lift()
                self.flyout.focus_force()
                return

        self._build_quick_flyout()

    def _build_quick_flyout(self):
        """Creates the clean, modern Windows 11 flyout card above the system tray."""
        self.flyout = tk.Toplevel(self.root)
        self.flyout.withdraw()  # Crucial: keep hidden from OS window manager during construction to prevent top-left flash
        self.flyout.title("PCDeck Quick Access")
        self.flyout.overrideredirect(True)
        self.flyout.configure(bg="#18181b")
        self.flyout.attributes("-topmost", True)

        apply_crisp_window_icon(self.flyout)

        # Main container with subtle 1px border
        container = tk.Frame(
            self.flyout,
            bg="#18181b",
            highlightbackground="#3f3f46",
            highlightcolor="#3f3f46",
            highlightthickness=1,
            padx=14,
            pady=12,
        )
        container.pack(fill="both", expand=True)

        # 1. Top Header Row: Hostname, Status Pill, Close 'X'
        top_row = tk.Frame(container, bg="#18181b")
        top_row.pack(fill="x", pady=(0, 10))

        title_col = tk.Frame(top_row, bg="#18181b")
        title_col.pack(side="left")

        tk.Label(
            title_col,
            text="PCDeck",
            font=(F_FAMILY, 11, "bold"),
            fg="#f4f4f5",
            bg="#18181b",
        ).pack(anchor="w")

        try:
            hostname = socket.gethostname()
        except Exception:
            hostname = "PC"
        self.flyout_host_lbl = tk.Label(
            title_col,
            text=f"{hostname} • Port {SERVER_PORT}",
            font=(F_FAMILY, 8),
            fg="#a1a1aa",
            bg="#18181b",
        )
        self.flyout_host_lbl.pack(anchor="w")

        right_col = tk.Frame(top_row, bg="#18181b")
        right_col.pack(side="right")

        # Status Pill
        status_pill = tk.Frame(
            right_col,
            bg="#27272a",
            padx=8,
            pady=3,
            highlightbackground="#3f3f46",
            highlightthickness=1,
        )
        status_pill.pack(side="left", padx=(0, 6))

        tk.Label(
            status_pill,
            text="● Active",
            font=(F_FAMILY, 8, "bold"),
            fg="#22c55e",
            bg="#27272a",
        ).pack()

        # Close X
        close_btn = tk.Label(
            right_col,
            text="✕",
            font=(F_FAMILY, 9),
            fg="#a1a1aa",
            bg="#18181b",
            cursor="hand2",
            padx=4,
            pady=2,
        )
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda e: self.flyout.withdraw())
        close_btn.bind("<Enter>", lambda e: close_btn.config(fg="#f4f4f5"))
        close_btn.bind("<Leave>", lambda e: close_btn.config(fg="#a1a1aa"))

        # 2. QR Code Display Card
        qr_frame = tk.Frame(
            container,
            bg="#27272a",
            padx=10,
            pady=10,
            highlightbackground="#3f3f46",
            highlightthickness=1,
        )
        qr_frame.pack(fill="x", pady=(0, 8))

        self.flyout_qr_lbl = tk.Label(qr_frame, bg="#ffffff")
        self.flyout_qr_lbl.pack(pady=(0, 6))

        tk.Label(
            qr_frame,
            text="Scan with phone camera or PCDeck app",
            font=(F_FAMILY, 8),
            fg="#a1a1aa",
            bg="#27272a",
        ).pack()

        # 3. Web Remote URL Box
        web_box = tk.Frame(
            container,
            bg="#27272a",
            padx=8,
            pady=6,
            highlightbackground="#3f3f46",
            highlightthickness=1,
        )
        web_box.pack(fill="x", pady=(0, 10))

        web_hdr = tk.Frame(web_box, bg="#27272a")
        web_hdr.pack(fill="x", pady=(0, 4))
        tk.Label(
            web_hdr,
            text="WEB REMOTE",
            font=(F_FAMILY, 8, "bold"),
            fg="#38bdf8",
            bg="#27272a",
        ).pack(side="left")

        self.flyout_url_entry = tk.Entry(
            web_box,
            font=(F_MONO, 8),
            bg="#18181b",
            fg="#38bdf8",
            insertbackground="#f4f4f5",
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground="#3f3f46",
            highlightcolor="#38bdf8",
        )
        self.flyout_url_entry.pack(fill="x", ipady=3, pady=(0, 6))

        btn_row = tk.Frame(web_box, bg="#27272a")
        btn_row.pack(fill="x")

        self.flyout_copy_btn = tk.Button(
            btn_row,
            text="Copy Link",
            font=(F_FAMILY, 8, "bold"),
            fg="#f4f4f5",
            bg="#3f3f46",
            activeforeground="#f4f4f5",
            activebackground="#52525b",
            bd=0,
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=3,
            command=self._on_flyout_copy_link,
        )
        self.flyout_copy_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

        open_browser_btn = tk.Button(
            btn_row,
            text="Open in Browser",
            font=(F_FAMILY, 8),
            fg="#a1a1aa",
            bg="#27272a",
            activeforeground="#f4f4f5",
            activebackground="#3f3f46",
            bd=1,
            relief="solid",
            highlightthickness=0,
            cursor="hand2",
            padx=10,
            pady=3,
            command=lambda: webbrowser.open(self.flyout_url_entry.get()),
        )
        open_browser_btn.pack(side="right", fill="x", expand=True)

        # 4. Bottom Actions: Open Full Dashboard & Exit
        bottom_row = tk.Frame(container, bg="#18181b")
        bottom_row.pack(fill="x", side="bottom")

        dash_btn = tk.Button(
            bottom_row,
            text="Open Dashboard",
            font=(F_FAMILY, 8, "bold"),
            fg="#18181b",
            bg="#38bdf8",
            activeforeground="#18181b",
            activebackground="#0284c7",
            bd=0,
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=4,
            command=self.open_dashboard,
        )
        dash_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

        exit_btn = tk.Button(
            bottom_row,
            text="Exit",
            font=(F_FAMILY, 8),
            fg="#a1a1aa",
            bg="#27272a",
            activeforeground="#f4f4f5",
            activebackground="#3f3f46",
            bd=1,
            relief="solid",
            highlightthickness=0,
            cursor="hand2",
            padx=10,
            pady=4,
            command=self.quit_application,
        )
        exit_btn.pack(side="right")

        # Auto-dismiss when user clicks outside the window
        def _on_focus_out(event):
            try:
                def _check():
                    if hasattr(self, "flyout") and self.flyout and self.flyout.winfo_exists():
                        f = self.flyout.focus_get()
                        if f is None or not str(f).startswith(str(self.flyout)):
                            self.flyout.withdraw()
                self.root.after(150, _check)
            except Exception:
                pass

        self.flyout.bind("<FocusOut>", _on_focus_out)

        self._update_flyout_content()
        self._position_flyout()
        self.flyout.deiconify()
        self.flyout.lift()
        self.flyout.focus_force()

    def _position_flyout(self):
        """Positions the flyout cleanly in the bottom-right above the Windows taskbar without any top-left flash."""
        card_w = 320
        card_h = 425
        try:
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            pos_x = max(10, sw - card_w - 14)
            pos_y = max(10, sh - card_h - 50)
            self.flyout.geometry(f"{card_w}x{card_h}+{pos_x}+{pos_y}")
            self.flyout.update_idletasks()
        except Exception:
            self.flyout.geometry(f"{card_w}x{card_h}")

    def _update_flyout_content(self):
        """Updates the flyout's QR code and Web Remote URL with the latest local IP and token."""
        try:
            gateway_url = self._get_gateway_qr_url()
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=4,
                border=1,
            )
            qr.add_data(gateway_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="#000000", back_color="#ffffff")
            self.flyout_qr_photo = ImageTk.PhotoImage(img)
            self.flyout_qr_lbl.config(image=self.flyout_qr_photo)

            clean_url = gateway_url.replace("/connect?", "/?tab=screen&").replace("/connect", "/?tab=screen")
            self.flyout_url_entry.config(state="normal")
            self.flyout_url_entry.delete(0, tk.END)
            self.flyout_url_entry.insert(0, clean_url)
            self.flyout_url_entry.config(state="readonly")
        except Exception as e:
            log_debug(f"_update_flyout_content error: {e}")

    def _on_flyout_copy_link(self):
        """Copies the web remote URL to the clipboard with quick visual feedback."""
        try:
            url = self.flyout_url_entry.get()
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            self.flyout_copy_btn.config(text="Copied", fg="#22c55e")
            self.root.after(1500, lambda: self.flyout_copy_btn.config(text="Copy Link", fg="#f4f4f5") if hasattr(self, "flyout_copy_btn") and self.flyout_copy_btn.winfo_exists() else None)
        except Exception:
            pass

    def on_closing(self):
        try:
            # 0. Stop the Wi-Fi watchdog so its thread cannot fire Tk callbacks
            #    into a window that is being torn down.
            try:
                stop_watchdog()
            except Exception:
                pass

            # 1. Stop audio streamer to release WASAPI / PortAudio / sounddevice DLLs
            try:
                try:
                    from server.audio_streamer import audio_streamer
                except ImportError:
                    from audio_streamer import audio_streamer
                audio_streamer.stop()
            except Exception:
                pass

            # 2. Signal server shutdown
            if self.server:
                self.server.should_exit = True

            # 3. Destroy phone remote window if open
            if hasattr(self, "phone_remote_win") and self.phone_remote_win:
                try:
                    self.phone_remote_win.is_streaming = False
                    if self.phone_remote_win.win.winfo_exists():
                        self.phone_remote_win.win.destroy()
                except Exception:
                    pass

            # 4. Restore Windows WLAN AutoConfig to guarantee Wi-Fi is never left disabled
            try:
                if wifi_latency_manager:
                    wifi_latency_manager._cleanup_on_exit()
                restore_all_wlan_autoconfig()
            except Exception:
                pass

            # 5. Destroy main Tk window
            self.root.destroy()
        except Exception:
            pass
        finally:
            try:
                restore_all_wlan_autoconfig()
            except Exception:
                pass
            os._exit(0)



class PhoneRemoteWindow:
    """Cyberpunk Interactive Phone Screen Streamer with Auto-Quality & Auto-FPS Engine."""

    def __init__(self, parent: tk.Tk, gui_app):
        self.parent = parent
        self.gui_app = gui_app
        self.win = tk.Toplevel(parent)
        self.win.withdraw()  # Prevent top-left flash during construction
        self.win.title("PCDeck Pro - Live Phone Controller")
        try:
            sw = self.parent.winfo_screenwidth()
            sh = self.parent.winfo_screenheight()
            px = max(0, (sw - 450) // 2)
            py = max(0, (sh - 740) // 2)
            self.win.geometry(f"450x740+{px}+{py}")
        except Exception:
            self.win.geometry("450x740")
        self.win.minsize(380, 580)
        self.win.configure(bg=C_BG)

        # Set Crisp Window Icon for Titlebar, Taskbar, and Alt-Tab
        apply_crisp_window_icon(self.win)

        # State
        self.active_serial = ""
        self.active_model = ""
        self.phone_w = 720
        self.phone_h = 1600
        self.rendered_img_x = 0
        self.rendered_img_y = 0
        self.rendered_img_w = 0
        self.rendered_img_h = 0

        self.is_streaming = False
        self.stream_thread = None
        self.current_photo = None
        self.last_frame_pil = None
        self.adb_connected = False

        # Reverse-control diagnostics. `preflight` stays None until the first probe
        # finishes, which the pad renders as "Checking for a phone…" rather than
        # asserting anything about a device it has not looked for yet.
        self.preflight = None
        self._last_stage = None
        self._capture_fail_streak = 0

        # Adaptive Metrics
        self.current_latency_ms = 0
        self.measured_fps = 0.0
        self.adaptive_quality_label = "Auto HD"
        self.downscale_factor = 1.0

        # Touch gesture state
        self.touch_start_x = 0
        self.touch_start_y = 0
        self.touch_start_time = 0
        self.is_dragging = False

        self._build_ui()
        self.refresh_devices_and_connect()
        self.start_adaptive_stream()

        self.win.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self):
        # 1. Clean Top Header
        hdr = tk.Frame(self.win, bg=C_SURFACE, bd=1, relief="solid")
        hdr.pack(fill="x", padx=10, pady=(8, 4))

        title_box = tk.Frame(hdr, bg=C_SURFACE)
        title_box.pack(side="left", padx=8, pady=6)

        self.device_title_lbl = tk.Label(
            title_box,
            text="LIVE PHONE CONTROLLER",
            font=F_SUBHEAD,
            fg=C_ACCENT,
            bg=C_SURFACE,
        )
        self.device_title_lbl.pack(anchor="w")

        self.device_sub_lbl = tk.Label(
            title_box,
            text="Detecting attached phone...",
            font=F_SMALL,
            fg=C_TEXT_DIM,
            bg=C_SURFACE,
        )
        self.device_sub_lbl.pack(anchor="w")

        # Header Right: Live HUD Badge & Scrcpy Launch Button
        hdr_actions = tk.Frame(hdr, bg=C_SURFACE)
        hdr_actions.pack(side="right", padx=6, pady=6)

        btn_scrcpy = tk.Button(
            hdr_actions,
            text="MIRROR PHONE SCREEN (60 FPS)",
            font=F_SMALL_STRONG,
            fg=C_BG,
            bg=C_ACCENT,
            bd=0,
            cursor="hand2",
            command=lambda: launch_scrcpy(self.active_serial or None),
            padx=6,
            pady=3,
        )
        btn_scrcpy.pack(side="right", padx=(4, 0))

        self.hud_badge = tk.Label(
            hdr_actions,
            text="● CONNECTING",
            font=F_SMALL_STRONG,
            fg=C_BG,
            bg=C_WARNING,
            padx=8,
            pady=3,
        )
        self.hud_badge.pack(side="right")

        # 2. Main Interactive Viewport Canvas
        pad_container = tk.Frame(
            self.win,
            bg=C_INPUT,
            bd=0,
            relief="solid",
            highlightbackground=C_BORDER,
            highlightthickness=1,
        )
        pad_container.pack(fill="both", expand=True, padx=10, pady=4)

        self.canvas = tk.Canvas(
            pad_container,
            bg=C_INPUT,
            bd=0,
            highlightthickness=0,
            cursor="crosshair",
        )
        self.canvas.pack(fill="both", expand=True, padx=2, pady=2)

        # Mouse & Touch Event Bindings on Canvas
        self.canvas.bind("<Configure>", self._redraw_pad)
        self.canvas.bind("<Button-1>", self._on_touch_start)
        self.canvas.bind("<B1-Motion>", self._on_touch_move)
        self.canvas.bind("<ButtonRelease-1>", self._on_touch_end)
        self.canvas.bind("<Button-2>", lambda e: self.send_nav("home"))
        self.canvas.bind("<Button-3>", lambda e: self.send_nav("back"))
        self.canvas.bind("<MouseWheel>", self._on_scroll)
        self.canvas.bind("<Key>", self._on_canvas_key)

        # 3. Streamlined Floating Bottom Navigation Bar (Back, Home, Recents, Notifications, Snap, Sleep)
        nav_bar = tk.Frame(self.win, bg=C_SURFACE, bd=1, relief="solid")
        nav_bar.pack(fill="x", padx=10, pady=(2, 4))

        buttons = [
            ("◀ Back", C_ACCENT, lambda: self.send_nav("back")),
            ("⌂ Home", C_WARNING, lambda: self.send_nav("home")),
            ("▤ Apps", C_DANGER, lambda: self.send_nav("recents")),
            ("Notifs", C_ACCENT, lambda: self.send_nav("notifications")),
            ("Snap", C_SUCCESS, self.take_phone_screenshot),
            ("Sleep", C_TEXT_DIM, lambda: self.send_adb_key("223")),
        ]

        for text, color, cmd in buttons:
            fg_color = C_TEXT if color in (C_DANGER, C_TEXT_DIM) else C_BG
            btn = tk.Button(
                nav_bar,
                text=text,
                font=F_SMALL_STRONG,
                fg=fg_color,
                bg=color,
                bd=0,
                cursor="hand2",
                command=cmd,
                pady=4,
            )
            btn.pack(side="left", fill="x", expand=True, padx=2, pady=4)

        # 4. Minimal Text / Clipboard Input Deck
        type_bar = tk.Frame(self.win, bg=C_SURFACE, bd=1, relief="solid")
        type_bar.pack(fill="x", padx=10, pady=(0, 6))

        self.text_entry = tk.Entry(
            type_bar,
            font=F_BODY,
            fg=C_ACCENT,
            bg=C_INPUT,
            bd=0,
        )
        self.text_entry.pack(side="left", fill="x", expand=True, padx=6, pady=4)
        self.text_entry.bind("<Return>", lambda e: self.send_text_input())

        btn_send = tk.Button(
            type_bar,
            text="SEND ↵",
            font=F_SMALL_STRONG,
            fg=C_BG,
            bg=C_ACCENT,
            bd=0,
            cursor="hand2",
            command=self.send_text_input,
            padx=6,
            pady=3,
        )
        btn_send.pack(side="left", padx=2, pady=4)

        btn_paste = tk.Button(
            type_bar,
            text="PASTE",
            font=F_SMALL_STRONG,
            fg=C_BG,
            bg=C_WARNING,
            bd=0,
            cursor="hand2",
            command=self.send_clipboard_to_phone,
            padx=6,
            pady=3,
        )
        btn_paste.pack(side="left", padx=(2, 4), pady=4)

        self.win.update_idletasks()
        self.win.deiconify()

    def refresh_devices_and_connect(self):
        """Run the ADB preflight and update status with whatever it found.

        This used to collapse every non-working state into "offline", so a missing
        adb.exe, a wedged daemon and an un-tapped authorization prompt all showed
        the same message. Now the window carries the actual stage so it can say
        which one it is and what to do about it.
        """
        def _bg():
            pf = adb_preflight()
            self.preflight = pf
            dev = pf.get("device")

            if pf["ok"] and dev:
                self.active_serial = dev["serial"]
                self.active_model = dev["model"]
                self.adb_connected = True
                self.phone_w, self.phone_h = get_device_resolution(self.active_serial)
            else:
                self.adb_connected = False
                self.active_serial = dev["serial"] if dev else ""
                self.active_model = dev["model"] if dev else ""
                # A stale frame under a failure message reads as a live stream that
                # has merely frozen, so clear it and let the pad show the diagnosis.
                self.last_frame_pil = None
                self._capture_fail_streak = 0

            # One line in the log per state change, with adb's own output. Without
            # this there is no record of why reverse control did not come up.
            if getattr(self, "_last_stage", None) != pf["stage"]:
                self._last_stage = pf["stage"]
                self._log_adb(f"preflight: {pf['stage']} — {pf['headline']}")
                if pf["detail"]:
                    for line in pf["detail"].splitlines():
                        if line.strip():
                            self._log_adb(f"  {line.strip()}")

            # Tk is not thread-safe. Probing winfo_exists() from this worker can
            # raise "main thread is not in main loop", and because that happened
            # before the after() calls it killed the thread and the UI never
            # updated — the same silent failure this whole change exists to remove.
            # Schedule the work and let a dead window fail harmlessly; the
            # diagnosis above is already in the log either way.
            self._ui(self._update_status_ui)
            self._ui(self._redraw_pad)

        threading.Thread(target=_bg, daemon=True).start()

    def _ui(self, fn):
        """Marshal `fn` onto the Tk thread from a worker.

        The old call sites did `if self.win.winfo_exists(): self.win.after(...)`,
        which touches Tk from the wrong thread; that can raise "main thread is not
        in main loop" and kill the worker before it ever schedules the update.
        after() alone is enough, and anything that goes wrong here means the window
        is gone, which is not worth reporting.
        """
        try:
            self.win.after(0, fn)
            return True
        except (tk.TclError, RuntimeError, AttributeError):
            return False

    def _log_adb(self, msg: str):
        """Record a diagnostic line in ~/pcdeck_pro_debug.log.

        The capture loop and the preflight both write here. Reverse control failing
        silently is the whole reported problem, so when someone says "it just shows
        a blank window" there needs to be a file that says why.
        """
        try:
            log_debug(f"[REMOTE] {msg}")
        except Exception:
            # Diagnostics must never be the thing that breaks the window.
            pass

    def _update_status_ui(self):
        if not hasattr(self, "hud_badge") or not self.hud_badge.winfo_exists():
            return
        if self.adb_connected:
            mode = "Wi-Fi" if ":" in self.active_serial else "USB"
            self.device_title_lbl.config(text=f"{self.active_model}")
            self.device_sub_lbl.config(
                text=f"{mode} • {self.phone_w}x{self.phone_h} • Auto-Quality Active",
                fg=C_ACCENT,
            )
            # HUD formatting
            fps_display = f"{self.measured_fps:.1f} FPS" if self.measured_fps > 0 else "Active"
            lat_color = C_SUCCESS if self.current_latency_ms < 80 else (C_WARNING if self.current_latency_ms < 150 else C_WARNING)
            self.hud_badge.config(
                text=f"● {fps_display} | {self.current_latency_ms}ms | {self.adaptive_quality_label}",
                bg=lat_color,
                fg=C_BG,
            )
            return

        # Not connected. Title says what is wrong instead of naming the feature:
        # "LIVE PHONE CONTROLLER" over an empty canvas read as a broken stream.
        pf = getattr(self, "preflight", None) or {}
        stage = pf.get("stage", "no_device")
        headline = pf.get("headline", "No phone is connected to this PC.")

        badges = {
            "no_binary": ("● ADB MISSING", C_DANGER, C_TEXT),
            "binary_broken": ("● ADB BLOCKED", C_DANGER, C_TEXT),
            "daemon_error": ("● ADB ERROR", C_DANGER, C_TEXT),
            "no_device": ("● NO PHONE", C_DANGER, C_TEXT),
            "offline": ("● NOT READY", C_WARNING, C_BG),
            "unauthorized": ("● UNAUTHORIZED", C_WARNING, C_BG),
        }
        text, bg, fg = badges.get(stage, ("● NO PHONE", C_DANGER, C_TEXT))
        self.hud_badge.config(text=text, bg=bg, fg=fg)

        self.device_title_lbl.config(text=self.active_model or "Reverse Control")
        first_step = (pf.get("steps") or [""])[0]
        self.device_sub_lbl.config(
            text=headline if not first_step else f"{headline}  {first_step}",
            fg=C_WARNING if stage in ("offline", "unauthorized") else C_TEXT_DIM,
        )

    def start_adaptive_stream(self):
        """High-Performance Screen Capture Loop with Auto-Quality & Auto-FPS dynamic tuning."""
        self.is_streaming = True

        def _capture_loop():
            adb_bin = get_adb_path()
            last_time = time.perf_counter()
            frame_count = 0
            fps_timer = time.perf_counter()

            while self.is_streaming:
                try:
                    if self.adb_connected:
                        t_start = time.perf_counter()

                        cmd = [adb_bin]
                        if self.active_serial:
                            cmd.extend(["-s", self.active_serial])
                        cmd.extend(["exec-out", "screencap", "-p"])

                        proc = subprocess.run(
                            cmd,
                            capture_output=True,
                            timeout=3.0,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                        )
                        raw_data = proc.stdout
                        t_capture_end = time.perf_counter()

                        capture_duration_ms = int((t_capture_end - t_start) * 1000)
                        self.current_latency_ms = capture_duration_ms

                        # ================= AUTO-QUALITY ADAPTATION =================
                        # Adjust downscale & interpolation based on round-trip capture latency
                        if capture_duration_ms < 65:
                            self.adaptive_quality_label = "Ultra HD"
                            self.downscale_factor = 1.0
                        elif capture_duration_ms < 120:
                            self.adaptive_quality_label = "Auto High"
                            self.downscale_factor = 0.85
                        elif capture_duration_ms < 180:
                            self.adaptive_quality_label = "Auto Balanced"
                            self.downscale_factor = 0.70
                        else:
                            self.adaptive_quality_label = "Auto Eco"
                            self.downscale_factor = 0.50

                        if len(raw_data) > 2048:
                            buf = io.BytesIO(raw_data)
                            img = Image.open(buf)
                            self.last_frame_pil = img
                            self._capture_fail_streak = 0

                            self._ui(self._render_captured_frame)
                        else:                            # A short read is not a frame. Usually adb printed an
                            # error to stderr — "device unauthorized", "device
                            # offline", "closed" — and the old code dropped it on
                            # the floor, which is why the window went blank with no
                            # explanation. Surface it and re-run the preflight so
                            # the pad can say what actually happened.
                            self._capture_fail_streak = self._capture_fail_streak + 1
                            err = (proc.stderr or b"").decode("utf-8", "replace").strip()
                            if self._capture_fail_streak in (1, 5, 25):
                                self._log_adb(
                                    f"screencap returned {len(raw_data)} bytes "
                                    f"(attempt {self._capture_fail_streak}): "
                                    f"{err or 'no stderr'}"
                                )
                            if self._capture_fail_streak == 3:
                                # Three in a row is a real loss of the device, not a
                                # dropped frame. Stop pretending the stream is live.
                                self.last_frame_pil = None
                                self.adb_connected = False
                                self.refresh_devices_and_connect()
                            time.sleep(0.4)

                        # ================= AUTO-FPS MEASUREMENT =================
                        frame_count += 1
                        now = time.perf_counter()
                        if now - fps_timer >= 1.0:
                            self.measured_fps = frame_count / (now - fps_timer)
                            frame_count = 0
                            fps_timer = now
                            self._ui(self._update_status_ui)

                        # Target adaptive frame delay
                        target_delay = 0.001 if capture_duration_ms > 80 else 0.015
                        time.sleep(target_delay)
                    else:
                        time.sleep(1.0)
                except subprocess.TimeoutExpired:
                    # The phone stopped answering within 3s. Common and often
                    # transient (screen off, Wi-Fi roam), so tolerate a few before
                    # declaring the device gone.
                    self._capture_fail_streak = self._capture_fail_streak + 1
                    if self._capture_fail_streak in (1, 5, 25):
                        self._log_adb(
                            f"screencap timed out after 3s "
                            f"(attempt {self._capture_fail_streak})"
                        )
                    if self._capture_fail_streak == 3:
                        self.last_frame_pil = None
                        self.adb_connected = False
                        self.refresh_devices_and_connect()
                    time.sleep(0.5)
                except Exception as exc:
                    # This used to be a bare `except Exception: sleep(1)`, which is
                    # exactly why a broken reverse-control session produced a blank
                    # window and no clue. Every failure now leaves a trace, rate
                    # limited so a persistent fault cannot flood the log file.
                    self._capture_fail_streak = self._capture_fail_streak + 1
                    if self._capture_fail_streak in (1, 5, 25):
                        self._log_adb(
                            f"capture loop error (attempt {self._capture_fail_streak}): "
                            f"{type(exc).__name__}: {exc}"
                        )
                    if self._capture_fail_streak == 3:
                        self.last_frame_pil = None
                        self.adb_connected = False
                        self.refresh_devices_and_connect()
                    time.sleep(1.0)

        self.stream_thread = threading.Thread(target=_capture_loop, daemon=True)
        self.stream_thread.start()

    def _render_captured_frame(self):
        """Draw current captured frame onto canvas fitting aspect ratio with adaptive quality."""
        if not self.last_frame_pil or not hasattr(self, "canvas") or not self.canvas.winfo_exists():
            return
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 10 or ch < 10:
            return

        img = self.last_frame_pil
        iw, ih = img.size
        self.phone_w = iw
        self.phone_h = ih

        scale = min(cw / iw, ch / ih)
        rw = max(1, int(iw * scale))
        rh = max(1, int(ih * scale))
        rx = (cw - rw) // 2
        ry = (ch - rh) // 2

        self.rendered_img_x = rx
        self.rendered_img_y = ry
        self.rendered_img_w = rw
        self.rendered_img_h = rh

        # Choose resampling filter according to latency tier
        resample_mode = Image.Resampling.BILINEAR if self.current_latency_ms < 120 else Image.Resampling.NEAREST
        resized = img.resize((rw, rh), resample_mode)
        self.current_photo = ImageTk.PhotoImage(resized)

        self.canvas.delete("all")
        self.canvas.create_image(rx, ry, anchor="nw", image=self.current_photo)
        self.canvas.create_rectangle(rx, ry, rx + rw, ry + rh, outline=C_ACCENT, width=1)

    def _redraw_pad(self, event=None):
        if self.last_frame_pil:
            self._render_captured_frame()
            return
        if not hasattr(self, "canvas") or not self.canvas.winfo_exists():
            return
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 10 or h < 10:
            return
        self.canvas.delete("all")

        # The placeholder used to read "LIVE PHONE CONTROLLER" with a row of control
        # hints under it, which is what made a failed connection look like a working
        # feature showing a blank screen. When there is no stream, this space belongs
        # to the reason there is no stream.
        pf = getattr(self, "preflight", None)
        if pf is None:
            self.canvas.create_text(
                w / 2, h / 2, text="Checking for a phone…",
                font=F_HEADING, fill=C_TEXT_DIM,
            )
            return

        stage = pf.get("stage", "no_device")
        headline = pf.get("headline", "No phone is connected to this PC.")
        steps = pf.get("steps") or []
        accent = C_WARNING if stage in ("offline", "unauthorized") else C_DANGER

        text_w = max(160, w - 56)

        # Everything is top-anchored ("n") so a single translate at the end centres
        # the block exactly. Mixing anchors here put the block 28px off centre and
        # pushed the tallest state 13px off the top of the canvas.
        def line(text, fnt, colour, gap):
            item = self.canvas.create_text(
                w / 2, 0, text=text, font=fnt, fill=colour,
                width=text_w, justify="center", anchor="n",
            )
            return item, gap

        items = [line("!", (F_FAMILY, 26, "bold"), accent, 12),
                 line(headline, F_HEADING, C_TEXT, 12)]

        # Numbered because these are ordered things to try, not a feature list.
        for i, step in enumerate(steps, 1):
            items.append(line(f"{i}.  {step}", F_SMALL, C_TEXT_DIM, 6))

        if stage in ("no_device", "offline"):
            # Separated by space, not by fading out: C_BORDER_STRONG is a divider
            # colour and sits at 1.56:1 on this surface, which is not readable text.
            items[-1] = (items[-1][0], items[-1][1] + 10)
            items.append(line(
                "Tap REFRESH once connected, or WIRELESS MODE to pair over Wi-Fi.",
                F_SMALL, C_TEXT_DIM, 0,
            ))

        # Stack by each item's measured height — wrapped text height cannot be
        # derived from character counts, and the canvas is resizable.
        y = 0
        for item, gap in items:
            self.canvas.coords(item, w / 2, y)
            _, y0, _, y1 = self.canvas.bbox(item)
            y += (y1 - y0) + gap

        # Centre if it fits; otherwise pin to the top. Clipping the bottom of the
        # hint line is recoverable — the window is resizable — but clipping the
        # headline off the top would hide the very thing this exists to say.
        block_h = y
        offset = max(10, (h - block_h) / 2) if block_h < h - 20 else 10
        if offset:
            for item, _ in items:
                self.canvas.move(item, 0, offset)

    def _map_canvas_to_phone(self, cx, cy):
        if self.rendered_img_w > 0 and self.rendered_img_h > 0:
            norm_x = max(0.0, min(1.0, (cx - self.rendered_img_x) / self.rendered_img_w))
            norm_y = max(0.0, min(1.0, (cy - self.rendered_img_y) / self.rendered_img_h))
        else:
            w = max(1, self.canvas.winfo_width())
            h = max(1, self.canvas.winfo_height())
            norm_x = max(0.0, min(1.0, cx / w))
            norm_y = max(0.0, min(1.0, cy / h))

        px = int(norm_x * self.phone_w)
        py = int(norm_y * self.phone_h)
        return px, py

    def _on_touch_start(self, event):
        self.canvas.focus_set()
        self.touch_start_x = event.x
        self.touch_start_y = event.y
        self.touch_start_time = time.time()
        self.is_dragging = False

        # Visual Ripple Indicator
        self.canvas.delete("ripple")
        self.canvas.create_oval(
            event.x - 12,
            event.y - 12,
            event.x + 12,
            event.y + 12,
            outline=C_SUCCESS,
            width=2,
            tags="ripple",
        )
        self.win.after(200, lambda: self.canvas.delete("ripple"))

    def _on_touch_move(self, event):
        dx = abs(event.x - self.touch_start_x)
        dy = abs(event.y - self.touch_start_y)
        if dx > 6 or dy > 6:
            self.is_dragging = True

    def _on_touch_end(self, event):
        duration_ms = int((time.time() - self.touch_start_time) * 1000)
        px, py = self._map_canvas_to_phone(event.x, event.y)

        if not self.is_dragging or duration_ms < 180:
            self.send_command(f"phone_tap,{px},{py}")
        else:
            start_px, start_py = self._map_canvas_to_phone(self.touch_start_x, self.touch_start_y)
            self.send_command(
                f"phone_swipe,{start_px},{start_py},{px},{py},{max(80, min(800, duration_ms))}"
            )

    def _on_scroll(self, event):
        mid_x = self.phone_w // 2
        start_y = self.phone_h // 2
        delta_y = 500 if event.delta > 0 else -500
        end_y = max(100, min(self.phone_h - 100, start_y + delta_y))
        self.send_command(f"phone_swipe,{mid_x},{start_y},{mid_x},{end_y},200")

    def _on_canvas_key(self, event):
        if event.keysym in ("BackSpace", "Delete"):
            self.send_adb_key("67")
        elif event.keysym == "Return":
            self.send_adb_key("66")
        elif event.char and event.char.isprintable():
            self.send_command(f"phone_text,{event.char}")

    def send_nav(self, action: str):
        self.send_command(f"phone_nav,{action}")

    def send_adb_key(self, keycode: str):
        def _bg():
            adb_bin = get_adb_path()
            cmd = [adb_bin]
            if self.active_serial:
                cmd.extend(["-s", self.active_serial])
            cmd.extend(["shell", "input", "keyevent", keycode])
            try:
                subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=3.0,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
            except Exception:
                pass

        threading.Thread(target=_bg, daemon=True).start()

    def send_text_input(self):
        txt = self.text_entry.get()
        if txt:
            self.send_command(f"phone_text,{txt}")
            self.text_entry.delete(0, tk.END)

    def send_clipboard_to_phone(self):
        try:
            clip = self.win.clipboard_get()
            if clip:
                self.send_command(f"phone_text,{clip}")
        except Exception:
            pass

    def send_command(self, cmd_str: str):
        def _dispatch():
            # 1. Send via local HTTP API
            try:
                data = json.dumps({"cmd": cmd_str}).encode("utf-8")
                req = urllib.request.Request(
                    f"http://127.0.0.1:{SERVER_PORT}/api/phone/command",
                    data=data,
                    headers={"Content-Type": "application/json"},
                )
                urllib.request.urlopen(req, timeout=1.0)
            except Exception:
                pass

            # 2. Hardware ADB execution
            adb_bin = get_adb_path()
            cmd_prefix = [adb_bin]
            if self.active_serial:
                cmd_prefix.extend(["-s", self.active_serial])

            try:
                if cmd_str.startswith("phone_tap,"):
                    parts = cmd_str.split(",")
                    subprocess.run(
                        cmd_prefix + ["shell", "input", "tap", parts[1], parts[2]],
                        capture_output=True,
                        timeout=3.0,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                    )
                elif cmd_str.startswith("phone_swipe,"):
                    parts = cmd_str.split(",")
                    subprocess.run(
                        cmd_prefix
                        + [
                            "shell",
                            "input",
                            "swipe",
                            parts[1],
                            parts[2],
                            parts[3],
                            parts[4],
                            parts[5],
                        ],
                        capture_output=True,
                        timeout=3.0,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                    )
                elif cmd_str.startswith("phone_nav,"):
                    act = cmd_str.split(",")[1]
                    key_map = {
                        "back": "4",
                        "home": "3",
                        "recents": "187",
                        "notifications": "83",
                        "lock": "26",
                        "power": "26",
                    }
                    if act in key_map:
                        subprocess.run(
                            cmd_prefix + ["shell", "input", "keyevent", key_map[act]],
                            capture_output=True,
                            timeout=3.0,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                        )
                elif cmd_str.startswith("phone_text,"):
                    text = cmd_str.split(",", 1)[1]
                    subprocess.run(
                        cmd_prefix
                        + [
                            "shell",
                            "input",
                            "text",
                            text.replace(" ", "%s"),
                        ],
                        capture_output=True,
                        timeout=3.0,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                    )
            except Exception:
                pass

        threading.Thread(target=_dispatch, daemon=True).start()

    def open_wireless_dialog(self):
        """Modern dialog to pair via wireless ADB (Direct connect & Android 11+ code pairing)."""
        dlg = tk.Toplevel(self.win)
        dlg.withdraw()  # Prevent top-left flash during construction
        dlg.title("PCDeck Pro - Wireless ADB Setup")
        try:
            sw = self.win.winfo_screenwidth()
            sh = self.win.winfo_screenheight()
            dx = max(0, (sw - 440) // 2)
            dy = max(0, (sh - 360) // 2)
            dlg.geometry(f"440x360+{dx}+{dy}")
        except Exception:
            dlg.geometry("440x360")
        dlg.configure(bg=C_SURFACE)
        apply_crisp_window_icon(dlg)

        tk.Label(
            dlg,
            text="WIRELESS DEBUGGING SETUP",
            font=F_HEADING,
            fg=C_ACCENT,
            bg=C_SURFACE,
        ).pack(pady=(12, 2))

        tk.Label(
            dlg,
            text="Control your Android phone over Wi-Fi without USB cables.",
            font=F_SMALL,
            fg=C_TEXT_DIM,
            bg=C_SURFACE,
        ).pack(pady=(0, 8))

        # METHOD 1: 1-Click Switch if USB is plugged in
        m1_card = tk.Frame(dlg, bg=C_SURFACE_2, bd=1, relief="solid")
        m1_card.pack(fill="x", padx=16, pady=4)

        tk.Label(
            m1_card,
            text="Method 1: USB Plugged In (1-Click Switch)",
            font=F_SMALL_STRONG,
            fg=C_SUCCESS,
            bg=C_SURFACE_2,
        ).pack(anchor="w", padx=8, pady=(4, 2))

        def _do_usb_switch():
            res_lbl.config(text="Switching USB to Wireless TCP/IP...", fg=C_ACCENT)
            def _bg():
                ok, msg = switch_device_to_wireless(self.active_serial)
                if ok:
                    dlg.after(0, lambda: res_lbl.config(text=f"{msg}", fg=C_SUCCESS))
                    dlg.after(1000, lambda: (self.refresh_devices_and_connect(), dlg.destroy()))
                else:
                    dlg.after(0, lambda: res_lbl.config(text=f"{msg}", fg=C_DANGER))
            threading.Thread(target=_bg, daemon=True).start()

        btn_usb_sw = tk.Button(
            m1_card,
            text="SWITCH CONNECTED USB PHONE TO WIRELESS",
            font=F_SMALL_STRONG,
            fg=C_BG,
            bg=C_ACCENT,
            bd=0,
            cursor="hand2",
            command=_do_usb_switch,
            pady=4,
        )
        btn_usb_sw.pack(fill="x", padx=8, pady=(2, 6))

        # METHOD 2: Direct Wireless Connection / Pairing
        m2_card = tk.Frame(dlg, bg=C_SURFACE_2, bd=1, relief="solid")
        m2_card.pack(fill="x", padx=16, pady=4)

        tk.Label(
            m2_card,
            text="Method 2: Wireless Debugging (Android 11+)",
            font=F_SMALL_STRONG,
            fg=C_ACCENT,
            bg=C_SURFACE_2,
        ).pack(anchor="w", padx=8, pady=(4, 2))

        ip_row = tk.Frame(m2_card, bg=C_SURFACE_2)
        ip_row.pack(fill="x", padx=8, pady=2)
        tk.Label(ip_row, text="Connect IP:Port:", font=F_SMALL, fg=C_TEXT_DIM, bg=C_SURFACE_2, width=16, anchor="w").pack(side="left")
        ip_entry = tk.Entry(ip_row, font=F_BODY, fg=C_ACCENT, bg=C_INPUT, bd=1, relief="solid")
        ip_entry.pack(side="left", fill="x", expand=True)
        default_ip = getattr(self, "phone_ip", f"{LOCAL_IP.rsplit('.', 1)[0]}.")
        ip_entry.insert(0, f"{default_ip}:5555")

        pair_row = tk.Frame(m2_card, bg=C_SURFACE_2)
        pair_row.pack(fill="x", padx=8, pady=2)
        tk.Label(pair_row, text="Pair Port (Android 11+):", font=F_SMALL, fg=C_TEXT_DIM, bg=C_SURFACE_2, width=16, anchor="w").pack(side="left")
        pair_port_entry = tk.Entry(pair_row, font=F_BODY, fg=C_ACCENT, bg=C_INPUT, bd=1, relief="solid")
        pair_port_entry.pack(side="left", fill="x", expand=True)

        code_row = tk.Frame(m2_card, bg=C_SURFACE_2)
        code_row.pack(fill="x", padx=8, pady=2)
        tk.Label(code_row, text="Pair Code (6-digit):", font=F_SMALL, fg=C_TEXT_DIM, bg=C_SURFACE_2, width=16, anchor="w").pack(side="left")
        code_entry = tk.Entry(code_row, font=F_BODY, fg=C_WARNING, bg=C_INPUT, bd=1, relief="solid")
        code_entry.pack(side="left", fill="x", expand=True)

        res_lbl = tk.Label(dlg, text="", font=F_SMALL_STRONG, fg=C_WARNING, bg=C_SURFACE, wraplength=400)
        res_lbl.pack(pady=4)

        def _do_connect():
            target = ip_entry.get().strip()
            pair_code = code_entry.get().strip()
            pair_port = pair_port_entry.get().strip()
            if not target:
                return
            res_lbl.config(text="Connecting to Wireless ADB...", fg=C_ACCENT)

            def _bg():
                adb_bin = get_adb_path()
                try:
                    # If 6-digit pair code provided, pair first
                    if pair_code:
                        ip_part = target.split(":")[0]
                        pair_target = f"{ip_part}:{pair_port}" if pair_port else target
                        res_pair = subprocess.run(
                            [adb_bin, "pair", pair_target, pair_code],
                            capture_output=True,
                            text=True,
                            timeout=8.0,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                        )
                        pair_out = res_pair.stdout.strip()
                        if "successfully paired" not in pair_out.lower():
                            dlg.after(0, lambda: res_lbl.config(text=f"Pairing failed: {pair_out or res_pair.stderr.strip()}", fg=C_DANGER))
                            return

                    # Connect to wireless target (connect port)
                    res = subprocess.run(
                        [adb_bin, "connect", target],
                        capture_output=True,
                        text=True,
                        timeout=8.0,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                    )
                    out = res.stdout.strip()
                    if "connected to" in out.lower() or "already connected" in out.lower():
                        dlg.after(0, lambda: res_lbl.config(text=f"{out}", fg=C_SUCCESS))
                        dlg.after(800, lambda: (self.refresh_devices_and_connect(), dlg.destroy()))
                    else:
                        dlg.after(0, lambda: res_lbl.config(text=f"{out}", fg=C_DANGER))
                except Exception as e:
                    dlg.after(0, lambda: res_lbl.config(text=f"Error: {e}", fg=C_DANGER))

            threading.Thread(target=_bg, daemon=True).start()

        btn_conn = tk.Button(
            m2_card,
            text="CONNECT / PAIR WIRELESS ADB",
            font=F_SMALL_STRONG,
            fg=C_BG,
            bg=C_ACCENT,
            bd=0,
            cursor="hand2",
            command=_do_connect,
            pady=4,
        )
        btn_conn.pack(fill="x", padx=8, pady=(4, 6))

        dlg.update_idletasks()
        dlg.deiconify()

    def take_phone_screenshot(self):
        """Take screenshot from phone and save to PC Downloads."""
        def _bg():
            adb_bin = get_adb_path()
            cmd = [adb_bin]
            if self.active_serial:
                cmd.extend(["-s", self.active_serial])
            cmd.extend(["exec-out", "screencap", "-p"])
            try:
                res = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=6.0,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
                if len(res.stdout) > 1000:
                    filename = f"Phone_Screenshot_{int(time.time())}.png"
                    filepath = os.path.join(TRANSFER_DIR, filename)
                    with open(filepath, "wb") as f:
                        f.write(res.stdout)
                    try:
                        os.startfile(filepath)
                    except Exception:
                        pass
            except Exception:
                pass

        threading.Thread(target=_bg, daemon=True).start()

    def on_close(self):
        self.is_streaming = False
        self.win.destroy()


def is_admin() -> bool:
    """Check if current process has Administrator privileges on Windows."""
    if sys.platform != "win32":
        return True
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def elevate_if_needed():
    """
    If running on Windows without Administrator rights, relaunches with UAC prompt
    so PCDeck can inject inputs into elevated apps/games (Elden Ring, Task Manager).
    """
    if sys.platform == "win32" and not is_admin():
        try:
            import ctypes
            if getattr(sys, "frozen", False):
                target = sys.executable
                params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
            else:
                target = sys.executable
                script = os.path.abspath(sys.argv[0])
                args = [f'"{script}"'] + [f'"{arg}"' for arg in sys.argv[1:]]
                params = " ".join(args)

            ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", target, params, None, 1)
            if ret > 32:
                sys.exit(0)
        except Exception as e:
            log_debug(f"Elevation request failed: {e}")


_SINGLE_INSTANCE_MUTEX_HANDLE = None
_IPC_WNDPROC_REF = None

IPC_WINDOW_CLASS = "PCDeck_IPC_Class"
IPC_WINDOW_NAME = "PCDeck_IPC_Window"
IPC_MESSAGE_STRING = "PCDeck_SingleInstance_ShowApp"
IPC_EVENT_GLOBAL = r"Global\PCDeck_ShowApp_Event"
IPC_EVENT_LOCAL = r"Local\PCDeck_ShowApp_Event"


def signal_existing_instance_to_show(event_names=None, window_class=None, message_string=None):
    """
    Sends IPC signals to the running primary instance to wake up, un-hide from tray,
    and bring its Tkinter GUI to the foreground. Uses dual mechanisms:
    1. Win32 Named Event (SetEvent) for instant non-blocking wake up.
    2. RegisterWindowMessageW broadcast and direct post to dedicated IPC window class.
    3. Fallback: FindWindowW title scanning and ShowWindow/SetForegroundWindow.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from ctypes import wintypes
        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32

        target_events = event_names if event_names is not None else [IPC_EVENT_GLOBAL, IPC_EVENT_LOCAL]
        target_class = window_class if window_class is not None else IPC_WINDOW_CLASS
        target_msg = message_string if message_string is not None else IPC_MESSAGE_STRING

        # 1. Signal Win32 Named Event (instant, immune to window state or desktop focus restrictions)
        for ev_name in target_events:
            try:
                kernel32.OpenEventW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
                kernel32.OpenEventW.restype = wintypes.HANDLE
                kernel32.SetEvent.argtypes = [wintypes.HANDLE]
                kernel32.SetEvent.restype = wintypes.BOOL
                kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
                kernel32.CloseHandle.restype = wintypes.BOOL

                h_ev = kernel32.OpenEventW(0x0002, False, ev_name)  # EVENT_MODIFY_STATE = 0x0002
                if h_ev:
                    kernel32.SetEvent(h_ev)
                    kernel32.CloseHandle(h_ev)
            except Exception:
                pass

        # 2. Post Registered Windows Message via custom window class and session broadcast
        try:
            user32.RegisterWindowMessageW.argtypes = [wintypes.LPCWSTR]
            user32.RegisterWindowMessageW.restype = ctypes.c_uint
            user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
            user32.FindWindowW.restype = wintypes.HWND
            user32.PostMessageW.argtypes = [wintypes.HWND, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM]
            user32.PostMessageW.restype = wintypes.BOOL

            wm_show = user32.RegisterWindowMessageW(target_msg)
            if wm_show:
                hwnd_ipc = user32.FindWindowW(target_class, None)
                if hwnd_ipc:
                    user32.PostMessageW(hwnd_ipc, wm_show, 0, 0)
        except Exception:
            pass

        # 3. Fallback: Title scan for direct HWND restore
        try:
            user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
            user32.ShowWindow.restype = wintypes.BOOL
            user32.SetForegroundWindow.argtypes = [wintypes.HWND]
            user32.SetForegroundWindow.restype = wintypes.BOOL

            for title in [
                "PCDeck - Wireless PC Touch Deck & Streamer",
                "PCDeck Pro - Wireless PC Touch Deck & Streamer",
                "PCDeck Pro",
                "PCDeck Server",
            ]:
                hwnd = user32.FindWindowW(None, title)
                if hwnd:
                    user32.ShowWindow(hwnd, 9)  # 9 = SW_RESTORE
                    user32.SetForegroundWindow(hwnd)
                    break
        except Exception:
            pass
    except Exception as e:
        log_debug(f"Signal existing instance failed: {e}")


def acquire_single_instance_lock(is_tray_launch: bool = False) -> bool:
    """
    Enforce strict single-instance mutual exclusion via Win32 Named Mutex.
    Uses bInitialOwner=True to atomically take ownership and prevent startup race conditions.
    Retains handle until process termination (never explicitly closed during shutdown).
    """
    global _SINGLE_INSTANCE_MUTEX_HANDLE
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            kernel32 = ctypes.windll.kernel32
            ERROR_ALREADY_EXISTS = 183
            ERROR_ACCESS_DENIED = 5

            kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
            kernel32.CreateMutexW.restype = wintypes.HANDLE

            # Session-local mutex first (always accessible to medium integrity / packaged apps)
            mutex_names = [
                r"Local\PCDeck_SingleInstance_Mutex_Pro",
                r"Global\PCDeck_SingleInstance_Mutex_Pro"
            ]
            for mutex_name in mutex_names:
                h_mutex = kernel32.CreateMutexW(None, True, mutex_name)
                last_error = kernel32.GetLastError()
                # If a valid handle was returned and ERROR_ALREADY_EXISTS, an instance is genuinely running
                if h_mutex and last_error == ERROR_ALREADY_EXISTS:
                    log_debug(f"PCDeck instance already running (detected via {mutex_name}).")
                    if not is_tray_launch:
                        signal_existing_instance_to_show()
                    return False

                # If mutex was successfully created and owned without collision
                if h_mutex and last_error == 0:
                    _SINGLE_INSTANCE_MUTEX_HANDLE = h_mutex
                    break
        except Exception as e:
            log_debug(f"Mutex creation exception: {e}")
    return True


def start_single_instance_ipc_server(root: tk.Tk, on_show_callback, event_names=None, window_class=None, message_string=None):
    """
    Starts background listeners in the primary instance to handle show requests
    from secondary instances:
    1. Win32 Named Event listener thread (waits on CreateEventW).
    2. Hidden Win32 IPC Message Window (pumps messages for RegisterWindowMessageW).
    When triggered, queues on_show_callback onto the Tkinter main thread via root.after.
    """
    if sys.platform != "win32":
        return

    try:
        import ctypes
        from ctypes import wintypes
        import threading
        import time

        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32

        target_events = event_names if event_names is not None else [IPC_EVENT_LOCAL, IPC_EVENT_GLOBAL]
        target_class = window_class if window_class is not None else IPC_WINDOW_CLASS
        target_msg = message_string if message_string is not None else IPC_MESSAGE_STRING

        import queue
        _ipc_queue = queue.Queue()
        last_trigger_time = 0.0

        def debounced_trigger():
            nonlocal last_trigger_time
            now = time.time()
            if now - last_trigger_time > 0.4:
                last_trigger_time = now
                _ipc_queue.put(True)

        def _poll_queue():
            triggered = False
            while not _ipc_queue.empty():
                try:
                    _ipc_queue.get_nowait()
                    triggered = True
                except Exception:
                    break
            if triggered:
                try:
                    on_show_callback()
                except Exception as e:
                    log_debug(f"on_show_callback error: {e}")
            try:
                root.after(150, _poll_queue)
            except Exception:
                pass

        try:
            root.after(150, _poll_queue)
        except Exception:
            pass

        # --- 1. Named Event Listener ---
        kernel32.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.CreateEventW.restype = wintypes.HANDLE
        kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel32.WaitForSingleObject.restype = wintypes.DWORD

        h_event = None
        for ev_name in target_events:
            try:
                h_event = kernel32.CreateEventW(None, False, False, ev_name)
                if h_event:
                    break
            except Exception:
                pass

        if h_event:
            def _event_listener_worker():
                while True:
                    res = kernel32.WaitForSingleObject(h_event, 1000)
                    if res == 0:  # WAIT_OBJECT_0
                        debounced_trigger()

            threading.Thread(target=_event_listener_worker, daemon=True, name="PCDeck-IPC-Event").start()

        # --- 2. Win32 Hidden IPC Message Window ---
        user32.RegisterWindowMessageW.argtypes = [wintypes.LPCWSTR]
        user32.RegisterWindowMessageW.restype = ctypes.c_uint
        wm_show = user32.RegisterWindowMessageW(target_msg)
        if not wm_show:
            return

        WNDPROC = ctypes.WINFUNCTYPE(
            ctypes.c_int64,
            wintypes.HWND,
            ctypes.c_uint,
            wintypes.WPARAM,
            wintypes.LPARAM
        )
        user32.DefWindowProcW.argtypes = [
            wintypes.HWND,
            ctypes.c_uint,
            wintypes.WPARAM,
            wintypes.LPARAM
        ]
        user32.DefWindowProcW.restype = ctypes.c_int64

        WM_CLOSE = 0x0010
        WM_QUERYENDSESSION = 0x0011
        WM_ENDSESSION = 0x0016
        WM_POWERBROADCAST = 0x0218
        PBT_APMSUSPEND = 0x0004
        PBT_APMRESUMEAUTOMATIC = 0x0012

        def py_wndproc(hwnd, msg, wparam, lparam):
            if msg == wm_show:
                debounced_trigger()
                return 0
            elif msg == WM_QUERYENDSESSION:
                # Windows Restart Manager / OS Quiesce requesting permission to shut down
                log_debug("Win32 WM_QUERYENDSESSION received: returning 1 (quiesce approved)")
                return 1
            elif msg == WM_ENDSESSION:
                # OS session is ending or Store AppX update is terminating the process
                log_debug(f"Win32 WM_ENDSESSION received (wparam={wparam}). Exiting cleanly.")
                if wparam:
                    import os
                    os._exit(0)
                return 0
            elif msg == WM_CLOSE:
                # Windows Restart Manager sent WM_CLOSE to process window to service app
                log_debug("Win32 WM_CLOSE received on IPC window. Performing clean quiesce.")
                import os
                os._exit(0)
            elif msg == WM_POWERBROADCAST:
                if wparam == PBT_APMSUSPEND:
                    log_debug("Windows Modern Standby / Sleep detected (PBT_APMSUSPEND).")
                elif wparam == PBT_APMRESUMEAUTOMATIC:
                    log_debug("Windows resumed from Standby (PBT_APMRESUMEAUTOMATIC).")
                return 1
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        global _IPC_WNDPROC_REF
        _IPC_WNDPROC_REF = WNDPROC(py_wndproc)

        class WNDCLASSEX(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_uint),
                ("style", ctypes.c_uint),
                ("lpfnWndProc", WNDPROC),
                ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int),
                ("hInstance", wintypes.HINSTANCE),
                ("hIcon", wintypes.HICON),
                ("hCursor", wintypes.HICON),
                ("hbrBackground", wintypes.HBRUSH),
                ("lpszMenuName", wintypes.LPCWSTR),
                ("lpszClassName", wintypes.LPCWSTR),
                ("hIconSm", wintypes.HICON),
            ]

        user32.RegisterClassExW.argtypes = [ctypes.POINTER(WNDCLASSEX)]
        user32.RegisterClassExW.restype = wintypes.ATOM

        user32.CreateWindowExW.argtypes = [
            wintypes.DWORD,
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            wintypes.DWORD,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.HWND,
            wintypes.HMENU,
            wintypes.HINSTANCE,
            wintypes.LPVOID
        ]
        user32.CreateWindowExW.restype = wintypes.HWND

        user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, ctypes.c_uint, ctypes.c_uint]
        user32.GetMessageW.restype = wintypes.BOOL

        user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
        user32.TranslateMessage.restype = wintypes.BOOL

        user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
        user32.DispatchMessageW.restype = ctypes.c_int64
        kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        kernel32.GetModuleHandleW.restype = wintypes.HINSTANCE

        def _message_window_worker():
            try:
                h_inst = kernel32.GetModuleHandleW(None)
                wc = WNDCLASSEX()
                wc.cbSize = ctypes.sizeof(WNDCLASSEX)
                wc.lpfnWndProc = _IPC_WNDPROC_REF
                wc.hInstance = h_inst
                wc.lpszClassName = target_class
                user32.RegisterClassExW(ctypes.byref(wc))

                hwnd = user32.CreateWindowExW(
                    0,
                    target_class,
                    IPC_WINDOW_NAME,
                    0, 0, 0, 0, 0,
                    None, None,
                    h_inst,
                    None
                )

                msg = wintypes.MSG()
                while user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) > 0:
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
            except Exception as e:
                log_debug(f"IPC message window loop exception: {e}")

        threading.Thread(target=_message_window_worker, daemon=True, name="PCDeck-IPC-Msg").start()
    except Exception as e:
        log_debug(f"start_single_instance_ipc_server failed: {e}")



def show_native_toast_notification(title: str, message: str, action_url: Optional[str] = None, action_label: Optional[str] = None) -> bool:
    """Dispatches a native Windows 10/11 interactive toast notification banner with action buttons for MSIX package."""
    if sys.platform != "win32":
        return False
    aumid = PCDeckProGUI._get_msix_aumid()
    if not aumid:
        return False
    try:
        action_xml = ""
        if action_url and action_label:
            action_xml = f'<actions><action content="{action_label}" arguments="{action_url}" activationType="protocol"/></actions>'

        ps_script = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
$template = @"
<toast duration="long">
    <visual>
        <binding template="ToastGeneric">
            <text>{title}</text>
            <text>{message}</text>
        </binding>
    </visual>
    {action_xml}
</toast>
"@
$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($template)
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("{aumid}")
$notifier.Show($toast)
"""
        subprocess.Popen(
            ["powershell", "-ExecutionPolicy", "Bypass", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_script],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
        )
        return True
    except Exception as e:
        log_debug(f"show_native_toast_notification error: {e}")
        return False


def main():
    import multiprocessing
    multiprocessing.freeze_support()
    start_minimized = any(arg in sys.argv for arg in ["--tray", "--minimized", "--startup", "-m"])
    # Enforce strict single-instance check before any UI, socket, or thread creation
    if not acquire_single_instance_lock(is_tray_launch=start_minimized):
        log_debug("Duplicate instance detected at startup. Exiting cleanly.")
        sys.exit(0)

    try:
        log_debug(f"Starting PCDeck Pro GUI Application... (start_minimized={start_minimized}, admin={is_admin()})")
        root = tk.Tk()
        root.report_callback_exception = lambda exc, val, tb: global_excepthook(exc, val, tb)
        root.withdraw()  # Prevent top-left flashing while GUI builds and calculates centered position
        app_gui = PCDeckProGUI(root, start_minimized=start_minimized)
        start_single_instance_ipc_server(root, app_gui.open_dashboard)
        if not start_minimized:
            root.update_idletasks()
            root.deiconify()
            try:
                root.lift()
                root.attributes("-topmost", True)
                root.after(250, lambda: root.attributes("-topmost", False))
                root.focus_force()
            except Exception:
                pass
        log_debug("Entering root.mainloop()...")
        root.mainloop()
        log_debug("root.mainloop() exited. Terminating process cleanly.")
        import os
        os._exit(0)
    except Exception as e:
        log_debug(f"Fatal error in main(): {traceback.format_exc()}")
        try:
            messagebox.showerror("PCDeck Pro Error", f"Fatal error: {e}")
        except Exception:
            pass
        import os
        os._exit(1)


if __name__ == "__main__":
    main()

