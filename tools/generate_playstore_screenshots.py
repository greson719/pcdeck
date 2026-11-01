"""
PCDeck — High-Converting Google Play Store Screenshot Generator
Generates premium horizontal (1920x1080, 16:9) showcase slides + 1024x500 Feature Graphic
matching the Cyber-Neon Obsidian glassmorphic aesthetic.
"""

import os
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUTPUT_DIR = "playstore_assets"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Colors (Obsidian Cyber-Neon Palette)
BG_DARK = (7, 10, 19)
BG_SURFACE = (15, 22, 35)
BG_CARD = (20, 29, 46)
CYAN_ACCENT = (0, 240, 255)
CYAN_GLOW = (0, 240, 255, 60)
LIME_ACCENT = (0, 255, 102)
PURPLE_ACCENT = (168, 85, 247)
YELLOW_ACCENT = (255, 230, 0)
TEXT_WHITE = (255, 255, 255)
TEXT_MUTED = (160, 175, 200)
BORDER_COLOR = (35, 48, 75)

# Fonts
def get_font(size, bold=False):
    font_path = "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"
    if not os.path.exists(font_path):
        font_path = "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"
    return ImageFont.truetype(font_path, size)


def draw_rounded_rect(draw, bbox, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(bbox, radius=radius, fill=fill, outline=outline, width=width)


def create_cyber_background(width, height, glow_color=(0, 240, 255), glow_pos=(0.7, 0.5)):
    # Base gradient
    bg = Image.new("RGBA", (width, height), BG_DARK)
    draw = ImageDraw.Draw(bg)

    # Top-to-bottom subtle vertical gradient
    for y in range(height):
        ratio = y / height
        r = int(7 + (13 - 7) * ratio)
        g = int(10 + (19 - 10) * ratio)
        b = int(19 + (36 - 19) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

    # Grid overlay
    grid_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    grid_draw = ImageDraw.Draw(grid_img)
    grid_spacing = 60
    for x in range(0, width, grid_spacing):
        grid_draw.line([(x, 0), (x, height)], fill=(255, 255, 255, 6), width=1)
    for y in range(0, height, grid_spacing):
        grid_draw.line([(0, y), (width, y)], fill=(255, 255, 255, 6), width=1)
    bg = Image.alpha_composite(bg, grid_img)

    # Radial ambient glow
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    gx, gy = int(width * glow_pos[0]), int(height * glow_pos[1])
    max_r = int(min(width, height) * 0.75)
    for r in range(max_r, 0, -15):
        alpha = int(45 * (1.0 - (r / max_r) ** 1.5))
        glow_draw.ellipse(
            [gx - r, gy - r, gx + r, gy + r],
            fill=(glow_color[0], glow_color[1], glow_color[2], alpha)
        )
    glow = glow.filter(ImageFilter.GaussianBlur(radius=50))
    bg = Image.alpha_composite(bg, glow)

    return bg


def create_phone_mockup(screen_img, is_horizontal=False, target_width=None, target_height=None):
    """Wraps a screenshot in a sleek cyber smartphone frame with glass border & rounded corners."""
    orig_w, orig_h = screen_img.size

    # Bezel thickness
    bezel = 14
    corner_radius = 36
    screen_radius = 24

    if is_horizontal:
        if target_width:
            frame_w = target_width
            frame_h = int(target_width * (orig_h / orig_w)) + (bezel * 2)
        elif target_height:
            frame_h = target_height
            frame_w = int(target_height * (orig_w / orig_h)) + (bezel * 2)
        else:
            frame_w, frame_h = 1050, int(1050 * (orig_h / orig_w)) + (bezel * 2)
    else:
        if target_height:
            frame_h = target_height
            frame_w = int(target_height * (orig_w / orig_h)) + (bezel * 2)
        elif target_width:
            frame_w = target_width
            frame_h = int(target_width * (orig_h / orig_w)) + (bezel * 2)
        else:
            frame_h = 820
            frame_w = int(frame_h * (orig_w / orig_h)) + (bezel * 2)

    screen_w = frame_w - (bezel * 2)
    screen_h = frame_h - (bezel * 2)

    # Resize input screen
    screen_resized = screen_img.convert("RGBA").resize((screen_w, screen_h), Image.Resampling.LANCZOS)

    # Mask screen with rounded corners
    screen_mask = Image.new("L", (screen_w, screen_h), 0)
    mask_draw = ImageDraw.Draw(screen_mask)
    mask_draw.rounded_rectangle([0, 0, screen_w, screen_h], radius=screen_radius, fill=255)

    # Frame canvas
    frame = Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
    frame_draw = ImageDraw.Draw(frame)

    # Outer bezel with metallic gradient
    frame_draw.rounded_rectangle([0, 0, frame_w, frame_h], radius=corner_radius, fill=(18, 24, 38, 255), outline=(0, 240, 255, 180), width=2)
    frame_draw.rounded_rectangle([2, 2, frame_w - 2, frame_h - 2], radius=corner_radius - 2, fill=(12, 16, 26, 255), outline=(45, 60, 90, 255), width=1)

    # Paste masked screen
    frame.paste(screen_resized, (bezel, bezel), screen_mask)

    # Camera punch hole
    if not is_horizontal:
        hole_r = 7
        hole_x = frame_w // 2
        hole_y = bezel + 14
        frame_draw.ellipse([hole_x - hole_r, hole_y - hole_r, hole_x + hole_r, hole_y + hole_r], fill=(5, 8, 14, 255), outline=(30, 40, 60, 255), width=1)
    else:
        hole_r = 6
        hole_x = bezel + 16
        hole_y = frame_h // 2
        frame_draw.ellipse([hole_x - hole_r, hole_y - hole_r, hole_x + hole_r, hole_y + hole_r], fill=(5, 8, 14, 255), outline=(30, 40, 60, 255), width=1)

    # Add drop shadow
    shadow_pad = 40
    total_w = frame_w + (shadow_pad * 2)
    total_h = frame_h + (shadow_pad * 2)
    container = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))

    # Glow shadow
    glow_shadow = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_shadow)
    glow_draw.rounded_rectangle(
        [shadow_pad - 10, shadow_pad - 5, shadow_pad + frame_w + 10, shadow_pad + frame_h + 15],
        radius=corner_radius + 10,
        fill=(0, 240, 255, 45)
    )
    glow_shadow = glow_shadow.filter(ImageFilter.GaussianBlur(radius=25))
    container = Image.alpha_composite(container, glow_shadow)

    # Dark drop shadow
    dark_shadow = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
    dark_draw = ImageDraw.Draw(dark_shadow)
    dark_draw.rounded_rectangle(
        [shadow_pad + 5, shadow_pad + 15, shadow_pad + frame_w + 5, shadow_pad + frame_h + 25],
        radius=corner_radius,
        fill=(0, 0, 0, 180)
    )
    dark_shadow = dark_shadow.filter(ImageFilter.GaussianBlur(radius=20))
    container = Image.alpha_composite(container, dark_shadow)

    container.paste(frame, (shadow_pad, shadow_pad), frame)
    return container


