"""
High-Performance Screen Streaming Engine for PCDeck Pro
Captures the PC desktop with ultra-low latency 64-bit Win32 GDI and turbo JPEG compression.
"""

import io
import os
import sys
import time
import threading
from typing import Optional, Tuple
from PIL import Image

# ---------------------------------------------------------------------------
# High-Performance 64-Bit Win32 GDI Capture Setup
# ---------------------------------------------------------------------------
_USE_WIN32_GDI = sys.platform == "win32"

if _USE_WIN32_GDI:
    import ctypes
    from ctypes import wintypes, c_void_p, c_int, byref, Structure, sizeof

    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    # Enable Per-Monitor DPI Awareness
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass

    user32.OpenInputDesktop.restype = wintypes.HANDLE
    user32.OpenInputDesktop.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]

    user32.SetThreadDesktop.restype = wintypes.BOOL
    user32.SetThreadDesktop.argtypes = [wintypes.HANDLE]

    def _attach_desktop():
        try:
            hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
            if hdesk:
                user32.SetThreadDesktop(hdesk)
        except Exception:
            pass

    # Declare exact 64-bit types to prevent pointer sign-extension corruption
    user32.GetDC.restype = c_void_p
    user32.GetDC.argtypes = [c_void_p]

    user32.ReleaseDC.restype = c_int
    user32.ReleaseDC.argtypes = [c_void_p, c_void_p]

    user32.GetDesktopWindow.restype = c_void_p

    user32.GetSystemMetrics.restype = c_int
    user32.GetSystemMetrics.argtypes = [c_int]

    gdi32.CreateCompatibleDC.restype = c_void_p
    gdi32.CreateCompatibleDC.argtypes = [c_void_p]

    gdi32.CreateCompatibleBitmap.restype = c_void_p
    gdi32.CreateCompatibleBitmap.argtypes = [c_void_p, c_int, c_int]

    gdi32.SelectObject.restype = c_void_p
    gdi32.SelectObject.argtypes = [c_void_p, c_void_p]

    gdi32.BitBlt.restype = c_int
    gdi32.BitBlt.argtypes = [c_void_p, c_int, c_int, c_int, c_int, c_void_p, c_int, c_int, wintypes.DWORD]

    gdi32.DeleteDC.restype = c_int
    gdi32.DeleteDC.argtypes = [c_void_p]

    gdi32.DeleteObject.restype = c_int
    gdi32.DeleteObject.argtypes = [c_void_p]

    gdi32.GetDIBits.restype = c_int
    gdi32.GetDIBits.argtypes = [c_void_p, c_void_p, wintypes.UINT, wintypes.UINT, c_void_p, c_void_p, wintypes.UINT]

    class BITMAPINFOHEADER(Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD),
            ("biWidth", wintypes.LONG),
            ("biHeight", wintypes.LONG),
            ("biPlanes", wintypes.WORD),
            ("biBitCount", wintypes.WORD),
            ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD),
            ("biXPelsPerMeter", wintypes.LONG),
            ("biYPelsPerMeter", wintypes.LONG),
            ("biClrUsed", wintypes.DWORD),
            ("biClrImportant", wintypes.DWORD),
        ]

    class POINT(Structure):
        _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

    class CURSORINFO(Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("flags", wintypes.DWORD),
            ("hCursor", wintypes.HANDLE),
            ("ptScreenPos", POINT),
        ]

    class ICONINFO(Structure):
        _fields_ = [
            ("fIcon", wintypes.BOOL),
            ("xHotspot", wintypes.DWORD),
            ("yHotspot", wintypes.DWORD),
            ("hbmMask", wintypes.HBITMAP),
            ("hbmColor", wintypes.HBITMAP),
        ]

    user32.GetCursorInfo.restype = wintypes.BOOL
    user32.GetCursorInfo.argtypes = [ctypes.POINTER(CURSORINFO)]

    user32.GetIconInfo.restype = wintypes.BOOL
    user32.GetIconInfo.argtypes = [wintypes.HICON, ctypes.POINTER(ICONINFO)]

    user32.DrawIconEx.restype = wintypes.BOOL
    user32.DrawIconEx.argtypes = [
        c_void_p, c_int, c_int, wintypes.HICON, c_int, c_int,
        wintypes.UINT, c_void_p, wintypes.UINT
    ]
else:
    def _attach_desktop():
        pass


