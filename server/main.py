"""
NeonTrack - High-Performance PC Remote Control Server
FastAPI + Native Win32 Input Simulation + Low-Latency Screen Streaming + Fast File Transfers
"""

import asyncio
import datetime
import email.utils
import io
import math
import os
import re
import socket
import sys
import shutil
import threading
import time
from typing import Optional, Set

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
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("PCDeckPro.NeonMouse.v2026")
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
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
    from server.audio_streamer import audio_streamer
except ImportError:
    try:
        from input_controller import WindowsInputController as InputController
        from screen_streamer import ScreenStreamer
        from audio_streamer import audio_streamer
    except ImportError:
        from .input_controller import WindowsInputController as InputController
        from .screen_streamer import ScreenStreamer
        from .audio_streamer import audio_streamer

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
    """Ensure Windows Defender Firewall allows inbound TCP traffic on port 8000 on Private and Public networks."""
    if sys.platform == "win32":
        try:
            subprocess.run(
                [
                    "netsh", "advfirewall", "firewall", "add", "rule",
                    "name=PCDeck Pro Port 8000", "dir=in", "action=allow",
                    "protocol=TCP", "localport=8000", "profile=any"
                ],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                timeout=4,
            )
        except Exception:
            pass


ensure_windows_firewall_rule()


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
            is_wifi = any(k in iface_lower for k in ["wi-fi", "wlan", "wireless", "hotspot", "802.11"])
            is_eth = any(k in iface_lower for k in ["ethernet", "eth", "lan"]) and not is_vpn

            for snic in nic_addrs:
                if snic.family == socket.AF_INET:
                    ip = snic.address
                    if ip and not ip.startswith("127.") and not ip.startswith("169.254."):
                        # Priority rank: Wi-Fi/Hotspot (0) > Physical Ethernet (1) > Other non-VPN (2) > VPN (3)
                        priority = 3 if is_vpn else (0 if is_wifi else (1 if is_eth else 2))
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
    for target in [("192.168.1.1", 80), ("192.168.43.1", 80), ("192.168.0.1", 80), ("10.0.0.1", 80), ("8.8.8.8", 80), ("1.1.1.1", 80)]:
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


@app.get("/api/info")
async def get_info():
    """Return server system info and connection state."""
    cur_x, cur_y = controller.get_cursor_pos()
    mon = streamer.monitor_info
    live_ip = get_local_ip()
    return {
        "status": "online",
        "ip": live_ip,
        "port": SERVER_PORT,
        "url": f"http://{live_ip}:{SERVER_PORT}",
        "transfer_dir": TRANSFER_DIR,
        "clients_connected": len(active_connections) + len(screen_connections),
        "screen": {
            "width": mon["width"],
            "height": mon["height"],
            "monitors": mon["count"],
        },
        "cursor": {"x": cur_x, "y": cur_y},
    }


