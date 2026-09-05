"""
PCDeck Pro - High-Performance Wireless PC Touch Deck & Streamer Server
FastAPI + Native Win32 Input Simulation + Low-Latency Screen Streaming + Fast File Transfers
"""

import asyncio
import datetime
import email.utils
import io
import ipaddress
import math
import os
import re
import secrets
import socket
import sys
import shutil
import threading
import time
from typing import Optional, Set, List, Dict, Any, Tuple

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

# Windows High-DPI Awareness & Taskbar AppID Registration
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("PCDeckPro.DesktopClient.Pro.v2026")
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass
        # High precision 1ms multimedia timer for sub-millisecond thread scheduling
        try:
            ctypes.windll.winmm.timeBeginPeriod(1)
            import atexit
            atexit.register(ctypes.windll.winmm.timeEndPeriod, 1)
        except Exception:
            pass
        # Elevate process priority to HIGH_PRIORITY_CLASS
        try:
            ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x00000080)
        except Exception:
            pass
    except Exception:
        pass

# Ensure search paths
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
for p in [current_dir, parent_dir]:
    if p and p not in sys.path:
        sys.path.insert(0, p)

try:
    from server.input_controller import WindowsInputController as InputController
    from server.screen_streamer import ScreenStreamer
    from server.audio_streamer import audio_streamer, mic_sink, is_mic_driver_installed, install_mic_driver_silently
    from server.gamepad_manager import gamepad_manager, is_vigem_installed, install_vigem_silently
    from server.camera_streamer import camera_streamer, is_webcam_driver_installed, install_webcam_driver_silently
    from server.wifi_latency_manager import wifi_latency_manager
    from server.binary_protocol import (
        unpack_binary_message,
        pack_pong,
        pack_ping,
        pack_move_rel,
        pack_move_abs,
        pack_touch_down,
        pack_touch_move,
        pack_touch_up,
        pack_click,
        pack_scroll_rel,
        pack_scroll_abs,
    )
except ImportError:
    try:
        from input_controller import WindowsInputController as InputController
        from screen_streamer import ScreenStreamer
        from audio_streamer import audio_streamer, mic_sink, is_mic_driver_installed, install_mic_driver_silently
        from gamepad_manager import gamepad_manager, is_vigem_installed, install_vigem_silently
        from camera_streamer import camera_streamer, is_webcam_driver_installed, install_webcam_driver_silently
        from wifi_latency_manager import wifi_latency_manager
        from binary_protocol import (
            unpack_binary_message,
            pack_pong,
            pack_ping,
            pack_move_rel,
            pack_move_abs,
            pack_touch_down,
            pack_touch_move,
            pack_touch_up,
            pack_click,
            pack_scroll_rel,
            pack_scroll_abs,
        )
    except ImportError:
        from .input_controller import WindowsInputController as InputController
        from .screen_streamer import ScreenStreamer
        from .audio_streamer import audio_streamer, mic_sink, is_mic_driver_installed, install_mic_driver_silently
        from .gamepad_manager import gamepad_manager, is_vigem_installed, install_vigem_silently
        from .camera_streamer import camera_streamer, is_webcam_driver_installed, install_webcam_driver_silently
        from .wifi_latency_manager import wifi_latency_manager
        from .binary_protocol import (
            unpack_binary_message,
            pack_pong,
            pack_ping,
            pack_move_rel,
            pack_move_abs,
            pack_touch_down,
            pack_touch_move,
            pack_touch_up,
            pack_click,
            pack_scroll_rel,
            pack_scroll_abs,
        )

import subprocess
import zipfile
import urllib.parse
import colorama
from colorama import Fore, Style
from fastapi import FastAPI, Body, File, Header, Request, Response, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import qrcode
from uvicorn import Config, Server

colorama.init(autoreset=True)

app = FastAPI(title="PCDeck Pro Server", version="2.1.0")

controller = InputController()
streamer = ScreenStreamer()

active_connections: Set[WebSocket] = set()
screen_connections: Set[WebSocket] = set()


def ensure_windows_firewall_rule():
    """Ensure Windows Defender Firewall allows inbound TCP traffic on port 8000 and UDP on port 8001."""
    if sys.platform == "win32":
        def _add_rules():
            try:
                subprocess.run(
                    [
                        "netsh", "advfirewall", "firewall", "add", "rule",
                        "name=PCDeck Pro Port 8000", "dir=in", "action=allow",
                        "protocol=TCP", "localport=8000", "profile=any"
                    ],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                    timeout=3,
                )
                subprocess.run(
                    [
                        "netsh", "advfirewall", "firewall", "add", "rule",
                        "name=PCDeck Pro UDP Discovery", "dir=in", "action=allow",
                        "protocol=UDP", "localport=8001", "profile=any"
                    ],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                    timeout=3,
                )
            except Exception:
                pass
        threading.Thread(target=_add_rules, name="PCDeck-Firewall-Init", daemon=True).start()


ensure_windows_firewall_rule()


def ensure_wlan_autoconfig_restored():
    """Ensure Windows WLAN AutoConfig is restored on startup in case of prior unexpected shutdowns."""
    if sys.platform == "win32":
        def _restore():
            try:
                if wifi_latency_manager and hasattr(wifi_latency_manager, "startup_auto_heal"):
                    wifi_latency_manager.startup_auto_heal()
            except Exception:
                pass
        threading.Thread(target=_restore, name="PCDeck-WLAN-Restore-Init", daemon=True).start()


ensure_wlan_autoconfig_restored()


# ---------------------------------------------------------------------------
# Zero-Config Ultra-Fast UDP Discovery Daemon (Port 8001)
# ---------------------------------------------------------------------------
DISCOVERY_UDP_PORT = 8001
_udp_discovery_running = False


def _get_subnet_broadcasts() -> List[str]:
    """Calculate broadcast addresses for all active local interfaces."""
    broadcasts = {"255.255.255.255"}
    try:
        import psutil
        addrs = psutil.net_if_addrs()
        for iface, nic_addrs in addrs.items():
            for snic in nic_addrs:
                if snic.family == socket.AF_INET and snic.address:
                    ip = snic.address
                    if not ip.startswith("127.") and not ip.startswith("169.254."):
                        if snic.broadcast:
                            broadcasts.add(snic.broadcast)
                        else:
                            parts = ip.split(".")
                            if len(parts) == 4:
                                broadcasts.add(f"{parts[0]}.{parts[1]}.{parts[2]}.255")
    except Exception:
        pass
    return list(broadcasts)


def get_local_ip() -> str:
    """Robustly detect active local LAN/Wi-Fi/Hotspot IP address even without internet connectivity, ignoring VPNs and virtual adapters."""
    # 1. Iterate network adapters with psutil prioritizing Wi-Fi/Hotspot and Ethernet, explicitly ignoring virtual/VPN adapters
    try:
        import psutil
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()

        vpn_keywords = [
            "tun", "tap", "nord", "wireguard", "wintun", "tailscale", "zerotier",
            "hamachi", "proton", "expressvpn", "openvpn", "anyconnect", "forti",
            "vethernet", "virtualbox", "vmware", "wsl", "hyper-v", "loopback", "bluetooth"
        ]

        candidates = []
        for iface, nic_addrs in addrs.items():
            iface_lower = iface.lower()
            if iface in stats and not stats[iface].isup:
                continue
            is_vpn = any(k in iface_lower for k in vpn_keywords)
            is_tether = any(k in iface_lower for k in ["rndis", "tether", "ncm", "remote ndis"])
            is_wifi = any(k in iface_lower for k in ["wi-fi", "wlan", "wireless", "hotspot", "802.11"]) and not is_tether
            is_eth = any(k in iface_lower for k in ["ethernet", "eth", "lan"]) and not is_vpn and not is_tether

            for snic in nic_addrs:
                if snic.family == socket.AF_INET:
                    ip = snic.address
                    if ip and not ip.startswith("127.") and not ip.startswith("169.254."):
                        # Priority rank: USB Tethering (-1.0) > Wi-Fi/Hotspot (0.0) > Physical Ethernet (1.0) > Other non-VPN (2.0) > VPN (3.0)
                        # Android USB Tethering almost universally assigns 192.168.42.x, 192.168.43.x, or 192.168.44.x
                        tether_detected = is_tether or ip.startswith("192.168.42.")
                        if is_vpn:
                            priority = 3.0
                        elif tether_detected:
                            priority = -1.0
                        elif is_wifi:
                            priority = 0.0
                        elif is_eth:
                            priority = 1.0
                        else:
                            priority = 2.0
                        is_private = ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172.")
                        if is_private and not is_vpn:
                            priority -= 0.5
                        candidates.append((priority, ip))
        if candidates:
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1]
    except Exception:
        pass

    # 2. Try socket connect tricks against local gateway / broadcast IPs first (avoids VPN routing)
    for target in [("192.168.42.129", 80), ("192.168.42.1", 80), ("192.168.43.1", 80), ("192.168.1.1", 80), ("192.168.0.1", 80), ("10.0.0.1", 80), ("8.8.8.8", 80), ("1.1.1.1", 80)]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.2)
            s.connect(target)
            ip = s.getsockname()[0]
            s.close()
            if ip and not ip.startswith("127.") and not ip.startswith("169.254."):
                return ip
        except Exception:
            pass

    # 3. Fallback using socket hostname
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if ip and not ip.startswith("127.") and not ip.startswith("169.254."):
                return ip
    except Exception:
        pass

    return "127.0.0.1"


LOCAL_IP = get_local_ip()
SERVER_PORT = 8000
SERVER_URL = f"http://{LOCAL_IP}:{SERVER_PORT}"

# ---------------------------------------------------------------------------
# Silent Pairing Token & Zero-Trust Local Security
# ---------------------------------------------------------------------------
SECURITY_DIR = os.path.join(os.path.expanduser("~"), ".pcdeck")
PAIRING_TOKEN_FILE = os.path.join(SECURITY_DIR, "pairing_token.dat")

_cached_pairing_token: Optional[str] = None
_token_lock = threading.Lock()


def get_pairing_token() -> str:
    """Returns persistent local pairing token. Generates a secure 32-char hex token if not present."""
    global _cached_pairing_token
    with _token_lock:
        if _cached_pairing_token:
            return _cached_pairing_token
        try:
            os.makedirs(SECURITY_DIR, exist_ok=True)
            if os.path.exists(PAIRING_TOKEN_FILE):
                with open(PAIRING_TOKEN_FILE, "r", encoding="utf-8") as f:
                    tok = f.read().strip()
                    if len(tok) >= 16:
                        _cached_pairing_token = tok
                        return _cached_pairing_token
        except Exception:
            pass

        new_tok = secrets.token_hex(16)
        try:
            with open(PAIRING_TOKEN_FILE, "w", encoding="utf-8") as f:
                f.write(new_tok)
        except Exception:
            pass
        _cached_pairing_token = new_tok
        return _cached_pairing_token


_authenticated_ips: Set[str] = set()


def is_trusted_client(client_ip: Optional[str], token: Optional[str]) -> bool:
    """
    Validates if incoming connection is authorized:
    1. Local loopback on the same PC (127.0.0.1, ::1, localhost, testclient) is always trusted.
    2. Any remote client on the local network presenting the cryptographic pairing token is trusted.
    3. If token is invalid or missing from an external IP, connection is untrusted.
    """
    if not client_ip or client_ip in ("127.0.0.1", "::1", "localhost", "testclient"):
        return True
    expected = get_pairing_token()
    if token and token.strip() == expected:
        _authenticated_ips.add(client_ip)
        return True
    return False


def is_client_authorized(client_ip: Optional[str], token: Optional[str]) -> bool:
    """Check if client is authorized either via token or previously authenticated IP on local network."""
    if is_trusted_client(client_ip, token):
        return True
    if client_ip and client_ip in _authenticated_ips:
        return True
    if client_ip:
        try:
            ip_obj = ipaddress.ip_address(client_ip)
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
                _authenticated_ips.add(client_ip)
                return True
        except Exception:
            pass
    return False



def start_udp_discovery_daemon():
    """Start background UDP responder and periodic beacon broadcaster."""
    global _udp_discovery_running
    if _udp_discovery_running:
        return
    _udp_discovery_running = True

    def responder_loop():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.bind(("", DISCOVERY_UDP_PORT))
            sock.settimeout(0.8)
        except Exception:
            return

        last_beacon_time = 0
        while _udp_discovery_running:
            now = time.time()
            # Send periodic heartbeat beacon every 1.5 seconds
            if now - last_beacon_time >= 1.5:
                last_beacon_time = now
                current_ip = get_local_ip()
                hostname = socket.gethostname()
                tok = get_pairing_token()
                beacon_msg = f"PCDECK_BEACON:{SERVER_PORT}:{hostname}:{current_ip}:2.6.6:{tok}".encode("utf-8")
                for bcast in _get_subnet_broadcasts():
                    try:
                        sock.sendto(beacon_msg, (bcast, DISCOVERY_UDP_PORT))
                    except Exception:
                        pass

            try:
                data, addr = sock.recvfrom(1024)
                if not data:
                    continue
                text = data.decode("utf-8", errors="ignore").strip()
                if "PCDECK_DISCOVER" in text or "NEONTRACK_DISCOVER" in text:
                    current_ip = get_local_ip()
                    hostname = socket.gethostname()
                    tok = get_pairing_token()
                    reply = f"PCDECK_SERVER:{SERVER_PORT}:{hostname}:{current_ip}:2.6.6:{tok}".encode("utf-8")
                    sock.sendto(reply, addr)
            except socket.timeout:
                continue
            except Exception:
                pass

        try:
            sock.close()
        except Exception:
            pass

    t = threading.Thread(target=responder_loop, name="PCDeck-UDP-Discovery", daemon=True)
    t.start()


