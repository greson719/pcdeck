#!/usr/bin/env python3
"""
PCDeck — Gaming Slides Generator (Slides 8 & 9)
Builds two separate, full-size 1920x1080 showcase slides for:
1. Slide 8: Wireless Virtual Gamepad Controller (screenshots/gamepad.png)
2. Slide 9: On-Screen Game HUD Touch Overlay (screenshots/hud.png)
"""

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = ROOT / "screenshots"
OUTPUT_MSSTORE = ROOT / "msstore_assets"

# Obsidian Cyber-Neon Palette
BG_OBSIDIAN = (10, 14, 23)
SURFACE_CARD = (19, 25, 38, 252)
CARD_BORDER = (45, 60, 90, 255)
CYAN = (0, 240, 255)
GOLD = (255, 200, 30)
LIME = (0, 255, 102)
PURPLE = (168, 85, 247)
WHITE = (255, 255, 255)
TEXT_MUTED = (165, 180, 205)

def get_font(size, bold=False):
    font_path = "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"
    if not os.path.exists(font_path):
        font_path = "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"
    return ImageFont.truetype(font_path, size)

def create_base_canvas(width=1920, height=1080, accent_color=GOLD, glow_center=(0.75, 0.5)):
    canvas = Image.new("RGBA", (width, height), BG_OBSIDIAN)
    draw = ImageDraw.Draw(canvas)

    for y in range(height):
        ratio = y / height
        r = int(10 + 6 * ratio)
        g = int(14 + 8 * ratio)
        b = int(23 + 14 * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

    grid = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(grid)
    for x in range(0, width, 60):
        g_draw.line([(x, 0), (x, height)], fill=(255, 255, 255, 5), width=1)
    for y in range(0, height, 60):
        g_draw.line([(0, y), (width, y)], fill=(255, 255, 255, 5), width=1)
    canvas = Image.alpha_composite(canvas, grid)

    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    gx, gy = int(width * glow_center[0]), int(height * glow_center[1])
    max_r = int(min(width, height) * 0.75)
    for r in range(max_r, 0, -12):
        alpha = int(70 * (1.0 - (r / max_r) ** 1.3))
        glow_draw.ellipse([gx - r, gy - r, gx + r, gy + r], fill=(accent_color[0], accent_color[1], accent_color[2], alpha))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=50))
    canvas = Image.alpha_composite(canvas, glow)

    return canvas

def make_phone_frame(screen_img, is_horizontal=True, target_size=1080, accent=GOLD):
    orig_w, orig_h = screen_img.size
    bezel = 10
    corner_r = 34
    screen_r = 24

    if is_horizontal:
        frame_w = target_size
        frame_h = int(target_size * (orig_h / orig_w)) + (bezel * 2)
    else:
        frame_h = target_size
        frame_w = int(target_size * (orig_w / orig_h)) + (bezel * 2)

    screen_w = frame_w - (bezel * 2)
    screen_h = frame_h - (bezel * 2)

    screen_resized = screen_img.convert("RGB").resize((screen_w, screen_h), Image.Resampling.LANCZOS).convert("RGBA")

    screen_mask = Image.new("L", (screen_w, screen_h), 0)
    s_draw = ImageDraw.Draw(screen_mask)
    s_draw.rounded_rectangle([0, 0, screen_w, screen_h], radius=screen_r, fill=255)

    frame = Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
    f_draw = ImageDraw.Draw(frame)
    f_draw.rounded_rectangle([0, 0, frame_w - 1, frame_h - 1], radius=corner_r, fill=(20, 26, 40, 255), outline=accent, width=2)
    f_draw.rounded_rectangle([2, 2, frame_w - 3, frame_h - 3], radius=corner_r - 2, fill=(10, 14, 22, 255), outline=(48, 65, 96, 255), width=1)

    frame.paste(screen_resized, (bezel, bezel), screen_mask)

    if not is_horizontal:
        cx, cy = frame_w // 2, bezel + 12
        f_draw.ellipse([cx - 5, cy - 5, cx + 5, cy + 5], fill=(3, 5, 8, 255), outline=(35, 48, 70, 255), width=1)
    else:
        cx, cy = bezel + 12, frame_h // 2
        f_draw.ellipse([cx - 5, cy - 5, cx + 5, cy + 5], fill=(3, 5, 8, 255), outline=(35, 48, 70, 255), width=1)

    pad = 50
    total_w = frame_w + (pad * 2)
    total_h = frame_h + (pad * 2)
    container = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))

    halo = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
    h_draw = ImageDraw.Draw(halo)
    h_draw.rounded_rectangle([pad - 16, pad - 12, pad + frame_w + 16, pad + frame_h + 20], radius=corner_r + 16, fill=(accent[0], accent[1], accent[2], 75))
    halo = halo.filter(ImageFilter.GaussianBlur(radius=30))
    container = Image.alpha_composite(container, halo)

    shadow = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
    sh_draw = ImageDraw.Draw(shadow)
    sh_draw.rounded_rectangle([pad + 8, pad + 18, pad + frame_w + 8, pad + frame_h + 30], radius=corner_r, fill=(0, 0, 0, 230))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=24))
    container = Image.alpha_composite(container, shadow)

    container.paste(frame, (pad, pad), frame)
    return container