class ScreenStreamer:
    """Manages high-speed desktop frame grabbing and JPEG compression."""

    def __init__(self):
        self._lock = threading.Lock()
        self.running = False
        self._latest_jpeg: Optional[bytes] = None
        self._width: int = 1920
        self._height: int = 1080
        self._monitor_idx: int = 1
        self.quality: int = 90
        self.scale: float = 1.0
        self.fps_limit: int = 30
        self._thread: Optional[threading.Thread] = None
        self._generation: int = 0
        self._frame_id: int = 0
        self._consumers: int = 0

    @property
    def monitor_info(self) -> dict:
        if _USE_WIN32_GDI:
            _attach_desktop()
            w = user32.GetSystemMetrics(0)
            h = user32.GetSystemMetrics(1)
            return {"width": w, "height": h, "top": 0, "left": 0, "count": 1}
        else:
            import mss
            sct = mss.mss()
            mon = sct.monitors[min(self._monitor_idx, len(sct.monitors) - 1)]
            return {
                "width": mon["width"],
                "height": mon["height"],
                "top": mon["top"],
                "left": mon["left"],
                "count": len(sct.monitors) - 1,
            }

    def grab_single_frame(self, quality: int = 50, scale: float = 0.75) -> Tuple[bytes, int, int]:
        """Capture and encode a single frame on demand."""
        if _USE_WIN32_GDI:
            _attach_desktop()
            w = user32.GetSystemMetrics(0)
            h = user32.GetSystemMetrics(1)
            hdc_screen = user32.GetDC(None)
            hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
            hbm = gdi32.CreateCompatibleBitmap(hdc_screen, w, h)
            old_bm = gdi32.SelectObject(hdc_mem, hbm)

            # SRCCOPY (0x00CC0020) - Fast hardware GPU blit without CAPTUREBLT to prevent PC cursor flicker
            gdi32.BitBlt(hdc_mem, 0, 0, w, h, hdc_screen, 0, 0, 0x00CC0020)

            # Draw cursor into stream image
            try:
                ci = CURSORINFO()
                ci.cbSize = sizeof(CURSORINFO)
                if user32.GetCursorInfo(byref(ci)) and (ci.flags & 1) and ci.hCursor:
                    ii = ICONINFO()
                    if user32.GetIconInfo(ci.hCursor, byref(ii)):
                        cx = ci.ptScreenPos.x - ii.xHotspot
                        cy = ci.ptScreenPos.y - ii.yHotspot
                        user32.DrawIconEx(hdc_mem, cx, cy, ci.hCursor, 0, 0, 0, None, 3)
                        if ii.hbmMask:
                            gdi32.DeleteObject(ii.hbmMask)
                        if ii.hbmColor:
                            gdi32.DeleteObject(ii.hbmColor)
            except Exception:
                pass

            bmi = BITMAPINFOHEADER()
            bmi.biSize = sizeof(BITMAPINFOHEADER)
            bmi.biWidth = w
            bmi.biHeight = -h  # top-down
            bmi.biPlanes = 1
            bmi.biBitCount = 32
            bmi.biCompression = 0

            buf = (ctypes.c_char * (w * h * 4))()
            gdi32.GetDIBits(hdc_mem, hbm, 0, h, buf, byref(bmi), 0)

            img = Image.frombuffer("RGB", (w, h), buf, "raw", "BGRX", 0, 1)

            gdi32.SelectObject(hdc_mem, old_bm)
            gdi32.DeleteObject(hbm)
            gdi32.DeleteDC(hdc_mem)
            user32.ReleaseDC(None, hdc_screen)

            orig_w, orig_h = w, h
            if 0.1 < scale < 0.99:
                target_w = int(orig_w * scale)
                target_h = int(orig_h * scale)
                img = img.resize((target_w, target_h), Image.Resampling.BILINEAR)

            out = io.BytesIO()
            img.save(out, format="JPEG", quality=quality, subsampling=1, optimize=False)
            return out.getvalue(), orig_w, orig_h
        else:
            import mss
            sct = mss.mss()
            mon = sct.monitors[min(self._monitor_idx, len(sct.monitors) - 1)]
            shot = sct.grab(mon)
            img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
            orig_w, orig_h = shot.size
            if 0.1 < scale < 0.99:
                target_w = int(orig_w * scale)
                target_h = int(orig_h * scale)
                img = img.resize((target_w, target_h), Image.Resampling.BILINEAR)
            out = io.BytesIO()
            img.save(out, format="JPEG", quality=quality, subsampling=1, optimize=False)
            return out.getvalue(), orig_w, orig_h

    def _capture_loop(self, generation: int):
        """High-speed desktop capture loop with zero frame stalls."""
        if _USE_WIN32_GDI:
            self._capture_loop_win32(generation)
        else:
            self._capture_loop_mss(generation)

    def _capture_loop_win32(self, generation: int):
        _attach_desktop()
        hdc_screen = None
        hdc_mem = None
        hbm = None
        old_bm = None
        cur_w, cur_h = 0, 0
        cur_target_w, cur_target_h = 0, 0
        buf = None
        bmi = None
        prev_jpeg: Optional[bytes] = None

        try:
            while self.running and self._generation == generation:
                start_t = time.time()
                try:
                    w = user32.GetSystemMetrics(0)
                    h = user32.GetSystemMetrics(1)
                    target_w = int(w * self.scale) if 0.1 < self.scale < 0.99 else w
                    target_h = int(h * self.scale) if 0.1 < self.scale < 0.99 else h

                    if w != cur_w or h != cur_h or target_w != cur_target_w or target_h != cur_target_h or hdc_mem is None:
                        # Re-allocate GDI surfaces on resolution change
                        if hdc_mem:
                            try:
                                gdi32.SelectObject(hdc_mem, old_bm)
                                gdi32.DeleteObject(hbm)
                                gdi32.DeleteDC(hdc_mem)
                                user32.ReleaseDC(None, hdc_screen)
                            except Exception:
                                pass

                        cur_w, cur_h = w, h
                        cur_target_w, cur_target_h = target_w, target_h
                        self._width, self._height = w, h
                        hdc_screen = user32.GetDC(None)
                        hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
                        hbm = gdi32.CreateCompatibleBitmap(hdc_screen, target_w, target_h)
                        old_bm = gdi32.SelectObject(hdc_mem, hbm)
                        # STRETCH_HALFTONE (4) provides crisp high-quality anti-aliasing for text
                        gdi32.SetStretchBltMode(hdc_mem, 4)

                        bmi = BITMAPINFOHEADER()
                        bmi.biSize = sizeof(BITMAPINFOHEADER)
                        bmi.biWidth = target_w
                        bmi.biHeight = -target_h  # top-down DIB
                        bmi.biPlanes = 1
                        bmi.biBitCount = 32
                        bmi.biCompression = 0
                        buf = (ctypes.c_char * (target_w * target_h * 4))()

                    # Blit/Stretch desktop directly to target memory DC using zero-flicker SRCCOPY (0x00CC0020)
                    if target_w != w or target_h != h:
                        gdi32.StretchBlt(hdc_mem, 0, 0, target_w, target_h, hdc_screen, 0, 0, w, h, 0x00CC0020)
                    else:
                        gdi32.BitBlt(hdc_mem, 0, 0, w, h, hdc_screen, 0, 0, 0x00CC0020)

                    # Smoothly draw the mouse cursor into the offscreen buffer with zero PC physical monitor flicker
                    try:
                        ci = CURSORINFO()
                        ci.cbSize = sizeof(CURSORINFO)
                        if user32.GetCursorInfo(byref(ci)) and (ci.flags & 1) and ci.hCursor:
                            ii = ICONINFO()
                            if user32.GetIconInfo(ci.hCursor, byref(ii)):
                                cx = ci.ptScreenPos.x - ii.xHotspot
                                cy = ci.ptScreenPos.y - ii.yHotspot
                                if target_w != w:
                                    cx = int(cx * (target_w / w))
                                    cy = int(cy * (target_h / h))
                                user32.DrawIconEx(hdc_mem, cx, cy, ci.hCursor, 0, 0, 0, None, 3)
                                if ii.hbmMask:
                                    gdi32.DeleteObject(ii.hbmMask)
                                if ii.hbmColor:
                                    gdi32.DeleteObject(ii.hbmColor)
                    except Exception:
                        pass

                    gdi32.GetDIBits(hdc_mem, hbm, 0, target_h, buf, byref(bmi), 0)

                    img = Image.frombuffer("RGB", (target_w, target_h), buf, "raw", "BGRX", 0, 1)

                    out = io.BytesIO()
                    # subsampling=0 (4:4:4 RGB) ensures razor-sharp text & UI fonts with ultra-fast encoding
                    img.save(out, format="JPEG", quality=self.quality, subsampling=0, optimize=False)
                    jpeg = out.getvalue()

                    with self._lock:
                        if self._generation != generation:
                            break
                        self._latest_jpeg = jpeg
                        self._frame_id += 1
                    prev_jpeg = jpeg

                except Exception as e:
                    time.sleep(0.05)

                frame_interval = 1.0 / max(1, self.fps_limit)
                elapsed = time.time() - start_t
                sleep_time = frame_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

        finally:
            with self._lock:
                if self._generation == generation:
                    self.running = False
            if hdc_mem:
                try:
                    gdi32.SelectObject(hdc_mem, old_bm)
                    gdi32.DeleteObject(hbm)
                    gdi32.DeleteDC(hdc_mem)
                    user32.ReleaseDC(None, hdc_screen)
                except Exception:
                    pass

    def _capture_loop_mss(self, generation: int):
        import mss
        sct = None
        prev_jpeg: Optional[bytes] = None

        try:
            while self.running and self._generation == generation:
                start_t = time.time()
                try:
                    if sct is None:
                        sct = mss.mss()
                    mon = sct.monitors[min(self._monitor_idx, len(sct.monitors) - 1)]
                    shot = sct.grab(mon)

                    img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
                    orig_w, orig_h = shot.size
                    self._width = orig_w
                    self._height = orig_h

                    if 0.1 < self.scale < 0.99:
                        target_w = int(orig_w * self.scale)
                        target_h = int(orig_h * self.scale)
                        img = img.resize((target_w, target_h), Image.Resampling.BILINEAR)

                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=self.quality, subsampling=0, optimize=False)
                    jpeg = buf.getvalue()

                    with self._lock:
                        if self._generation != generation:
                            break
                        self._latest_jpeg = jpeg
                        if jpeg != prev_jpeg:
                            self._frame_id += 1
                    prev_jpeg = jpeg

                except Exception:
                    try:
                        if sct:
                            sct.close()
                    except Exception:
                        pass
                    sct = None
                    time.sleep(0.05)

                frame_interval = 1.0 / max(1, self.fps_limit)
                elapsed = time.time() - start_t
                sleep_time = frame_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
        finally:
            with self._lock:
                if self._generation == generation:
                    self.running = False
            if sct:
                try:
                    sct.close()
                except Exception:
                    pass

    def _start_locked(self):
        """Starts the capture thread. Caller must hold self._lock."""
        if hasattr(self, "_stop_timer") and self._stop_timer:
            self._stop_timer.cancel()
            self._stop_timer = None
        if not self.running or self._thread is None or not self._thread.is_alive():
            self._generation += 1
            generation = self._generation
            self.running = True
            self._thread = threading.Thread(
                target=self._capture_loop, args=(generation,), daemon=True
            )
            self._thread.start()

    def _shutdown_locked(self):
        """Retires the current capture session. Caller must hold self._lock."""
        if hasattr(self, "_stop_timer") and self._stop_timer:
            self._stop_timer.cancel()
            self._stop_timer = None
        self.running = False
        self._generation += 1
        thread = self._thread
        self._thread = None
        self._latest_jpeg = None
        return thread

    @staticmethod
    def _join(thread):
        if thread and thread is not threading.current_thread():
            try:
                thread.join(timeout=0.3)
            except Exception:
                pass

    def acquire(self):
        """Registers a viewer and guarantees capture is running immediately."""
        with self._lock:
            if hasattr(self, "_stop_timer") and self._stop_timer:
                self._stop_timer.cancel()
                self._stop_timer = None
            self._consumers += 1
            self._start_locked()

    def release(self):
        """Unregisters a viewer with a graceful 4s warm cooldown instead of immediate thread kill."""
        with self._lock:
            self._consumers = max(0, self._consumers - 1)
            if self._consumers > 0:
                return
            # Keep capture engine warm for 4 seconds in case client is switching tabs or reconnecting
            if hasattr(self, "_stop_timer") and self._stop_timer:
                self._stop_timer.cancel()
            def _delayed_stop():
                with self._lock:
                    if self._consumers == 0:
                        self._shutdown_locked()
            self._stop_timer = threading.Timer(4.0, _delayed_stop)
            self._stop_timer.daemon = True
            self._stop_timer.start()

    def start(self):
        """Start background capture thread."""
        with self._lock:
            self._start_locked()

    def stop(self):
        """Hard stop: drops the stale frame so no client is served a frozen desktop."""
        with self._lock:
            self._consumers = 0
            thread = self._shutdown_locked()
        self._join(thread)

    def get_latest_jpeg(self) -> Optional[bytes]:
        with self._lock:
            return self._latest_jpeg

    def get_latest_frame(self) -> Tuple[Optional[bytes], int]:
        """Returns the newest frame together with its id, so callers can skip resends."""
        with self._lock:
            return self._latest_jpeg, self._frame_id


# Singleton streamer instance
streamer = ScreenStreamer()
