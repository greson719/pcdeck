"""
PCDeck Pro - Wireless HD Webcam Virtual Camera Streamer
Receives video frames from phone camera over WebSocket (/ws/cam) and feeds them into
the Windows DirectShow / Media Foundation virtual camera device via pyvirtualcam.
"""

import io
import os
import subprocess
import sys
import threading
import time
from typing import Optional, Tuple
from PIL import Image, ImageDraw

try:
    import pyvirtualcam
    _HAS_PYVIRTUALCAM = True
except ImportError:
    pyvirtualcam = None
    _HAS_PYVIRTUALCAM = False

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    np = None
    _HAS_NUMPY = False

try:
    import simplejpeg
    _HAS_SIMPLEJPEG = True
except ImportError:
    simplejpeg = None
    _HAS_SIMPLEJPEG = False


def is_webcam_driver_installed() -> bool:
    """
    Checks if a virtual camera driver (OBS Virtual Camera or UnityCapture)
    is installed and functional on the host.
    """
    if sys.platform != "win32":
        return os.path.exists("/dev/video0") or os.path.exists("/sys/module/v4l2loopback")

    # 1. Fast DirectShow Device Registry Check (instant, un-cached)
    try:
        import winreg
        clsid_path = r"CLSID\{860BB310-5D01-11D0-BD3B-00A0C911CE86}\Instance"
        for root_key in (winreg.HKEY_CLASSES_ROOT, winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                with winreg.OpenKey(root_key, clsid_path, 0, winreg.KEY_READ) as key:
                    count, _, _ = winreg.QueryInfoKey(key)
                    for i in range(count):
                        sub_name = winreg.EnumKey(key, i)
                        try:
                            with winreg.OpenKey(key, sub_name) as sub_key:
                                friendly_name, _ = winreg.QueryValueEx(sub_key, "FriendlyName")
                                fn_lower = friendly_name.lower()
                                if any(k in fn_lower for k in ("obs virtual", "unity", "virtual camera", "droidcam", "video capture")):
                                    return True
                        except Exception:
                            pass
            except Exception:
                pass
    except Exception:
        pass

    # 2. PyVirtualCam functional test if available
    if _HAS_PYVIRTUALCAM:
        try:
            cam = pyvirtualcam.Camera(width=640, height=480, fps=30)
            cam.close()
            return True
        except Exception:
            pass

    return False


def get_drivers_dir() -> str:
    """Returns absolute path to the drivers directory (handles dev & PyInstaller frozen modes)."""
    if getattr(sys, "frozen", False):
        meipass_drivers = os.path.join(getattr(sys, "_MEIPASS", ""), "drivers")
        if os.path.exists(meipass_drivers):
            return meipass_drivers
        exe_drivers = os.path.join(os.path.dirname(sys.executable), "drivers")
        if os.path.exists(exe_drivers):
            return exe_drivers
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "drivers")


def has_internet_connection() -> bool:
    """Checks if host PC has an active internet connection."""
    import socket
    for host in [("1.1.1.1", 53), ("8.8.8.8", 53)]:
        try:
            socket.create_connection(host, timeout=1.5)
            return True
        except OSError:
            pass
    return False