@app.get("/api/qr")
async def get_qr():
    """Serve the connection QR code as a PNG image."""
    live_ip = get_local_ip()
    img_bytes = generate_qr_image_bytes(f"http://{live_ip}:{SERVER_PORT}")
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
        with open(dest_path, mode, buffering=4194304) as f:
            if offset > 0 and mode == "r+b":
                f.seek(offset)
            async for chunk in request.stream():
                if chunk:
                    f.write(chunk)
                    total_written += len(chunk)
            f.flush()

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
    path: str,
    range_header: Optional[str] = Header(None, alias="Range"),
):
    """Download any specified file from PC to phone with high-speed 1MB chunked streaming and HTTP Range support."""
    if not path or not os.path.exists(path) or not os.path.isfile(path):
        return JSONResponse(status_code=404, content={"error": "File not found"})
    try:
        file_size = os.path.getsize(path)
        clean_filename = os.path.basename(path)

        start = 0
        end = file_size - 1
        status_code = 200

        if isinstance(range_header, str) and range_header.startswith("bytes="):
            parts = range_header.replace("bytes=", "").split("-")
            if parts[0]:
                start = int(parts[0])
            if len(parts) > 1 and parts[1]:
                end = int(parts[1])
            status_code = 206

        content_length = max(0, end - start + 1)

        def file_iterator():
            with open(path, "rb", buffering=4194304) as f:
                if start > 0:
                    f.seek(start)
                remaining = content_length
                chunk_size = 2097152  # 2MB high-throughput chunks
                while remaining > 0:
                    read_len = min(chunk_size, remaining)
                    chunk = f.read(read_len)
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk

        headers = {
            "Content-Length": str(content_length),
            "Content-Disposition": f'attachment; filename="{urllib.parse.quote(clean_filename)}"',
            "Accept-Ranges": "bytes",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "X-Content-Type-Options": "nosniff",
        }

        if status_code == 206:
            headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"

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
    zip_filename = f"NeonTrack_Batch_{timestamp}.zip"

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
    candidates = [
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
    candidates = [
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
async def download_file_legacy(filename: str):
    return await download_any_file(os.path.join(TRANSFER_DIR, os.path.basename(filename)))

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
async def get_connect_gateway():
    """Serve the pairing gateway (Download APK vs Launch Web Remote)."""
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


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main Trackpad and control WebSocket endpoint."""
    await websocket.accept()
    active_connections.add(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            if data.startswith("p,"):
                parts = data.split(",")
                await websocket.send_text(f"pong,{parts[1]}")
            else:
                dispatch_command(data)

    except WebSocketDisconnect:
        active_connections.remove(websocket)
    except Exception as e:
        if websocket in active_connections:
            active_connections.remove(websocket)


@app.websocket("/ws/screen")
async def websocket_screen_endpoint(websocket: WebSocket):
    """Zero-Lag adaptive binary screen streaming & interactive touch display endpoint."""
    await websocket.accept()
    screen_connections.add(websocket)
    streamer.acquire()

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

    async def send_frames():
        last_sent_id = initial_id if initial_jpeg else -1
        last_keepalive_at = time.time()
        loop = asyncio.get_running_loop()
        while True:
            try:
                # Wait for the exact moment a new frame is captured (0ms latency!)
                jpeg, frame_id = await loop.run_in_executor(
                    None, streamer.wait_next_frame, last_sent_id, 0.8
                )
                now = time.time()
                if jpeg and frame_id != last_sent_id:
                    last_sent_id = frame_id
                    last_keepalive_at = now
                    await websocket.send_bytes(jpeg)
                elif (now - last_keepalive_at) > 1.2:
                    last_keepalive_at = now
                    # Lightweight keepalive ping to keep connection and watchdog alive without flooding video pipe
                    await websocket.send_text("h")
            except (asyncio.CancelledError, WebSocketDisconnect, Exception):
                break

    async def receive_cmds():
        try:
            while True:
                data = await websocket.receive_text()
                if data.startswith("cfg,"):
                    parts = data.split(",")
                    if len(parts) >= 4:
                        streamer.quality = max(20, min(100, int(parts[1])))
                        streamer.scale = max(0.3, min(1.0, float(parts[2])))
                        streamer.fps_limit = max(10, min(60, int(parts[3])))
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
        streamer.release()
        try:
            await websocket.close()
        except Exception:
            pass


@app.websocket("/ws/audio")
async def websocket_audio_endpoint(websocket: WebSocket):
    """Ultra-low-latency real-time PCM audio streaming endpoint for mobile phone."""
    await websocket.accept()
    audio_queue = audio_streamer.register_subscriber()

    try:
        # Send audio configuration handshake: "cfg,{sample_rate},{channels},16"
        await websocket.send_text(f"cfg,{audio_streamer.sample_rate},{audio_streamer.channels},16")

        async def stream_audio_loop():
            try:
                while True:
                    chunk = await audio_queue.get()
                    if chunk:
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
    print(Fore.YELLOW + Style.BRIGHT + "  [+] NEONTRACK 2.1 - PC REMOTE CONTROL SERVER")
    print(Fore.CYAN + "=" * 60)
    print(f"{Fore.GREEN}  [+] Local LAN IP   : {Fore.WHITE}{LOCAL_IP}")
    print(f"{Fore.GREEN}  [+] Server Port    : {Fore.WHITE}{SERVER_PORT}")
    print(f"{Fore.GREEN}  [+] Web URL        : {Fore.CYAN}{SERVER_URL}")
    print(f"{Fore.GREEN}  [+] Transfers Dir  : {Fore.YELLOW}{TRANSFER_DIR}")
    print(f"{Fore.GREEN}  [+] Desktop Hub    : {Fore.CYAN}{SERVER_URL}/desktop")
    print(Fore.CYAN + "-" * 60)
    print(Fore.YELLOW + "  Scan QR code in the Mobile App to Connect:")
    try:
        print_ascii_qr(SERVER_URL)
    except Exception:
        pass
    print(Fore.CYAN + "=" * 60)
    print(Fore.WHITE + "  Press Ctrl+C to stop the server.\n")


def run_server():
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