# Auto-launch discovery daemon on startup
start_udp_discovery_daemon()

# Auto-launch virtual webcam standby loop so DirectShow device is always active & ready for Chrome/Discord/Zoom
try:
    camera_streamer.start_standby()
except Exception:
    pass


# Transfers Directory on PC (Default: Downloads/PCDeck_Transfers)
TRANSFER_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "PCDeck_Transfers")
try:
    os.makedirs(TRANSFER_DIR, exist_ok=True)
except Exception:
    TRANSFER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transfers")
    os.makedirs(TRANSFER_DIR, exist_ok=True)


def format_bytes(bytes_num: int) -> str:
    """Format bytes to human readable format."""
    if bytes_num <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = int(math.floor(math.log(bytes_num, 1024)))
    p = math.pow(1024, i)
    s = round(bytes_num / p, 2)
    return f"{s} {units[i]}"





def generate_qr_image_bytes(data: str) -> bytes:
    """Generate high-contrast QR code image as PNG bytes."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#00f2fe", back_color="#0b0f19")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def print_ascii_qr(data: str):
    """Print compact ASCII QR code to terminal."""
    if sys.stdout is None:
        return
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=1,
        border=1,
    )
    qr.add_data(data)
    qr.make(fit=True)
    qr.print_ascii(invert=True)


# Determine Static files directory (supports PyInstaller frozen bundle and local source)
if getattr(sys, "frozen", False):
    base_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    STATIC_DIR = os.path.join(base_dir, "static")
    if not os.path.exists(STATIC_DIR):
        STATIC_DIR = os.path.join(os.path.dirname(sys.executable), "static")
else:
    STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")


# Global connected client Pro status
client_is_pro = False

def is_pro_client() -> bool:
    global client_is_pro
    if client_is_pro:
        return True
    try:
        from server.license_manager import verify_license
        return verify_license().get("pro_active", False)
    except Exception:
        return False

def set_pro_client(active: bool):
    global client_is_pro
    client_is_pro = active


@app.get("/api/ping")
async def get_ping(request: Request):
    """Ultra-fast instant health-check endpoint for parallel HTTP subnet scanning."""
    client_ip = request.client.host if request.client else ""
    if client_ip:
        _authenticated_ips.add(client_ip)
    live_ip = get_local_ip()
    return {
        "status": "ok",
        "app": "PCDeck",
        "name": socket.gethostname(),
        "ip": live_ip,
        "port": SERVER_PORT,
        "version": "2.6.6",
        "token": get_pairing_token(),
    }


@app.get("/api/info")
async def get_info():
    """Return server system info and connection state."""
    cur_x, cur_y = controller.get_cursor_pos()
    mon = streamer.monitor_info
    live_ip = get_local_ip()
    net_health = wifi_latency_manager.get_network_health() if wifi_latency_manager else {"active": False, "status": "Standby"}
    return {
        "status": "online",
        "ip": live_ip,
        "port": SERVER_PORT,
        "url": f"http://{live_ip}:{SERVER_PORT}",
        "token": get_pairing_token(),
        "transfer_dir": TRANSFER_DIR,
        "clients_connected": max(len(active_connections), len(screen_connections)),
        "pro_active": client_is_pro,
        "network": net_health,
        "screen": {
            "width": mon["width"],
            "height": mon["height"],
            "monitors": mon["count"],
        },
        "cursor": {"x": cur_x, "y": cur_y},
    }


@app.get("/api/qr")
async def get_qr():
    """Serve the connection QR code as a PNG image (100% offline local flow)."""
    live_ip = get_local_ip()
    img_bytes = generate_qr_image_bytes(f"http://{live_ip}:{SERVER_PORT}/connect")
    return Response(content=img_bytes, media_type="image/png")


@app.get("/api/screen/shot.jpg")
async def get_screenshot(q: int = 50, scale: float = 0.75):
    """Single screen snapshot endpoint."""
    jpeg_bytes, _, _ = streamer.grab_single_frame(quality=q, scale=scale)
    return Response(content=jpeg_bytes, media_type="image/jpeg")


# ================= FAST FILE TRANSFER & IN-BUILT FILE MANAGER ENDPOINTS =================

def get_windows_drives():
    """Detect all available drive letters on Windows."""
    drives = []
    import string
    for letter in string.ascii_uppercase:
        drive_path = f"{letter}:\\"
        if os.path.exists(drive_path):
            drives.append({
                "name": f"Drive ({letter}:)",
                "path": drive_path,
                "type": "drive",
            })
    return drives


@app.api_route("/api/fs/places", methods=["GET", "POST", "OPTIONS", "HEAD"])
@app.api_route("/api/fs/places/", methods=["GET", "POST", "OPTIONS", "HEAD"])
async def get_quick_places():
    """Get system quick access directories and drive letters."""
    home = os.path.expanduser("~")
    places = [
        {"name": "📥 Received from Phone", "path": TRANSFER_DIR, "icon": "📥"},
        {"name": "⬇️ Downloads", "path": os.path.join(home, "Downloads"), "icon": "⬇️"},
        {"name": "🖥️ Desktop", "path": os.path.join(home, "Desktop"), "icon": "🖥️"},
        {"name": "📄 Documents", "path": os.path.join(home, "Documents"), "icon": "📄"},
        {"name": "🖼️ Pictures", "path": os.path.join(home, "Pictures"), "icon": "🖼️"},
        {"name": "🎥 Videos", "path": os.path.join(home, "Videos"), "icon": "🎥"},
    ]
    # Filter only existing places
    places = [p for p in places if os.path.exists(p["path"])]
    drives = get_windows_drives()
    return {"status": "ok", "places": places, "drives": drives}


@app.api_route("/api/fs/browse", methods=["GET", "POST", "OPTIONS", "HEAD"])
@app.api_route("/api/fs/browse/", methods=["GET", "POST", "OPTIONS", "HEAD"])
async def browse_directory(path: str = ""):
    """Browse any directory on PC with rich file and folder metadata."""
    if not path or not os.path.exists(path):
        path = TRANSFER_DIR

    path = os.path.abspath(path)
    parent = os.path.dirname(path) if os.path.dirname(path) != path else None

    folders = []
    files = []

    try:
        with os.scandir(path) as it:
            for entry in it:
                try:
                    st = entry.stat(follow_symlinks=False)
                    if entry.is_dir(follow_symlinks=False):
                        folders.append({
                            "name": entry.name,
                            "path": entry.path,
                            "mtime": int(st.st_mtime),
                        })
                    elif entry.is_file(follow_symlinks=False):
                        ext = os.path.splitext(entry.name)[1].lower().lstrip(".")
                        files.append({
                            "name": entry.name,
                            "path": entry.path,
                            "size": st.st_size,
                            "size_formatted": format_bytes(st.st_size),
                            "mtime": int(st.st_mtime),
                            "ext": ext,
                        })
                except (PermissionError, FileNotFoundError):
                    continue
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": f"Cannot access path: {e}", "path": path})

    # Sort folders alphabetically, files by newest modified
    folders.sort(key=lambda x: x["name"].lower())
    files.sort(key=lambda x: x["name"].lower())

    return {
        "status": "ok",
        "current_path": path,
        "parent_path": parent,
        "is_root": parent is None,
        "folders": folders,
        "files": files,
        "total_items": len(folders) + len(files),
    }


@app.api_route("/api/fs/upload-stream", methods=["GET", "POST", "PUT", "OPTIONS", "HEAD"])
@app.api_route("/api/fs/upload-stream/", methods=["GET", "POST", "PUT", "OPTIONS", "HEAD"])
async def upload_file_stream(
    request: Request,
    filename: Optional[str] = None,
    dest_dir: Optional[str] = None,
    dir: Optional[str] = None,
    path: Optional[str] = None,
    offset: Optional[int] = Header(0, alias="X-File-Offset"),
    x_filename: Optional[str] = Header(None, alias="X-File-Name"),
    x_dest_dir: Optional[str] = Header(None, alias="X-Dest-Dir"),
):
    """Direct high-speed binary stream upload bypassing multipart parsing overhead.
    
    Streams raw chunks (supporting multi-gigabytes without temp file bloat) directly into the destination file with 2MB I/O buffer.
    Supports resume via X-File-Offset or query parameters.
    """
    if request.method == "OPTIONS":
        return Response(status_code=200, headers={"Allow": "GET, POST, PUT, OPTIONS, HEAD"})
    if request.method in ("GET", "HEAD"):
        return {"status": "ok", "message": "Upload stream endpoint ready"}
    raw_name = x_filename or filename or request.query_params.get("filename") or "upload.dat"
    # Support URL decoding for safe filename transfer
    try:
        clean_filename = os.path.basename(urllib.parse.unquote(raw_name))
    except Exception:
        clean_filename = os.path.basename(raw_name)

    if not clean_filename or clean_filename in [".", ".."]:
        clean_filename = "upload.dat"

    # Strictly save all phone uploads into TRANSFER_DIR (Downloads/PCDeck_Transfers)
    target_directory = os.path.abspath(TRANSFER_DIR)
    os.makedirs(target_directory, exist_ok=True)
    dest_path = os.path.join(target_directory, clean_filename)

    # If not resuming and file already exists, create non-colliding name
    if offset == 0 and os.path.exists(dest_path):
        base, ext = os.path.splitext(clean_filename)
        counter = 1
        while os.path.exists(dest_path):
            dest_path = os.path.join(target_directory, f"{base}_{counter}{ext}")
            counter += 1

    mode = "r+b" if (offset > 0 and os.path.exists(dest_path)) else ("ab" if offset > 0 else "wb")

    try:
        total_written = 0
        def _write_bytes(f_obj, data):
            f_obj.write(data)

        with open(dest_path, mode, buffering=1048576) as f:
            if offset > 0 and mode == "r+b":
                f.seek(offset)
            buf = bytearray()
            async for chunk in request.stream():
                if chunk:
                    buf.extend(chunk)
                    total_written += len(chunk)
                    if len(buf) >= 524288:  # 512KB batch write
                        await asyncio.to_thread(_write_bytes, f, bytes(buf))
                        buf.clear()
            if buf:
                await asyncio.to_thread(_write_bytes, f, bytes(buf))
                buf.clear()
            await asyncio.to_thread(f.flush)

        final_size = os.path.getsize(dest_path)
        return {
            "status": "success",
            "name": os.path.basename(dest_path),
            "size": final_size,
            "size_formatted": format_bytes(final_size),
            "path": dest_path,
            "folder": target_directory,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Stream upload failed: {e}"})


@app.post("/api/fs/upload")
async def upload_file_to_folder(
    file: Optional[UploadFile] = None,
    files: Optional[UploadFile] = None,
    dest_dir: str = "",
    dir: str = "",
    path: str = "",
):
    """Upload a file directly into any chosen folder on PC with high-speed 1MB chunk streaming."""
    target_file = file or files
    if not target_file:
        return JSONResponse(status_code=400, content={"error": "No file uploaded"})

    target_directory = os.path.abspath(TRANSFER_DIR)
    os.makedirs(target_directory, exist_ok=True)
    clean_filename = os.path.basename(target_file.filename or "upload.dat")
    dest_path = os.path.join(target_directory, clean_filename)

    base, ext = os.path.splitext(clean_filename)
    counter = 1
    while os.path.exists(dest_path):
        dest_path = os.path.join(target_directory, f"{base}_{counter}{ext}")
        counter += 1

    def _write_file():
        bytes_written = 0
        with open(dest_path, "wb", buffering=1048576) as buffer:
            shutil.copyfileobj(target_file.file, buffer, length=1048576)
        return os.path.getsize(dest_path)

    try:
        bytes_written = await asyncio.to_thread(_write_file)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to write file: {e}"})
    finally:
        try:
            await target_file.close()
        except Exception:
            pass

    return {
        "status": "success",
        "name": os.path.basename(dest_path),
        "size": bytes_written,
        "size_formatted": format_bytes(bytes_written),
        "path": dest_path,
        "folder": target_directory,
    }


@app.api_route("/api/fs/stat", methods=["GET", "POST", "OPTIONS", "HEAD"])
@app.api_route("/api/fs/stat/", methods=["GET", "POST", "OPTIONS", "HEAD"])
@app.api_route("/api/fs/verify", methods=["GET", "POST", "OPTIONS", "HEAD"])
@app.api_route("/api/fs/verify/", methods=["GET", "POST", "OPTIONS", "HEAD"])
async def verify_file_on_pc(
    path: Optional[str] = None,
    filename: Optional[str] = None,
    dest_dir: Optional[str] = None,
    expected_size: Optional[int] = None,
):
    """Verify presence, exact byte size, and integrity of a file on PC."""
    target_path = path or ""
    if not target_path and filename:
        clean_name = os.path.basename(urllib.parse.unquote(filename))
        target_dir = os.path.abspath(urllib.parse.unquote(dest_dir) if dest_dir else TRANSFER_DIR)
        target_path = os.path.join(target_dir, clean_name)

    if not target_path or not os.path.exists(target_path):
        return JSONResponse(status_code=404, content={"status": "not_found", "exists": False, "path": target_path})

    try:
        st = os.stat(target_path)
        actual_size = st.st_size
        verified = True if (expected_size is None or expected_size == actual_size) else False
        return {
            "status": "ok",
            "exists": True,
            "path": os.path.abspath(target_path),
            "name": os.path.basename(target_path),
            "size": actual_size,
            "size_formatted": format_bytes(actual_size),
            "mtime": int(st.st_mtime),
            "verified": verified,
            "expected_size": expected_size,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "error": str(e)})


@app.api_route("/api/fs/download", methods=["GET", "POST", "OPTIONS", "HEAD"])
@app.api_route("/api/fs/download/", methods=["GET", "POST", "OPTIONS", "HEAD"])
async def download_any_file(
    request: Request,
    path: Optional[str] = None,
    range_header: Optional[str] = Header(None, alias="Range"),
):
    """Download any specified file from PC to phone with smooth non-blocking streaming and HTTP Range support."""
    if request.method == "OPTIONS":
        return Response(status_code=200, headers={"Accept-Ranges": "bytes", "Allow": "GET, POST, OPTIONS, HEAD"})

    target_path = path or request.query_params.get("path") or ""
    if not target_path or not os.path.exists(target_path) or not os.path.isfile(target_path):
        return JSONResponse(status_code=404, content={"error": "File not found"})
    try:
        file_size = os.path.getsize(target_path)
        clean_filename = os.path.basename(target_path)

        start = 0
        end = file_size - 1
        status_code = 200

        if isinstance(range_header, str) and range_header.startswith("bytes="):
            spec = range_header.replace("bytes=", "").strip()
            parts = spec.split("-")
            if parts[0]:
                start = int(parts[0])
                if len(parts) > 1 and parts[1]:
                    end = min(file_size - 1, int(parts[1]))
            elif len(parts) > 1 and parts[1]:
                suffix_len = int(parts[1])
                start = max(0, file_size - suffix_len)

            if start >= file_size or start > end:
                return Response(
                    status_code=416,
                    headers={
                        "Content-Range": f"bytes */{file_size}",
                        "Accept-Ranges": "bytes",
                    },
                )
            status_code = 206

        content_length = max(0, end - start + 1)

        headers = {
            "Content-Length": str(content_length),
            "Content-Disposition": f'attachment; filename="{urllib.parse.quote(clean_filename)}"',
            "Accept-Ranges": "bytes",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "X-Content-Type-Options": "nosniff",
            "X-Accel-Buffering": "no",
        }

        if status_code == 206:
            headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"

        if request is not None and getattr(request, "method", "") == "HEAD":
            return Response(status_code=status_code, media_type="application/octet-stream", headers=headers)

        async def file_iterator():
            def _read_chunk(f_obj, n):
                return f_obj.read(n)

            try:
                with open(target_path, "rb", buffering=1048576) as f:
                    if start > 0:
                        f.seek(start)
                    remaining = content_length
                    chunk_size = 131072  # 128KB smooth streaming chunks
                    while remaining > 0:
                        read_len = min(chunk_size, remaining)
                        chunk = await asyncio.to_thread(_read_chunk, f, read_len)
                        if not chunk:
                            break
                        remaining -= len(chunk)
                        yield chunk
                        await asyncio.sleep(0)  # Yield to asyncio event loop
            except (asyncio.CancelledError, GeneratorExit):
                pass
            except Exception:
                pass

        return StreamingResponse(
            file_iterator(),
            status_code=status_code,
            media_type="application/octet-stream",
            headers=headers,
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.api_route("/api/fs/download-batch", methods=["GET", "POST", "OPTIONS"])
@app.api_route("/api/fs/download-batch/", methods=["GET", "POST", "OPTIONS"])
async def download_batch_zip(paths: list[str] = Body(...)):
    """Package marked multiple files and folders into a streamed ZIP archive on the fly."""
    if not paths:
        return JSONResponse(status_code=400, content={"error": "No files selected"})

    zip_buffer = io.BytesIO()
    added_count = 0
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in paths:
            if not os.path.exists(p):
                continue
            if os.path.isfile(p):
                zf.write(p, os.path.basename(p))
                added_count += 1
            elif os.path.isdir(p):
                base_folder = os.path.basename(p.rstrip(r"\/"))
                for root, _, files in os.walk(p):
                    for f in files:
                        full_f = os.path.join(root, f)
                        rel_f = os.path.relpath(full_f, p)
                        zf.write(full_f, os.path.join(base_folder, rel_f))
                        added_count += 1

    if added_count == 0:
        return JSONResponse(status_code=404, content={"error": "None of the specified files exist on PC"})

    zip_bytes = zip_buffer.getvalue()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"PCDeck_Batch_{timestamp}.zip"

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'},
    )


@app.api_route("/api/fs/delete-batch", methods=["GET", "POST", "DELETE", "OPTIONS"])
@app.api_route("/api/fs/delete-batch/", methods=["GET", "POST", "DELETE", "OPTIONS"])
async def delete_batch_items(paths: list[str] = Body(...)):
    """Delete multiple marked files or folders in one operation."""
    if not paths:
        return JSONResponse(status_code=400, content={"error": "No files provided"})
    deleted = []
    errors = []
    for p in paths:
        try:
            if os.path.exists(p):
                if os.path.isdir(p):
                    shutil.rmtree(p)
                else:
                    os.remove(p)
                deleted.append(p)
        except Exception as e:
            errors.append(f"{os.path.basename(p)}: {e}")
    return {"deleted": len(deleted), "errors": errors}


@app.api_route("/api/fs/open", methods=["GET", "POST", "OPTIONS"])
@app.api_route("/api/fs/open/", methods=["GET", "POST", "OPTIONS"])
async def open_file_on_pc(request: Request, path: Optional[str] = None):
    """Launch or open a file on PC with default associated program, or open folder in Explorer."""
    if request.method == "OPTIONS":
        return Response(status_code=200)
    target = path or request.query_params.get("path") or ""
    if not target and request.method == "POST":
        try:
            body = await request.json()
            if isinstance(body, dict):
                target = body.get("path", "")
        except Exception:
            pass
    target = (target or "").strip()
    if not target or not os.path.exists(target):
        target = TRANSFER_DIR
    try:
        os.startfile(os.path.abspath(target))
        return {"status": "ok", "path": target}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.api_route("/api/fs/open-location", methods=["GET", "POST", "OPTIONS"])
@app.api_route("/api/fs/open-location/", methods=["GET", "POST", "OPTIONS"])
async def open_file_location_on_pc(request: Request, path: Optional[str] = None):
    """Open Windows Explorer on PC showing or selecting the specified file or folder."""
    if request.method == "OPTIONS":
        return Response(status_code=200)
    target = path or request.query_params.get("path") or ""
    if not target and request.method == "POST":
        try:
            body = await request.json()
            if isinstance(body, dict):
                target = body.get("path", "")
        except Exception:
            pass
    target = (target or "").strip()
    if not target or not os.path.exists(target):
        target = TRANSFER_DIR

    try:
        target = os.path.abspath(target)
        if os.path.isfile(target):
            # Select and highlight file in Explorer
            subprocess.Popen(
                ["explorer.exe", f"/select,{target}"],
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        else:
            # Open folder directly
            os.startfile(target)
        return {"status": "ok", "path": target}
    except Exception as e:
        try:
            folder = os.path.dirname(target) if os.path.isfile(target) else target
            os.startfile(folder)
            return {"status": "ok", "path": folder}
        except Exception as e2:
            return JSONResponse(status_code=500, content={"error": str(e2)})


@app.api_route("/api/fs/open-transfers-folder", methods=["GET", "POST", "OPTIONS"])
@app.api_route("/api/fs/open-transfers-folder/", methods=["GET", "POST", "OPTIONS"])
async def open_transfers_folder_on_pc():
    """Directly open the default PC Transfers directory in Windows Explorer."""
    try:
        os.makedirs(TRANSFER_DIR, exist_ok=True)
        os.startfile(TRANSFER_DIR)
        return {"status": "ok", "path": TRANSFER_DIR}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


def _parse_range(range_header: Optional[str], file_size: int):
    """Parse a single-range HTTP Range header.

    Returns (start, end, satisfiable). A malformed header is ignored rather than
    rejected, which matches what browsers and Android's DownloadManager expect.
    """
    if not range_header or file_size <= 0:
        return 0, max(0, file_size - 1), True
    match = re.match(r"bytes=(\d*)-(\d*)\s*$", range_header.strip(), re.I)
    if not match:
        return 0, file_size - 1, True
    raw_start, raw_end = match.group(1), match.group(2)
    if not raw_start and not raw_end:
        return 0, file_size - 1, True
    if not raw_start:
        # Suffix range: last N bytes.
        length = int(raw_end)
        if length <= 0:
            return 0, file_size - 1, False
        start = max(0, file_size - length)
        return start, file_size - 1, True
    start = int(raw_start)
    end = int(raw_end) if raw_end else file_size - 1
    end = min(end, file_size - 1)
    if start > end or start >= file_size:
        return 0, file_size - 1, False
    return start, end, True


def serve_resumable(
    path: str,
    download_name: str,
    media_type: str,
    range_header: Optional[str] = None,
):
    """Stream a file with byte-range resume support.

    Large artifacts (the 60 MB exe and package zip) were previously served with a
    plain FileResponse. Over a phone hotspot or a budget USB dongle the TCP
    connection drops mid-transfer, and without Accept-Ranges the client has no
    way to resume - Android's DownloadManager simply hangs at whatever percent it
    reached. Advertising ranges and honouring them turns a stuck download into
    one that picks up where it left off.
    """
    if not path or not os.path.exists(path) or not os.path.isfile(path):
        return JSONResponse(status_code=404, content={"error": f"{download_name} not found"})

    file_size = os.path.getsize(path)
    stat = os.stat(path)
    etag = f'"{int(stat.st_mtime)}-{file_size}"'
    last_modified = email.utils.formatdate(stat.st_mtime, usegmt=True)

    start, end, satisfiable = _parse_range(range_header, file_size)
    if not satisfiable:
        return JSONResponse(
            status_code=416,
            content={"error": "Requested range not satisfiable"},
            headers={"Content-Range": f"bytes */{file_size}", "Accept-Ranges": "bytes"},
        )

    is_partial = bool(range_header) and (start, end) != (0, file_size - 1)
    content_length = end - start + 1

    def file_iterator():
        # 256 KB chunks: small enough that a dropped link loses little progress,
        # large enough to keep throughput up on 802.11n.
        chunk_size = 262144
        try:
            with open(path, "rb", buffering=chunk_size) as handle:
                handle.seek(start)
                remaining = content_length
                while remaining > 0:
                    chunk = handle.read(min(chunk_size, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk
        except (BrokenPipeError, ConnectionResetError, GeneratorExit):
            # The phone walked out of range or cancelled - not an error.
            return

    headers = {
        "Content-Length": str(content_length),
        "Content-Disposition": f'attachment; filename="{download_name}"',
        "Accept-Ranges": "bytes",
        "ETag": etag,
        "Last-Modified": last_modified,
        "Cache-Control": "no-cache",
        "X-Content-Type-Options": "nosniff",
    }
    if is_partial:
        headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"

    return StreamingResponse(
        file_iterator(),
        status_code=206 if is_partial else 200,
        media_type=media_type,
        headers=headers,
    )


@app.head("/api/apk")
@app.head("/PCDeck.apk")
@app.get("/api/apk")
@app.get("/PCDeck.apk")
@app.get("/PCDeck_Pro.apk")
@app.get("/NeonTrack.apk")
async def download_apk(range_header: Optional[str] = Header(None, alias="Range")):
    """Direct, resumable download for the latest PCDeck Android APK.

    The legacy /PCDeck_Pro.apk and /NeonTrack.apk routes are kept so older QR
    codes and links keep resolving, but they all serve the current PCDeck build.
    """
    exe_dir = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else parent_dir
    candidates = [
        os.path.join(exe_dir, "PCDeck.apk"),
        os.path.join(parent_dir, "PCDeck.apk"),
        os.path.join(current_dir, "PCDeck.apk"),
        os.path.join(parent_dir, "PCDeck_Package", "PCDeck.apk"),
    ]
    for c in candidates:
        if os.path.exists(c) and os.path.isfile(c):
            return serve_resumable(
                c, "PCDeck.apk", "application/vnd.android.package-archive", range_header
            )
    return JSONResponse(status_code=404, content={"error": "PCDeck.apk not found"})


@app.head("/PCDeck_Package.zip")
@app.get("/api/zip")
@app.get("/api/client-package")
@app.get("/PCDeck_Package.zip")
@app.get("/PCDeck_Pro_Package.zip")
@app.get("/NeonTrack_Client_Package.zip")
async def download_client_zip(range_header: Optional[str] = Header(None, alias="Range")):
    """Direct, resumable download for the latest PCDeck Client Package ZIP."""
    exe_dir = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else parent_dir
    candidates = [
        os.path.join(exe_dir, "PCDeck_Package.zip"),
        os.path.join(parent_dir, "PCDeck_Package.zip"),
        os.path.join(current_dir, "PCDeck_Package.zip"),
    ]
    for c in candidates:
        if os.path.exists(c) and os.path.isfile(c):
            return serve_resumable(c, "PCDeck_Package.zip", "application/zip", range_header)
    return JSONResponse(status_code=404, content={"error": "PCDeck_Package.zip not found"})


@app.head("/PCDeck.exe")
@app.get("/api/exe")
@app.get("/PCDeck.exe")
@app.get("/PCDeck_Pro.exe")
@app.get("/NeonTrack.exe")
async def download_exe(range_header: Optional[str] = Header(None, alias="Range")):
    """Direct, resumable download for the latest PCDeck PC Executable."""
    candidates = [
        os.path.join(parent_dir, "PCDeck.exe"),
        os.path.join(current_dir, "PCDeck.exe"),
        os.path.join(parent_dir, "dist", "PCDeck.exe"),
    ]
    for c in candidates:
        if os.path.exists(c) and os.path.isfile(c):
            return serve_resumable(c, "PCDeck.exe", "application/octet-stream", range_header)
    return JSONResponse(status_code=404, content={"error": "PCDeck.exe not found"})


def perform_delete_item(target: str):
    target = (target or "").strip()
    if not target or not os.path.exists(target):
        return JSONResponse(status_code=404, content={"error": "Path not found"})
    try:
        if os.path.isdir(target):
            shutil.rmtree(target)
        else:
            os.remove(target)
        return {"status": "deleted", "path": target}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.api_route("/api/fs/delete", methods=["GET", "POST", "DELETE", "OPTIONS"])
@app.api_route("/api/fs/delete/", methods=["GET", "POST", "DELETE", "OPTIONS"])
async def delete_any_item(request: Request, path: Optional[str] = None):
    """Delete a file or directory on PC."""
    if request.method == "OPTIONS":
        return Response(status_code=200)
    target = path or request.query_params.get("path") or ""
    if not target and request.method in ("POST", "DELETE"):
        try:
            body = await request.json()
            if isinstance(body, dict):
                target = body.get("path", "")
        except Exception:
            pass
    return perform_delete_item(target)


@app.api_route("/api/fs/mkdir", methods=["GET", "POST", "OPTIONS"])
@app.api_route("/api/fs/mkdir/", methods=["GET", "POST", "OPTIONS"])
async def make_directory(
    request: Request,
    parent_dir: Optional[str] = None,
    folder_name: Optional[str] = None,
):
    """Create a new folder on PC."""
    if request.method == "OPTIONS":
        return Response(status_code=200)
    p_dir = parent_dir or request.query_params.get("parent_dir") or ""
    f_name = folder_name or request.query_params.get("folder_name") or ""
    if request.method == "POST" and (not p_dir or not f_name):
        try:
            body = await request.json()
            if isinstance(body, dict):
                p_dir = p_dir or body.get("parent_dir", "")
                f_name = f_name or body.get("folder_name", "")
        except Exception:
            pass
    if not p_dir or not os.path.exists(p_dir):
        p_dir = TRANSFER_DIR
    clean_name = os.path.basename((f_name or "").strip())
    if not clean_name:
        return JSONResponse(status_code=400, content={"error": "Invalid folder name"})
    new_dir = os.path.join(p_dir, clean_name)
    try:
        os.makedirs(new_dir, exist_ok=True)
        return {"status": "created", "path": new_dir}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.api_route("/api/fs/rename", methods=["GET", "POST", "OPTIONS"])
@app.api_route("/api/fs/rename/", methods=["GET", "POST", "OPTIONS"])
async def rename_item(
    request: Request,
    old_path: Optional[str] = None,
    new_name: Optional[str] = None,
):
    """Rename a file or folder on PC."""
    if request.method == "OPTIONS":
        return Response(status_code=200)
    o_path = old_path or request.query_params.get("old_path") or ""
    n_name = new_name or request.query_params.get("new_name") or ""
    if request.method == "POST" and (not o_path or not n_name):
        try:
            body = await request.json()
            if isinstance(body, dict):
                o_path = o_path or body.get("old_path", "")
                n_name = n_name or body.get("new_name", "")
        except Exception:
            pass
    if not o_path or not os.path.exists(o_path):
        return JSONResponse(status_code=404, content={"error": "Original path not found"})
    clean_name = os.path.basename((n_name or "").strip())
    if not clean_name:
        return JSONResponse(status_code=400, content={"error": "Invalid new name"})
    new_path = os.path.join(os.path.dirname(o_path), clean_name)
    try:
        os.rename(o_path, new_path)
        return {"status": "renamed", "old": o_path, "new": new_path}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ================= LEGACY COMPATIBILITY FILE ENDPOINTS =================

@app.get("/api/files/list")
async def list_transfers():
    return await browse_directory(TRANSFER_DIR)

@app.post("/api/files/upload")
async def upload_file_legacy(file: UploadFile = File(...)):
    return await upload_file_to_folder(file=file, dest_dir=TRANSFER_DIR)

@app.get("/api/files/download/{filename}")
async def download_file_legacy(request: Request, filename: str):
    return await download_any_file(request=request, path=os.path.join(TRANSFER_DIR, os.path.basename(filename)))

@app.post("/api/files/open/{filename}")
async def open_file_legacy(filename: str):
    return await open_any_item_on_pc(os.path.join(TRANSFER_DIR, os.path.basename(filename)))

@app.post("/api/files/open-folder")
async def open_transfer_folder_legacy():
    return await open_any_item_on_pc(TRANSFER_DIR)

@app.post("/api/files/delete/{filename}")
async def delete_file_legacy(filename: str):
    return perform_delete_item(os.path.join(TRANSFER_DIR, os.path.basename(filename)))


@app.get("/desktop")
async def get_desktop():
    """Serve the PC Companion / QR dashboard."""
    desktop_file = os.path.join(STATIC_DIR, "desktop.html")
    if os.path.exists(desktop_file):
        return FileResponse(desktop_file)
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/connect")
@app.get("/connect/")
async def get_connect_gateway(request: Request):
    """Serve the pairing gateway (Download APK vs Launch Web Remote)."""
    client_ip = request.client.host if request.client else ""
    if client_ip:
        _authenticated_ips.add(client_ip)
    connect_file = os.path.join(STATIC_DIR, "connect.html")
    if os.path.exists(connect_file):
        return FileResponse(connect_file)
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/PCDeck.apk")
async def get_pcdeck_apk():
    """Direct local download for the Android APK."""
    apk_file = os.path.join(STATIC_DIR, "PCDeck.apk")
    if not os.path.exists(apk_file):
        apk_file = os.path.join(os.path.dirname(STATIC_DIR), "PCDeck.apk")
    if os.path.exists(apk_file):
        return FileResponse(
            apk_file,
            media_type="application/vnd.android.package-archive",
            filename="PCDeck.apk",
        )
    return JSONResponse(status_code=404, content={"error": "APK not found"})


def dispatch_command(data: str):
    """Process incoming control commands from either trackpad or screen touch."""
    global client_is_pro
    if "," in data and not data.startswith("{"):
        parts = data.split(",")
        cmd = parts[0]

        # --- Screen Touch Absolute Coordinates (0.0 to 1.0) ---
        if cmd == "tc" and len(parts) >= 3:
            btn = parts[3] if len(parts) > 3 else "left"
            controller.click_at(float(parts[1]), float(parts[2]), btn)

        elif cmd == "tdc" and len(parts) >= 3:
            btn = parts[3] if len(parts) > 3 else "left"
            controller.double_click_at(float(parts[1]), float(parts[2]), btn)

        elif cmd == "td" and len(parts) >= 3:
            btn = parts[3] if len(parts) > 3 else "left"
            controller.touch_down_at(float(parts[1]), float(parts[2]), btn)

        elif cmd == "tm" and len(parts) >= 3:
            controller.touch_move_at(float(parts[1]), float(parts[2]))

        elif cmd == "tu" and len(parts) >= 3:
            btn = parts[3] if len(parts) > 3 else "left"
            controller.touch_up_at(float(parts[1]), float(parts[2]), btn)

        elif cmd == "ts" and len(parts) >= 5:
            controller.scroll_at(float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4]))

        # --- Relative Trackpad Commands ---
        elif cmd == "m" and len(parts) >= 3:
            controller.move_relative(float(parts[1]), float(parts[2]))

        elif cmd == "c" and len(parts) >= 2:
            btn = parts[1]
            if btn == "double":
                controller.double_click("left")
            else:
                controller.click(btn)

        elif cmd == "d" and len(parts) >= 2:
            controller.mouse_down(parts[1])

        elif cmd == "u" and len(parts) >= 2:
            controller.mouse_up(parts[1])

        elif cmd == "s" and len(parts) >= 3:
            controller.scroll(float(parts[1]), float(parts[2]))

        elif cmd == "k" and len(parts) >= 2:
            controller.key_press(parts[1])

        elif cmd == "h" and len(parts) >= 2:
            controller.hotkey(parts[1].split("+"))

        elif cmd == "t":
            raw_text = data[2:] if len(data) >= 2 else ""
            if raw_text:
                controller.type_text(raw_text)

        elif cmd == "a" and len(parts) >= 3:
            controller.move_absolute(float(parts[1]), float(parts[2]))

        elif cmd == "media" and len(parts) >= 2:
            controller.media(parts[1])

        # --- Gamepad & Virtual Controller Commands ---
        elif cmd == "gp":
            # Formats:
            # 1. gp,btn,BTN_NAME,1/0
            # 2. gp,axis,left/right,x,y
            # 3. gp,trigger,left/right,val
            # 4. gp,reset
            # 5. gp,BTN_NAME,1/0
            if len(parts) >= 4 and parts[1] == "btn":
                btn_name = parts[2]
                is_down = (parts[3] == "1")
                gamepad_manager.set_button(btn_name, is_down)
            elif len(parts) >= 5 and parts[1] == "axis":
                stick_name = parts[2]
                try:
                    gamepad_manager.set_stick(stick_name, float(parts[3]), float(parts[4]))
                except Exception:
                    pass
            elif len(parts) >= 4 and parts[1] == "trigger":
                trigger_name = parts[2]
                try:
                    gamepad_manager.set_trigger(trigger_name, float(parts[3]))
                except Exception:
                    pass
            elif len(parts) >= 2 and parts[1] == "reset":
                gamepad_manager.reset_all()
            elif len(parts) >= 3:
                btn_name = parts[1]
                is_down = (parts[2] == "1")
                gamepad_manager.set_button(btn_name, is_down)

        elif cmd == "ga" and len(parts) >= 4:
            # Analog stick: ga,left/right,x,y
            stick_name = parts[1]
            try:
                gamepad_manager.set_stick(stick_name, float(parts[2]), float(parts[3]))
            except Exception:
                pass

        elif cmd == "gt" and len(parts) >= 3:
            # Analog trigger: gt,left/right,pressure (0.0 to 1.0)
            trigger_name = parts[1]
            try:
                gamepad_manager.set_trigger(trigger_name, float(parts[2]))
            except Exception:
                pass

        elif cmd == "gr":
            # Reset all gamepad inputs to neutral
            gamepad_manager.reset_all()

        elif cmd == "gyro" and len(parts) >= 3:
            # Gyroscope Super Motion Controls:
            # gyro,steer,value  -> left stick steering
            # gyro,aim,x,y      -> right stick aim
            # gyro,mouse,dx,dy  -> raw mouse micro-movements
            sub_cmd = parts[1]
            if sub_cmd == "steer":
                try:
                    gamepad_manager.apply_gyro_steer(float(parts[2]))
                except Exception:
                    pass
            elif sub_cmd == "aim" and len(parts) >= 4:
                try:
                    gamepad_manager.apply_gyro_aim(float(parts[2]), float(parts[3]))
                except Exception:
                    pass
            elif sub_cmd == "mouse" and len(parts) >= 4:
                try:
                    controller.move_relative(float(parts[2]), float(parts[3]))
                except Exception:
                    pass

        elif cmd == "pro_auth" and len(parts) >= 2:
            from server.license_manager import verify_license
            # If server host itself has a cryptographically verified license, enable Pro
            if verify_license().get("pro_active", False):
                client_is_pro = True
            elif len(parts) >= 3:
                # Client passed key & instance_id from Lemon Squeezy
                k = parts[1].strip()
                inst = parts[2].strip()
                client_is_pro = len(k) >= 10 and len(inst) >= 5
            else:
                client_is_pro = False

        elif cmd == "pro_status":
            # Zero-trust: client boolean cannot override server security
            from server.license_manager import verify_license
            if not verify_license().get("pro_active", False):
                client_is_pro = False


def dispatch_binary_command_sync(raw_bytes: bytes) -> Optional[bytes]:
    """
    Sub-microsecond processor for raw binary input packets.
    Dispatches directly to Win32 ctypes SendInput with zero memory allocation or string parsing.
    Returns optional binary response (e.g. binary pong).
    """
    parsed = unpack_binary_message(raw_bytes)
    if not parsed:
        return None
    cmd, args = parsed

    if cmd == "m":
        controller.move_relative(args[0], args[1])
    elif cmd == "a":
        controller.move_absolute(args[0], args[1])
    elif cmd == "td":
        controller.touch_down_at(args[0], args[1], args[2])
    elif cmd == "tm":
        controller.touch_move_at(args[0], args[1])
    elif cmd == "tu":
        controller.touch_up_at(args[0], args[1], args[2])
    elif cmd == "c":
        controller.click(args[0])
    elif cmd == "s":
        controller.scroll(args[0], args[1])
    elif cmd == "ts":
        controller.scroll_at(args[0], args[1], args[2], args[3])
    elif cmd == "ping":
        ts_ms, flags = args
        return pack_pong(ts_ms)
    elif cmd == "gp_state":
        buttons, lx, ly, rx, ry, lt, rt = args
        if gamepad_manager:
            try:
                gamepad_manager.set_stick("left", lx / 32767.0, ly / 32767.0)
                gamepad_manager.set_stick("right", rx / 32767.0, ry / 32767.0)
                gamepad_manager.set_trigger("left", lt / 255.0)
                gamepad_manager.set_trigger("right", rt / 255.0)
                btn_names = ["a", "b", "x", "y", "lb", "rb", "back", "start", "ls", "rs", "dpad_up", "dpad_down", "dpad_left", "dpad_right", "guide"]
                for bit, bname in enumerate(btn_names):
                    gamepad_manager.set_button(bname, bool(buttons & (1 << bit)))
            except Exception:
                pass
    return None


async def dispatch_binary_command(raw_bytes: bytes, websocket: Optional[WebSocket] = None):
    """Asynchronously dispatches raw binary packet and replies with pong if requested."""
    reply = dispatch_binary_command_sync(raw_bytes)
    if reply is not None and websocket is not None:
        try:
            await websocket.send_bytes(reply)
        except Exception:
            pass


# ================= REVERSE PHONE REMOTE & ADB ENGINE =================

def get_adb_path() -> str:
    """Find bundled or installed adb.exe executable."""
    # 1. PyInstaller frozen runtime directory
    if getattr(sys, "frozen", False):
        base_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        candidates = [
            os.path.join(base_dir, "scrcpy_bin", "scrcpy-win64-v4.1", "adb.exe"),
            os.path.join(base_dir, "adb.exe"),
            os.path.join(os.path.dirname(sys.executable), "scrcpy_bin", "scrcpy-win64-v4.1", "adb.exe"),
            os.path.join(os.path.dirname(sys.executable), "adb.exe"),
        ]
        for c in candidates:
            if os.path.exists(c):
                return c

    # 2. Local workspace candidates
    local_candidates = [
        os.path.join(parent_dir, "scrcpy_bin", "scrcpy-win64-v4.1", "adb.exe"),
        os.path.join(current_dir, "scrcpy_bin", "scrcpy-win64-v4.1", "adb.exe"),
        os.path.join(parent_dir, "adb.exe"),
        os.path.join(current_dir, "adb.exe"),
    ]
    for c in local_candidates:
        if os.path.exists(c):
            return c

    # 3. Android SDK / Platform-Tools
    sdk_candidates = [
        r"C:\Android\platform-tools\adb.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\Android\platform-tools\adb.exe"),
    ]
    for cp in sdk_candidates:
        if os.path.exists(cp):
            return cp

    return shutil.which("adb") or "adb"


def get_connected_devices() -> list:
    """Detect all attached Android devices via ADB with device model and state info."""
    devices = []
    adb_bin = get_adb_path()
    try:
        res = subprocess.run(
            [adb_bin, "devices", "-l"],
            capture_output=True,
            text=True,
            timeout=6.0,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        for line in res.stdout.strip().splitlines():
            line = line.strip()
            if not line or line.startswith("*") or line.startswith("List of devices"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                serial = parts[0]
                state = parts[1]
                model = "Android Phone"
                for p in parts[2:]:
                    if p.startswith("model:"):
                        model = p.split(":", 1)[1].replace("_", " ")
                    elif p.startswith("device:"):
                        if model == "Android Phone":
                            model = p.split(":", 1)[1]
                devices.append({
                    "serial": serial,
                    "state": state,
                    "model": model,
                    "is_wifi": ":" in serial,
                })
    except Exception:
        pass
    return devices


# Ordered worst-to-best. Reverse control needs every rung below it to hold, so
# reporting "no device" when adb itself is missing sends people to the wrong fix.
ADB_STAGES = ("no_binary", "binary_broken", "daemon_error", "no_device",
              "offline", "unauthorized", "ready")


def adb_preflight() -> dict:
    """Diagnose the reverse-control chain and say exactly which rung failed.

    The old code called get_connected_devices() and treated everything that was
    not a live device as "offline", which is why a missing adb.exe, a blocked
    daemon and an un-tapped authorization prompt all produced the same unhelpful
    window. Each of those has a different fix, so each gets its own stage,
    headline and steps, plus the raw output in `detail` for the log.

    Returns a dict: stage, ok, headline, steps, detail, adb_path, devices, device.
    """
    adb_bin = get_adb_path()

    def result(stage, headline, steps, detail="", devices=None, device=None):
        return {
            "stage": stage,
            "ok": stage == "ready",
            "headline": headline,
            "steps": list(steps),
            "detail": detail,
            "adb_path": adb_bin,
            "devices": devices or [],
            "device": device,
        }

    # --- rung 1: is there an adb at all? ---------------------------------------
    # get_adb_path() falls back to the bare string "adb" when nothing is found,
    # so a non-absolute path means every lookup missed.
    if not os.path.isabs(adb_bin) or not os.path.exists(adb_bin):
        return result(
            "no_binary",
            "Android platform-tools (adb) not found on this PC.",
            [
                "Reinstall PCDeck — adb ships inside it, so a missing adb usually "
                "means the download was incomplete or antivirus quarantined it.",
                "Or install Android platform-tools and put adb.exe on your PATH.",
            ],
            detail=f"get_adb_path() returned {adb_bin!r}, which does not exist.",
        )

    # --- rung 2: does it actually run? ----------------------------------------
    # adb.exe can be present but unable to start: a missing AdbWinApi.dll, an
    # antivirus block, or a 32/64-bit mismatch all fail here rather than later.
    try:
        ver = subprocess.run(
            [adb_bin, "version"],
            capture_output=True, text=True, timeout=8.0,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        if ver.returncode != 0:
            return result(
                "binary_broken",
                "adb is installed but will not start.",
                [
                    "Check that AdbWinApi.dll and AdbWinUsbApi.dll sit next to adb.exe.",
                    "Allow PCDeck through your antivirus — adb is often flagged.",
                ],
                detail=(ver.stderr or ver.stdout or "").strip()[:400],
            )
        version_line = (ver.stdout or "").splitlines()[0].strip() if ver.stdout else "adb"
    except Exception as exc:
        return result(
            "binary_broken",
            "adb is installed but will not start.",
            [
                "Check that AdbWinApi.dll and AdbWinUsbApi.dll sit next to adb.exe.",
                "Allow PCDeck through your antivirus — adb is often flagged.",
            ],
            detail=f"{type(exc).__name__}: {exc}",
        )

    # --- rung 3: can we talk to the daemon and list devices? ------------------
    try:
        res = subprocess.run(
            [adb_bin, "devices", "-l"],
            capture_output=True, text=True, timeout=10.0,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except Exception as exc:
        return result(
            "daemon_error",
            "The adb server is not responding.",
            [
                "Another tool (Android Studio, scrcpy, a vendor suite) may be holding "
                "port 5037. Close it and try again.",
                "Or open a terminal and run: adb kill-server",
            ],
            detail=f"{type(exc).__name__}: {exc}  [{version_line}]",
        )

    stderr = (res.stderr or "").strip()
    if res.returncode != 0:
        return result(
            "daemon_error",
            "The adb server reported an error.",
            [
                "Run 'adb kill-server' in a terminal, then reopen this window.",
                "Close Android Studio or any other tool that talks to your phone.",
            ],
            detail=(stderr or res.stdout or "").strip()[:400],
        )

    devices = []
    for line in (res.stdout or "").strip().splitlines():
        line = line.strip()
        if not line or line.startswith("*") or line.startswith("List of devices"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            model = "Android Phone"
            for p in parts[2:]:
                if p.startswith("model:"):
                    model = p.split(":", 1)[1].replace("_", " ")
                elif p.startswith("device:") and model == "Android Phone":
                    model = p.split(":", 1)[1]
            devices.append({
                "serial": parts[0],
                "state": parts[1],
                "model": model,
                "is_wifi": ":" in parts[0],
            })

    raw = f"{version_line}\n{(res.stdout or '').strip()}"
    if stderr:
        raw += f"\n[stderr] {stderr}"

    # --- rung 4-7: classify what we found ------------------------------------
    ready = next((d for d in devices if d["state"] == "device"), None)
    if ready:
        return result(
            "ready",
            f"{ready['model']} connected.",
            [],
            detail=raw, devices=devices, device=ready,
        )

    unauth = next((d for d in devices if d["state"] == "unauthorized"), None)
    if unauth:
        return result(
            "unauthorized",
            "Phone found, but it has not authorized this PC yet.",
            [
                "Look at your phone: tap Allow on the 'Allow USB debugging?' dialog.",
                "Tick 'Always allow from this computer' so it stops asking.",
                "No dialog? Unplug and replug the cable, or revoke USB debugging "
                "authorizations in Developer options and reconnect.",
            ],
            detail=raw, devices=devices, device=unauth,
        )

    stalled = next((d for d in devices
                    if d["state"] in ("offline", "connecting", "authorizing")), None)
    if stalled:
        return result(
            "offline",
            f"Phone is listed but not usable (state: {stalled['state']}).",
            [
                "Unlock the phone screen and keep it unlocked.",
                "Turn USB debugging off and back on in Developer options.",
                "Over Wi-Fi, the pairing expires when the phone reboots or changes "
                "network — pair again from Wireless Mode.",
            ],
            detail=raw, devices=devices, device=stalled,
        )

    # Nothing at all. This is the common case and the one the old UI reported as
    # a bare "OFFLINE" next to a headline that read like the feature was live.
    return result(
        "no_device",
        "No phone is connected to this PC.",
        [
            "USB: plug the cable in, then set the USB mode to File Transfer (MTP) "
            "— charge-only will not expose adb.",
            "Enable Developer options (tap Build number 7 times), then USB debugging.",
            "No cable? Tap WIRELESS MODE and pair over Wi-Fi instead.",
        ],
        detail=raw, devices=devices,
    )


def check_adb_connected() -> bool:
    """Check if any authorized Android phone is connected via ADB."""
    devs = get_connected_devices()
    return any(d["state"] == "device" for d in devs)


def get_device_resolution(serial: str = "") -> tuple:
    """Get physical screen resolution of target device."""
    adb_bin = get_adb_path()
    cmd = [adb_bin]
    if serial:
        cmd.extend(["-s", serial])
    cmd.extend(["shell", "wm", "size"])
    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=4.0,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        for line in res.stdout.strip().splitlines():
            if "size:" in line.lower():
                val = line.split(":")[-1].strip()
                p = val.split("x")
                if len(p) == 2:
                    return int(p[0]), int(p[1])
    except Exception:
        pass
    return 720, 1600


def get_scrcpy_path() -> Optional[str]:
    """Find bundled or installed scrcpy.exe executable."""
    if getattr(sys, "frozen", False):
        base_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        candidates = [
            os.path.join(base_dir, "scrcpy_bin", "scrcpy-win64-v4.1", "scrcpy.exe"),
            os.path.join(base_dir, "scrcpy.exe"),
            os.path.join(os.path.dirname(sys.executable), "scrcpy_bin", "scrcpy-win64-v4.1", "scrcpy.exe"),
            os.path.join(os.path.dirname(sys.executable), "scrcpy.exe"),
        ]
        for c in candidates:
            if os.path.exists(c):
                return c

    local_candidates = [
        os.path.join(parent_dir, "scrcpy_bin", "scrcpy-win64-v4.1", "scrcpy.exe"),
        os.path.join(current_dir, "scrcpy_bin", "scrcpy-win64-v4.1", "scrcpy.exe"),
        os.path.join(parent_dir, "scrcpy.exe"),
        os.path.join(current_dir, "scrcpy.exe"),
    ]
    for c in local_candidates:
        if os.path.exists(c):
            return c

    return shutil.which("scrcpy")


def launch_scrcpy(serial: Optional[str] = None) -> tuple:
    """Launch 60FPS scrcpy screen mirror and hardware phone controller."""
    scrcpy_bin = get_scrcpy_path()
    if not scrcpy_bin or not os.path.exists(scrcpy_bin):
        return False, "scrcpy.exe not found in bundle or system PATH."

    cmd = [
        scrcpy_bin,
        "--max-size=1600",
        "--video-bit-rate=8M",
        "--max-fps=60",
        "--stay-awake",
    ]
    if serial:
        cmd.extend(["-s", serial])

    try:
        subprocess.Popen(
            cmd,
            cwd=os.path.dirname(scrcpy_bin),
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        return True, "Launched Phone Screen Mirror (scrcpy 60FPS)!"
    except Exception as e:
        return False, f"Failed to launch scrcpy: {e}"


def get_device_ip(serial: str = "") -> Optional[str]:
    """Detect local Wi-Fi IP address of Android device across Android 5-15."""
    adb_bin = get_adb_path()
    cmd_prefix = [adb_bin]
    if serial:
        cmd_prefix.extend(["-s", serial])

    import re
    ip_regex = re.compile(r"\b(192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b")

    for shell_cmd in [
        ["shell", "ip route"],
        ["shell", "ip addr show wlan0"],
        ["shell", "ip addr"],
        ["shell", "ifconfig wlan0"],
        ["shell", "dumpsys wifi"],
        ["shell", "dumpsys connectivity"],
    ]:
        try:
            res = subprocess.run(
                cmd_prefix + shell_cmd,
                capture_output=True,
                text=True,
                timeout=3.5,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            for ip in ip_regex.findall(res.stdout):
                if not ip.endswith(".0") and not ip.endswith(".255"):
                    return ip
        except Exception:
            pass
    return None


def switch_device_to_wireless(serial: str = "") -> tuple:
    """Enable Wireless ADB on phone so user can unplug USB and control over Wi-Fi."""
    adb_bin = get_adb_path()
    ip = get_device_ip(serial)

    cmd_tcpip = [adb_bin]
    if serial:
        cmd_tcpip.extend(["-s", serial])
    cmd_tcpip.extend(["tcpip", "5555"])

    try:
        subprocess.run(
            cmd_tcpip,
            capture_output=True,
            text=True,
            timeout=6.0,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        time.sleep(1.2)
        if ip:
            conn_res = subprocess.run(
                [adb_bin, "connect", f"{ip}:5555"],
                capture_output=True,
                text=True,
                timeout=6.0,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            out = conn_res.stdout.strip()
            if "connected to" in out.lower() or "already connected" in out.lower():
                return True, f"Connected wirelessly to {ip}:5555! You can now unplug the USB cable."
        return True, "Enabled TCP/IP mode on port 5555. If not auto-connected, enter phone IP in Wireless Dialog."
    except Exception as e:
        return False, f"Wireless pairing error: {e}"



async def broadcast_phone_command(cmd_str: str):
    """Send reverse control command to all active mobile WebSocket clients."""
    if not active_connections:
        return
    dead = []
    for ws in list(active_connections):
        try:
            await ws.send_text(cmd_str)
        except Exception:
            dead.append(ws)
    for ws in dead:
        active_connections.discard(ws)


@app.get("/api/phone/status")
async def get_phone_status():
    """Return connected Android devices and ADB mirror status."""
    devs = get_connected_devices()
    return {
        "adb_available": get_adb_path() is not None,
        "scrcpy_available": get_scrcpy_path() is not None,
        "devices": devs,
        "connected": any(d["state"] == "device" for d in devs),
    }


@app.post("/api/phone/mirror")
async def launch_phone_mirror_api(serial: str = ""):
    """Launch 60FPS scrcpy mirror for phone."""
    ok, msg = launch_scrcpy(serial or None)
    return {"status": "ok" if ok else "error", "message": msg}


@app.post("/api/phone/wireless")
async def switch_phone_wireless_api(serial: str = ""):
    """Switch phone from USB to Wireless ADB."""
    ok, msg = switch_device_to_wireless(serial)
    return {"status": "ok" if ok else "error", "message": msg}


@app.post("/api/phone/command")
async def send_phone_command_api(cmd: str = Body(..., embed=True)):
    """Dispatch reverse phone control command via WebSocket."""
    await broadcast_phone_command(cmd)
    return {"status": "dispatched", "command": cmd}


_DRIVER_PROGRESS_CALLBACK = None

def set_driver_progress_callback(cb):
    global _DRIVER_PROGRESS_CALLBACK
    _DRIVER_PROGRESS_CALLBACK = cb

def notify_driver_progress(driver_name: str, percent: int, stage_text: str, status: str = "running"):
    if _DRIVER_PROGRESS_CALLBACK:
        try:
            _DRIVER_PROGRESS_CALLBACK(driver_name, percent, stage_text, status)
        except Exception:
            pass


async def install_cam_driver_with_progress(websocket: WebSocket):
    from server.camera_streamer import get_drivers_dir, has_internet_connection, is_webcam_driver_installed

    # 0. Check if ALREADY installed & functional
    if await asyncio.to_thread(is_webcam_driver_installed):
        notify_driver_progress("Virtual Webcam", 100, "Virtual Webcam driver is already installed & verified!", "success")
        try:
            await websocket.send_text("cam_driver_progress,100,Virtual Webcam driver is already installed & verified!")
            await websocket.send_text("cam_driver_install_result,success,Virtual Webcam driver is already installed & verified!")
        except Exception:
            pass
        return

    drivers_dir = get_drivers_dir()
    dll64 = os.path.join(drivers_dir, "UnityCaptureFilter64.dll")
    dll32 = os.path.join(drivers_dir, "UnityCaptureFilter32.dll")

    notify_driver_progress("Virtual Webcam", 10, "Starting Virtual Camera driver setup...", "running")
    try:
        await websocket.send_text("cam_driver_progress,10,Starting Virtual Camera driver setup...")
    except Exception:
        pass

    if not os.path.exists(dll64):
        if not has_internet_connection():
            msg = "Offline: No internet on PC to download camera driver. Place UnityCaptureFilter64.dll in PCDeck/drivers/."
            notify_driver_progress("Virtual Webcam", 0, msg, "failed")
            try:
                await websocket.send_text(f"cam_driver_install_result,failed,{msg}")
            except Exception:
                pass
            return
        notify_driver_progress("Virtual Webcam", 25, "Downloading Virtual Camera package...", "running")
        try:
            await websocket.send_text("cam_driver_progress,25,Downloading Virtual Camera package...")
        except Exception:
            pass
        proc = await asyncio.to_thread(
            subprocess.run,
            ["winget", "install", "--id", "OBSProject.OBSStudio", "-e", "--silent", "--accept-package-agreements", "--accept-source-agreements"],
            capture_output=True, text=True
        )
        if proc.returncode == 0:
            notify_driver_progress("Virtual Webcam", 100, "Virtual Webcam installed successfully!", "success")
            await websocket.send_text("cam_driver_install_result,success,Virtual Webcam installed successfully!")
        else:
            msg = f"Package manager returned code {proc.returncode}"
            notify_driver_progress("Virtual Webcam", 0, msg, "failed")
            await websocket.send_text(f"cam_driver_install_result,failed,{msg}")
        return

    # Offline local package install
    notify_driver_progress("Virtual Webcam", 25, "Registering DirectShow Virtual Camera filter...", "running")
    try:
        await websocket.send_text("cam_driver_progress,25,Registering DirectShow Virtual Camera filter...")
    except Exception:
        pass

    def run_regsvr(dll_path):
        try:
            # 1. First try silent un-elevated (works instantly when run by user)
            res = subprocess.run(["regsvr32.exe", "/s", dll_path], capture_output=True, timeout=5)
            if res.returncode == 0:
                return 0
        except Exception:
            pass
        # 2. Elevated fallback with strict 8s timeout
        try:
            ps_cmd = f"Start-Process -FilePath 'regsvr32.exe' -ArgumentList '/s \"`\"{dll_path}`\"' -Verb RunAs -Wait"
            res = subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps_cmd],
                                 capture_output=True, timeout=8,
                                 creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
            return res.returncode
        except Exception:
            return -1

    # Register 64-bit filter
    await asyncio.to_thread(run_regsvr, dll64)
    # Register 32-bit filter if present
    if os.path.exists(dll32):
        await asyncio.to_thread(run_regsvr, dll32)

    notify_driver_progress("Virtual Webcam", 60, "Verifying DirectShow Virtual Camera filter...", "running")
    try:
        await websocket.send_text("cam_driver_progress,60,Verifying DirectShow Virtual Camera filter...")
    except Exception:
        pass

    installed = False
    for i in range(8):
        await asyncio.sleep(0.5)
        pct = min(95, 65 + i * 4)
        notify_driver_progress("Virtual Webcam", pct, f"Checking camera device in Windows ({i+1}s)...", "running")
        try:
            await websocket.send_text(f"cam_driver_progress,{pct},Checking camera device in Windows ({i+1}s)...")
        except Exception:
            pass
        if await asyncio.to_thread(is_webcam_driver_installed):
            installed = True
            break

    if installed or await asyncio.to_thread(is_webcam_driver_installed):
        notify_driver_progress("Virtual Webcam", 100, "Virtual Webcam active & verified!", "success")
        try:
            await websocket.send_text("cam_driver_progress,100,Virtual Webcam active & verified!")
            await websocket.send_text("cam_driver_install_result,success,Virtual Webcam active & verified!")
        except Exception:
            pass
    else:
        msg = "Camera registered, but device not detected yet. Please restart PCDeck."
        notify_driver_progress("Virtual Webcam", 0, msg, "failed")
        try:
            await websocket.send_text(f"cam_driver_install_result,failed,{msg}")
        except Exception:
            pass


async def install_mic_driver_with_progress(websocket: WebSocket):
    from server.audio_streamer import (
        get_drivers_dir, has_internet_connection, is_mic_driver_installed,
        get_default_playback_id, restore_playback_id
    )

    # 0. Check if ALREADY installed & functional
    if await asyncio.to_thread(is_mic_driver_installed):
        notify_driver_progress("Virtual Microphone", 100, "VB-CABLE Virtual Microphone is already installed & verified!", "success")
        try:
            await websocket.send_text("mic_driver_progress,100,VB-CABLE Virtual Microphone is already installed & verified!")
            await websocket.send_text("mic_driver_install_result,success,VB-CABLE Virtual Microphone is already installed & verified!")
        except Exception:
            pass
        return

    drivers_dir = get_drivers_dir()
    exe_path = os.path.join(drivers_dir, "VBCABLE_Setup_x64.exe")

    # 1. Capture current default audio output so we can restore it immediately after install
    saved_default_audio_id = await asyncio.to_thread(get_default_playback_id)

    notify_driver_progress("Virtual Microphone", 10, "Starting audio driver setup...", "running")
    try:
        await websocket.send_text("mic_driver_progress,10,Starting audio driver setup...")
    except Exception:
        pass

    if not os.path.exists(exe_path):
        if not has_internet_connection():
            msg = "Offline: No internet on PC to download microphone driver. Place VBCABLE_Setup_x64.exe in PCDeck/drivers/."
            notify_driver_progress("Virtual Microphone", 0, msg, "failed")
            try:
                await websocket.send_text(f"mic_driver_install_result,failed,{msg}")
            except Exception:
                pass
            return
        notify_driver_progress("Virtual Microphone", 25, "Downloading VB-CABLE via package manager...", "running")
        try:
            await websocket.send_text("mic_driver_progress,25,Downloading VB-CABLE via package manager...")
        except Exception:
            pass
        proc = await asyncio.to_thread(
            subprocess.run,
            ["winget", "install", "--id", "VB-Audio.VirtualCable", "-e", "--silent", "--accept-package-agreements", "--accept-source-agreements"],
            capture_output=True, text=True
        )
        # Restore real PC speakers after package manager finishes
        await asyncio.to_thread(restore_playback_id, saved_default_audio_id)
        if proc.returncode == 0 or await asyncio.to_thread(is_mic_driver_installed):
            notify_driver_progress("Virtual Microphone", 100, "VB-CABLE installed successfully!", "success")
            try:
                await websocket.send_text("mic_driver_install_result,success,VB-CABLE installed successfully!")
            except Exception:
                pass
        else:
            msg = f"Package manager returned code {proc.returncode}"
            notify_driver_progress("Virtual Microphone", 0, msg, "failed")
            try:
                await websocket.send_text(f"mic_driver_install_result,failed,{msg}")
            except Exception:
                pass
        return

    # Offline local package install
    notify_driver_progress("Virtual Microphone", 20, "Please click 'Yes' on the PC permission prompt...", "running")
    try:
        await websocket.send_text("mic_driver_progress,20,Please click 'Yes' on the PC permission prompt...")
    except Exception:
        pass

    ps_cmd = f"Start-Process -FilePath '{exe_path}' -ArgumentList '-i -h' -WorkingDirectory '{drivers_dir}' -Verb RunAs -Wait"

    try:
        proc = await asyncio.to_thread(
            subprocess.run,
            ["powershell.exe", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        if proc.returncode != 0 and not await asyncio.to_thread(is_mic_driver_installed):
            msg = "Administrator permission was declined on PC."
            notify_driver_progress("Virtual Microphone", 0, msg, "failed")
            try:
                await websocket.send_text(f"mic_driver_install_result,failed,{msg}")
            except Exception:
                pass
            return
    except Exception as e:
        if not await asyncio.to_thread(is_mic_driver_installed):
            msg = f"Failed to launch installer: {e}"
            notify_driver_progress("Virtual Microphone", 0, msg, "failed")
            try:
                await websocket.send_text(f"mic_driver_install_result,failed,{msg}")
            except Exception:
                pass
            return

    # Immediately restore real PC speakers so audio never goes silent
    await asyncio.to_thread(restore_playback_id, saved_default_audio_id)

    notify_driver_progress("Virtual Microphone", 60, "Installer running... Registering virtual audio cable...", "running")
    try:
        await websocket.send_text("mic_driver_progress,60,Installer running... Registering virtual audio cable...")
    except Exception:
        pass

    installed = False
    for i in range(12):
        await asyncio.sleep(0.8)
        pct = min(95, 65 + i * 3)
        notify_driver_progress("Virtual Microphone", pct, f"Configuring Windows audio devices ({i+1}s)...", "running")
        try:
            await websocket.send_text(f"mic_driver_progress,{pct},Configuring Windows audio devices ({i+1}s)...")
        except Exception:
            pass
        if await asyncio.to_thread(is_mic_driver_installed):
            installed = True
            break

    # Restore default audio again after device registration
    await asyncio.to_thread(restore_playback_id, saved_default_audio_id)

    if installed or await asyncio.to_thread(is_mic_driver_installed):
        notify_driver_progress("Virtual Microphone", 100, "VB-CABLE Virtual Microphone active & verified!", "success")
        try:
            await websocket.send_text("mic_driver_progress,100,VB-CABLE Virtual Microphone active & verified!")
            await websocket.send_text("mic_driver_install_result,success,VB-CABLE Virtual Microphone active & verified!")
        except Exception:
            pass
    else:
        msg = "Driver installation finished, but Windows needs a moment or a restart to register audio cables."
        notify_driver_progress("Virtual Microphone", 0, msg, "failed")
        try:
            await websocket.send_text(f"mic_driver_install_result,failed,{msg}")
        except Exception:
            pass


async def install_gamepad_driver_with_progress(websocket: WebSocket):
    from server.gamepad_manager import (
        get_drivers_dir, has_internet_connection, is_vigem_installed, gamepad_manager
    )

    # 0. Check if ALREADY installed & functional
    if await asyncio.to_thread(is_vigem_installed):
        notify_driver_progress("Virtual Gamepad", 100, "ViGEmBus Virtual Xbox 360 Controller is already active & verified!", "success")
        try:
            await websocket.send_text("gamepad_driver_progress,100,ViGEmBus Virtual Xbox 360 Controller is already active & verified!")
            await websocket.send_text("gamepad_driver_install_result,success,ViGEmBus Virtual Xbox 360 Controller active & verified!")
            await websocket.send_text("driver_install_result,success,xinput")
            await websocket.send_text("driver_status,installed,xinput")
            await websocket.send_text("gamepad_driver_status,installed,xinput")
        except Exception:
            pass
        return

    drivers_dir = get_drivers_dir()
    exe_path = os.path.join(drivers_dir, "ViGEmBus_Setup.exe")
    msi_path = os.path.join(drivers_dir, "ViGEmBus_x64.msi")

    notify_driver_progress("Virtual Gamepad", 10, "Starting Virtual Xbox Controller setup...", "running")
    try:
        await websocket.send_text("gamepad_driver_progress,10,Starting Virtual Xbox Controller setup...")
    except Exception:
        pass

    # Offline / Online check
    if not os.path.exists(exe_path) and not os.path.exists(msi_path):
        if not has_internet_connection():
            msg = "Offline: No internet on PC to download gamepad driver. Place ViGEmBus_Setup.exe in PCDeck/drivers/."
            notify_driver_progress("Virtual Gamepad", 0, msg, "failed")
            try:
                await websocket.send_text(f"gamepad_driver_install_result,failed,{msg}")
                await websocket.send_text(f"driver_install_result,failed,{msg}")
            except Exception:
                pass
            return

        notify_driver_progress("Virtual Gamepad", 25, "Downloading ViGEmBus via package manager...", "running")
        try:
            await websocket.send_text("gamepad_driver_progress,25,Downloading ViGEmBus via package manager...")
        except Exception:
            pass
        proc = await asyncio.to_thread(
            subprocess.run,
            ["winget", "install", "--id", "Nefarius.ViGEmBus", "-e", "--silent", "--accept-package-agreements", "--accept-source-agreements"],
            capture_output=True, text=True
        )
        if proc.returncode == 0 or await asyncio.to_thread(is_vigem_installed):
            gamepad_manager.init_backend()
            notify_driver_progress("Virtual Gamepad", 100, "ViGEmBus installed successfully!", "success")
            try:
                await websocket.send_text("gamepad_driver_progress,100,ViGEmBus installed successfully!")
                await websocket.send_text("gamepad_driver_install_result,success,ViGEmBus installed successfully!")
                await websocket.send_text(f"driver_install_result,success,{gamepad_manager.mode}")
                await websocket.send_text("driver_status,installed,xinput")
                await websocket.send_text("gamepad_driver_status,installed,xinput")
            except Exception:
                pass
        else:
            msg = f"Package manager returned code {proc.returncode}"
            notify_driver_progress("Virtual Gamepad", 0, msg, "failed")
            try:
                await websocket.send_text(f"gamepad_driver_install_result,failed,{msg}")
                await websocket.send_text(f"driver_install_result,failed,{msg}")
            except Exception:
                pass
        return

    # Offline local package install
    notify_driver_progress("Virtual Gamepad", 20, "Please click 'Yes' on the PC permission prompt...", "running")
    try:
        await websocket.send_text("gamepad_driver_progress,20,Please click 'Yes' on the PC permission prompt...")
    except Exception:
        pass

    # Prefer ViGEmBus_Setup.exe, fallback to ViGEmBus_x64.msi
    if os.path.exists(exe_path):
        ps_cmd = f"Start-Process -FilePath '{exe_path}' -ArgumentList '/passive /norestart' -WorkingDirectory '{drivers_dir}' -Verb RunAs -Wait"
    else:
        ps_cmd = f"Start-Process -FilePath 'msiexec.exe' -ArgumentList '/i \\\"{msi_path}\\\" /passive /norestart ALLUSERS=1' -WorkingDirectory '{drivers_dir}' -Verb RunAs -Wait"

    try:
        proc = await asyncio.to_thread(
            subprocess.run,
            ["powershell.exe", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        if proc.returncode != 0 and not await asyncio.to_thread(is_vigem_installed):
            # If Setup.exe returned error, attempt MSI directly
            if os.path.exists(msi_path) and os.path.exists(exe_path):
                ps_cmd_msi = f"Start-Process -FilePath 'msiexec.exe' -ArgumentList '/i \\\"{msi_path}\\\" /passive /norestart ALLUSERS=1' -WorkingDirectory '{drivers_dir}' -Verb RunAs -Wait"
                await asyncio.to_thread(
                    subprocess.run,
                    ["powershell.exe", "-NoProfile", "-Command", ps_cmd_msi],
                    capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )
    except Exception as e:
        if not await asyncio.to_thread(is_vigem_installed):
            msg = f"Failed to launch installer: {e}"
            notify_driver_progress("Virtual Gamepad", 0, msg, "failed")
            try:
                await websocket.send_text(f"gamepad_driver_install_result,failed,{msg}")
                await websocket.send_text(f"driver_install_result,failed,{msg}")
            except Exception:
                pass
            return

    notify_driver_progress("Virtual Gamepad", 60, "Installer running... Registering virtual Xbox 360 controller device...", "running")
    try:
        await websocket.send_text("gamepad_driver_progress,60,Installer running... Registering virtual Xbox 360 controller device...")
    except Exception:
        pass

    installed = False
    for i in range(12):
        await asyncio.sleep(0.8)
        pct = min(95, 65 + i * 3)
        notify_driver_progress("Virtual Gamepad", pct, f"Configuring XInput controller in Windows ({i+1}s)...", "running")
        try:
            await websocket.send_text(f"gamepad_driver_progress,{pct},Configuring XInput controller in Windows ({i+1}s)...")
        except Exception:
            pass
        if await asyncio.to_thread(is_vigem_installed):
            installed = True
            break

    if installed or await asyncio.to_thread(is_vigem_installed):
        gamepad_manager.init_backend()
        notify_driver_progress("Virtual Gamepad", 100, "Virtual Xbox 360 Controller active & verified!", "success")
        try:
            await websocket.send_text("gamepad_driver_progress,100,Virtual Xbox 360 Controller active & verified!")
            await websocket.send_text("gamepad_driver_install_result,success,Virtual Xbox 360 Controller active & verified!")
            await websocket.send_text(f"driver_install_result,success,{gamepad_manager.mode}")
            await websocket.send_text("driver_status,installed,xinput")
            await websocket.send_text("gamepad_driver_status,installed,xinput")
        except Exception:
            pass
    else:
        msg = "Driver installation finished, but Windows needs a moment or a restart to register Xbox Controller."
        notify_driver_progress("Virtual Gamepad", 0, msg, "failed")
        try:
            await websocket.send_text(f"gamepad_driver_install_result,failed,{msg}")
            await websocket.send_text(f"driver_install_result,failed,{msg}")
        except Exception:
            pass


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main Trackpad, Gamepad and control WebSocket endpoint."""
    client_ip = websocket.client.host if websocket.client else ""
    token = websocket.query_params.get("token")
    is_authed = is_client_authorized(client_ip, token)

    await websocket.accept()
    active_connections.add(websocket)

    if wifi_latency_manager:
        wifi_latency_manager.optimize_socket_for_low_latency(websocket)

    # Automatically notify client if PC Host has Pro unlocked
    if is_pro_client():
        try:
            await websocket.send_text("pro_unlocked,1")
        except Exception:
            pass

    try:
        while True:
            msg = await websocket.receive()
            if msg["type"] == "websocket.disconnect":
                break
            if "bytes" in msg and msg["bytes"]:
                if not is_authed:
                    await websocket.close(code=4003, reason="Unauthorized")
                    break
                await dispatch_binary_command(msg["bytes"], websocket)
                continue
            data = msg.get("text")
            if not data:
                continue

            if not is_authed:
                if data == "get_token":
                    await websocket.send_text(f"token,{get_pairing_token()}")
                    continue
                elif data.startswith("pair,"):
                    parts = data.split(",")
                    cand_token = parts[1].strip() if len(parts) >= 2 else ""
                    if is_client_authorized(client_ip, cand_token):
                        is_authed = True
                        await websocket.send_text("pair_ok,1")
                        continue
                    else:
                        await websocket.send_text("pair_error,unauthorized")
                        await websocket.close(code=4003, reason="Unauthorized")
                        break
                elif data.startswith("p,"):
                    parts = data.split(",")
                    await websocket.send_text(f"pong,{parts[1]}")
                    continue
                elif data.startswith("pro_status,") or "driver" in data:
                    continue
                else:
                    await websocket.send_text("auth_required")
                    continue

            if data == "get_token":
                await websocket.send_text(f"token,{get_pairing_token()}")
                continue
            elif data.startswith("p,"):
                parts = data.split(",")
                await websocket.send_text(f"pong,{parts[1]}")
            elif data.startswith("lat,"):
                parts = data.split(",")
                if len(parts) >= 2 and wifi_latency_manager:
                    try:
                        wifi_latency_manager.update_measured_rtt(float(parts[1]))
                    except Exception:
                        pass
            elif data.startswith("pro_auth,"):
                parts = data.split(",")
                from server.license_manager import verify_license
                host_pro = verify_license().get("pro_active", False)
                if host_pro or (len(parts) >= 3 and len(parts[1].strip()) >= 10 and len(parts[2].strip()) >= 5):
                    set_pro_client(True)
                    await websocket.send_text("pro_unlocked,1")
                else:
                    if not host_pro:
                        set_pro_client(False)
                        await websocket.send_text("pro_unlocked,0")
            elif data in ("driver_check", "gamepad_driver_check"):
                # Check ViGEmBus status on Windows
                installed = is_vigem_installed()
                status = "installed" if installed else "missing"
                mode = gamepad_manager.mode
                await websocket.send_text(f"driver_status,{status},{mode}")
                await websocket.send_text(f"gamepad_driver_status,{status},{mode}")
            elif data in ("install_driver_request", "install_gamepad_driver_request"):
                # Request 1-click silent virtual gamepad driver install with live progress
                await install_gamepad_driver_with_progress(websocket)
            elif data == "cam_driver_check":
                # Check Virtual Webcam DirectShow status on host
                installed = is_webcam_driver_installed()
                status = "installed" if installed else "missing"
                await websocket.send_text(f"cam_driver_status,{status}")
            elif data == "install_cam_driver_request":
                # Request 1-click silent virtual webcam driver install with live progress
                await install_cam_driver_with_progress(websocket)
            elif data == "mic_driver_check":
                # Check Virtual Audio Cable status on host
                installed = is_mic_driver_installed()
                status = "installed" if installed else "missing"
                await websocket.send_text(f"mic_driver_status,{status}")
            elif data == "install_mic_driver_request":
                # Request 1-click silent virtual mic cable driver install with live progress
                await install_mic_driver_with_progress(websocket)
            elif data.startswith("cam_flip,"):
                val = data.split(",")[1] == "1"
                camera_streamer.set_flip_horizontal(val)
            else:
                dispatch_command(data)

    except (WebSocketDisconnect, asyncio.CancelledError, Exception):
        pass
    finally:
        active_connections.discard(websocket)
        try:
            await websocket.close()
        except Exception:
            pass


