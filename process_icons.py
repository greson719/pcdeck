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


from PIL import Image, ImageDraw


def main():
    if not os.path.exists(SOURCE_IMG):
        print(f"Error: {SOURCE_IMG} not found!")
        return

    print(f"[*] Loading master logo from {SOURCE_IMG}...")
    master_raw = Image.open(SOURCE_IMG).convert("RGBA")

    # Apply pure black background (#000000) behind the logo with smooth roll-off
    arr = np.array(master_raw, dtype=np.float32)
    r, g, b, a = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    sat = np.max(arr[:, :, :3], axis=2) - np.min(arr[:, :, :3], axis=2)
    bg_weight = np.clip((35.0 - sat) / 10.0, 0, 1) * np.clip((95.0 - lum) / 15.0, 0, 1)
    out_arr = arr.copy()
    for c in range(3):
        out_arr[:, :, c] = out_arr[:, :, c] * (1.0 - bg_weight)
    out_arr[:, :, 3] = 255.0  # Solid black everywhere behind logo!
    master_img = Image.fromarray(np.clip(out_arr, 0, 255).astype(np.uint8), "RGBA")

    # Create square master image on solid black
    w, h = master_img.size
    max_dim = max(w, h)
    sq_master = Image.new("RGBA", (max_dim, max_dim), (0, 0, 0, 255))
    offset_x = (max_dim - w) // 2
    offset_y = (max_dim - h) // 2
    sq_master.paste(master_img, (offset_x, offset_y))

    # 1. Master PNGs
    img_512 = sq_master.resize((512, 512), Image.Resampling.LANCZOS)
    img_256 = sq_master.resize((256, 256), Image.Resampling.LANCZOS)
    img_192 = sq_master.resize((192, 192), Image.Resampling.LANCZOS)

    # Save root copies (optimized)
    master_img.save("PCDeck_Master_Logo.png", format="PNG", optimize=True)
    img_256.save("PCDeck_Mouse_Logo.png", format="PNG", optimize=True)
    img_256.save("PCDeck_Logo.png", format="PNG", optimize=True)
    img_512.save("icon.png", format="PNG", optimize=True)
    img_512.save("icon-512.png", format="PNG", optimize=True)

    # Save static, website, and android_app/assets
    dest_folders = ["static", "website", "android_app/assets"]
    for folder in dest_folders:
        os.makedirs(folder, exist_ok=True)
        img_256.save(os.path.join(folder, "PCDeck_Mouse_Logo.png"), format="PNG", optimize=True)
        img_256.save(os.path.join(folder, "PCDeck_Logo.png"), format="PNG", optimize=True)
        img_512.save(os.path.join(folder, "PCDeck_Master_Logo.png"), format="PNG", optimize=True)
        img_256.save(os.path.join(folder, "icon.png"), format="PNG", optimize=True)
        img_512.save(os.path.join(folder, "icon-512.png"), format="PNG", optimize=True)
        img_192.save(os.path.join(folder, "favicon.png"), format="PNG", optimize=True)

    print("[+] Saved pure master PNGs across root, static, website, and android_app/assets")

    # 2. Windows Multi-Resolution ICOs (16, 20, 24, 32, 40, 48, 64, 128, 256)
    ico_sizes = [16, 20, 24, 32, 40, 48, 64, 128, 256]
    frames = [sq_master.resize((sz, sz), Image.Resampling.LANCZOS) for sz in ico_sizes]

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

    # 3. Android Adaptive Icon Foreground (432x432 canvas with centered 270x270 master on solid black)
    drawable_dir = os.path.join("android_app", "res", "drawable")
    os.makedirs(drawable_dir, exist_ok=True)
    fg_432 = Image.new("RGBA", (432, 432), (0, 0, 0, 255))
    logo_fit = sq_master.resize((270, 270), Image.Resampling.LANCZOS)
    fg_432.paste(logo_fit, ((432 - 270) // 2, (432 - 270) // 2))
    fg_432.save(os.path.join(drawable_dir, "ic_launcher_foreground.png"), format="PNG", optimize=True)

    # Legacy fallback drawable (192x192 on solid black)
    legacy_drawable = Image.new("RGBA", (192, 192), (0, 0, 0, 255))
    logo_192 = sq_master.resize((154, 154), Image.Resampling.LANCZOS)
    legacy_drawable.paste(logo_192, ((192 - 154) // 2, (192 - 154) // 2))
    legacy_drawable.save(os.path.join(drawable_dir, "ic_launcher.png"), format="PNG", optimize=True)
    print("[+] Saved Android adaptive foreground (solid black background, centered safe zone) and fallback drawable")

    # 4. Android Mipmap Densities (Exact 1:1 natural sizing with solid black background)
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

        # 1. Square icon on solid black:
        sq_icon = Image.new("RGBA", (size, size), (0, 0, 0, 255))
        inner_sz = int(size * 0.80)
        logo_inner = sq_master.resize((inner_sz, inner_sz), Image.Resampling.LANCZOS)
        sq_icon.paste(logo_inner, ((size - inner_sz) // 2, (size - inner_sz) // 2))
        sq_icon.save(os.path.join(dir_path, "ic_launcher.png"), format="PNG", optimize=True)

        # 2. Round icon: Anti-aliased black circular disc with centered logo
        round_icon = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        mask_hires = Image.new("L", (size * 4, size * 4), 0)
        draw = ImageDraw.Draw(mask_hires)
        draw.ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=255)
        mask = mask_hires.resize((size, size), Image.Resampling.LANCZOS)

        round_icon.paste(sq_icon, (0, 0), mask)
        round_icon.save(os.path.join(dir_path, "ic_launcher_round.png"), format="PNG", optimize=True)
        print(f"[+] Generated Android mipmap: {folder} ({size}x{size}) with black background")

    print("\n[OK] Master logo applied everywhere with pure black background and zero transparency artifacts!")


if __name__ == "__main__":
    main()



