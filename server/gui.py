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
import winreg

from PIL import Image, ImageTk
import qrcode
import uvicorn

LOG_FILE = os.path.join(os.path.expanduser("~"), "pcdeck_pro_debug.log")

# ---------------------------------------------------------------------------
# Design tokens
#
# One accent, neutral surfaces, and saturated colour reserved for state. The
# previous palette ran five neons (cyan, lime, yellow, pink, orange) at full
# saturation against near-black, which is what made the client read as generic.
# Change a value here and it applies across every screen.
# ---------------------------------------------------------------------------
C_BG = "#0d1117"             # window background
C_SURFACE = "#151b24"        # panels / cards
C_SURFACE_2 = "#1c2330"      # rows, nested blocks
C_SURFACE_3 = "#222b39"      # hover / raised chips
C_INPUT = "#0f141b"          # entry + combobox fields
C_BORDER = "#262d3a"         # default hairline
C_BORDER_STRONG = "#333c4d"  # emphasised divider

C_TEXT = "#e6edf3"           # primary copy (never pure white - harsh on dark)
C_TEXT_DIM = "#8b98a9"       # secondary copy
C_BLACK = "#000000"

C_ACCENT = "#22d3ee"         # the single brand accent
C_SUCCESS = "#3fb950"        # connected / running
C_WARNING = "#d29922"        # attention
C_DANGER = "#f85149"         # stop / error

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

def log_debug(msg: str):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass

def global_excepthook(exc_type, exc_value, exc_tb):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] UNCAUGHT EXCEPTION:\n")
            traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
    except Exception:
        pass

sys.excepthook = global_excepthook

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
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("PCDeckPro.DesktopClient.Pro.v2026")
    except Exception:
        pass

# Ensure search paths and working directory
if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(sys.executable))
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
        start_watchdog,
        stop_watchdog,
    )


def apply_crisp_window_icon(window):
    """
    Sets high-DPI crystal-sharp icon for Window title bar, Alt+Tab switcher, and Windows Taskbar.
    Directly interfaces with Win32 WM_SETICON, SetClassLongPtrW (with 64-bit ctypes argtypes),
    and SetWindowPos on all native HWNDs (frame + child) to ensure Windows 11 Taskbar never shows Tk feather.
    """
    try:
        meipass_dir = getattr(sys, "_MEIPASS", "")
        icon_candidates = [
            os.path.join(meipass_dir, "app_icon.ico"),
            os.path.join(meipass_dir, "PCDeck.ico"),
            os.path.join(meipass_dir, "icon.ico"),
            os.path.join(parent_dir, "app_icon.ico"),
            os.path.join(current_dir, "app_icon.ico"),
            os.path.join(parent_dir, "PCDeck.ico"),
            os.path.join(current_dir, "PCDeck.ico"),
            os.path.join(parent_dir, "icon.ico"),
            os.path.join(current_dir, "icon.ico"),
        ]
        ico_file = next((p for p in icon_candidates if p and os.path.exists(p)), None)
        if ico_file:
            ico_abs = os.path.abspath(ico_file)
            try:
                window.iconbitmap(default=ico_abs)
            except Exception:
                try:
                    window.iconbitmap(ico_abs)
                except Exception:
                    pass

        # Load multi-res PNG photos for Tkinter window iconphoto (Alt+Tab & Window manager)
        png_candidates = [
            os.path.join(meipass_dir, "PCDeck_Mouse_Logo.png"),
            os.path.join(meipass_dir, "icon.png"),
            os.path.join(parent_dir, "PCDeck_Mouse_Logo.png"),
            os.path.join(current_dir, "PCDeck_Mouse_Logo.png"),
            os.path.join(parent_dir, "icon.png"),
            os.path.join(current_dir, "icon.png"),
        ]
        png_file = next((p for p in png_candidates if p and os.path.exists(p)), None)
        if png_file:
            try:
                base_img = Image.open(png_file)
                photos = []
                for s in [16, 24, 32, 48, 64, 128, 256]:
                    photos.append(ImageTk.PhotoImage(base_img.resize((s, s), Image.Resampling.LANCZOS)))
                window.iconphoto(False, *photos)
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

                    hwnd_ancestor = None
                    try:
                        hwnd_ancestor = user32.GetAncestor(hwnd_child, 2)  # GA_ROOT = 2
                    except Exception:
                        pass

                    hwnd_parent = None
                    try:
                        hwnd_parent = user32.GetParent(hwnd_child)
                    except Exception:
                        pass

                    hwnds = {h for h in [hwnd_frame, hwnd_child, hwnd_ancestor, hwnd_parent] if h}

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
            window.after(50, _inject_win32_icons)
            window.after(300, _inject_win32_icons)
    except Exception as e:
        log_debug(f"apply_crisp_window_icon error: {e}")


class PCDeckProGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("PCDeck - Wireless PC Touch Deck & Streamer")
        self.root.geometry("960x640")
        self.root.minsize(920, 600)
        self.root.configure(bg=C_BG)

        # Set Window Icon for Titlebar, Taskbar, and Alt-Tab
        apply_crisp_window_icon(self.root)

        meipass_dir = getattr(sys, "_MEIPASS", "")
        png_candidates = [
            os.path.join(meipass_dir, "PCDeck_Mouse_Logo.png"),
            os.path.join(meipass_dir, "icon.png"),
            os.path.join(parent_dir, "PCDeck_Mouse_Logo.png"),
            os.path.join(current_dir, "PCDeck_Mouse_Logo.png"),
            os.path.join(parent_dir, "icon.png"),
            os.path.join(current_dir, "icon.png"),
        ]
        master_png = next((p for p in png_candidates if p and os.path.exists(p)), None)
        if master_png:
            try:
                self.logo_img = Image.open(master_png)
                self.logo_photo = ImageTk.PhotoImage(self.logo_img.resize((36, 36), Image.Resampling.LANCZOS))
            except Exception:
                self.logo_photo = None
        else:
            self.logo_photo = None

        # Server Handle & Telemetry
        self.server: Optional[uvicorn.Server] = None
        self.server_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.start_time = time.time()

        # State Variables
        self.start_boot_var = tk.BooleanVar(value=self.check_autostart_registry())
        self.reconnect_var = tk.StringVar(value="auto")
        self.fps_var = tk.StringVar(value="30")
        self.qr_photo = None
        self.active_serial = ""
        self.active_model = ""
        self.phone_remote_win = None

        # Wi-Fi Auto-Reconnector Configuration
        self.wifi_config = load_wifi_config()
        self.auto_wifi_var = tk.BooleanVar(value=self.wifi_config.get("auto_reconnect_on_launch", False))

        self._cleanup_legacy_autostart()
        self._build_ui()
        self.start_server()
        self._init_wifi_reconnector()
        self._start_metrics_loop()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _build_ui(self):
        # 1. Top Cyber-Neon Header Bar
        header = tk.Frame(
            self.root,
            bg=C_SURFACE,
            bd=0,
            relief="solid",
            highlightbackground=C_BORDER,
            highlightthickness=1,
        )
        header.pack(fill="x", padx=16, pady=(12, 8))

        brand_frame = tk.Frame(header, bg=C_SURFACE)
        brand_frame.pack(side="left", padx=14, pady=10)

        # Brand Icon Badge
        if hasattr(self, "logo_photo") and self.logo_photo:
            logo_lbl = tk.Label(brand_frame, image=self.logo_photo, bg=C_SURFACE)
            logo_lbl.pack(side="left", padx=(0, 10))

        title_box = tk.Frame(brand_frame, bg=C_SURFACE)
        title_box.pack(side="left")

        title_row = tk.Frame(title_box, bg=C_SURFACE)
        title_row.pack(anchor="w")

        tk.Label(
            title_row,
            text="PC",
            font=F_TITLE,
            fg=C_TEXT,
            bg=C_SURFACE,
        ).pack(side="left")

        tk.Label(
            title_row,
            text="Deck",
            font=F_TITLE,
            fg=C_ACCENT,
            bg=C_SURFACE,
        ).pack(side="left")

        sub_lbl = tk.Label(
            title_box,
            text="WIRELESS PC TOUCH DECK & STREAMER",
            font=F_SMALL_STRONG,
            fg=C_TEXT_DIM,
            bg=C_SURFACE,
        )
        sub_lbl.pack(anchor="w")

        # Right Header Stats
        header_right = tk.Frame(header, bg=C_SURFACE)
        header_right.pack(side="right", padx=14, pady=10)

        self.status_pill = tk.Label(
            header_right,
            text=f"● SERVER: [ONLINE] ({LOCAL_IP}:{SERVER_PORT})",
            font=F_BODY_STRONG,
            fg=C_BG,
            bg=C_SUCCESS,
            bd=0,
            padx=12,
            pady=4,
        )
        self.status_pill.pack(side="right", padx=(8, 0))

        self.client_badge = tk.Label(
            header_right,
            text="0 Clients",
            font=F_BODY_STRONG,
            fg=C_ACCENT,
            bg=C_SURFACE_3,
            bd=1,
            relief="solid",
            padx=10,
            pady=3,
        )
        self.client_badge.pack(side="right")

        self.pro_badge = tk.Label(
            header_right,
            text="★ PRO ACTIVE",
            font=F_SMALL_STRONG,
            fg="#ffd700",
            bg="#221e10",
            bd=1,
            relief="solid",
            padx=8,
            pady=3,
        )

        # 2. Main 2-Column Content Layout
        content = tk.Frame(self.root, bg=C_BG)
        content.pack(fill="both", expand=True, padx=16, pady=4)

        # Cyber-Neon Combobox styling with strict dark background mapping
        try:
            combo_style = ttk.Style()
            combo_style.theme_use("clam")
            combo_style.configure(
                "Cyber.TCombobox",
                fieldbackground=C_INPUT,
                background=C_SURFACE_3,
                foreground=C_ACCENT,
                darkcolor=C_INPUT,
                lightcolor=C_BORDER,
                selectbackground=C_ACCENT,
                selectforeground=C_BG,
                arrowcolor=C_ACCENT,
                bordercolor=C_BORDER,
                padding=4,
            )
            combo_style.map(
                "Cyber.TCombobox",
                fieldbackground=[("readonly", C_INPUT), ("active", C_SURFACE), ("!disabled", C_INPUT)],
                background=[("readonly", C_SURFACE_3), ("active", C_BORDER), ("!disabled", C_SURFACE_3)],
                foreground=[("readonly", C_ACCENT), ("active", C_ACCENT), ("!disabled", C_ACCENT)],
                selectbackground=[("readonly", C_ACCENT)],
                selectforeground=[("readonly", C_BG)],
            )
            self.root.option_add("*TCombobox*Listbox.background", C_INPUT)
            self.root.option_add("*TCombobox*Listbox.foreground", C_ACCENT)
            self.root.option_add("*TCombobox*Listbox.selectBackground", C_ACCENT)
            self.root.option_add("*TCombobox*Listbox.selectForeground", C_BG)
        except Exception:
            pass

        # ---------------- PRO STREAMDECK 2-PANEL LAYOUT ----------------

        # ---------------- LEFT PANEL: Connection Gateway (Width ~ 310px) ----------------
        left_col = tk.Frame(
            content,
            bg=C_SURFACE,
            bd=0,
            relief="solid",
            highlightbackground=C_BORDER,
            highlightthickness=1,
            width=310,
        )
        left_col.pack(side="left", fill="both", padx=(0, 8), pady=4)
        left_col.pack_propagate(False)

        # Header: CONNECT GATEWAY
        qr_hdr = tk.Frame(left_col, bg=C_SURFACE)
        qr_hdr.pack(fill="x", padx=12, pady=(10, 4))

        tk.Label(
            qr_hdr,
            text="CONNECT GATEWAY",
            font=F_LABEL,
            fg=C_ACCENT,
            bg=C_SURFACE,
        ).pack(side="left")

        tk.Label(
            qr_hdr,
            text="Scan to Connect",
            font=F_SMALL,
            fg=C_TEXT_DIM,
            bg=C_SURFACE,
        ).pack(side="right")

        # QR Code Card
        qr_card = tk.Frame(
            left_col,
            bg=C_INPUT,
            bd=2,
            relief="solid",
            highlightbackground=C_BORDER,
            highlightthickness=1,
        )
        qr_card.pack(padx=14, pady=4)

        self.qr_label = tk.Label(qr_card, bg=C_INPUT, bd=0)
        self.qr_label.pack(padx=6, pady=6)
        self._generate_qr_image()

        # IP Address Bar with Copy
        ip_box = tk.Frame(
            left_col,
            bg=C_INPUT,
            bd=0,
            relief="solid",
            highlightbackground=C_BORDER,
            highlightthickness=1,
        )
        ip_box.pack(fill="x", padx=14, pady=(4, 6))

        self.ip_entry = tk.Entry(
            ip_box,
            font=(F_MONO, 9, "bold"),
            fg=C_ACCENT,
            bg=C_INPUT,
            readonlybackground=C_INPUT,
            selectbackground=C_ACCENT,
            selectforeground=C_BG,
            bd=0,
            justify="center",
        )
        self.ip_entry.insert(0, f"http://{LOCAL_IP}:{SERVER_PORT}")
        self.ip_entry.config(state="readonly")
        self.ip_entry.pack(side="left", fill="x", expand=True, padx=4, pady=4)

        copy_btn = tk.Button(
            ip_box,
            text="Copy",
            font=F_SMALL_STRONG,
            fg=C_TEXT,
            bg=C_SURFACE_3,
            bd=0,
            cursor="hand2",
            padx=8,
            command=self.copy_ip,
        )
        copy_btn.pack(side="right", padx=3, pady=3)

        # WI-FI & HOTSPOTS Card
        wifi_card = tk.Frame(
            left_col,
            bg=C_SURFACE_2,
            bd=0,
            relief="solid",
            highlightbackground=C_BORDER,
            highlightthickness=1,
        )
        wifi_card.pack(fill="x", padx=14, pady=(4, 6))

        wifi_hdr = tk.Frame(wifi_card, bg=C_SURFACE_2)
        wifi_hdr.pack(fill="x", padx=8, pady=(6, 2))

        tk.Label(
            wifi_hdr,
            text="WI-FI & HOTSPOTS",
            font=F_LABEL,
            fg=C_TEXT,
            bg=C_SURFACE_2,
        ).pack(side="left")

        self.wifi_status_badge = tk.Label(
            wifi_hdr,
            text="● Searching...",
            font=F_SMALL_STRONG,
            fg=C_BG,
            bg=C_WARNING,
            padx=6,
            pady=1,
        )
        self.wifi_status_badge.pack(side="right")

        # Combobox
        wifi_combo_row = tk.Frame(wifi_card, bg=C_SURFACE_2)
        wifi_combo_row.pack(fill="x", padx=8, pady=(2, 4))

        self.wifi_select_var = tk.StringVar()
        self.wifi_combo = ttk.Combobox(
            wifi_combo_row,
            textvariable=self.wifi_select_var,
            font=F_SMALL,
            style="Cyber.TCombobox",
            state="readonly",
        )
        self.wifi_combo.pack(fill="x", expand=True)

        # Buttons Row: CONNECT & SCAN
        wifi_act_row = tk.Frame(wifi_card, bg=C_SURFACE_2)
        wifi_act_row.pack(fill="x", padx=8, pady=(0, 4))

        self.btn_wifi_connect = tk.Button(
            wifi_act_row,
            text="CONNECT",
            font=F_SMALL_STRONG,
            fg=C_BG,
            bg=C_ACCENT,
            bd=0,
            cursor="hand2",
            padx=8,
            pady=2,
            command=self._on_wifi_connect_clicked,
        )
        self.btn_wifi_connect.pack(side="left", fill="x", expand=True, padx=(0, 2))

        self.btn_wifi_scan = tk.Button(
            wifi_act_row,
            text="SCAN",
            font=F_SMALL_STRONG,
            fg=C_TEXT,
            bg=C_SURFACE_3,
            bd=0,
            cursor="hand2",
            padx=8,
            pady=2,
            command=self._on_wifi_scan_clicked,
        )
        self.btn_wifi_scan.pack(side="right", padx=(2, 0))

        # Auto-reconnect Checkbox
        tk.Checkbutton(
            wifi_card,
            text="Auto-connect on launch",
            variable=self.auto_wifi_var,
            font=F_SMALL,
            fg=C_TEXT_DIM,
            bg=C_SURFACE_2,
            selectcolor=C_BG,
            activebackground=C_SURFACE_2,
            command=self._on_auto_wifi_toggle,
        ).pack(anchor="w", padx=8, pady=(0, 4))

        # Diagnostics & Resolution Card
        diag_box = tk.Frame(left_col, bg=C_SURFACE_3, bd=1, relief="solid")
        diag_box.pack(fill="x", padx=14, pady=(2, 8))

        self.phone_status_lbl = tk.Label(
            diag_box,
            text=f"● Wi-Fi: {LOCAL_IP}",
            font=F_SMALL_STRONG,
            fg=C_SUCCESS,
            bg=C_SURFACE_3,
            anchor="w",
        )
        self.phone_status_lbl.pack(fill="x", padx=8, pady=(4, 1))

        self.screen_lbl = tk.Label(
            diag_box,
            text=f"🖥️ PC: {controller.screen_width} x {controller.screen_height} (60 FPS)",
            font=(F_MONO, 8),
            fg=C_TEXT_DIM,
            bg=C_SURFACE_3,
            anchor="w",
        )
        self.screen_lbl.pack(fill="x", padx=8, pady=(0, 4))

        # ---------------- RIGHT PANEL: Actions & Power Center (Expand=True) ----------------
        right_col = tk.Frame(
            content,
            bg=C_SURFACE,
            bd=0,
            relief="solid",
            highlightbackground=C_BORDER,
            highlightthickness=1,
        )
        right_col.pack(side="right", fill="both", expand=True, padx=(0, 0), pady=4)

        # 1. TOP STATUS BAR (Uptime, Network, Latency)
        top_status_card = tk.Frame(right_col, bg=C_SURFACE_2, bd=1, relief="solid")
        top_status_card.pack(fill="x", padx=14, pady=(10, 4))

        self.uptime_lbl = tk.Label(
            top_status_card,
            text="⏱️ Uptime: 00:00:00",
            font=F_SMALL_STRONG,
            fg=C_TEXT,
            bg=C_SURFACE_2,
            padx=8,
            pady=4,
        )
        self.uptime_lbl.pack(side="left")

        self.network_health_lbl = tk.Label(
            top_status_card,
            text="📶 Network: Excellent (100%)",
            font=F_SMALL_STRONG,
            fg=C_SUCCESS,
            bg=C_SURFACE_2,
            padx=8,
            pady=4,
        )
        self.network_health_lbl.pack(side="left", padx=8)

        tk.Label(
            top_status_card,
            text="⚡ Latency: < 1ms",
            font=F_SMALL_STRONG,
            fg=C_ACCENT,
            bg=C_SURFACE_2,
            padx=8,
            pady=4,
        ).pack(side="right")

        # 2. HERO CARD: LIVE PHONE CONTROLLER
        hero_card = tk.Frame(
            right_col,
            bg=C_SURFACE_2,
            bd=0,
            relief="solid",
            highlightbackground=C_BORDER,
            highlightthickness=1,
        )
        hero_card.pack(fill="x", padx=14, pady=4)

        hero_hdr = tk.Frame(hero_card, bg=C_SURFACE_2)
        hero_hdr.pack(fill="x", padx=10, pady=(6, 2))

        tk.Label(
            hero_hdr,
            text="LIVE PHONE SCREEN & TOUCH CONTROL",
            font=F_LABEL,
            fg=C_TEXT,
            bg=C_SURFACE_2,
        ).pack(side="left")

        self.stream_status_badge = tk.Label(
            hero_hdr,
            text="● READY",
            font=F_SMALL_STRONG,
            fg=C_BG,
            bg=C_SUCCESS,
            padx=6,
            pady=1,
        )
        self.stream_status_badge.pack(side="right")

        tk.Label(
            hero_card,
            text="Cast and control your Android phone in real-time with ultra-low latency. Includes hardware touch & keyboard.",
            font=F_SMALL,
            fg=C_TEXT_DIM,
            bg=C_SURFACE_2,
            justify="left",
            wraplength=480,
        ).pack(anchor="w", padx=10, pady=(0, 6))

        hero_btn_row = tk.Frame(hero_card, bg=C_SURFACE_2)
        hero_btn_row.pack(fill="x", padx=10, pady=(0, 6))

        self.btn_primary_stream = tk.Button(
            hero_btn_row,
            text="OPEN LIVE PHONE CONTROLLER",
            font=F_BODY_STRONG,
            fg=C_BG,
            bg=C_ACCENT,
            bd=0,
            cursor="hand2",
            command=self.open_phone_remote,
            pady=6,
        )
        self.btn_primary_stream.pack(side="left", fill="x", expand=True, padx=(0, 4))

        btn_wireless_mode = tk.Button(
            hero_btn_row,
            text="WIRELESS MODE",
            font=F_SMALL_STRONG,
            fg=C_TEXT,
            bg=C_SURFACE_3,
            bd=0,
            cursor="hand2",
            command=self.quick_wireless_connect,
            pady=6,
            padx=8,
        )
        btn_wireless_mode.pack(side="right", padx=(4, 0))

        # 3. 2x2 POWER TOOLS GRID
        tools_grid = tk.Frame(right_col, bg=C_SURFACE)
        tools_grid.pack(fill="x", padx=14, pady=4)

        # Tile 1: 📤 Send Files
        tile1 = tk.Frame(tools_grid, bg=C_SURFACE_2, bd=1, relief="solid")
        tile1.pack(side="left", fill="both", expand=True, padx=(0, 4))

        t1_hdr = tk.Frame(tile1, bg=C_SURFACE_2)
        t1_hdr.pack(fill="x", padx=8, pady=(4, 1))
        tk.Label(t1_hdr, text="📤 SEND FILES", font=F_LABEL, fg=C_TEXT, bg=C_SURFACE_2).pack(side="left")

        tk.Label(tile1, text="Drop files to phone", font=F_SMALL, fg=C_TEXT_DIM, bg=C_SURFACE_2).pack(anchor="w", padx=8)

        tk.Button(
            tile1,
            text="SELECT FILES",
            font=F_SMALL_STRONG,
            fg=C_BG,
            bg=C_ACCENT,
            bd=0,
            cursor="hand2",
            command=self.send_files_to_phone,
            pady=3,
        ).pack(fill="x", padx=8, pady=(4, 6))

        # Tile 2: 📂 Open Transfers
        tile2 = tk.Frame(tools_grid, bg=C_SURFACE_2, bd=1, relief="solid")
        tile2.pack(side="right", fill="both", expand=True, padx=(4, 0))

        t2_hdr = tk.Frame(tile2, bg=C_SURFACE_2)
        t2_hdr.pack(fill="x", padx=8, pady=(4, 1))
        tk.Label(t2_hdr, text="📂 RECEIVED", font=F_LABEL, fg=C_TEXT, bg=C_SURFACE_2).pack(side="left")

        tk.Label(tile2, text="View received files", font=F_SMALL, fg=C_TEXT_DIM, bg=C_SURFACE_2).pack(anchor="w", padx=8)

        tk.Button(
            tile2,
            text="OPEN TRANSFERS",
            font=F_SMALL_STRONG,
            fg=C_TEXT,
            bg=C_SURFACE_3,
            bd=0,
            cursor="hand2",
            command=self.open_transfers_folder,
            pady=3,
        ).pack(fill="x", padx=8, pady=(4, 6))

        # Row 2 of Tools: Audio Streaming & Preferences
        tools_grid2 = tk.Frame(right_col, bg=C_SURFACE)
        tools_grid2.pack(fill="x", padx=14, pady=4)

        # Tile 3: 🔊 Audio Streaming
        tile3 = tk.Frame(tools_grid2, bg=C_SURFACE_2, bd=1, relief="solid")
        tile3.pack(side="left", fill="both", expand=True, padx=(0, 4))

        t3_hdr = tk.Frame(tile3, bg=C_SURFACE_2)
        t3_hdr.pack(fill="x", padx=8, pady=(4, 1))
        tk.Label(t3_hdr, text="🔊 AUDIO STREAM", font=F_LABEL, fg=C_TEXT, bg=C_SURFACE_2).pack(side="left")

        self.audio_status_lbl = tk.Label(t3_hdr, text="OFF", font=F_SMALL_STRONG, fg=C_TEXT_DIM, bg=C_SURFACE_3, padx=4)
        self.audio_status_lbl.pack(side="right")

        tk.Label(tile3, text="PC audio to headphones", font=F_SMALL, fg=C_TEXT_DIM, bg=C_SURFACE_2).pack(anchor="w", padx=8)

        tk.Button(
            tile3,
            text="AUDIO STREAM (ON/OFF)",
            font=F_SMALL_STRONG,
            fg=C_TEXT,
            bg=C_SURFACE_3,
            bd=0,
            cursor="hand2",
            command=self.open_phone_remote,
            pady=3,
        ).pack(fill="x", padx=8, pady=(4, 6))

        # Tile 4: ⚙️ Preferences
        tile4 = tk.Frame(tools_grid2, bg=C_SURFACE_2, bd=1, relief="solid")
        tile4.pack(side="right", fill="both", expand=True, padx=(4, 0))

        t4_hdr = tk.Frame(tile4, bg=C_SURFACE_2)
        t4_hdr.pack(fill="x", padx=8, pady=(4, 1))
        tk.Label(t4_hdr, text="⚙️ PREFERENCES", font=F_LABEL, fg=C_TEXT, bg=C_SURFACE_2).pack(side="left")

        tk.Label(tile4, text="System startup settings", font=F_SMALL, fg=C_TEXT_DIM, bg=C_SURFACE_2).pack(anchor="w", padx=8)

        tk.Checkbutton(
            tile4,
            text="Start with Windows",
            variable=self.start_boot_var,
            font=F_SMALL,
            fg=C_TEXT,
            bg=C_SURFACE_2,
            selectcolor=C_BG,
            activebackground=C_SURFACE_2,
            command=self.save_settings,
        ).pack(anchor="w", padx=8, pady=(4, 6))

        # 4. MOBILE COMPANION APP CARD
        app_card = tk.Frame(
            right_col,
            bg=C_SURFACE_2,
            bd=0,
            relief="solid",
            highlightbackground=C_BORDER,
            highlightthickness=1,
        )
        app_card.pack(fill="x", padx=14, pady=4)

        app_hdr = tk.Frame(app_card, bg=C_SURFACE_2)
        app_hdr.pack(fill="x", padx=10, pady=(6, 2))

        tk.Label(
            app_hdr,
            text="MOBILE COMPANION APP",
            font=F_LABEL,
            fg=C_ACCENT,
            bg=C_SURFACE_2,
        ).pack(side="left")

        app_body = tk.Frame(app_card, bg=C_SURFACE_2)
        app_body.pack(fill="x", padx=10, pady=(0, 6))

        app_btn_row = tk.Frame(app_body, bg=C_SURFACE_2)
        app_btn_row.pack(fill="x", pady=(2, 0))

        tk.Button(
            app_btn_row,
            text="🌐 Download Android App (pcdeck.vercel.app)",
            font=F_SMALL_STRONG,
            fg=C_BG,
            bg=C_ACCENT,
            bd=0,
            cursor="hand2",
            padx=8,
            pady=4,
            command=lambda: webbrowser.open("https://pcdeck.vercel.app"),
        ).pack(fill="x", expand=True)

        # 5. SYSTEM POWER BAR (Restart & Stop)
        pwr_bar = tk.Frame(right_col, bg=C_SURFACE)
        pwr_bar.pack(fill="x", padx=14, pady=(6, 8))

        tk.Button(
            pwr_bar,
            text="🔄 RESTART SERVER",
            font=F_BODY_STRONG,
            fg=C_BG,
            bg=C_ACCENT,
            bd=0,
            cursor="hand2",
            command=self.restart_server,
            pady=4,
            padx=12,
        ).pack(side="left", fill="x", expand=True, padx=(0, 4))

        tk.Button(
            pwr_bar,
            text="⏹️ STOP SERVER",
            font=F_BODY_STRONG,
            fg=C_TEXT,
            bg=C_DANGER,
            bd=0,
            cursor="hand2",
            command=self.stop_server,
            pady=4,
            padx=12,
        ).pack(side="right", fill="x", expand=True, padx=(4, 0))

        # Start live uptime ticker
        self._start_uptime_ticker()

    def _start_uptime_ticker(self):
        self._update_uptime_tick()

    def _update_uptime_tick(self):
        try:
            if hasattr(self, "uptime_lbl") and self.uptime_lbl and self.uptime_lbl.winfo_exists():
                elapsed = int(time.time() - getattr(self, "start_time", time.time()))
                hrs, rem = divmod(elapsed, 3600)
                mins, secs = divmod(rem, 60)
                self.uptime_lbl.config(text=f"⏱️ Uptime: {hrs:02d}:{mins:02d}:{secs:02d}")
                self.root.after(1000, self._update_uptime_tick)
        except Exception:
            pass

    def _generate_qr_image(self):
        """Generate and display Tk PhotoImage QR with maximum contrast."""
        url = getattr(self, "server_url", SERVER_URL)
        clean_ip = url.replace("http://", "").replace("https://", "")
        gateway_url = f"https://pcdeck.vercel.app/connect?ip={clean_ip}"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=5,
            border=2,
        )
        qr.add_data(gateway_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color=C_BLACK, back_color=C_TEXT)

        self.qr_photo = ImageTk.PhotoImage(img)
        self.qr_label.config(image=self.qr_photo, bg=C_TEXT)

    def copy_ip(self):
        url = getattr(self, "server_url", SERVER_URL)
        self.root.clipboard_clear()
        self.root.clipboard_append(url)
        messagebox.showinfo("PCDeck Pro", f"Copied server address to clipboard:\n{url}")

    def refresh_network_ip(self):
        """Manually force detect local Wi-Fi or Hotspot IP address."""
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
                mode = "Offline Hotspot" if new_ip.startswith("192.168.43.") or new_ip.startswith("172.") else "Wi-Fi Ready"
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
            streamer.fps_limit = val
        except Exception:
            pass

    def _get_autostart_cmd(self) -> str:
        if getattr(sys, "frozen", False):
            return f'"{sys.executable}"'
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pcdeck_exe = os.path.join(parent_dir, "PCDeck.exe")
        if os.path.exists(pcdeck_exe):
            return f'"{pcdeck_exe}"'
        return f'"{sys.executable}" "{os.path.abspath(__file__)}"'

    def _cleanup_legacy_autostart(self):
        """Removes obsolete registry entries and startup folder shortcuts from older versions."""
        if sys.platform != "win32":
            return
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE | winreg.KEY_READ,
            )
            for legacy_name in ["NeonTrack", "PCDeckPro", "PCDeck_Server", "PCDeck_Pro"]:
                try:
                    winreg.DeleteValue(key, legacy_name)
                except Exception:
                    pass
            # If PCDeck is registered, verify that the target path still exists and is updated
            try:
                val, _ = winreg.QueryValueEx(key, "PCDeck")
                clean_path = str(val).strip('"').split('"')[0]
                if not os.path.exists(clean_path):
                    # Path is stale, update with current executable path
                    current_cmd = self._get_autostart_cmd()
                    winreg.SetValueEx(key, "PCDeck", 0, winreg.REG_SZ, current_cmd)
            except Exception:
                pass
            winreg.CloseKey(key)
        except Exception:
            pass

        # Check Windows Startup Folder for outdated .lnk shortcuts
        try:
            startup_dir = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup")
            if os.path.exists(startup_dir):
                for old_shortcut in ["NeonTrack.lnk", "PCDeck_Pro.lnk"]:
                    p = os.path.join(startup_dir, old_shortcut)
                    if os.path.exists(p):
                        try:
                            os.remove(p)
                        except Exception:
                            pass
        except Exception:
            pass

    def check_autostart_registry(self) -> bool:
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_READ,
            )
            val = None
            for kname in ["PCDeck", "PCDeck_Pro", "NeonTrack"]:
                try:
                    val, _ = winreg.QueryValueEx(key, kname)
                    if val:
                        break
                except Exception:
                    pass
            winreg.CloseKey(key)
            if not val:
                return False
            clean_path = str(val).strip('"').split('"')[0]
            return os.path.exists(clean_path)
        except Exception:
            return False

    def save_settings(self):
        autostart = self.start_boot_var.get()
        cmd = self._get_autostart_cmd()

        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE,
            )
            if autostart:
                winreg.SetValueEx(key, "PCDeck", 0, winreg.REG_SZ, cmd)
                for legacy in ["NeonTrack", "PCDeck_Pro", "PCDeckPro"]:
                    try:
                        winreg.DeleteValue(key, legacy)
                    except Exception:
                        pass
            else:
                for kname in ["PCDeck", "PCDeck_Pro", "NeonTrack", "PCDeckPro"]:
                    try:
                        winreg.DeleteValue(key, kname)
                    except Exception:
                        pass
            winreg.CloseKey(key)
        except Exception:
            pass
        self.update_fps()

    def start_server(self):
        if self.is_running:
            return

        def run_uvicorn():
            try:
                config = uvicorn.Config(
                    app=app,
                    host="0.0.0.0",
                    port=SERVER_PORT,
                    log_level="error",
                    access_log=False,
                )
                self.server = uvicorn.Server(config)
                log_debug(f"Starting uvicorn server on port {SERVER_PORT}...")
                self.server.run()
                log_debug("Uvicorn server finished.")
            except Exception as e:
                log_debug(f"Uvicorn server error: {traceback.format_exc()}")

        self.server_thread = threading.Thread(target=run_uvicorn, daemon=True)
        self.server_thread.start()
        self.is_running = True
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
                icon = "★" if n.get("is_saved") else "·"
                saved_tag = " [Saved]" if n.get("is_saved") else ""
                sig = f" ({n['signal']})" if n.get("signal") and n["signal"] != "Saved" else ""
                label = f"{icon} {n['ssid']}{saved_tag}{sig}"
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
        clean_ssid = re.sub(r"^[★·📶⚡]\s*", "", val)
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
                        f"● {st['ssid']}", C_SUCCESS, C_BG
                    ))
                    self.root.after(0, self.refresh_network_ip)
                else:
                    self.root.after(0, lambda: self._update_wifi_status_ui("● Connect Timeout", C_DANGER, C_TEXT))
            else:
                self.root.after(0, lambda: self._update_wifi_status_ui("● Connect Failed", C_DANGER, C_TEXT))

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

    def _start_metrics_loop(self):
        def update_metrics():
            try:
                # 1. Update active client count
                try:
                    from server.main import active_connections, screen_connections, get_local_ip
                except ImportError:
                    from main import active_connections, screen_connections, get_local_ip

                count = len(active_connections) + len(screen_connections)
                if hasattr(self, "client_badge") and self.client_badge.winfo_exists():
                    self.client_badge.config(text=f"{count} Client{'s' if count != 1 else ''}")

                # Pro License Badge sync
                try:
                    try:
                        from server.main import is_pro_client
                    except ImportError:
                        from main import is_pro_client
                    pro_active = is_pro_client()
                except Exception:
                    pro_active = False

                if hasattr(self, "pro_badge") and self.pro_badge.winfo_exists():
                    if pro_active and count > 0:
                        if not self.pro_badge.winfo_ismapped():
                            self.pro_badge.pack(side="right", padx=(0, 6))
                    else:
                        if self.pro_badge.winfo_ismapped():
                            self.pro_badge.pack_forget()

                # 2. Dynamic Hotspot / Wi-Fi IP auto-detection
                latest_ip = get_local_ip()
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
                            text="● Connect Wi-Fi / Phone Hotspot",
                            fg=C_WARNING,
                        )
                    else:
                        self.phone_status_lbl.config(
                            text=f"● Wi-Fi Online ({latest_ip})",
                            fg=C_SUCCESS,
                        )

                # 4. Periodic Wi-Fi Status Check (throttled to every 15s to keep USB dongles rock-solid)
                self._metrics_tick = getattr(self, "_metrics_tick", 0) + 1
                if self._metrics_tick % 5 == 0:
                    st = get_current_wifi_status()
                    if hasattr(self, "wifi_status_badge") and self.wifi_status_badge.winfo_exists():
                        current_badge = self.wifi_status_badge.cget("text")
                        if "Connecting" not in current_badge and "Scanning" not in current_badge:
                            if st["state"] == "connected" and st["ssid"]:
                                self.wifi_status_badge.config(
                                    text=f"● {st['ssid']} ({st['signal']})",
                                    bg=C_SUCCESS,
                                    fg=C_BG,
                                )
                            elif st["state"] != "connected":
                                self.wifi_status_badge.config(
                                    text="● Disconnected",
                                    bg=C_DANGER,
                                    fg=C_TEXT,
                                )

                # 5. Audio streaming status.
                #
                # This label used to be hardcoded to "ACTIVE (WASAPI)" at build
                # time and never updated, so it claimed audio was live even when
                # capture had failed or nothing was listening. Bind it to the
                # streamer's real state instead: a status light that always reads
                # green tells the user nothing.
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
                        # Audio is optional - a missing loopback device or a
                        # PyAudio import failure must not break the whole loop.
                        self.audio_status_lbl.config(text="● Unavailable", fg=C_WARNING)
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

            # 4. Destroy main Tk window
            self.root.destroy()
        except Exception:
            pass
        finally:
            os._exit(0)



