"""
PCDeck — Professional Google Play Store Showcase Graphics Generator (v2)
Renders high-converting, eye-catching 1920x1080 (16:9 Landscape) showcase cards
and 1024x500 Feature Graphic with cyber-neon glassmorphism, 3D device mockups,
ambient backlights, and pixel-accurate typography.
"""

import os
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUTPUT_DIR = "playstore_assets"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Aesthetic Palette (Cyber-Neon Obsidian)
BG_OBSIDIAN = (7, 10, 18)
BG_NAVY_DEEP = (10, 16, 28)
CYAN_ACCENT = (0, 240, 255)
LIME_ACCENT = (0, 255, 102)
PURPLE_ACCENT = (168, 85, 247)
YELLOW_ACCENT = (255, 220, 0)
ORANGE_ACCENT = (255, 120, 0)
TEXT_WHITE = (255, 255, 255)
TEXT_MUTED = (165, 180, 205)
CARD_BG = (16, 24, 38, 235)
CARD_BORDER = (40, 56, 85, 255)


def get_font(size, bold=False):
    font_path = "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"
    if not os.path.exists(font_path):
        font_path = "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"
    return ImageFont.truetype(font_path, size)


def create_premium_background(width, height, primary_color=(0, 240, 255), secondary_color=(0, 255, 102), glow_pos=(0.75, 0.45)):
    """Creates a multi-layered cyber-neon mesh background with subtle grid and ambient lighting."""
    bg = Image.new("RGBA", (width, height), BG_OBSIDIAN)
    draw = ImageDraw.Draw(bg)

    # 1. Base vertical subtle gradient
    for y in range(height):
        ratio = y / height
        r = int(7 + (13 - 7) * ratio)
        g = int(10 + (18 - 10) * ratio)
        b = int(18 + (34 - 18) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

    # 2. Geometric tech grid pattern
    grid_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    grid_draw = ImageDraw.Draw(grid_img)
    spacing = 50
    for x in range(0, width, spacing):
        grid_draw.line([(x, 0), (x, height)], fill=(255, 255, 255, 5), width=1)
    for y in range(0, height, spacing):
        grid_draw.line([(0, y), (width, y)], fill=(255, 255, 255, 5), width=1)
    
    # Diagonal subtle accent line in background
    grid_draw.line([(0, int(height * 0.8)), (width, int(height * 0.2))], fill=(primary_color[0], primary_color[1], primary_color[2], 12), width=2)
    bg = Image.alpha_composite(bg, grid_img)

    # 3. Ambient Primary Spotlight Glow (Behind mockups)
    glow1 = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    g1_draw = ImageDraw.Draw(glow1)
    gx1, gy1 = int(width * glow_pos[0]), int(height * glow_pos[1])
    r1 = int(min(width, height) * 0.65)
    for r in range(r1, 0, -12):
        alpha = int(60 * (1.0 - (r / r1) ** 1.3))
        g1_draw.ellipse([gx1 - r, gy1 - r, gx1 + r, gy1 + r], fill=(primary_color[0], primary_color[1], primary_color[2], alpha))
    glow1 = glow1.filter(ImageFilter.GaussianBlur(radius=50))
    bg = Image.alpha_composite(bg, glow1)

    # 4. Ambient Secondary Subtle Glow (Left/corner accent)
    glow2 = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    g2_draw = ImageDraw.Draw(glow2)
    gx2, gy2 = int(width * 0.15), int(height * 0.85)
    r2 = int(min(width, height) * 0.45)
    for r in range(r2, 0, -15):
        alpha = int(35 * (1.0 - (r / r2) ** 1.4))
        g2_draw.ellipse([gx2 - r, gy2 - r, gx2 + r, gy2 + r], fill=(secondary_color[0], secondary_color[1], secondary_color[2], alpha))
    glow2 = glow2.filter(ImageFilter.GaussianBlur(radius=45))
    bg = Image.alpha_composite(bg, glow2)

    return bg


def create_phone_mockup_pro(screen_img, is_horizontal=False, target_size=None, glow_accent=(0, 240, 255)):
    """Renders a flagship cyber-smartphone frame with realistic glass glare, camera bezel, and drop shadows."""
    orig_w, orig_h = screen_img.size

    bezel = 12
    corner_radius = 34
    screen_radius = 22

    if is_horizontal:
        target_w = target_size or 960
        frame_w = target_w
        frame_h = int(target_w * (orig_h / orig_w)) + (bezel * 2)
    else:
        target_h = target_size or 800
        frame_h = target_h
        frame_w = int(target_h * (orig_w / orig_h)) + (bezel * 2)

    screen_w = frame_w - (bezel * 2)
    screen_h = frame_h - (bezel * 2)

    # Resize screen
    screen_resized = screen_img.convert("RGBA").resize((screen_w, screen_h), Image.Resampling.LANCZOS)

    # Create Screen Mask
    screen_mask = Image.new("L", (screen_w, screen_h), 0)
    s_draw = ImageDraw.Draw(screen_mask)
    s_draw.rounded_rectangle([0, 0, screen_w, screen_h], radius=screen_radius, fill=255)

    # Frame body
    frame = Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
    f_draw = ImageDraw.Draw(frame)

    # Outer Titanium Bezel
    f_draw.rounded_rectangle([0, 0, frame_w - 1, frame_h - 1], radius=corner_radius, fill=(22, 28, 42, 255), outline=glow_accent, width=2)
    f_draw.rounded_rectangle([2, 2, frame_w - 3, frame_h - 3], radius=corner_radius - 2, fill=(11, 15, 24, 255), outline=(50, 68, 98, 255), width=1)

    # Paste Masked Screen
    frame.paste(screen_resized, (bezel, bezel), screen_mask)

    # Specular Glass Corner Reflection
    glare = Image.new("RGBA", (screen_w, screen_h), (0, 0, 0, 0))
    glare_draw = ImageDraw.Draw(glare)
    glare_points = [(0, 0), (int(screen_w * 0.45), 0), (0, int(screen_h * 0.45))]
    glare_draw.polygon(glare_points, fill=(255, 255, 255, 18))
    glare = glare.filter(ImageFilter.GaussianBlur(radius=8))
    frame.paste(glare, (bezel, bezel), screen_mask)

    # Camera Punch-hole
    if not is_horizontal:
        cx, cy = frame_w // 2, bezel + 12
        f_draw.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=(4, 6, 10, 255), outline=(30, 42, 60, 255), width=1)
        f_draw.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=(15, 25, 40, 255))
    else:
        cx, cy = bezel + 12, frame_h // 2
        f_draw.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=(4, 6, 10, 255), outline=(30, 42, 60, 255), width=1)

    # Build Drop Shadow & Ambient Neon Glow
    pad = 45
    total_w = frame_w + (pad * 2)
    total_h = frame_h + (pad * 2)
    canvas = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))

    # Outer Neon Color Halo
    halo = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
    h_draw = ImageDraw.Draw(halo)
    h_draw.rounded_rectangle([pad - 12, pad - 8, pad + frame_w + 12, pad + frame_h + 16], radius=corner_radius + 12, fill=(glow_accent[0], glow_accent[1], glow_accent[2], 55))
    halo = halo.filter(ImageFilter.GaussianBlur(radius=28))
    canvas = Image.alpha_composite(canvas, halo)

    # Deep Drop Shadow
    shadow = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
    sh_draw = ImageDraw.Draw(shadow)
    sh_draw.rounded_rectangle([pad + 6, pad + 16, pad + frame_w + 6, pad + frame_h + 28], radius=corner_radius, fill=(0, 0, 0, 200))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=22))
    canvas = Image.alpha_composite(canvas, shadow)

    canvas.paste(frame, (pad, pad), frame)
    return canvas


