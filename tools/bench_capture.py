import time
import io
import ctypes
from ctypes import wintypes, c_void_p, c_int, byref, Structure, sizeof
from PIL import Image

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

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

w = user32.GetSystemMetrics(0)
h = user32.GetSystemMetrics(1)

hdc_screen = user32.GetDC(None)
hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
hbm = gdi32.CreateCompatibleBitmap(hdc_screen, w, h)
old_bm = gdi32.SelectObject(hdc_mem, hbm)

bmi = BITMAPINFOHEADER()
bmi.biSize = sizeof(BITMAPINFOHEADER)
bmi.biWidth = w
bmi.biHeight = -h
bmi.biPlanes = 1
bmi.biBitCount = 32
bmi.biCompression = 0
buf = (ctypes.c_char * (w * h * 4))()

print(f"Desktop resolution: {w}x{h}")

# Test 1: BitBlt
t0 = time.perf_counter()
for _ in range(10):
    gdi32.BitBlt(hdc_mem, 0, 0, w, h, hdc_screen, 0, 0, 0x00CC0020)
t_blt = (time.perf_counter() - t0) / 10 * 1000

# Test 2: GetDIBits
t0 = time.perf_counter()
for _ in range(10):
    gdi32.GetDIBits(hdc_mem, hbm, 0, h, buf, byref(bmi), 0)
t_dib = (time.perf_counter() - t0) / 10 * 1000

# Test 3: frombuffer
t0 = time.perf_counter()
for _ in range(10):
    img = Image.frombuffer("RGB", (w, h), buf, "raw", "BGRX", 0, 1)
t_buf = (time.perf_counter() - t0) / 10 * 1000

# Test 4: JPEG encoding across modes
for (q, sub) in [(90, 0), (85, 0), (80, 0), (85, 1), (80, 2), (75, 2)]:
    t0 = time.perf_counter()
    for _ in range(10):
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=q, subsampling=sub, optimize=False)
        val = out.getvalue()
    t_jpg = (time.perf_counter() - t0) / 10 * 1000
    print(f"JPEG Q={q} subsampling={sub}: {t_jpg:.2f} ms, size={len(val)/1024:.1f} KB")

print(f"BitBlt: {t_blt:.2f} ms | GetDIBits: {t_dib:.2f} ms | Image.frombuffer: {t_buf:.2f} ms")

gdi32.SelectObject(hdc_mem, old_bm)
gdi32.DeleteObject(hbm)
gdi32.DeleteDC(hdc_mem)
user32.ReleaseDC(None, hdc_screen)
