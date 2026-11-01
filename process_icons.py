import os
import struct
import io
from PIL import Image, ImageEnhance, ImageDraw
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def write_multires_ico(frames: list[Image.Image], out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sorted_frames = sorted(frames, key=lambda f: f.width)
    png_data = []
    for f in sorted_frames:
        buf = io.BytesIO()
        f.save(buf, format="PNG", optimize=True)
        png_data.append(buf.getvalue())

    header = struct.pack("<HHH", 0, 1, len(sorted_frames))
    entries = []
    offset = 6 + 16 * len(sorted_frames)

    for f, data in zip(sorted_frames, png_data):
        w = 0 if f.width >= 256 else f.width
        h = 0 if f.height >= 256 else f.height
        entry = struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(data), offset)
        entries.append(entry)
        offset += len(data)

    full_data = bytearray()
    full_data.extend(header)
    for e in entries:
        full_data.extend(e)
    for d in png_data:
        full_data.extend(d)

    out_file = Path(out_path)
    try:
        if out_file.exists():
            out_file.unlink()
    except Exception:
        pass
    with open(str(out_file), "wb") as fp:
        fp.write(full_data)
    print(f"  [+] Wrote {out_file.relative_to(ROOT)} ({len(sorted_frames)} frames, {len(full_data)} bytes)")


def main():
    source_path = ROOT / "main_scorce_image.png"
    if not source_path.exists():
        source_path = ROOT / "main_source_image.png"
    print(f"[*] Loading master logo from {source_path}...")
    master = Image.open(source_path).convert("RGBA")

    # 1. Master PNG sizes
    img_1024 = master.resize((1024, 1024), Image.Resampling.LANCZOS)
    img_512 = master.resize((512, 512), Image.Resampling.LANCZOS)
    img_256 = master.resize((256, 256), Image.Resampling.LANCZOS)
    img_192 = master.resize((192, 192), Image.Resampling.LANCZOS)

    # Save root copies
    img_512.save(str(ROOT / "PCDeck_Master_Logo.png"), format="PNG", optimize=True)
    img_512.save(str(ROOT / "icon.png"), format="PNG", optimize=True)
    img_512.save(str(ROOT / "icon-512.png"), format="PNG", optimize=True)
    img_256.save(str(ROOT / "PCDeck_Mouse_Logo.png"), format="PNG", optimize=True)
    img_256.save(str(ROOT / "PCDeck_Logo.png"), format="PNG", optimize=True)
    img_192.save(str(ROOT / "favicon.png"), format="PNG", optimize=True)
    img_512.save(str(ROOT / "playstore_assets" / "App_Icon_512x512.png"), format="PNG", optimize=True)

    # Save to static, website, and android_app/assets
    # Mobile and Web UIs render at 28px-80px: 256x256 offers 4K retina clarity without wasting bandwidth/storage
    dest_folders = [ROOT / "static", ROOT / "website", ROOT / "android_app" / "assets"]
    for folder in dest_folders:
        folder.mkdir(parents=True, exist_ok=True)
        img_256.save(str(folder / "PCDeck_Master_Logo.png"), format="PNG", optimize=True)
        img_256.save(str(folder / "icon.png"), format="PNG", optimize=True)
        img_512.save(str(folder / "icon-512.png"), format="PNG", optimize=True)
        img_256.save(str(folder / "PCDeck_Mouse_Logo.png"), format="PNG", optimize=True)
        img_256.save(str(folder / "PCDeck_Logo.png"), format="PNG", optimize=True)
        img_192.save(str(folder / "favicon.png"), format="PNG", optimize=True)
    print("  [+] Saved optimized authentic PNGs across root, static, website, and android_app/assets")

    # 2. Windows Multi-Resolution ICO files (16, 20, 24, 32, 40, 48, 64, 128, 256)
    sizes = [16, 20, 24, 32, 40, 48, 64, 128, 256]
    ico_frames = []
    for sz in sizes:
        frame = master.resize((sz, sz), Image.Resampling.LANCZOS)
        if sz <= 32:
            enhancer = ImageEnhance.Sharpness(frame)
            frame = enhancer.enhance(1.3)
            enhancer_c = ImageEnhance.Contrast(frame)
            frame = enhancer_c.enhance(1.1)
        ico_frames.append(frame)

    ico_destinations = [
        ROOT / "app_icon.ico",
        ROOT / "PCDeck.ico",
        ROOT / "icon.ico",
        ROOT / "favicon.ico",
        ROOT / "static" / "favicon.ico",
        ROOT / "website" / "favicon.ico",
        ROOT / "android_app" / "assets" / "favicon.ico",
    ]
    for ico_path in ico_destinations:
        write_multires_ico(ico_frames, ico_path)

    # 3. Android launcher assets
    drawable_dir = ROOT / "android_app" / "res" / "drawable"
    drawable_dir.mkdir(parents=True, exist_ok=True)
    fg_432 = Image.new("RGBA", (432, 432), (0, 0, 0, 0))
    fg_logo = master.resize((288, 288), Image.Resampling.LANCZOS)
    pos = (432 - 288) // 2
    fg_432.paste(fg_logo, (pos, pos), fg_logo)
    fg_432.save(str(drawable_dir / "ic_launcher_foreground.png"), format="PNG")

    legacy_192 = master.resize((192, 192), Image.Resampling.LANCZOS)
    legacy_192.save(str(drawable_dir / "ic_launcher.png"), format="PNG")

    densities = {
        "mipmap-mdpi": 48,
        "mipmap-hdpi": 72,
        "mipmap-xhdpi": 96,
        "mipmap-xxhdpi": 144,
        "mipmap-xxxhdpi": 192,
    }
    for folder, sz in densities.items():
        dir_path = ROOT / "android_app" / "res" / folder
        dir_path.mkdir(parents=True, exist_ok=True)
        mip_icon = master.resize((sz, sz), Image.Resampling.LANCZOS)
        mip_icon.save(str(dir_path / "ic_launcher.png"), format="PNG")
        
        round_icon = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
        mask_hires = Image.new("L", (sz * 4, sz * 4), 0)
        draw = ImageDraw.Draw(mask_hires)
        draw.ellipse((0, 0, sz * 4 - 1, sz * 4 - 1), fill=255)
        mask = mask_hires.resize((sz, sz), Image.Resampling.LANCZOS)
        round_icon.paste(mip_icon, (0, 0), mask)
        round_icon.save(str(dir_path / "ic_launcher_round.png"), format="PNG")
    print("  [+] Generated Android launcher drawables and mipmaps")

    # 4. Inno Setup Bitmaps
    wiz_small = Image.new("RGB", (55, 55), (15, 23, 42))
    logo_small = master.resize((48, 48), Image.Resampling.LANCZOS)
    wiz_small.paste(logo_small.convert("RGB"), ((55 - 48) // 2, (55 - 48) // 2))
    wiz_small.save(str(ROOT / "WizardSmallImage.bmp"), format="BMP")

    banner_w, banner_h = 164, 314
    wiz_banner = Image.new("RGB", (banner_w, banner_h), (11, 15, 23))
    banner_logo = master.resize((140, 140), Image.Resampling.LANCZOS)
    wiz_banner.paste(banner_logo.convert("RGB"), ((banner_w - 140) // 2, (banner_h - 140) // 2))
    wiz_banner.save(str(ROOT / "WizardImage.bmp"), format="BMP")
    print("  [+] Generated Inno Setup Wizard bitmaps")

    print("\n[OK] Authentic bright icon generated and applied everywhere across all sizes!")

if __name__ == "__main__":
    main()