def create_pc_window_mockup_pro(window_img, target_width=720, glow_accent=(0, 240, 255)):
    """Renders a polished Windows 11 companion app window frame."""
    orig_w, orig_h = window_img.size
    target_h = int(target_width * (orig_h / orig_w))

    resized = window_img.convert("RGBA").resize((target_width, target_h), Image.Resampling.LANCZOS)
    corner_radius = 16

    mask = Image.new("L", (target_width, target_h), 0)
    m_draw = ImageDraw.Draw(mask)
    m_draw.rounded_rectangle([0, 0, target_width, target_h], radius=corner_radius, fill=255)

    frame = Image.new("RGBA", (target_width, target_h), (0, 0, 0, 0))
    frame.paste(resized, (0, 0), mask)

    f_draw = ImageDraw.Draw(frame)
    f_draw.rounded_rectangle([0, 0, target_width - 1, target_h - 1], radius=corner_radius, outline=glow_accent, width=2)

    # Drop shadow
    pad = 45
    total_w = target_width + (pad * 2)
    total_h = target_h + (pad * 2)
    canvas = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))

    halo = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
    h_draw = ImageDraw.Draw(halo)
    h_draw.rounded_rectangle([pad - 12, pad - 8, pad + target_width + 12, pad + target_h + 16], radius=corner_radius + 10, fill=(glow_accent[0], glow_accent[1], glow_accent[2], 50))
    halo = halo.filter(ImageFilter.GaussianBlur(radius=28))
    canvas = Image.alpha_composite(canvas, halo)

    shadow = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
    sh_draw = ImageDraw.Draw(shadow)
    sh_draw.rounded_rectangle([pad + 6, pad + 16, pad + target_width + 6, pad + target_h + 26], radius=corner_radius, fill=(0, 0, 0, 210))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=22))
    canvas = Image.alpha_composite(canvas, shadow)

    canvas.paste(frame, (pad, pad), frame)
    return canvas