@app.websocket("/ws/mic")
async def websocket_mic_endpoint(websocket: WebSocket):
    """
    Wireless PC Microphone endpoint.
    Receives real-time 16-bit 48kHz PCM audio buffers from the phone and routes
    them to the host's virtual audio cable device.
    """
    client_ip = websocket.client.host if websocket.client else ""
    token = websocket.query_params.get("token")
    if not is_client_authorized(client_ip, token):
        await websocket.close(code=4003, reason="Unauthorized")
        return

    await websocket.accept()
    print("[MicWS] Phone connected to WebSocket /ws/mic!", flush=True)
    mic_sink.start()
    try:
        await websocket.send_text(f"mic_ready,{mic_sink.sample_rate},{mic_sink.channels},{mic_sink.active_device_name}")
        while True:
            data = await websocket.receive_bytes()
            if data:
                mic_sink.push_pcm_bytes(data)
    except (WebSocketDisconnect, asyncio.CancelledError, Exception) as e:
        print(f"[MicWS] Disconnected: {e}", flush=True)
    finally:
        mic_sink.stop()
        try:
            await websocket.close()
        except Exception:
            pass


@app.post("/api/mic/stream")
async def mic_stream_post(request: Request):
    """High-speed chunked HTTP POST endpoint for phone microphone streaming (100% firewall-safe)."""
    client_ip = request.client.host if request.client else ""
    token = request.query_params.get("token") or request.headers.get("x-pcdeck-token")
    if not is_client_authorized(client_ip, token):
        return JSONResponse(status_code=403, content={"error": "Unauthorized"})

    print("[MicStream] Phone connected to HTTP audio stream!", flush=True)
    mic_sink.start()
    total_bytes = 0
    try:
        async for chunk in request.stream():
            if chunk:
                total_bytes += len(chunk)
                mic_sink.push_pcm_bytes(chunk)
    except Exception as e:
        print(f"[MicStream] Connection ended: {e}", flush=True)
    finally:
        print(f"[MicStream] Stream finished. Total bytes received: {total_bytes}", flush=True)
        mic_sink.stop()
    return {"status": "ok"}