def create_pc_window_mockup(window_img, target_width=860):
    """Wraps PC companion app screenshot in a sleek window frame."""
    orig_w, orig_h = window_img.size
    target_h = int(target_width * (orig_h / orig_w))

    resized = window_img.convert("RGBA").resize((target_width, target_h), Image.Resampling.LANCZOS)
    corner_radius = 16

    mask = Image.new("L", (target_width, target_h), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([0, 0, target_width, target_h], radius=corner_radius, fill=255)

    frame = Image.new("RGBA", (target_width, target_h), (0, 0, 0, 0))
    frame.paste(resized, (0, 0), mask)

    frame_draw = ImageDraw.Draw(frame)
    frame_draw.rounded_rectangle([0, 0, target_width - 1, target_h - 1], radius=corner_radius, outline=(0, 240, 255, 160), width=2)

    # Add drop shadow
    pad = 40
    total_w = target_width + (pad * 2)
    total_h = target_h + (pad * 2)
    container = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))

    glow_shadow = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_shadow)
    glow_draw.rounded_rectangle(
        [pad - 10, pad - 5, pad + target_width + 10, pad + target_h + 15],
        radius=corner_radius + 8,
        fill=(0, 240, 255, 40)
    )
    glow_shadow = glow_shadow.filter(ImageFilter.GaussianBlur(radius=25))
    container = Image.alpha_composite(container, glow_shadow)

    container.paste(frame, (pad, pad), frame)
    return container