def render_slide(filename, badge_text, line1, line2, subtitle, bullet_points, mockup_container, mockup_pos=(760, 220), accent=GOLD):
    W, H = 1920, 1080
    canvas = create_base_canvas(W, H, accent_color=accent)
    draw = ImageDraw.Draw(canvas)

    left_x = 75
    cur_y = 100

    # 1. Badge Pill
    font_badge = get_font(16, bold=True)
    bbox = font_badge.getbbox(badge_text)
    bw = bbox[2] - bbox[0] + 46
    bh = 38

    badge_img = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    b_draw = ImageDraw.Draw(badge_img)
    b_draw.rounded_rectangle([0, 0, bw - 1, bh - 1], radius=19, fill=(accent[0], accent[1], accent[2], 30), outline=(accent[0], accent[1], accent[2], 220), width=1)
    b_draw.ellipse([14, 14, 22, 22], fill=accent)
    b_draw.text((30, 8), badge_text, font=font_badge, fill=accent)
    canvas.paste(badge_img, (left_x, cur_y), badge_img)
    cur_y += bh + 24

    # 2. Headline
    font_t1 = get_font(50, bold=True)
    font_t2 = get_font(50, bold=True)
    draw.text((left_x, cur_y), line1, font=font_t1, fill=WHITE)
    cur_y += 62
    draw.text((left_x, cur_y), line2, font=font_t2, fill=accent)
    cur_y += 76

    # 3. Subtitle
    font_sub = get_font(22, bold=False)
    words = subtitle.split()
    lines = []
    curr = []
    for w in words:
        curr.append(w)
        if font_sub.getbbox(" ".join(curr))[2] > 640:
            curr.pop()
            lines.append(" ".join(curr))
            curr = [w]
    if curr:
        lines.append(" ".join(curr))

    for line in lines:
        draw.text((left_x, cur_y), line, font=font_sub, fill=TEXT_MUTED)
        cur_y += 32
    cur_y += 40

    # 4. Feature Cards
    font_pill = get_font(18, bold=True)
    for bp in bullet_points:
        p_bbox = font_pill.getbbox(bp)
        pw = p_bbox[2] - p_bbox[0] + 48
        ph = 50

        card = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        c_draw = ImageDraw.Draw(card)
        c_draw.rounded_rectangle([0, 0, pw - 1, ph - 1], radius=12, fill=SURFACE_CARD, outline=CARD_BORDER, width=1)
        c_draw.rounded_rectangle([6, 12, 10, ph - 12], radius=2, fill=accent)
        c_draw.text((22, 13), bp, font=font_pill, fill=WHITE)
        canvas.paste(card, (left_x, cur_y), card)
        cur_y += ph + 14

    # 5. Mockup
    canvas.paste(mockup_container, mockup_pos, mockup_container)

    # Save to msstore_assets and screenshots
    out_msstore = OUTPUT_MSSTORE / filename
    out_screenshots = SCREENSHOTS_DIR / filename
    OUTPUT_MSSTORE.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(out_msstore, quality=95)
    canvas.convert("RGB").save(out_screenshots, quality=95)
    print(f"[+] Saved Slide: {out_msstore}")

def generate_slides():
    img_gamepad = Image.open(SCREENSHOTS_DIR / "gamepad.png")
    img_hud = Image.open(SCREENSHOTS_DIR / "hud.png")

    # =========================================================================
    # SLIDE 8: WIRELESS VIRTUAL GAMEPAD CONTROLLER
    # (Phone is a blind console controller while looking at PC monitor)
    # =========================================================================
    phone_gamepad = make_phone_frame(img_gamepad, is_horizontal=True, target_size=1050, accent=GOLD)
    render_slide(
        "8_Virtual_Gamepad_Controller_1920x1080.png",
        "XINPUT WIRELESS CONTROLLER",
        "WIRELESS PC GAMEPAD",
        "HANDHELD CONSOLE",
        "Turn your smartphone into a full XInput handheld controller to play games on your PC monitor with dual analog thumbsticks, D-Pad, and triggers.",
        [
            "Dual Analog Thumbsticks & Precision D-Pad",
            "Left & Right Shoulder Bumpers + Triggers",
            "Native Windows XInput & ViGEm Support"
        ],
        phone_gamepad,
        mockup_pos=(760, 220),
        accent=GOLD
    )

    # =========================================================================
    # SLIDE 9: ON-SCREEN GAME HUD TOUCH OVERLAY
    # (Phone streams PC game and user plays directly on mobile screen)
    # =========================================================================
    phone_hud = make_phone_frame(img_hud, is_horizontal=True, target_size=1050, accent=CYAN)
    render_slide(
        "9_OnScreen_Game_HUD_Overlay_1920x1080.png",
        "IN-GAME TOUCH OVERLAY",
        "ON-SCREEN GAME HUD",
        "STREAM & PLAY GAMES",
        "Stream your favorite PC games directly to your phone screen at 60 FPS and control the action with transparent, customizable touch buttons.",
        [
            "60 FPS Low-Latency Direct Screen Stream",
            "Custom Button Layout & Visual In-Game Editor",
            "Zero Setup Required: Connects in Seconds"
        ],
        phone_hud,
        mockup_pos=(760, 220),
        accent=CYAN
    )

    # Clean up any leftover combined slide
    for old_file in [
        OUTPUT_MSSTORE / "8_Virtual_Gamepad_And_HUD_1920x1080.png",
        SCREENSHOTS_DIR / "gamepad_and_hud_showcase_1920x1080.png"
    ]:
        if old_file.exists():
            old_file.unlink()
            print(f"[-] Cleaned up old combined slide: {old_file.name}")

if __name__ == "__main__":
    generate_slides()