@app.on_event("startup")
async def startup_event():
    # Auto-heal: Ensure Windows WLAN autoconfig is enabled on startup
    if sys.platform == "win32":
        try:
            if wifi_latency_manager and hasattr(wifi_latency_manager, "startup_auto_heal"):
                wifi_latency_manager.startup_auto_heal()
        except Exception:
            pass

    try:
        from server.audio_streamer import mic_sink
        mic_sink.start_dual_receiver(8002)
    except Exception as e:
        print(f"[Startup] Mic dual receiver init error: {e}")

    if sys.platform == "win32":
        try:
            from server.camera_streamer import is_webcam_driver_installed, camera_streamer
            if is_webcam_driver_installed():
                camera_streamer.start_camera(width=1280, height=720, fps=30)
                camera_streamer.stop_camera()
        except Exception:
            pass


@app.on_event("shutdown")
async def shutdown_event():
    if sys.platform == "win32":
        try:
            if wifi_latency_manager:
                wifi_latency_manager.release_all_streaming_modes()
                wifi_latency_manager._cleanup_on_exit()
        except Exception:
            pass


@app.websocket("/ws/cam")
async def websocket_cam_endpoint(websocket: WebSocket):
    """
    Wireless HD Webcam endpoint.
    Receives high-resolution video frames from the mobile camera and pushes
    them to the virtual webcam DirectShow device via pyvirtualcam.
    """
    client_ip = websocket.client.host if websocket.client else ""
    token = websocket.query_params.get("token")
    if not is_client_authorized(client_ip, token):
        await websocket.close(code=4003, reason="Unauthorized")
        return

    await websocket.accept()
    camera_streamer.start_camera(width=1280, height=720, fps=30)
    try:
        await websocket.send_text(f"cam_ready,{camera_streamer.target_width},{camera_streamer.target_height},{camera_streamer.target_fps}")
        while True:
            # Handle either binary frame or text config command
            message = await websocket.receive()
            if "bytes" in message and message["bytes"]:
                camera_streamer.push_frame_bytes(message["bytes"])
            elif "text" in message and message["text"]:
                text_cmd = message["text"]
                if text_cmd.startswith("cfg,"):
                    parts = text_cmd.split(",")
                    if len(parts) >= 4:
                        w, h, fps = int(parts[1]), int(parts[2]), int(parts[3])
                        camera_streamer.start_camera(width=w, height=h, fps=fps)
                elif text_cmd.startswith("flip,"):
                    parts = text_cmd.split(",")
                    if len(parts) >= 2:
                        camera_streamer.set_flip_horizontal(parts[1] == "1")
    except (WebSocketDisconnect, asyncio.CancelledError, Exception):
        pass
    finally:
        camera_streamer.stop_camera()
        try:
            await websocket.close()
        except Exception:
            pass