def render_showcase_slide(
    filename,
    badge_text,
    title_line1,
    title_line2,
    subtitle_text,
    pills,
    mockup_img,
    mockup_pos=(920, 120),
    glow_color=(0, 240, 255),
    glow_pos=(0.75, 0.5)
):
    W, H = 1920, 1080
    canvas = create_cyber_background(W, H, glow_color=glow_color, glow_pos=glow_pos)
    draw = ImageDraw.Draw(canvas)

    # Left content positioning
    left_x = 100
    cur_y = 120

    # 1. Badge Pill
    font_badge = get_font(20, bold=True)
    badge_bbox = font_badge.getbbox(badge_text)
    badge_w = badge_bbox[2] - badge_bbox[0] + 36
    badge_h = 42

    badge_img = Image.new("RGBA", (badge_w, badge_h), (0, 0, 0, 0))
    b_draw = ImageDraw.Draw(badge_img)
    b_draw.rounded_rectangle([0, 0, badge_w - 1, badge_h - 1], radius=21, fill=(0, 240, 255, 25), outline=(0, 240, 255, 180), width=1)
    b_draw.text((18, 9), badge_text, font=font_badge, fill=CYAN_ACCENT)
    canvas.paste(badge_img, (left_x, cur_y), badge_img)
    cur_y += badge_h + 36

    # 2. Main Title (Two lines for punchiness)
    font_title = get_font(56, bold=True)
    draw.text((left_x, cur_y), title_line1, font=font_title, fill=TEXT_WHITE)
    cur_y += 68
    draw.text((left_x, cur_y), title_line2, font=font_title, fill=CYAN_ACCENT)
    cur_y += 84

    # 3. Subtitle / Value Prop
    font_sub = get_font(26, bold=False)
    # Word wrap subtitle
    words = subtitle_text.split()
    lines = []
    curr_line = []
    for word in words:
        curr_line.append(word)
        test_w = font_sub.getbbox(" ".join(curr_line))[2]
        if test_w > 720:
            curr_line.pop()
            lines.append(" ".join(curr_line))
            curr_line = [word]
    if curr_line:
        lines.append(" ".join(curr_line))

    for line in lines:
        draw.text((left_x, cur_y), line, font=font_sub, fill=TEXT_MUTED)
        cur_y += 38
    cur_y += 40

    # 4. Feature Pills / Highlights
    font_pill = get_font(22, bold=True)
    for pill in pills:
        pill_bbox = font_pill.getbbox(pill)
        pill_w = pill_bbox[2] - pill_bbox[0] + 44
        pill_h = 52

        pill_card = Image.new("RGBA", (pill_w, pill_h), (0, 0, 0, 0))
        p_draw = ImageDraw.Draw(pill_card)
        p_draw.rounded_rectangle([0, 0, pill_w - 1, pill_h - 1], radius=14, fill=(18, 26, 42, 230), outline=(40, 56, 88, 255), width=1)
        p_draw.text((22, 12), pill, font=font_pill, fill=TEXT_WHITE)
        canvas.paste(pill_card, (left_x, cur_y), pill_card)
        cur_y += pill_h + 16

    # 5. Paste Mockup Image on the Right
    canvas.paste(mockup_img, mockup_pos, mockup_img)

    # Save output
    out_path = os.path.join(OUTPUT_DIR, filename)
    canvas.convert("RGB").save(out_path, quality=95)
    print(f"OK: Generated '{out_path}'")