def render_master_slide(
    filename,
    badge_icon,
    badge_text,
    title_line1,
    title_line2,
    subtitle_text,
    pills,
    mockup_img,
    mockup_pos=(910, 100),
    primary_color=CYAN_ACCENT,
    secondary_color=LIME_ACCENT,
    glow_pos=(0.75, 0.45)
):
    W, H = 1920, 1080
    canvas = create_premium_background(W, H, primary_color=primary_color, secondary_color=secondary_color, glow_pos=glow_pos)
    draw = ImageDraw.Draw(canvas)

    left_x = 90
    cur_y = 110

    # 1. Glowing Badge Pill
    font_badge = get_font(18, bold=True)
    full_badge = f"{badge_icon}  {badge_text}"
    bbox = font_badge.getbbox(full_badge)
    bw = bbox[2] - bbox[0] + 36
    bh = 40

    badge_img = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    b_draw = ImageDraw.Draw(badge_img)
    b_draw.rounded_rectangle([0, 0, bw - 1, bh - 1], radius=20, fill=(primary_color[0], primary_color[1], primary_color[2], 25), outline=(primary_color[0], primary_color[1], primary_color[2], 200), width=1)
    b_draw.text((18, 9), full_badge, font=font_badge, fill=primary_color)
    canvas.paste(badge_img, (left_x, cur_y), badge_img)
    cur_y += bh + 32

    # 2. Punchy Two-Line Title
    font_t1 = get_font(54, bold=True)
    font_t2 = get_font(54, bold=True)
    draw.text((left_x, cur_y), title_line1, font=font_t1, fill=TEXT_WHITE)
    cur_y += 66
    draw.text((left_x, cur_y), title_line2, font=font_t2, fill=primary_color)
    cur_y += 82

    # 3. Subtitle / Value Prop
    font_sub = get_font(24, bold=False)
    words = subtitle_text.split()
    lines = []
    curr = []
    for w in words:
        curr.append(w)
        if font_sub.getbbox(" ".join(curr))[2] > 740:
            curr.pop()
            lines.append(" ".join(curr))
            curr = [w]
    if curr:
        lines.append(" ".join(curr))

    for line in lines:
        draw.text((left_x, cur_y), line, font=font_sub, fill=TEXT_MUTED)
        cur_y += 36
    cur_y += 38

    # 4. Feature Cards / Pills
    font_pill = get_font(20, bold=True)
    for p in pills:
        p_bbox = font_pill.getbbox(p)
        pw = p_bbox[2] - p_bbox[0] + 46
        ph = 52

        pill_card = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        p_draw = ImageDraw.Draw(pill_card)
        p_draw.rounded_rectangle([0, 0, pw - 1, ph - 1], radius=14, fill=CARD_BG, outline=CARD_BORDER, width=1)
        
        # Draw little left accent bar inside the pill
        p_draw.rounded_rectangle([6, 12, 10, ph - 12], radius=2, fill=primary_color)
        p_draw.text((24, 13), p, font=font_pill, fill=TEXT_WHITE)
        canvas.paste(pill_card, (left_x, cur_y), pill_card)
        cur_y += ph + 16

    # 5. Paste Mockup on the right
    canvas.paste(mockup_img, mockup_pos, mockup_img)

    # Save PNG
    out_file = os.path.join(OUTPUT_DIR, filename)
    canvas.convert("RGB").save(out_file, quality=95)
    print(f"OK: Generated master slide '{out_file}'")


