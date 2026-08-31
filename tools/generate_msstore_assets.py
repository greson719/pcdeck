import os
import sys
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "msstore_assets"
ICON_SRC = ROOT / "icon-512.png"
PLAYSTORE_DIR = ROOT / "playstore_assets"

# Obsidian Cyber-Neon Palette
BG_OBSIDIAN = (10, 14, 23)
SURFACE_DARK = (19, 25, 38)
CYAN = (0, 240, 255)
LIME = (0, 255, 102)
PURPLE = (168, 85, 247)
YELLOW = (255, 220, 0)
WHITE = (255, 255, 255)
TEXT_MUTED = (165, 180, 205)

MANIFEST_SCALED_SIZES = {
    # Square 44x44
    "Square44x44Logo.png": (44, 44),
    "Square44x44Logo.scale-100.png": (44, 44),
    "Square44x44Logo.scale-125.png": (55, 55),
    "Square44x44Logo.scale-150.png": (66, 66),
    "Square44x44Logo.scale-200.png": (88, 88),
    "Square44x44Logo.scale-400.png": (176, 176),
    "Square44x44Logo.targetsize-16.png": (16, 16),
    "Square44x44Logo.targetsize-24.png": (24, 24),
    "Square44x44Logo.targetsize-32.png": (32, 32),
    "Square44x44Logo.targetsize-48.png": (48, 48),
    "Square44x44Logo.targetsize-256.png": (256, 256),
    "Square44x44Logo.targetsize-16_altform-unplated.png": (16, 16),
    "Square44x44Logo.targetsize-24_altform-unplated.png": (24, 24),
    "Square44x44Logo.targetsize-32_altform-unplated.png": (32, 32),
    "Square44x44Logo.targetsize-48_altform-unplated.png": (48, 48),
    "Square44x44Logo.targetsize-256_altform-unplated.png": (256, 256),
    
    # Square 150x150
    "Square150x150Logo.png": (150, 150),
    "Square150x150Logo.scale-100.png": (150, 150),
    "Square150x150Logo.scale-125.png": (188, 188),
    "Square150x150Logo.scale-150.png": (225, 225),
    "Square150x150Logo.scale-200.png": (300, 300),
    "Square150x150Logo.scale-400.png": (600, 600),

    # Wide 310x150
    "Wide310x150Logo.png": (310, 150),
    "Wide310x150Logo.scale-100.png": (310, 150),
    "Wide310x150Logo.scale-125.png": (388, 188),
    "Wide310x150Logo.scale-150.png": (465, 225),
    "Wide310x150Logo.scale-200.png": (620, 300),
    "Wide310x150Logo.scale-400.png": (1240, 600),

    # Square 310x310
    "Square310x310Logo.png": (310, 310),
    "Square310x310Logo.scale-100.png": (310, 310),
    "Square310x310Logo.scale-125.png": (388, 388),
    "Square310x310Logo.scale-150.png": (465, 465),
    "Square310x310Logo.scale-200.png": (620, 620),
    "Square310x310Logo.scale-400.png": (1240, 1240),

    # StoreLogo
    "StoreLogo.png": (50, 50),
    "StoreLogo.scale-100.png": (50, 50),
    "StoreLogo.scale-125.png": (63, 63),
    "StoreLogo.scale-150.png": (75, 75),
    "StoreLogo.scale-200.png": (100, 100),
    "StoreLogo.scale-400.png": (200, 200),

    # SplashScreen
    "SplashScreen.png": (620, 300),
    "SplashScreen.scale-100.png": (620, 300),
    "SplashScreen.scale-125.png": (775, 375),
    "SplashScreen.scale-150.png": (930, 450),
    "SplashScreen.scale-200.png": (1240, 600),
    "SplashScreen.scale-400.png": (2480, 1200),
}


def get_font(size, bold=False):
    font_path = "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"
    if not os.path.exists(font_path):
        font_path = "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"
    return ImageFont.truetype(font_path, size)