def install_webcam_driver_silently(installer_path: Optional[str] = None) -> Tuple[bool, str]:
    """
    Installs or registers the virtual webcam driver on Windows.
    Offline-first: uses locally bundled driver package if present.
    Returns (success: bool, message: str).
    """
    if sys.platform != "win32":
        return False, "Virtual webcam driver installation is only supported on Windows."

    drivers_dir = get_drivers_dir()
    dll64 = installer_path or os.path.join(drivers_dir, "UnityCaptureFilter64.dll")
    dll32 = os.path.join(drivers_dir, "UnityCaptureFilter32.dll")

    # 1. Offline Install: Check for bundled UnityCapture DirectShow Filter DLL
    if os.path.exists(dll64):
        try:
            import ctypes
            # Register 64-bit and 32-bit filters
            args = f'/s "{dll64}"'
            if os.path.exists(dll32):
                args += f' /s "{dll32}"'

            ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", "regsvr32.exe", args, None, 1)
            if ret > 32:
                return True, "Offline virtual camera driver installed! Click 'Yes' on the PC permission prompt."
            elif ret == 1223:
                return False, "Installation cancelled: Administrator permission declined on PC."
            else:
                # Fallback to direct subprocess
                proc = subprocess.run(["regsvr32.exe", "/s", dll64], capture_output=True, text=True)
                if proc.returncode == 0:
                    return True, "UnityCapture Virtual Webcam driver registered successfully (Offline)."
                return False, f"regsvr32 returned error code {proc.returncode}"
        except Exception as e:
            return False, f"Driver execution error: {str(e)}"

    # 2. If offline and driver missing, notify user to connect to internet or place driver in drivers/
    if not has_internet_connection():
        return False, "Offline: No internet on PC to download camera driver. Connect to Wi-Fi/Internet, or place UnityCaptureFilter64.dll in PCDeck/drivers/."

    # 3. Online Fallback: Check for winget install of OBS Virtual Camera
    try:
        proc = subprocess.run(
            ["winget", "install", "--id", "OBSProject.OBSStudio", "-e", "--silent", "--accept-package-agreements", "--accept-source-agreements"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        if proc.returncode == 0:
            return True, "OBS Studio Virtual Camera driver installed successfully."
        else:
            return False, f"Driver package not found and winget returned code {proc.returncode}"
    except Exception as e:
        return False, f"Installation error: {str(e)}"



class CameraStreamer:
    """
    Manages incoming phone camera frames and streams them into a virtual webcam
    device on Windows (OBS, WhatsApp, Discord, Zoom, Teams compatible).
    Maintains a sleek cyber-neon standby loop so DirectShow never drops or shows
    the ugly default driver test patterns ('Unity has not started sending image data').
    """

    def __init__(self, width: int = 1280, height: int = 720, fps: int = 30):
        self.target_width = width
        self.target_height = height
        self.target_fps = fps
        self.is_active = False
        self.is_streaming_live = False
        self.flip_horizontal = False
        self.cam_device = None
        self.lock = threading.Lock()
        self.last_frame_time = 0.0
        self.frame_count = 0
        self._standby_frame = None
        self._latest_live_frame = None
        self._worker_thread = None
        self._running = True

    def set_flip_horizontal(self, flip: bool):
        """Toggle horizontal mirroring on or off."""
        self.flip_horizontal = bool(flip)
        print(f"[CameraStreamer] Flip horizontal: {self.flip_horizontal}")

    def _get_standby_frame(self) -> Optional[np.ndarray]:
        if self._standby_frame is None or self._standby_frame.shape[:2] != (self.target_height, self.target_width):
            self._standby_frame = self._render_standby_frame(self.target_width, self.target_height)
        return self._standby_frame

    def _render_standby_frame(self, w: int, h: int) -> np.ndarray:
        img = Image.new("RGB", (w, h), (9, 13, 22))
        draw = ImageDraw.Draw(img)
        # Cyber-neon outer border
        draw.rectangle([(20, 20), (w - 20, h - 20)], outline=(0, 240, 255), width=2)
        # Subtle inner border
        draw.rectangle([(24, 24), (w - 24, h - 24)], outline=(20, 35, 55), width=1)
        # Glowing badge
        badge_w, badge_h = min(420, w - 80), 50
        bx0 = (w - badge_w) // 2
        by0 = h // 2 - 90
        draw.rectangle([(bx0, by0), (bx0 + badge_w, by0 + badge_h)], fill=(0, 240, 255))
        draw.text((w // 2, by0 + badge_h // 2), "PCDECK WIRELESS HD WEBCAM", fill=(0, 0, 0), anchor="mm")
        # Subtitle & instructions
        draw.text((w // 2, h // 2 + 10), "STANDBY -- READY FOR CONNECTION", fill=(0, 240, 255), anchor="mm")
        draw.text((w // 2, h // 2 + 55), "Tap 'Start Webcam' in the PCDeck phone app to stream live video", fill=(160, 175, 195), anchor="mm")
        # Bottom status
        draw.text((w // 2, h - 45), "DirectShow Virtual Device Active -- WhatsApp / OBS / Zoom / Teams", fill=(70, 95, 125), anchor="mm")
        return np.ascontiguousarray(np.array(img, dtype=np.uint8))

    def _ensure_device_open(self) -> bool:
        if self.cam_device is not None:
            return True
        if not _HAS_PYVIRTUALCAM:
            return False
        try:
            self.cam_device = pyvirtualcam.Camera(
                width=self.target_width,
                height=self.target_height,
                fps=self.target_fps,
                fmt=pyvirtualcam.PixelFormat.RGB
            )
            print(f"[CameraStreamer] Virtual webcam open: {self.cam_device.device} ({self.target_width}x{self.target_height} @ {self.target_fps}fps)")
            return True
        except Exception:
            return False

    def start_standby(self):
        """Initializes virtual camera lazily on-demand when live stream is requested."""
        pass

    def start_camera(self, width: int = 1280, height: int = 720, fps: int = 30) -> bool:
        """Starts the virtual camera device and live streaming mode."""
        with self.lock:
            self.target_width = width
            self.target_height = height
            self.target_fps = fps
            self.is_active = True
            self.is_streaming_live = True
            self._standby_frame = None

            if not _HAS_PYVIRTUALCAM:
                return True

            if self.cam_device and (self.cam_device.width != width or self.cam_device.height != height):
                try:
                    self.cam_device.close()
                except Exception:
                    pass
                self.cam_device = None

            self._ensure_device_open()
            self._start_worker()
            return True

    def stop_camera(self):
        """Called when phone stops streaming. Puts camera worker to sleep to save Wi-Fi airtime and CPU."""
        with self.lock:
            self.is_streaming_live = False
            self._latest_live_frame = None
            self.last_frame_time = 0.0
            self._running = False
            if self.cam_device:
                try:
                    self.cam_device.close()
                except Exception:
                    pass
                self.cam_device = None
            print("[CameraStreamer] Phone stopped streaming; virtual camera put to sleep.", flush=True)

    def close_device(self):
        """Full shutdown of camera hardware sink."""
        self._running = False
        with self.lock:
            self.is_active = False
            self.is_streaming_live = False
            self._latest_live_frame = None
            if self.cam_device:
                try:
                    self.cam_device.close()
                except Exception:
                    pass
                self.cam_device = None
            print("[CameraStreamer] Virtual camera closed.")

    def _start_worker(self):
        if self._worker_thread and self._worker_thread.is_alive():
            return
        self._running = True
        self._worker_thread = threading.Thread(target=self._camera_pump_loop, daemon=True, name="PCDeckCamPump")
        self._worker_thread.start()

    def _camera_pump_loop(self):
        """
        Sole thread responsible for transmitting frames into pyvirtualcam at exact hardware timing.
        Guarantees rock-solid 30 FPS output with zero race conditions and zero event-loop blocking.
        """
        while self._running:
            try:
                frame_to_send = None
                with self.lock:
                    if not self._running:
                        break
                    # If live frame received within the last 1.0s, output live frame
                    if (time.time() - self.last_frame_time) < 1.0 and self._latest_live_frame is not None:
                        frame_to_send = self._latest_live_frame
                    else:
                        frame_to_send = self._get_standby_frame()

                if frame_to_send is not None and self._ensure_device_open() and self.cam_device:
                    self.cam_device.send(frame_to_send)
                    try:
                        self.cam_device.sleep_until_next_frame()
                    except Exception:
                        time.sleep(1.0 / self.target_fps)
                else:
                    time.sleep(0.033)
            except Exception:
                time.sleep(0.033)

    def push_frame_bytes(self, image_bytes: bytes):
        """
        Non-blocking ingestion of JPEG frame from phone.
        Decodes, applies aspect-preserving crop (no stretching!), and updates live frame pointer.
        """
        if not image_bytes:
            return

        self.frame_count += 1
        self.is_active = True
        self.is_streaming_live = True

        if not _HAS_NUMPY:
            return

        try:
            frame_arr = None
            # 1. Ultra-fast libjpeg-turbo decode (<1ms)
            if _HAS_SIMPLEJPEG:
                try:
                    frame_arr = simplejpeg.decode_jpeg(image_bytes, colorspace="RGB")
                except Exception:
                    frame_arr = None

            # 2. Fallback PIL decode if simplejpeg failed
            if frame_arr is None:
                img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                frame_arr = np.array(img, dtype=np.uint8)

            h, w = frame_arr.shape[:2]

            # 3. Aspect-Ratio Preserving Fit (Pillarbox/Letterbox - NO EXTREME ZOOM, NO STRETCHING)
            target_aspect = self.target_width / self.target_height
            frame_aspect = w / h

            if abs(frame_aspect - target_aspect) > 0.02:
                # Black background canvas
                canvas = np.zeros((self.target_height, self.target_width, 3), dtype=np.uint8)
                if frame_aspect < target_aspect:
                    # Portrait phone stream: fit full height, pillarbox sides
                    new_h = self.target_height
                    new_w = max(1, int(new_h * frame_aspect))
                    pil_sub = Image.fromarray(frame_arr).resize((new_w, new_h), Image.Resampling.BILINEAR)
                    x0 = (self.target_width - new_w) // 2
                    canvas[:, x0:x0 + new_w] = np.array(pil_sub, dtype=np.uint8)
                else:
                    # Extra-wide stream: fit full width, letterbox top/bottom
                    new_w = self.target_width
                    new_h = max(1, int(new_w / frame_aspect))
                    pil_sub = Image.fromarray(frame_arr).resize((new_w, new_h), Image.Resampling.BILINEAR)
                    y0 = (self.target_height - new_h) // 2
                    canvas[y0:y0 + new_h, :] = np.array(pil_sub, dtype=np.uint8)
                frame_arr = canvas
            elif frame_arr.shape[:2] != (self.target_height, self.target_width):
                pil_img = Image.fromarray(frame_arr)
                pil_img = pil_img.resize((self.target_width, self.target_height), Image.Resampling.BILINEAR)
                frame_arr = np.array(pil_img, dtype=np.uint8)

            # 5. Optional Horizontal Flip / Mirroring
            if self.flip_horizontal:
                frame_arr = np.fliplr(frame_arr)

            # Contiguous memory layout
            frame_arr = np.ascontiguousarray(frame_arr, dtype=np.uint8)

            # Update live frame pointer (atomic assignment in Python GIL)
            self._latest_live_frame = frame_arr
            self.last_frame_time = time.time()

        except Exception:
            pass


camera_streamer = CameraStreamer()