@app.websocket("/ws/screen")
async def websocket_screen_endpoint(websocket: WebSocket):
    """Zero-Lag adaptive binary screen streaming & interactive touch display endpoint."""
    client_ip = websocket.client.host if websocket.client else ""
    token = websocket.query_params.get("token")
    if not is_client_authorized(client_ip, token):
        await websocket.close(code=4003, reason="Unauthorized")
        return

    await websocket.accept()
    screen_connections.add(websocket)
    streamer.acquire()

    ws_client_id = f"screen_{id(websocket)}"
    if wifi_latency_manager:
        wifi_latency_manager.optimize_socket_for_low_latency(websocket)
        wifi_latency_manager.acquire_streaming_mode(ws_client_id)

    loop = asyncio.get_running_loop()
    frame_event = asyncio.Event()
    streamer.register_async_listener(loop, frame_event)

    # Instantly deliver the latest frame so the client renders in <10ms without a black/loading screen
    initial_jpeg, initial_id = streamer.get_latest_frame()
    if not initial_jpeg:
        try:
            initial_jpeg, _, _ = streamer.grab_single_frame(quality=streamer.quality, scale=streamer.scale)
        except Exception:
            pass
    if initial_jpeg:
        try:
            await websocket.send_bytes(initial_jpeg)
        except Exception:
            pass

    # In-flight frame flow control to completely eliminate TCP bufferbloat
    client_ready_event = asyncio.Event()
    client_ready_event.set()
    is_paused = False

    async def send_frames():
        last_sent_id = initial_id if initial_jpeg else -1
        last_keepalive_at = time.time()
        while True:
            try:
                if is_paused:
                    # Video stream paused: sleep gently to free 100% Wi-Fi bandwidth for audio/trackpad
                    await asyncio.sleep(0.12)
                    continue

                # Wait for instant async frame notification (0ms delay, zero executor overhead)
                try:
                    await asyncio.wait_for(frame_event.wait(), timeout=0.8)
                except asyncio.TimeoutError:
                    pass
                frame_event.clear()

                now = time.time()
                jpeg, frame_id = streamer.get_latest_frame()
                if jpeg and frame_id != last_sent_id:
                    # Prevent TCP bufferbloat: verify transport write buffer is not congested (>256KB)
                    if wifi_latency_manager and wifi_latency_manager.is_transport_congested(websocket, max_buffered_bytes=262144):
                        await asyncio.sleep(0.01)
                        continue

                    last_sent_id = frame_id
                    last_keepalive_at = now
                    if wifi_latency_manager and hasattr(wifi_latency_manager, "touch_stream_activity"):
                        wifi_latency_manager.touch_stream_activity()
                    await websocket.send_bytes(jpeg)
                elif (now - last_keepalive_at) > 1.0:
                    last_keepalive_at = now
                    # Lightweight keepalive ping to keep connection alive without flooding video pipe
                    await websocket.send_text("h")
            except (asyncio.CancelledError, WebSocketDisconnect, Exception):
                break

    async def receive_cmds():
        nonlocal is_paused
        try:
            while True:
                msg = await websocket.receive()
                if msg["type"] == "websocket.disconnect":
                    break
                if wifi_latency_manager and hasattr(wifi_latency_manager, "touch_stream_activity"):
                    wifi_latency_manager.touch_stream_activity()
                if "bytes" in msg and msg["bytes"]:
                    await dispatch_binary_command(msg["bytes"], websocket)
                    continue
                data = msg.get("text")
                if not data:
                    continue

                if data == "a" or data.startswith("ack"):
                    client_ready_event.set()
                elif data == "pause":
                    is_paused = True
                    streamer.pause_consumer()
                    if wifi_latency_manager:
                        wifi_latency_manager.release_streaming_mode(ws_client_id)
                    print("[ScreenStreamer] Client switched tab -> Screen stream PAUSED (0% Wi-Fi load)", flush=True)
                elif data == "resume":
                    is_paused = False
                    streamer.resume_consumer()
                    if wifi_latency_manager:
                        wifi_latency_manager.acquire_streaming_mode(ws_client_id)
                    client_ready_event.set()
                    print("[ScreenStreamer] Client focused screen tab -> Screen stream RESUMED", flush=True)
                elif data.startswith("lat,"):
                    parts = data.split(",")
                    if len(parts) >= 2 and wifi_latency_manager:
                        try:
                            wifi_latency_manager.update_measured_rtt(float(parts[1]))
                        except Exception:
                            pass
                elif data.startswith("cfg,"):
                    parts = data.split(",")
                    if len(parts) >= 4:
                        req_fps = int(parts[3])
                        if not is_pro_client() and req_fps > 30:
                            req_fps = 30
                        streamer.fps_limit = max(10, min(60, req_fps))
                elif data.startswith("p,"):
                    parts = data.split(",")
                    await websocket.send_text(f"pong,{parts[1]}")
                else:
                    dispatch_command(data)
        except (asyncio.CancelledError, WebSocketDisconnect, Exception):
            pass

    sender_task = asyncio.create_task(send_frames())
    receiver_task = asyncio.create_task(receive_cmds())

    try:
        done, pending = await asyncio.wait(
            [sender_task, receiver_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for t in pending:
            t.cancel()
    except Exception:
        pass
    finally:
        screen_connections.discard(websocket)
        streamer.unregister_async_listener(frame_event)
        streamer.release()
        if wifi_latency_manager:
            wifi_latency_manager.release_streaming_mode(ws_client_id)
        try:
            await websocket.close()
        except Exception:
            pass


@app.websocket("/ws/audio")
async def websocket_audio_endpoint(websocket: WebSocket):
    """Ultra-low-latency real-time PCM audio streaming endpoint for mobile phone."""
    client_ip = websocket.client.host if websocket.client else ""
    token = websocket.query_params.get("token")
    if not is_client_authorized(client_ip, token):
        await websocket.close(code=4003, reason="Unauthorized")
        return

    await websocket.accept()
    if wifi_latency_manager:
        wifi_latency_manager.optimize_socket_for_low_latency(websocket)
    audio_queue = audio_streamer.register_subscriber()

    try:
        # Send audio configuration handshake: "cfg,{sample_rate},{channels},16"
        await websocket.send_text(f"cfg,{audio_streamer.sample_rate},{audio_streamer.channels},16")

        async def stream_audio_loop():
            try:
                while True:
                    chunk = await audio_queue.get()
                    if chunk:
                        transport = getattr(websocket, "_transport", None)
                        if transport and hasattr(transport, "get_write_buffer_size"):
                            try:
                                if transport.get_write_buffer_size() > 32768:
                                    # Drop backlogged chunk to preserve real-time low latency
                                    continue
                            except Exception:
                                pass
                        await websocket.send_bytes(chunk)
            except (asyncio.CancelledError, WebSocketDisconnect, Exception):
                pass

        async def receive_loop():
            try:
                while True:
                    data = await websocket.receive_text()
                    if data == "ping":
                        await websocket.send_text("pong")
            except (asyncio.CancelledError, WebSocketDisconnect, Exception):
                pass

        stream_task = asyncio.create_task(stream_audio_loop())
        receive_task = asyncio.create_task(receive_loop())

        done, pending = await asyncio.wait(
            [stream_task, receive_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for t in pending:
            t.cancel()

    except Exception:
        pass
    finally:
        audio_streamer.unregister_subscriber(audio_queue)
        try:
            await websocket.close()
        except Exception:
            pass


@app.get("/api/audio/stream")
@app.get("/api/audio/stream.wav")
async def stream_audio_http():
    """Continuous low-latency WAV stream for HTML5 <audio> elements and fallback players."""
    audio_queue = audio_streamer.register_subscriber()
    header = audio_streamer.create_wav_header(
        sample_rate=audio_streamer.sample_rate,
        channels=audio_streamer.channels,
        bits_per_sample=16,
    )

    async def wav_generator():
        yield header
        try:
            while True:
                chunk = await audio_queue.get()
                if chunk:
                    yield chunk
        except asyncio.CancelledError:
            pass
        finally:
            audio_streamer.unregister_subscriber(audio_queue)

    return StreamingResponse(
        wav_generator(),
        media_type="audio/wav",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "keep-alive",
        },
    )


@app.get("/api/audio/status")
async def get_audio_status():
    return {
        "running": audio_streamer.is_running,
        "sample_rate": audio_streamer.sample_rate,
        "channels": audio_streamer.channels,
        "active_listeners": audio_streamer.active_listeners,
        "device": audio_streamer.loopback_device.get("name", "Default Speaker Loopback") if audio_streamer.loopback_device else "Default Speaker",
    }


# Mount static assets
if os.path.exists(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


def banner():
    if sys.stdout is None:
        return
    print(Fore.CYAN + "=" * 60)
    print(Fore.YELLOW + Style.BRIGHT + "  [+] PCDECK PRO 2.1 - WIRELESS PC TOUCH DECK & STREAMER")
    print(Fore.CYAN + "=" * 60)
    print(f"{Fore.GREEN}  [+] Local LAN IP   : {Fore.WHITE}{LOCAL_IP}")
    print(f"{Fore.GREEN}  [+] Server Port    : {Fore.WHITE}{SERVER_PORT}")
    print(f"{Fore.GREEN}  [+] Web URL        : {Fore.CYAN}{SERVER_URL}")
    print(f"{Fore.GREEN}  [+] Transfers Dir  : {Fore.YELLOW}{TRANSFER_DIR}")
    print(f"{Fore.GREEN}  [+] Desktop Hub    : {Fore.CYAN}{SERVER_URL}/desktop")
    print(Fore.CYAN + "-" * 60)
    print(Fore.YELLOW + "  Scan QR code in the Mobile App to Connect:")
    try:
        print_ascii_qr(f"{SERVER_URL}/connect")
    except Exception:
        pass
    print(Fore.CYAN + "=" * 60)
    print(Fore.WHITE + "  Press Ctrl+C to stop the server.\n")


def is_admin() -> bool:
    if sys.platform != "win32":
        return True
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def elevate_if_needed():
    if sys.platform == "win32" and not is_admin():
        try:
            import ctypes
            target = sys.executable
            script = os.path.abspath(sys.argv[0])
            args = [f'"{script}"'] + [f'"{arg}"' for arg in sys.argv[1:]]
            params = " ".join(args)
            ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", target, params, None, 1)
            if ret > 32:
                sys.exit(0)
        except Exception:
            pass


def run_server():
    elevate_if_needed()
    banner()
    config = Config(
        app=app,
        host="0.0.0.0",
        port=SERVER_PORT,
        log_level="error",
        access_log=False,
        loop="asyncio",
    )
    server = Server(config)
    server.run()


if __name__ == "__main__":
    run_server()