def create_base_canvas(width, height, accent_color=CYAN, glow_center=(0.72, 0.48)):
    canvas = Image.new("RGBA", (width, height), (*BG_OBSIDIAN, 255))
    draw = ImageDraw.Draw(canvas)

    for y in range(height):
        ratio = y / height
        r = int(10 + 6 * ratio)
        g = int(14 + 8 * ratio)
        b = int(23 + 14 * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

    grid = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(grid)
    step = max(40, width // 35)
    for x in range(0, width, step):
        g_draw.line([(x, 0), (x, height)], fill=(255, 255, 255, 7), width=1)
    for y in range(0, height, step):
        g_draw.line([(0, y), (width, y)], fill=(255, 255, 255, 7), width=1)
    canvas = Image.alpha_composite(canvas, grid)

    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    gx, gy = int(width * glow_center[0]), int(height * glow_center[1])
    max_r = int(min(width, height) * 0.75)
    for r in range(max_r, 0, max(8, max_r // 30)):
        alpha = int(75 * (1.0 - (r / max_r) ** 1.3))
        glow_draw.ellipse([gx - r, gy - r, gx + r, gy + r], fill=(*accent_color, alpha))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=max(20, width // 40)))
    canvas = Image.alpha_composite(canvas, glow)

    return canvas


def generate_manifest_assets(dest_dir: Path):
    dest_dir.mkdir(parents=True, exist_ok=True)
    if not ICON_SRC.exists():
        print(f"[!] Error: {ICON_SRC} not found.")
        sys.exit(1)

    img = Image.open(ICON_SRC).convert("RGBA")
    
    for filename, (w, h) in MANIFEST_SCALED_SIZES.items():
        out_path = dest_dir / filename
        resized = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        
        icon_copy = img.copy()
        if "Splash" in filename:
            logo_h = int(h * 0.45)
            logo_w = int(w * 0.45)
            icon_copy.thumbnail((logo_w, logo_h), Image.Resampling.LANCZOS)
        elif "Wide" in filename:
            logo_h = int(h * 0.65)
            icon_copy.thumbnail((logo_h, logo_h), Image.Resampling.LANCZOS)
        else:
            margin_ratio = 0.82 if "unplated" in filename or "targetsize" in filename else 0.78
            target_size = int(min(w, h) * margin_ratio)
            icon_copy.thumbnail((target_size, target_size), Image.Resampling.LANCZOS)

        offset_x = (w - icon_copy.width) // 2
        offset_y = (h - icon_copy.height) // 2
        resized.paste(icon_copy, (offset_x, offset_y), icon_copy)
        resized.save(out_path, "PNG")


def render_store_logo_300x300(out_path: Path):
    w, h = 300, 300
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    
    bg = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bg_draw = ImageDraw.Draw(bg)
    bg_draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=48, fill=(14, 19, 28, 255), outline=(0, 240, 255, 120), width=3)
    
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(glow)
    g_draw.ellipse([50, 50, 250, 250], fill=(0, 240, 255, 60))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=30))
    
    canvas = Image.alpha_composite(canvas, bg)
    canvas = Image.alpha_composite(canvas, glow)
    
    img = Image.open(ICON_SRC).convert("RGBA")
    img.thumbnail((220, 220), Image.Resampling.LANCZOS)
    ox = (w - img.width) // 2
    oy = (h - img.height) // 2
    canvas.paste(img, (ox, oy), img)
    
    canvas.save(out_path, "PNG")
    print(f"  [+] Rendered Store 1:1 Box Art: {out_path.name}")


def render_store_hero_banner(width, height, out_path: Path):
    canvas = create_base_canvas(width, height, accent_color=CYAN, glow_center=(0.72, 0.48))
    draw = ImageDraw.Draw(canvas)
    
    pad_left = int(width * 0.08)
    title_y = int(height * 0.28)
    
    # Category / Badge
    badge_bg = (0, 240, 255, 30)
    badge_border = (0, 240, 255, 140)
    b_w, b_h = int(width * 0.24), int(height * 0.07)
    
    badge_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    b_draw = ImageDraw.Draw(badge_layer)
    b_draw.rounded_rectangle([pad_left, title_y - b_h - int(height * 0.04), pad_left + b_w, title_y - int(height * 0.04)], 
                             radius=b_h // 2, fill=badge_bg, outline=badge_border, width=2)
    canvas = Image.alpha_composite(canvas, badge_layer)
    draw = ImageDraw.Draw(canvas)
    
    font_badge = get_font(int(height * 0.030), bold=True)
    draw.text((pad_left + int(b_w * 0.08), title_y - b_h - int(height * 0.04) + int(b_h * 0.20)), 
              "OFFICIAL WINDOWS UTILITY", fill=CYAN, font=font_badge)

    # Master Title
    font_title = get_font(int(height * 0.11), bold=True)
    draw.text((pad_left, title_y), "PCDeck", fill=WHITE, font=font_title)
    
    # Subtitle
    font_sub = get_font(int(height * 0.048), bold=True)
    sub_y = title_y + int(height * 0.14)
    draw.text((pad_left, sub_y), "Wireless Trackpad, Screen Mirror & Remote", fill=CYAN, font=font_sub)
    
    # Description
    font_desc = get_font(int(height * 0.030), bold=False)
    desc_y = sub_y + int(height * 0.08)
    desc_text = (
        "Turn your smartphone into a multi-touch trackpad, 60 FPS desktop screen mirror,\n"
        "live mechanical keyboard, audio loopback streamer, and cable-free file manager.\n"
        "100% Offline Local Wi-Fi - Zero Cloud Accounts - Zero Latency"
    )
    draw.text((pad_left, desc_y), desc_text, fill=TEXT_MUTED, font=font_desc, spacing=int(height * 0.012))

    # Feature Pill Badges
    pills = ["60 FPS Mirroring", "Multi-Touch Gestures", "Gigabit File Transfers", "Stereo Audio Bridge"]
    pill_x = pad_left
    pill_y = desc_y + int(height * 0.16)
    font_pill = get_font(int(height * 0.024), bold=True)
    
    for pill in pills:
        bbox = draw.textbbox((0, 0), pill, font=font_pill)
        pw = (bbox[2] - bbox[0]) + int(width * 0.025)
        ph = int(height * 0.055)
        
        p_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        p_draw = ImageDraw.Draw(p_layer)
        p_draw.rounded_rectangle([pill_x, pill_y, pill_x + pw, pill_y + ph], radius=ph // 2, 
                                 fill=(19, 25, 38, 220), outline=(45, 60, 90, 255), width=2)
        canvas = Image.alpha_composite(canvas, p_layer)
        draw = ImageDraw.Draw(canvas)
        draw.text((pill_x + int(width * 0.012), pill_y + int(ph * 0.22)), pill, fill=WHITE, font=font_pill)
        pill_x += pw + int(width * 0.012)

    # Right Side Graphic: Stylized Glassmorphism App Icon & Glow
    icon_box_size = int(height * 0.65)
    ix = int(width * 0.68)
    iy = int((height - icon_box_size) / 2)
    
    card_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    c_draw = ImageDraw.Draw(card_layer)
    c_draw.rounded_rectangle([ix, iy, ix + icon_box_size, iy + icon_box_size], radius=40, 
                             fill=(14, 19, 28, 240), outline=(0, 240, 255, 160), width=4)
    
    glow_card = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    gc_draw = ImageDraw.Draw(glow_card)
    gc_draw.rounded_rectangle([ix - 15, iy - 15, ix + icon_box_size + 15, iy + icon_box_size + 15], 
                              radius=50, fill=(0, 240, 255, 60))
    glow_card = glow_card.filter(ImageFilter.GaussianBlur(radius=25))
    
    canvas = Image.alpha_composite(canvas, glow_card)
    canvas = Image.alpha_composite(canvas, card_layer)
    
    img = Image.open(ICON_SRC).convert("RGBA")
    logo_size = int(icon_box_size * 0.75)
    img.thumbnail((logo_size, logo_size), Image.Resampling.LANCZOS)
    canvas.paste(img, (ix + (icon_box_size - img.width) // 2, iy + (icon_box_size - img.height) // 2), img)

    canvas.save(out_path, "PNG")
    print(f"  [+] Rendered Store Hero Artwork: {out_path.name} ({width}x{height})")


def copy_store_showcase_screenshots(dest_dir: Path):
    screenshot_mapping = [
        ("1_Hero_Suite_1920x1080.png", "1_Hero_Desktop_Suite_1920x1080.png"),
        ("2_MultiTouch_Trackpad_1920x1080.png", "2_MultiTouch_Trackpad_1920x1080.png"),
        ("3_Screen_Mirroring_1920x1080.png", "3_Desktop_Screen_Mirroring_1920x1080.png"),
        ("4_Live_Keyboard_Typing_1920x1080.png", "4_Live_Keyboard_Typing_1920x1080.png"),
        ("5_File_Transfer_1920x1080.png", "5_Local_File_Sharing_1920x1080.png"),
        ("6_Audio_Streaming_1920x1080.png", "6_PC_Audio_Loopback_Streaming_1920x1080.png"),
        ("7_Instant_QR_Pairing_1920x1080.png", "7_Instant_QR_Code_Pairing_1920x1080.png"),
    ]
    
    for src_name, dst_name in screenshot_mapping:
        src_path = PLAYSTORE_DIR / src_name
        if src_path.exists():
            shutil.copy2(src_path, dest_dir / dst_name)
            print(f"  [+] Synchronized Store Screenshot: {dst_name}")


def main():
    print("[*] Generating Microsoft Store Assets & High-DPI Manifests...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    render_store_logo_300x300(OUTPUT_DIR / "StoreLogo_300x300.png")
    render_store_hero_banner(2400, 1200, OUTPUT_DIR / "StoreHero_2400x1200.png")
    render_store_hero_banner(1920, 1080, OUTPUT_DIR / "StoreHero_1920x1080.png")
    render_store_hero_banner(1240, 600, OUTPUT_DIR / "StorePoster_1240x600.png")
    
    manifest_assets_dir = OUTPUT_DIR / "Manifest_Assets"
    generate_manifest_assets(manifest_assets_dir)
    print(f"  [+] Generated {len(MANIFEST_SCALED_SIZES)} High-DPI AppxManifest icons in msstore_assets/Manifest_Assets/")

    copy_store_showcase_screenshots(OUTPUT_DIR)
    print("[OK] All Microsoft Store visual assets successfully generated in 'msstore_assets/'!\n")


if __name__ == "__main__":
    main()