class PhoneRemoteWindow:
    """Cyberpunk Interactive Phone Screen Streamer with Auto-Quality & Auto-FPS Engine."""

    def __init__(self, parent: tk.Tk, gui_app):
        self.parent = parent
        self.gui_app = gui_app
        self.win = tk.Toplevel(parent)
        self.win.title("PCDeck Pro - Live Phone Controller")
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
        dlg.title("PCDeck Pro - Wireless ADB Setup")
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
        tk.Label(ip_row, text="Phone IP & Port:", font=F_SMALL, fg=C_TEXT_DIM, bg=C_SURFACE_2, width=14, anchor="w").pack(side="left")
        ip_entry = tk.Entry(ip_row, font=F_BODY, fg=C_ACCENT, bg=C_INPUT, bd=1, relief="solid")
        ip_entry.pack(side="left", fill="x", expand=True)
        ip_entry.insert(0, f"{LOCAL_IP.rsplit('.', 1)[0]}.:5555")

        code_row = tk.Frame(m2_card, bg=C_SURFACE_2)
        code_row.pack(fill="x", padx=8, pady=2)
        tk.Label(code_row, text="Pair Code (if pairing):", font=F_SMALL, fg=C_TEXT_DIM, bg=C_SURFACE_2, width=14, anchor="w").pack(side="left")
        code_entry = tk.Entry(code_row, font=F_BODY, fg=C_WARNING, bg=C_INPUT, bd=1, relief="solid")
        code_entry.pack(side="left", fill="x", expand=True)

        res_lbl = tk.Label(dlg, text="", font=F_SMALL_STRONG, fg=C_WARNING, bg=C_SURFACE, wraplength=400)
        res_lbl.pack(pady=4)

        def _do_connect():
            target = ip_entry.get().strip()
            pair_code = code_entry.get().strip()
            if not target:
                return
            res_lbl.config(text="Connecting to Wireless ADB...", fg=C_ACCENT)

            def _bg():
                adb_bin = get_adb_path()
                try:
                    # If 6-digit pair code provided, pair first
                    if pair_code:
                        res_pair = subprocess.run(
                            [adb_bin, "pair", target, pair_code],
                            capture_output=True,
                            text=True,
                            timeout=8.0,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                        )
                        pair_out = res_pair.stdout.strip()
                        if "successfully paired" not in pair_out.lower():
                            dlg.after(0, lambda: res_lbl.config(text=f"Pairing: {pair_out}", fg=C_DANGER))
                            return

                    # Connect to wireless target
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


def main():
    import multiprocessing
    multiprocessing.freeze_support()
    try:
        log_debug("Starting PCDeck Pro GUI Application...")
        root = tk.Tk()
        app_gui = PCDeckProGUI(root)
        log_debug("Entering root.mainloop()...")
        root.mainloop()
    except Exception as e:
        log_debug(f"Fatal error in main(): {traceback.format_exc()}")
        try:
            messagebox.showerror("PCDeck Pro Error", f"Fatal error: {e}")
        except Exception:
            pass


if __name__ == "__main__":
    main()