def generate_all():
    print("=======================================================")
    print("    [+] GENERATING GOOGLE PLAY STORE SHOWCASE ASSETS   ")
    print("=======================================================")

    transfers_dir = os.path.expanduser("~/Downloads/PCDeck_Transfers")

    # Load screenshots
    pc_screen = Image.open(r"C:/Users/GRESON/.gemini/antigravity/brain/2d46a58c-baa8-41df-9298-244019d6e827/.user_uploaded/media_1787933647713.png")
    # Crop the exact PCDeck window from the desktop screenshot (226, 38, 870, 529)
    pc_window = pc_screen.crop((226, 38, 870, 529))

    img_trackpad_v = Image.open(os.path.join(transfers_dir, "Screenshot_20260828-214527.png"))
    img_trackpad_h = Image.open(os.path.join(transfers_dir, "Screenshot_20260828-214558.png"))
    img_keyboard_h = Image.open(os.path.join(transfers_dir, "Screenshot_20260828-214449.png"))
    img_screen_h = Image.open(os.path.join(transfers_dir, "Screenshot_20260828-214630.png"))
    img_files_v = Image.open(os.path.join(transfers_dir, "Screenshot_20260828-214521.png"))
    img_settings_v = Image.open(os.path.join(transfers_dir, "Screenshot_20260828-214532.png"))
    img_qr_v = Image.open(os.path.join(transfers_dir, "Screenshot_20260828-214542.png"))

    # Slide 1: Hero Overview (PC App + Mobile Trackpad side-by-side)
    print("\n[+] Generating Slide 1: Hero Suite...")
    pc_mockup = create_pc_window_mockup(pc_window, target_width=660)
    phone_hero = create_phone_mockup(img_trackpad_v, is_horizontal=False, target_height=680)

    # Composite hero container
    hero_comp = Image.new("RGBA", (1050, 900), (0, 0, 0, 0))
    hero_comp.paste(pc_mockup, (0, 100), pc_mockup)
    hero_comp.paste(phone_hero, (540, 60), phone_hero)

    render_showcase_slide(
        "1_Hero_Suite_1920x1080.png",
        "PCDECK SUITE - WINDOWS 10 / 11 & ANDROID",
        "ULTRA-FAST WIRELESS",
        "PC CONTROL SUITE",
        "Turn your Android phone into an ultra-low-latency wireless trackpad, full mechanical keyboard, and real-time screen mirror.",
        [
            "⚡ Zero-Lag Direct Wi-Fi Connection",
            "🔒 100% Offline — Zero Cloud Accounts",
            "🚀 1-Tap Pairing with Auto-Discovery"
        ],
        hero_comp,
        mockup_pos=(860, 90),
        glow_color=CYAN_ACCENT,
        glow_pos=(0.75, 0.45)
    )

    # Slide 2: Multi-Touch Trackpad
    print("\n[+] Generating Slide 2: Precision Trackpad...")
    phone_trackpad = create_phone_mockup(img_trackpad_v, is_horizontal=False, target_height=820)
    render_showcase_slide(
        "2_MultiTouch_Trackpad_1920x1080.png",
        "PRECISION CURSOR ENGINE",
        "MULTI-TOUCH",
        "PRECISION TRACKPAD",
        "Ballistic cursor acceleration, adaptive tremor filtering, tactile drag-and-drop lock, and smooth kinetic inertia scrolling.",
        [
            "👆 1-Finger Tap: Instant Left Click",
            "✌️ 2-Finger Tap: Right Click Menu",
            "📜 Dedicated Scroll Strip & Kinetic Inertia"
        ],
        phone_trackpad,
        mockup_pos=(1150, 90),
        glow_color=CYAN_ACCENT,
        glow_pos=(0.78, 0.5)
    )

    # Slide 3: Full Mechanical Keyboard & Numpad
    print("\n[+] Generating Slide 3: Mechanical Keyboard & Numpad...")
    phone_keyboard = create_phone_mockup(img_keyboard_h, is_horizontal=True, target_width=980)
    render_showcase_slide(
        "3_Keyboard_Numpad_1920x1080.png",
        "FULL DESKTOP LAYOUT",
        "VIRTUAL MECHANICAL",
        "KEYBOARD & NUMPAD",
        "Complete desktop typing experience with dedicated Function keys (F1–F12), media deck, and rapid numpad calculations.",
        [
            "⌨️ Complete F1–F12 & Arrow Keys",
            "🔢 Dedicated Numpad for Rapid Entry",
            "⚡ 1-Tap Shortcuts: Copy, Paste, Alt+Tab"
        ],
        phone_keyboard,
        mockup_pos=(870, 240),
        glow_color=PURPLE_ACCENT,
        glow_pos=(0.75, 0.55)
    )

    # Slide 4: Real-Time Desktop Screen Streaming
    print("\n[+] Generating Slide 4: Screen Streaming...")
    phone_screen_stream = create_phone_mockup(img_screen_h, is_horizontal=True, target_width=980)
    render_showcase_slide(
        "4_Screen_Mirroring_1920x1080.png",
        "LOW-LATENCY STREAMING",
        "REAL-TIME DESKTOP",
        "SCREEN STREAMING",
        "Stream your Windows desktop directly to your phone screen at 60 FPS with 1:1 physical direct touch velocity and kinetic inertia.",
        [
            "🖥️ 1:1 Direct Physical Touch Tracking",
            "⚡ 60 FPS Ultra-Low Latency Video",
            "👆 Tap-to-Stop Inertia & Fling Physics"
        ],
        phone_screen_stream,
        mockup_pos=(870, 240),
        glow_color=LIME_ACCENT,
        glow_pos=(0.75, 0.55)
    )

    # Slide 5: High-Speed File Transfer
    print("\n[+] Generating Slide 5: Local File Transfer...")
    phone_files = create_phone_mockup(img_files_v, is_horizontal=False, target_height=820)
    render_showcase_slide(
        "5_File_Transfer_1920x1080.png",
        "GIGABIT LOCAL TRANSFERS",
        "CABLE-FREE HIGH-SPEED",
        "LOCAL FILE SHARING",
        "Transfer photos, 4K videos, documents, and archives between your PC and phone at full Wi-Fi speeds with auto-resume.",
        [
            "📁 Full Wi-Fi Bandwidth Throughput",
            "🔄 Chunked Streaming with Auto-Resume",
            "🔒 100% Private Local Network Transfer"
        ],
        phone_files,
        mockup_pos=(1150, 90),
        glow_color=CYAN_ACCENT,
        glow_pos=(0.78, 0.5)
    )

    # Slide 6: Live Stereo PC Audio Streaming
    print("\n[+] Generating Slide 6: PC Audio Streaming...")
    phone_audio = create_phone_mockup(img_settings_v, is_horizontal=False, target_height=820)
    render_showcase_slide(
        "6_Audio_Streaming_1920x1080.png",
        "WIRELESS AUDIO RELAY",
        "LIVE STEREO AUDIO",
        "TO PHONE EARBUDS",
        "Stream high-fidelity 48kHz stereo PC audio directly to your phone. Enjoy movies, music, and games through wireless earbuds.",
        [
            "🎧 48kHz Stereo Lossless PCM Audio",
            "⚡ Real-Time Low-Latency Sound Loop",
            "🔇 No Long Cables or Transmitters Needed"
        ],
        phone_audio,
        mockup_pos=(1150, 90),
        glow_color=YELLOW_ACCENT,
        glow_pos=(0.78, 0.5)
    )

    # Slide 7: Instant QR Code Pairing
    print("\n[+] Generating Slide 7: Instant QR Pairing...")
    phone_qr = create_phone_mockup(img_qr_v, is_horizontal=False, target_height=820)
    render_showcase_slide(
        "7_Instant_QR_Pairing_1920x1080.png",
        "SEAMLESS LOCAL CONNECTION",
        "1-TAP INSTANT",
        "QR CODE PAIRING",
        "Scan the on-screen QR code or connect across any shared Wi-Fi network or Mobile Hotspot in under three seconds.",
        [
            "📷 Instant Camera QR Auto-Connect",
            "🌐 Supports Local LAN & Mobile Hotspots",
            "🚫 Zero Logins, Accounts, or Cloud Servers"
        ],
        phone_qr,
        mockup_pos=(1150, 90),
        glow_color=CYAN_ACCENT,
        glow_pos=(0.78, 0.5)
    )

    # Slide 8: Google Play Store Feature Graphic (1024x500)
    print("\n[+] Generating Slide 8: Official Feature Graphic (1024x500)...")
    generate_feature_graphic(pc_window, img_trackpad_v, img_keyboard_h)

    print("\n=======================================================")
    print(f"OK: All 8 Play Store Showcase Assets Generated in '{OUTPUT_DIR}/'")
    print("=======================================================\n")