def generate_all_showcase():
    print("=======================================================")
    print("    [+] GENERATING REFINED PLAY STORE SHOWCASE ASSETS  ")
    print("=======================================================")

    transfers_dir = os.path.expanduser("~/Downloads/PCDeck_Transfers")

    # Load actual screenshots
    pc_screen = Image.open(r"C:/Users/GRESON/.gemini/antigravity/brain/2d46a58c-baa8-41df-9298-244019d6e827/.user_uploaded/media_1787933647713.png")
    pc_window = pc_screen.crop((226, 38, 870, 529))

    # Accurate Mapping:
    img_trackpad_v = Image.open(os.path.join(transfers_dir, "Screenshot_20260828-214527.png"))  # Trackpad Glide & Tap HUD + Clicks
    img_keyboard_h = Image.open(os.path.join(transfers_dir, "Screenshot_20260828-214449.png"))  # Landscape Full Keyboard & Numpad
    img_screen_h   = Image.open(os.path.join(transfers_dir, "Screenshot_20260828-214630.png"))  # Live Screen Mirroring 60FPS
    img_files_v    = Image.open(os.path.join(transfers_dir, "Screenshot_20260828-214521.png"))  # PC & Phone File Manager
    img_audio_v    = Image.open(os.path.join(transfers_dir, "Screenshot_20260828-214532.png"))  # Live Stereo PC Audio 48kHz & Media
    img_qr_v       = Image.open(os.path.join(transfers_dir, "Screenshot_20260828-214542.png"))  # QR Scanner Viewfinder

    # SLIDE 1: HERO SUITE (PC App Window + Phone Trackpad)
    print("\n[+] 1. Slide 1: Hero Suite...")
    pc_mock = create_pc_window_mockup_pro(pc_window, target_width=640, glow_accent=CYAN_ACCENT)
    phone_hero = create_phone_mockup_pro(img_trackpad_v, is_horizontal=False, target_size=680, glow_accent=CYAN_ACCENT)
    
    hero_container = Image.new("RGBA", (1050, 880), (0, 0, 0, 0))
    hero_container.paste(pc_mock, (0, 110), pc_mock)
    hero_container.paste(phone_hero, (540, 50), phone_hero)

    render_master_slide(
        "1_Hero_Suite_1920x1080.png",
        "⚡", "PCDECK UTILITY SUITE • WINDOWS & ANDROID",
        "WIRELESS PC CONTROL",
        "REDEFINED FOR ANDROID",
        "Transform your smartphone into an ultra-low-latency multi-touch trackpad, full mechanical keyboard, and real-time screen mirror.",
        [
            "⚡ Sub-Millisecond Input Latency",
            "🔒 100% Offline — Zero Cloud Accounts",
            "🚀 1-Tap Pairing via QR Code & Wi-Fi"
        ],
        hero_container,
        mockup_pos=(860, 90),
        primary_color=CYAN_ACCENT,
        secondary_color=LIME_ACCENT,
        glow_pos=(0.75, 0.45)
    )

    # SLIDE 2: MULTI-TOUCH PRECISION TRACKPAD
    print("\n[+] 2. Slide 2: Multi-Touch Trackpad...")
    phone_trackpad = create_phone_mockup_pro(img_trackpad_v, is_horizontal=False, target_size=820, glow_accent=CYAN_ACCENT)
    render_master_slide(
        "2_MultiTouch_Trackpad_1920x1080.png",
        "🖱️", "BALLISTIC CURSOR ENGINE",
        "MULTI-TOUCH",
        "PRECISION TRACKPAD",
        "Smooth ballistic cursor acceleration with adaptive tremor filtering, tactile drag-lock, and native kinetic scrolling inertia.",
        [
            "👆 1-Finger Tap: Instant Left Click",
            "✌️ 2-Finger Tap: Context Right Click",
            "📜 Dedicated Scroll Strip with Fling Inertia"
        ],
        phone_trackpad,
        mockup_pos=(1140, 85),
        primary_color=CYAN_ACCENT,
        secondary_color=PURPLE_ACCENT,
        glow_pos=(0.78, 0.5)
    )

    # SLIDE 3: FULL MECHANICAL KEYBOARD & NUMPAD
    print("\n[+] 3. Slide 3: Mechanical Keyboard & Numpad...")
    phone_kbd = create_phone_mockup_pro(img_keyboard_h, is_horizontal=True, target_size=980, glow_accent=PURPLE_ACCENT)
    render_master_slide(
        "3_Keyboard_Numpad_1920x1080.png",
        "⌨️", "DESKTOP-GRADE TYPING",
        "FULL MECHANICAL",
        "KEYBOARD & NUMPAD",
        "Complete desktop typing layout with F1–F12 function keys, dedicated 17-key numpad, media controls, and 1-tap shortcuts.",
        [
            "🔢 17-Key Mechanical Cyber Numpad",
            "⌨️ Complete F1–F12 & Navigation Cluster",
            "⚡ 1-Tap Shortcuts: Copy, Paste, Alt+Tab, Win+D"
        ],
        phone_kbd,
        mockup_pos=(860, 235),
        primary_color=PURPLE_ACCENT,
        secondary_color=CYAN_ACCENT,
        glow_pos=(0.75, 0.55)
    )

    # SLIDE 4: REAL-TIME DESKTOP SCREEN STREAMING
    print("\n[+] 4. Slide 4: Real-Time Screen Streaming...")
    phone_screen = create_phone_mockup_pro(img_screen_h, is_horizontal=True, target_size=980, glow_accent=LIME_ACCENT)
    render_master_slide(
        "4_Screen_Mirroring_1920x1080.png",
        "🖥️", "60 FPS DESKTOP MIRRORING",
        "REAL-TIME ZERO-LAG",
        "PC SCREEN STREAMING",
        "Stream your Windows desktop directly to your phone at 60 FPS with 1:1 physical direct touch tracking and kinetic fling inertia.",
        [
            "⚡ 60 FPS Low-Latency Adaptive Stream",
            "👆 1:1 Direct Touch Velocity Tracking",
            "⌨️ On-Screen Quick Type Keyboard Bar"
        ],
        phone_screen,
        mockup_pos=(860, 235),
        primary_color=LIME_ACCENT,
        secondary_color=CYAN_ACCENT,
        glow_pos=(0.75, 0.55)
    )

    # SLIDE 5: HIGH-SPEED LOCAL FILE TRANSFER
    print("\n[+] 5. Slide 5: High-Speed File Transfer...")
    phone_files = create_phone_mockup_pro(img_files_v, is_horizontal=False, target_size=820, glow_accent=CYAN_ACCENT)
    render_master_slide(
        "5_File_Transfer_1920x1080.png",
        "📁", "CABLE-FREE LOCAL STORAGE",
        "HIGH-SPEED LOCAL",
        "FILE SHARING & STORAGE",
        "Transfer 4K videos, documents, and archives directly between your PC and phone at full Wi-Fi speeds with auto-resume support.",
        [
            "📁 Unthrottled Gigabit Wi-Fi Speeds",
            "🔄 Automatic Chunk Streaming & Resume",
            "📱 Dedicated PC & Phone File Explorers"
        ],
        phone_files,
        mockup_pos=(1140, 85),
        primary_color=CYAN_ACCENT,
        secondary_color=YELLOW_ACCENT,
        glow_pos=(0.78, 0.5)
    )

    # SLIDE 6: LIVE STEREO PC AUDIO STREAMING
    print("\n[+] 6. Slide 6: Live Stereo Audio...")
    phone_audio = create_phone_mockup_pro(img_audio_v, is_horizontal=False, target_size=820, glow_accent=YELLOW_ACCENT)
    render_master_slide(
        "6_Audio_Streaming_1920x1080.png",
        "🎧", "48kHz LOSSLESS AUDIO RELAY",
        "LIVE STEREO AUDIO",
        "STREAMED TO EARBUDS",
        "Listen to PC games, YouTube, Spotify, and movies privately through your wireless earbuds over Wi-Fi with zero audio cables.",
        [
            "🔊 High-Fidelity 48kHz Stereo PCM",
            "⚡ Real-Time Zero-Lag Audio Loopback",
            "⏯️ Full Media Playback & Volume Deck"
        ],
        phone_audio,
        mockup_pos=(1140, 85),
        primary_color=YELLOW_ACCENT,
        secondary_color=ORANGE_ACCENT,
        glow_pos=(0.78, 0.5)
    )

    # SLIDE 7: INSTANT QR CODE PAIRING
    print("\n[+] 7. Slide 7: Instant QR Pairing...")
    phone_qr = create_phone_mockup_pro(img_qr_v, is_horizontal=False, target_size=820, glow_accent=CYAN_ACCENT)
    render_master_slide(
        "7_Instant_QR_Pairing_1920x1080.png",
        "📷", "1-TAP LOCAL CONNECTION",
        "INSTANT 3-SECOND",
        "QR CODE PAIRING",
        "Point your camera at the QR code displayed on your PC screen to pair instantly across any shared Wi-Fi or Mobile Hotspot.",
        [
            "📷 Built-In High-Speed QR Scanner",
            "🌐 Seamless Local LAN & Hotspot Support",
            "⚡ Zero Login, Zero Signup, Zero Cloud"
        ],
        phone_qr,
        mockup_pos=(1140, 85),
        primary_color=CYAN_ACCENT,
        secondary_color=LIME_ACCENT,
        glow_pos=(0.78, 0.5)
    )

    # SLIDE 8: OFFICIAL FEATURE GRAPHIC (1024x500)
    print("\n[+] 8. Slide 8: Official Feature Graphic (1024x500)...")
    generate_feature_graphic_pro(pc_window, img_trackpad_v)

    print("\n=======================================================")
    print("OK: ALL 8 REFINED ASSETS GENERATED IN 'playstore_assets/'")
    print("=======================================================\n")


