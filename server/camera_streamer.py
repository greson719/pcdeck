"""
PCDeck Pro - Wireless HD Webcam Virtual Camera Streamer
Receives video frames from phone camera over WebSocket (/ws/cam) and feeds them into
the Windows DirectShow / Media Foundation virtual camera device via pyvirtualcam.
"""

import io
import sys
import threading
import time
from typing import Optional, Tuple
from PIL import Image

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


class CameraStreamer:
    """
    Manages incoming phone camera frames and streams them into a virtual webcam
    device on Windows (OBS, Discord, Zoom, Teams compatible).
    """

    def __init__(self, width: int = 1280, height: int = 720, fps: int = 30):
        self.target_width = width
        self.target_height = height
        self.target_fps = fps
        self.is_active = False
        self.cam_device = None
        self.lock = threading.Lock()
        self.last_frame_time = 0.0
        self.frame_count = 0

    def start_camera(self, width: int = 1280, height: int = 720, fps: int = 30) -> bool:
        """Starts the virtual camera device."""
        with self.lock:
            self.target_width = width
            self.target_height = height
            self.target_fps = fps
            
            if not _HAS_PYVIRTUALCAM:
                print("[CameraStreamer] pyvirtualcam not installed. Frame receiver active (virtual device disabled).")
                self.is_active = True
                return True

            try:
                if self.cam_device:
                    self.cam_device.close()
                self.cam_device = pyvirtualcam.Camera(
                    width=self.target_width,
                    height=self.target_height,
                    fps=self.target_fps,
                    fmt=pyvirtualcam.PixelFormat.RGB
                )
                self.is_active = True
                print(f"[CameraStreamer] Virtual webcam active: {self.cam_device.device} ({width}x{height} @ {fps}fps)")
                return True
            except Exception as e:
                print(f"[CameraStreamer] Could not open virtual camera device ({e}). Ingesting frames in loopback mode.")
                self.is_active = True
                return True

    def stop_camera(self):
        """Stops the virtual camera device."""
        with self.lock:
            self.is_active = False
            if self.cam_device:
                try:
                    self.cam_device.close()
                except Exception:
                    pass
                self.cam_device = None
            print("[CameraStreamer] Virtual camera stopped.")

    def push_frame_bytes(self, image_bytes: bytes):
        """Processes incoming JPEG or raw image frame from phone."""
        if not image_bytes or not self.is_active:
            return

        self.last_frame_time = time.time()
        self.frame_count += 1

        if self.cam_device and _HAS_NUMPY:
            try:
                # Decode JPEG image
                img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                if img.size != (self.target_width, self.target_height):
                    img = img.resize((self.target_width, self.target_height), Image.Resampling.BILINEAR)
                
                frame_arr = np.array(img)
                with self.lock:
                    if self.cam_device:
                        self.cam_device.send(frame_arr)
            except Exception as e:
                pass


camera_streamer = CameraStreamer()
