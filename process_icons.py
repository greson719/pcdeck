import os
import struct
import io
import numpy as np
from PIL import Image

SOURCE_IMG = "PCDeck_Master_Logo.png"

def write_multires_ico(frames: list[Image.Image], out_path: str):
    """
    Writes a true multi-resolution Windows .ico file containing distinct,
    pre-rendered PNG frames for Windows Explorer, Taskbar, and Titlebar.
    """
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    sorted_frames = sorted(frames, key=lambda f: f.width)
    png_data = []
    for f in sorted_frames:
        buf = io.BytesIO()
        f.save(buf, format="PNG", optimize=True)
        png_data.append(buf.getvalue())

    # ICO Header: idReserved (0), idType (1 = icon), idCount (num images)
    header = struct.pack("<HHH", 0, 1, len(sorted_frames))
    entries = []
    offset = 6 + 16 * len(sorted_frames)

    for f, data in zip(sorted_frames, png_data):
        w = 0 if f.width >= 256 else f.width
        h = 0 if f.height >= 256 else f.height
        # bWidth, bHeight, bColorCount, bReserved, wPlanes, wBitCount, dwBytesInRes, dwImageOffset
        entry = struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(data), offset)
        entries.append(entry)
        offset += len(data)

    with open(out_path, "wb") as fp:
        fp.write(header)
        for e in entries:
            fp.write(e)
        for d in png_data:
            fp.write(d)


def main():
    if not os.path.exists(SOURCE_IMG):
        print(f"Error: {SOURCE_IMG} not found!")
        return

    print(f"[*] Loading pure Photoshop master logo from {SOURCE_IMG} (zero effects, 100% untouched)...")
    master_img = Image.open(SOURCE_IMG).convert("RGBA")

    # 1. Master PNGs
    img_512 = master_img.resize((512, 512), Image.Resampling.LANCZOS)
    img_256 = master_img.resize((256, 256), Image.Resampling.LANCZOS)
    img_192 = master_img.resize((192, 192), Image.Resampling.LANCZOS)

    # Save root copies
    master_img.save("PCDeck_Mouse_Logo.png", format="PNG", optimize=True)
    master_img.save("PCDeck_Logo.png", format="PNG", optimize=True)
    img_512.save("icon.png", format="PNG", optimize=True)
    img_512.save("icon-512.png", format="PNG", optimize=True)

    # Save static, website, and android_app/assets
    dest_folders = ["static", "website", "android_app/assets"]
    for folder in dest_folders:
        os.makedirs(folder, exist_ok=True)
        img_256.save(os.path.join(folder, "PCDeck_Mouse_Logo.png"), format="PNG", optimize=True)
        img_256.save(os.path.join(folder, "PCDeck_Logo.png"), format="PNG", optimize=True)
        img_256.save(os.path.join(folder, "PCDeck_Master_Logo.png"), format="PNG", optimize=True)
        img_256.save(os.path.join(folder, "icon.png"), format="PNG", optimize=True)
        img_512.save(os.path.join(folder, "icon-512.png"), format="PNG", optimize=True)
        img_192.save(os.path.join(folder, "favicon.png"), format="PNG", optimize=True)

    print("[+] Saved pure master PNGs across root, static, website, and android_app/assets")

    # 2. Windows Multi-Resolution ICOs (16, 20, 24, 32, 40, 48, 64, 128, 256)
    ico_sizes = [16, 20, 24, 32, 40, 48, 64, 128, 256]
    frames = [master_img.resize((sz, sz), Image.Resampling.LANCZOS) for sz in ico_sizes]

    ico_destinations = [
        "app_icon.ico",
        "PCDeck.ico",
        "icon.ico",
        "static/favicon.ico",
        "website/favicon.ico",
        "android_app/assets/favicon.ico",
    ]
    for ico_path in ico_destinations:
        write_multires_ico(frames, ico_path)
    print(f"[+] Built multi-resolution ICOs with {len(ico_sizes)} MIP levels for Windows Explorer, Taskbar & Titlebar")

    # 3. Android Adaptive Icon Foreground (432x432 canvas with centered 288x288 master so Android launcher never zooms/crops the logo)
    drawable_dir = os.path.join("android_app", "res", "drawable")
    os.makedirs(drawable_dir, exist_ok=True)
    adaptive_fg = master_img.resize((288, 288), Image.Resampling.LANCZOS)
    canvas_432 = Image.new("RGBA", (432, 432), (0, 0, 0, 0))
    pos = (432 - 288) // 2
    canvas_432.paste(adaptive_fg, (pos, pos), adaptive_fg)
    canvas_432.save(os.path.join(drawable_dir, "ic_launcher_foreground.png"), format="PNG", optimize=True)

    # Legacy fallback drawable (Exact 1:1 natural sizing)
    legacy_drawable = master_img.resize((192, 192), Image.Resampling.LANCZOS)
    legacy_drawable.save(os.path.join(drawable_dir, "ic_launcher.png"), format="PNG", optimize=True)
    print("[+] Saved Android adaptive foreground (exact natural framing, zero zoom) and fallback drawable")

    # 4. Android Mipmap Densities (Exact 1:1 natural sizing)
    densities = {
        "mipmap-mdpi": 48,
        "mipmap-hdpi": 72,
        "mipmap-xhdpi": 96,
        "mipmap-xxhdpi": 144,
        "mipmap-xxxhdpi": 192,
    }

    for folder, size in densities.items():
        dir_path = os.path.join("android_app", "res", folder)
        os.makedirs(dir_path, exist_ok=True)
        icon = master_img.resize((size, size), Image.Resampling.LANCZOS)
        icon.save(os.path.join(dir_path, "ic_launcher.png"), format="PNG", optimize=True)
        icon.save(os.path.join(dir_path, "ic_launcher_round.png"), format="PNG", optimize=True)
        print(f"[+] Generated Android mipmap: {folder} ({size}x{size})")

    print("\n[OK] Photoshop master logo applied everywhere with ZERO zoom and ZERO effects!")


if __name__ == "__main__":
    main()