def generate_feature_graphic_pro(pc_window, img_trackpad):
    """Generates the official 1024x500 Feature Graphic with premium visual balance."""
    W, H = 1024, 500
    canvas = create_premium_background(W, H, primary_color=CYAN_ACCENT, secondary_color=LIME_ACCENT, glow_pos=(0.7, 0.5))
    draw = ImageDraw.Draw(canvas)

    font_badge = get_font(14, bold=True)
    font_t1 = get_font(38, bold=True)
    font_t2 = get_font(38, bold=True)
    font_sub = get_font(18, bold=False)
    font_pill = get_font(14, bold=True)

    # Badge Pill
    b_text = "⚡ 100% OFFLINE PC UTILITY SUITE"
    draw.rounded_rectangle([48, 65, 300, 95], radius=15, fill=(0, 240, 255, 30), outline=(0, 240, 255, 180), width=1)
    draw.text((62, 71), b_text, font=font_badge, fill=CYAN_ACCENT)

    # Title
    draw.text((48, 115), "PC DECK", font=font_t1, fill=TEXT_WHITE)
    draw.text((48, 162), "WIRELESS REMOTE", font=font_t2, fill=CYAN_ACCENT)

    # Subtitle
    draw.text((48, 225), "Precision Trackpad • Mechanical Keyboard", font=font_sub, fill=TEXT_MUTED)
    draw.text((48, 252), "60 FPS Screen Mirroring • Gigabit File Transfer", font=font_sub, fill=TEXT_MUTED)

    # Pills
    pills = ["⚡ 0ms Latency", "🔒 100% Offline", "🎧 Stereo Audio"]
    cx = 48
    for p in pills:
        pw = font_pill.getbbox(p)[2] - font_pill.getbbox(p)[0] + 30
        draw.rounded_rectangle([cx, 320, cx + pw, 356], radius=10, fill=CARD_BG, outline=CARD_BORDER, width=1)
        draw.rounded_rectangle([cx + 4, 328, cx + 7, 348], radius=2, fill=CYAN_ACCENT)
        draw.text((cx + 14, 328), p, font=font_pill, fill=TEXT_WHITE)
        cx += pw + 12

    # Mockups
    pc_mock = create_pc_window_mockup_pro(pc_window, target_width=370, glow_accent=CYAN_ACCENT)
    phone_mock = create_phone_mockup_pro(img_trackpad, is_horizontal=False, target_size=420, glow_accent=CYAN_ACCENT)

    canvas.paste(pc_mock, (430, 95), pc_mock)
    canvas.paste(phone_mock, (635, 35), phone_mock)

    out_file = os.path.join(OUTPUT_DIR, "Feature_Graphic_1024x500.png")
    canvas.convert("RGB").save(out_file, quality=95)
    print(f"OK: Generated Feature Graphic '{out_file}'")


if __name__ == "__main__":
    generate_all_showcase()