def generate_feature_graphic(pc_window, img_trackpad, img_keyboard):
    """Generates official 1024x500 Google Play Store Feature Graphic."""
    W, H = 1024, 500
    canvas = create_cyber_background(W, H, glow_color=CYAN_ACCENT, glow_pos=(0.7, 0.5))
    draw = ImageDraw.Draw(canvas)

    # Left text
    font_badge = get_font(14, bold=True)
    font_title = get_font(38, bold=True)
    font_sub = get_font(18, bold=False)

    # Badge
    b_text = "OFFLINE PC UTILITY SUITE"
    draw.rounded_rectangle([48, 70, 260, 98], radius=14, fill=(0, 240, 255, 30), outline=(0, 240, 255, 160), width=1)
    draw.text((62, 74), b_text, font=font_badge, fill=CYAN_ACCENT)

    # Title
    draw.text((48, 120), "PC DECK", font=font_title, fill=TEXT_WHITE)
    draw.text((48, 168), "WIRELESS REMOTE", font=font_title, fill=CYAN_ACCENT)

    # Subtitle
    draw.text((48, 230), "Precision Trackpad • Mechanical Keyboard", font=font_sub, fill=TEXT_MUTED)
    draw.text((48, 258), "60 FPS Screen Mirroring • File Transfers", font=font_sub, fill=TEXT_MUTED)

    # Pills
    font_pill = get_font(14, bold=True)
    pills = ["⚡ 0ms Latency", "🔒 100% Offline", "🎧 Stereo Audio"]
    cur_x = 48
    for p in pills:
        p_w = font_pill.getbbox(p)[2] - font_pill.getbbox(p)[0] + 28
        draw.rounded_rectangle([cur_x, 320, cur_x + p_w, 356], radius=10, fill=(18, 26, 42, 240), outline=(40, 56, 88, 255), width=1)
        draw.text((cur_x + 14, 328), p, font=font_pill, fill=TEXT_WHITE)
        cur_x += p_w + 12

    # Mockups on right
    phone_hero = create_phone_mockup(img_trackpad, is_horizontal=False, target_height=420)
    canvas.paste(phone_hero, (640, 40), phone_hero)

    pc_mock = create_pc_window_mockup(pc_window, target_width=360)
    canvas.paste(pc_mock, (440, 110), pc_mock)

    # Re-paste phone on top
    canvas.paste(phone_hero, (640, 40), phone_hero)

    out_path = os.path.join(OUTPUT_DIR, "Feature_Graphic_1024x500.png")
    canvas.convert("RGB").save(out_path, quality=95)
    print(f"OK: Generated Feature Graphic '{out_path}'")


if __name__ == "__main__":
    generate_all()
