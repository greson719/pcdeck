"""
PCDeck — Final Master Google Play Store Showcase Assets Generator
Incorporates high-resolution PC desktop wallpaper, multi-touch finger ripples,
PC cursor motion trails, and user's QR scanner viewfinder.
"""

import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUTPUT_DIR = "playstore_assets"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Obsidian Cyber-Neon Palette
BG_OBSIDIAN = (6, 9, 16)
CYAN_ACCENT = (0, 240, 255)
LIME_ACCENT = (0, 255, 102)
PURPLE_ACCENT = (168, 85, 247)
YELLOW_ACCENT = (255, 220, 0)
ORANGE_ACCENT = (255, 120, 0)
TEXT_WHITE = (255, 255, 255)
TEXT_MUTED = (165, 180, 205)
CARD_BG = (15, 22, 36, 250)
CARD_BORDER = (45, 65, 98, 255)


def get_font(size, bold=False):
    font_path = "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"
    if not os.path.exists(font_path):
        font_path = "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"
    return ImageFont.truetype(font_path, size)


def create_premium_background(width, height, primary_color=(0, 240, 255), secondary_color=(0, 255, 102), glow_pos=(0.75, 0.5)):
    bg = Image.new("RGBA", (width, height), BG_OBSIDIAN)
    draw = ImageDraw.Draw(bg)

    # 1. Base Gradient
    for y in range(height):
        ratio = y / height
        r = int(6 + (14 - 6) * ratio)
        g = int(9 + (20 - 9) * ratio)
        b = int(16 + (36 - 16) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

    # 2. Geometric Tech Grid
    grid_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    grid_draw = ImageDraw.Draw(grid_img)
    spacing = 60
    for x in range(0, width, spacing):
        grid_draw.line([(x, 0), (x, height)], fill=(255, 255, 255, 6), width=1)
    for y in range(0, height, spacing):
        grid_draw.line([(0, y), (width, y)], fill=(255, 255, 255, 6), width=1)
    bg = Image.alpha_composite(bg, grid_img)

    # 3. Ambient Primary Glow
    glow1 = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    g1_draw = ImageDraw.Draw(glow1)
    gx1, gy1 = int(width * glow_pos[0]), int(height * glow_pos[1])
    r1 = int(min(width, height) * 0.8)
    for r in range(r1, 0, -10):
        alpha = int(85 * (1.0 - (r / r1) ** 1.2))
        g1_draw.ellipse([gx1 - r, gy1 - r, gx1 + r, gy1 + r], fill=(primary_color[0], primary_color[1], primary_color[2], alpha))
    glow1 = glow1.filter(ImageFilter.GaussianBlur(radius=55))
    bg = Image.alpha_composite(bg, glow1)

    # 4. Secondary Glow
    glow2 = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    g2_draw = ImageDraw.Draw(glow2)
    gx2, gy2 = int(width * 0.12), int(height * 0.88)
    r2 = int(min(width, height) * 0.45)
    for r in range(r2, 0, -15):
        alpha = int(35 * (1.0 - (r / r2) ** 1.4))
        g2_draw.ellipse([gx2 - r, gy2 - r, gx2 + r, gy2 + r], fill=(secondary_color[0], secondary_color[1], secondary_color[2], alpha))
    glow2 = glow2.filter(ImageFilter.GaussianBlur(radius=45))
    bg = Image.alpha_composite(bg, glow2)

    return bg


def create_phone_mockup_max(screen_img, is_horizontal=False, target_size=None, glow_accent=(0, 240, 255)):
    orig_w, orig_h = screen_img.size

    bezel = 10
    corner_radius = 34
    screen_radius = 24

    if is_horizontal:
        target_w = target_size or 1080
        frame_w = target_w
        frame_h = int(target_w * (orig_h / orig_w)) + (bezel * 2)
    else:
        target_h = target_size or 980
        frame_h = target_h
        frame_w = int(target_h * (orig_w / orig_h)) + (bezel * 2)

    screen_w = frame_w - (bezel * 2)
    screen_h = frame_h - (bezel * 2)

    screen_resized = screen_img.convert("RGB").resize((screen_w, screen_h), Image.Resampling.LANCZOS).convert("RGBA")

    screen_mask = Image.new("L", (screen_w, screen_h), 0)
    s_draw = ImageDraw.Draw(screen_mask)
    s_draw.rounded_rectangle([0, 0, screen_w, screen_h], radius=screen_radius, fill=255)

    frame = Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
    f_draw = ImageDraw.Draw(frame)

    f_draw.rounded_rectangle([0, 0, frame_w - 1, frame_h - 1], radius=corner_radius, fill=(22, 28, 44, 255), outline=glow_accent, width=2)
    f_draw.rounded_rectangle([2, 2, frame_w - 3, frame_h - 3], radius=corner_radius - 2, fill=(10, 14, 22, 255), outline=(48, 65, 96, 255), width=1)

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
    canvas = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))

    # Glowing Halo
    halo = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
    h_draw = ImageDraw.Draw(halo)
    h_draw.rounded_rectangle([pad - 16, pad - 12, pad + frame_w + 16, pad + frame_h + 20], radius=corner_radius + 16, fill=(glow_accent[0], glow_accent[1], glow_accent[2], 85))
    halo = halo.filter(ImageFilter.GaussianBlur(radius=32))
    canvas = Image.alpha_composite(canvas, halo)

    # 3D Drop Shadow
    shadow = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
    sh_draw = ImageDraw.Draw(shadow)
    sh_draw.rounded_rectangle([pad + 8, pad + 20, pad + frame_w + 8, pad + frame_h + 34], radius=corner_radius, fill=(0, 0, 0, 235))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=26))
    canvas = Image.alpha_composite(canvas, shadow)

    canvas.paste(frame, (pad, pad), frame)
    return canvas


def create_pc_window_mockup_max(window_img, target_width=800, glow_accent=(0, 240, 255)):
    orig_w, orig_h = window_img.size
    target_h = int(target_width * (orig_h / orig_w))

    resized = window_img.convert("RGB").resize((target_width, target_h), Image.Resampling.LANCZOS).convert("RGBA")
    corner_radius = 16

    mask = Image.new("L", (target_width, target_h), 0)
    m_draw = ImageDraw.Draw(mask)
    m_draw.rounded_rectangle([0, 0, target_width, target_h], radius=corner_radius, fill=255)

    frame = Image.new("RGBA", (target_width, target_h), (0, 0, 0, 0))
    frame.paste(resized, (0, 0), mask)

    f_draw = ImageDraw.Draw(frame)
    f_draw.rounded_rectangle([0, 0, target_width - 1, target_h - 1], radius=corner_radius, outline=glow_accent, width=2)

    pad = 50
    total_w = target_width + (pad * 2)
    total_h = target_h + (pad * 2)
    canvas = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))

    halo = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
    h_draw = ImageDraw.Draw(halo)
    h_draw.rounded_rectangle([pad - 14, pad - 10, pad + target_width + 14, pad + target_h + 18], radius=corner_radius + 12, fill=(glow_accent[0], glow_accent[1], glow_accent[2], 70))
    halo = halo.filter(ImageFilter.GaussianBlur(radius=30))
    canvas = Image.alpha_composite(canvas, halo)

    shadow = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
    sh_draw = ImageDraw.Draw(shadow)
    sh_draw.rounded_rectangle([pad + 8, pad + 18, pad + target_width + 8, pad + target_h + 30], radius=corner_radius, fill=(0, 0, 0, 235))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=24))
    canvas = Image.alpha_composite(canvas, shadow)

    canvas.paste(frame, (pad, pad), frame)
    return canvas


def draw_pc_mouse_cursor(draw, x, y):
    """Draws an authentic, sharp Windows mouse cursor with shadow."""
    points = [
        (x, y),
        (x, y + 36),
        (x + 9, y + 27),
        (x + 18, y + 43),
        (x + 25, y + 39),
        (x + 16, y + 24),
        (x + 28, y + 24)
    ]
    shadow_pts = [(px + 3, py + 3) for (px, py) in points]
    draw.polygon(shadow_pts, fill=(0, 0, 0, 180))
    draw.polygon(points, fill=(255, 255, 255, 255), outline=(0, 0, 0, 255))


def render_max_slide(
    filename,
    badge_label,
    title_line1,
    title_line2,
    subtitle_text,
    pills,
    mockup_img,
    mockup_pos=(980, 20),
    primary_color=CYAN_ACCENT,
    secondary_color=LIME_ACCENT,
    glow_pos=(0.75, 0.5)
):
    W, H = 1920, 1080
    canvas = create_premium_background(W, H, primary_color=primary_color, secondary_color=secondary_color, glow_pos=glow_pos)
    draw = ImageDraw.Draw(canvas)

    left_x = 75
    cur_y = 90

    # 1. Badge Pill
    font_badge = get_font(18, bold=True)
    bbox = font_badge.getbbox(badge_label)
    bw = bbox[2] - bbox[0] + 50
    bh = 40

    badge_img = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    b_draw = ImageDraw.Draw(badge_img)
    b_draw.rounded_rectangle([0, 0, bw - 1, bh - 1], radius=20, fill=(primary_color[0], primary_color[1], primary_color[2], 35), outline=(primary_color[0], primary_color[1], primary_color[2], 230), width=1)
    b_draw.ellipse([14, 15, 22, 23], fill=primary_color)
    b_draw.text((32, 9), badge_label, font=font_badge, fill=primary_color)
    canvas.paste(badge_img, (left_x, cur_y), badge_img)
    cur_y += bh + 26

    # 2. Headline
    font_t1 = get_font(58, bold=True)
    font_t2 = get_font(58, bold=True)
    draw.text((left_x, cur_y), title_line1, font=font_t1, fill=TEXT_WHITE)
    cur_y += 70
    draw.text((left_x, cur_y), title_line2, font=font_t2, fill=primary_color)
    cur_y += 86

    # 3. Subtitle
    font_sub = get_font(24, bold=False)
    words = subtitle_text.split()
    lines = []
    curr = []
    for w in words:
        curr.append(w)
        if font_sub.getbbox(" ".join(curr))[2] > 700:
            curr.pop()
            lines.append(" ".join(curr))
            curr = [w]
    if curr:
        lines.append(" ".join(curr))

    for line in lines:
        draw.text((left_x, cur_y), line, font=font_sub, fill=TEXT_MUTED)
        cur_y += 36
    cur_y += 42

    # 4. Feature Pills
    font_pill = get_font(20, bold=True)
    for p in pills:
        p_bbox = font_pill.getbbox(p)
        pw = p_bbox[2] - p_bbox[0] + 52
        ph = 54

        pill_card = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        p_draw = ImageDraw.Draw(pill_card)
        p_draw.rounded_rectangle([0, 0, pw - 1, ph - 1], radius=14, fill=CARD_BG, outline=CARD_BORDER, width=1)
        p_draw.rounded_rectangle([6, 12, 10, ph - 12], radius=2, fill=primary_color)
        p_draw.text((24, 14), p, font=font_pill, fill=TEXT_WHITE)
        canvas.paste(pill_card, (left_x, cur_y), pill_card)
        cur_y += ph + 16

    # 5. Device Mockup
    canvas.paste(mockup_img, mockup_pos, mockup_img)

    out_file = os.path.join(OUTPUT_DIR, filename)
    canvas.convert("RGB").save(out_file, quality=95)
    print(f"OK: Generated master slide '{out_file}'")


def generate_all_refined():
    transfers_dir = os.path.expanduser("~/Downloads/PCDeck_Transfers")

    # Screenshots
    pc_screen = Image.open(r"C:/Users/GRESON/.gemini/antigravity/brain/2d46a58c-baa8-41df-9298-244019d6e827/.user_uploaded/media_1787933647713.png")
    pc_window = pc_screen.crop((226, 38, 870, 529))

    # User uploaded high-res PC Desktop
    pc_desktop_hd = Image.open(r"C:/Users/GRESON/.gemini/antigravity/brain/2d46a58c-baa8-41df-9298-244019d6e827/.user_uploaded/media_1787948672035.jpg")

    # User uploaded exact QR Scanner viewfinder
    img_qr_viewfinder = Image.open(r"C:/Users/GRESON/.gemini/antigravity/brain/2d46a58c-baa8-41df-9298-244019d6e827/.user_uploaded/media_1787947871359.png")

    img_trackpad_raw = Image.open(os.path.join(transfers_dir, "Screenshot_20260828-214542.png"))  # Trackpad
    img_screen_stream = Image.open(os.path.join(transfers_dir, "Screenshot_20260828-214630.png"))  # 60FPS Screen Mirroring
    img_typing_keyboard = Image.open(os.path.join(transfers_dir, "Screenshot_20260828-214558.png"))  # Live Typing
    img_files = Image.open(os.path.join(transfers_dir, "Screenshot_20260828-214521.png"))  # File Manager
    img_audio_media = Image.open(os.path.join(transfers_dir, "Screenshot_20260828-214527.png"))  # 48kHz Stereo Audio

    # =========================================================================
    # SLIDE 1: HERO SUITE (PC App + Phone Trackpad)
    # =========================================================================
    print("\n[+] 1. Slide 1: Hero Suite...")
    pc_mock = create_pc_window_mockup_max(pc_window, target_width=780, glow_accent=CYAN_ACCENT)
    phone_hero = create_phone_mockup_max(img_trackpad_raw, is_horizontal=False, target_size=880, glow_accent=CYAN_ACCENT)
    
    hero_container = Image.new("RGBA", (1180, 1020), (0, 0, 0, 0))
    hero_container.paste(pc_mock, (0, 180), pc_mock)
    hero_container.paste(phone_hero, (550, 20), phone_hero)

    render_max_slide(
        "1_Hero_Suite_1920x1080.png",
        "PCDECK SUITE • WINDOWS & ANDROID",
        "WIRELESS PC CONTROL",
        "REDEFINED FOR ANDROID",
        "Transform your smartphone into an ultra-low-latency multi-touch trackpad, real-time screen mirror, and high-speed file transfer hub.",
        [
            "Sub-Millisecond Input Latency",
            "100% Offline — Zero Cloud Accounts",
            "1-Tap Pairing via QR Code & Wi-Fi"
        ],
        hero_container,
        mockup_pos=(750, 25),
        primary_color=CYAN_ACCENT,
        secondary_color=LIME_ACCENT,
        glow_pos=(0.75, 0.5)
    )

    # =========================================================================
    # SLIDE 2: MULTI-TOUCH TRACKPAD (WITH FINGER TOUCH & HD PC DESKTOP CURSOR)
    # =========================================================================
    print("\n[+] 2. Slide 2: Multi-Touch Trackpad with Finger Touch & HD PC Cursor...")
    # Add glowing finger touch ripple to the trackpad surface
    img_trackpad_with_touch = img_trackpad_raw.copy()
    t_draw = ImageDraw.Draw(img_trackpad_with_touch, "RGBA")
    
    # Touch Point 1 (Index finger gliding)
    cx1, cy1 = 440, 1200
    for r in range(120, 20, -10):
        alpha = int(90 * (1.0 - (r / 120) ** 1.5))
        t_draw.ellipse([cx1 - r, cy1 - r, cx1 + r, cy1 + r], fill=(0, 240, 255, alpha))
    t_draw.ellipse([cx1 - 22, cy1 - 22, cx1 + 22, cy1 + 22], fill=(255, 255, 255, 240), outline=(0, 240, 255, 255), width=4)

    # Touch Point 2 (Second finger gesture)
    cx2, cy2 = 640, 1140
    for r in range(90, 15, -10):
        alpha = int(75 * (1.0 - (r / 90) ** 1.5))
        t_draw.ellipse([cx2 - r, cy2 - r, cx2 + r, cy2 + r], fill=(0, 255, 102, alpha))
    t_draw.ellipse([cx2 - 18, cy2 - 18, cx2 + 18, cy2 + 18], fill=(255, 255, 255, 240), outline=(0, 255, 102, 255), width=3)

    # Use the high-res PC desktop uploaded by user!
    pc_desktop_mock = create_pc_window_mockup_max(pc_desktop_hd, target_width=740, glow_accent=CYAN_ACCENT)
    
    # Draw Windows Mouse Cursor actively hovering on PC desktop
    pc_draw = ImageDraw.Draw(pc_desktop_mock)
    draw_pc_mouse_cursor(pc_draw, 440, 260)
    
    # Glowing cursor pulse on PC desktop
    for r in range(60, 10, -8):
        alpha = int(80 * (1.0 - (r / 60) ** 1.4))
        pc_draw.ellipse([440 - r, 260 - r, 440 + r, 260 + r], fill=(0, 240, 255, alpha))

    phone_trackpad_mock = create_phone_mockup_max(img_trackpad_with_touch, is_horizontal=False, target_size=960, glow_accent=CYAN_ACCENT)

    slide2_container = Image.new("RGBA", (1160, 1020), (0, 0, 0, 0))
    slide2_container.paste(pc_desktop_mock, (0, 180), pc_desktop_mock)
    slide2_container.paste(phone_trackpad_mock, (540, 15), phone_trackpad_mock)

    render_max_slide(
        "2_MultiTouch_Trackpad_1920x1080.png",
        "BALLISTIC CURSOR ENGINE",
        "MULTI-TOUCH",
        "PRECISION TRACKPAD",
        "Touch gestures on your phone instantly drive the Windows cursor with smooth ballistic acceleration and sub-millisecond precision.",
        [
            "1-Finger Glide: Instant PC Cursor Motion",
            "2-Finger Tap: Context Right Click Menu",
            "Dedicated Scroll Strip with Kinetic Inertia"
        ],
        slide2_container,
        mockup_pos=(750, 25),
        primary_color=CYAN_ACCENT,
        secondary_color=PURPLE_ACCENT,
        glow_pos=(0.78, 0.5)
    )

    # =========================================================================
    # SLIDE 3: 60 FPS REAL-TIME SCREEN STREAMING (WITH HD DESKTOP SOURCE)
    # =========================================================================
    print("\n[+] 3. Slide 3: Real-Time Screen Streaming...")
    phone_stream = create_phone_mockup_max(img_screen_stream, is_horizontal=True, target_size=1080, glow_accent=LIME_ACCENT)
    render_max_slide(
        "3_Screen_Mirroring_1920x1080.png",
        "60 FPS DESKTOP MIRRORING",
        "REAL-TIME ZERO-LAG",
        "PC SCREEN STREAMING",
        "Stream your Windows desktop directly to your phone at 60 FPS with 1:1 physical direct touch tracking and kinetic fling inertia.",
        [
            "60 FPS Low-Latency Adaptive Stream",
            "1:1 Direct Touch Velocity Tracking",
            "Full-Resolution Display Mirroring"
        ],
        phone_stream,
        mockup_pos=(750, 220),
        primary_color=LIME_ACCENT,
        secondary_color=CYAN_ACCENT,
        glow_pos=(0.75, 0.55)
    )

    # =========================================================================
    # SLIDE 4: LIVE ON-SCREEN KEYBOARD & TYPING
    # =========================================================================
    print("\n[+] 4. Slide 4: Live On-Screen Typing...")
    phone_typing = create_phone_mockup_max(img_typing_keyboard, is_horizontal=True, target_size=1080, glow_accent=PURPLE_ACCENT)
    render_max_slide(
        "4_Live_Keyboard_Typing_1920x1080.png",
        "REAL-TIME TEXT INPUT",
        "LIVE ON-SCREEN",
        "KEYBOARD & TYPING",
        "Type on your phone keyboard and send keystrokes directly to your Windows desktop with instant Unicode synchronization.",
        [
            "Real-Time Keystroke Synchronization",
            "Slide-Up Quick Type Input Bar",
            "1-Tap Copy, Paste & Search Hotkeys"
        ],
        phone_typing,
        mockup_pos=(750, 220),
        primary_color=PURPLE_ACCENT,
        secondary_color=CYAN_ACCENT,
        glow_pos=(0.75, 0.55)
    )

    # =========================================================================
    # SLIDE 5: HIGH-SPEED LOCAL FILE TRANSFER
    # =========================================================================
    print("\n[+] 5. Slide 5: High-Speed File Transfer...")
    phone_files = create_phone_mockup_max(img_files, is_horizontal=False, target_size=980, glow_accent=CYAN_ACCENT)
    render_max_slide(
        "5_File_Transfer_1920x1080.png",
        "CABLE-FREE LOCAL STORAGE",
        "HIGH-SPEED LOCAL",
        "FILE SHARING & STORAGE",
        "Transfer 4K videos, documents, and archives directly between your PC and phone at full Wi-Fi speeds with auto-resume support.",
        [
            "Unthrottled Gigabit Wi-Fi Speeds",
            "Automatic Chunk Streaming & Resume",
            "Dedicated PC & Phone File Explorers"
        ],
        phone_files,
        mockup_pos=(980, 20),
        primary_color=CYAN_ACCENT,
        secondary_color=YELLOW_ACCENT,
        glow_pos=(0.78, 0.5)
    )

    # =========================================================================
    # SLIDE 6: LIVE STEREO PC AUDIO & MEDIA DECK
    # =========================================================================
    print("\n[+] 6. Slide 6: Live Stereo Audio...")
    phone_audio = create_phone_mockup_max(img_audio_media, is_horizontal=False, target_size=980, glow_accent=YELLOW_ACCENT)
    render_max_slide(
        "6_Audio_Streaming_1920x1080.png",
        "48kHz LOSSLESS AUDIO RELAY",
        "LIVE STEREO AUDIO",
        "STREAMED TO EARBUDS",
        "Listen to PC games, YouTube, Spotify, and movies privately through your wireless earbuds over Wi-Fi with zero audio cables.",
        [
            "High-Fidelity 48kHz Stereo PCM",
            "Real-Time Zero-Lag Audio Loopback",
            "Full Media Playback & Volume Deck"
        ],
        phone_audio,
        mockup_pos=(980, 20),
        primary_color=YELLOW_ACCENT,
        secondary_color=ORANGE_ACCENT,
        glow_pos=(0.78, 0.5)
    )

    # =========================================================================
    # SLIDE 7: 1-TAP QR CODE PAIRING (USER UPLOADED SCANNER VIEW)
    # =========================================================================
    print("\n[+] 7. Slide 7: 1-Tap QR Code Scanning (Using media_1787947871359.png)...")
    phone_qr_scanner = create_phone_mockup_max(img_qr_viewfinder, is_horizontal=False, target_size=920, glow_accent=YELLOW_ACCENT)
    pc_qr_window = create_pc_window_mockup_max(pc_window, target_width=720, glow_accent=CYAN_ACCENT)

    slide7_container = Image.new("RGBA", (1150, 1020), (0, 0, 0, 0))
    slide7_container.paste(pc_qr_window, (0, 180), pc_qr_window)
    slide7_container.paste(phone_qr_scanner, (520, 20), phone_qr_scanner)

    render_max_slide(
        "7_Instant_QR_Pairing_1920x1080.png",
        "1-TAP INSTANT CONNECTION",
        "QUICK 3-SECOND",
        "QR CODE PAIRING",
        "Point your phone camera at the QR code on your PC screen to pair instantly over local Wi-Fi or mobile hotspot — zero typing required.",
        [
            "Instant Optical QR Auto-Connect",
            "Seamless Local Wi-Fi & Hotspot LAN",
            "Zero Cloud Servers or Accounts Needed"
        ],
        slide7_container,
        mockup_pos=(750, 25),
        primary_color=YELLOW_ACCENT,
        secondary_color=CYAN_ACCENT,
        glow_pos=(0.75, 0.5)
    )

    # =========================================================================
    # SLIDE 8: OFFICIAL FEATURE GRAPHIC (1024x500)
    # =========================================================================
    print("\n[+] 8. Slide 8: Official Feature Graphic (1024x500)...")
    generate_feature_graphic_max(pc_window, img_trackpad_with_touch)

    print("\n=======================================================")
    print("OK: ALL 8 MASTER PLAY STORE ASSETS FULLY GENERATED!")
    print("=======================================================\n")


def generate_feature_graphic_max(pc_window, img_trackpad):
    W, H = 1024, 500
    canvas = create_premium_background(W, H, primary_color=CYAN_ACCENT, secondary_color=LIME_ACCENT, glow_pos=(0.7, 0.5))
    draw = ImageDraw.Draw(canvas)

    font_badge = get_font(14, bold=True)
    font_t1 = get_font(42, bold=True)
    font_t2 = get_font(42, bold=True)
    font_sub = get_font(18, bold=False)
    font_pill = get_font(14, bold=True)

    b_text = "100% OFFLINE PC UTILITY SUITE"
    draw.rounded_rectangle([48, 55, 310, 87], radius=16, fill=(0, 240, 255, 30), outline=(0, 240, 255, 180), width=1)
    draw.ellipse([60, 67, 68, 75], fill=CYAN_ACCENT)
    draw.text((76, 63), b_text, font=font_badge, fill=CYAN_ACCENT)

    draw.text((48, 102), "PC DECK", font=font_t1, fill=TEXT_WHITE)
    draw.text((48, 150), "WIRELESS REMOTE", font=font_t2, fill=CYAN_ACCENT)

    draw.text((48, 218), "Precision Trackpad • Live Screen Mirroring", font=font_sub, fill=TEXT_MUTED)
    draw.text((48, 245), "48kHz Stereo Audio • Gigabit File Transfers", font=font_sub, fill=TEXT_MUTED)

    pills = ["0ms Latency", "100% Offline", "Stereo Audio"]
    cx = 48
    for p in pills:
        pw = font_pill.getbbox(p)[2] - font_pill.getbbox(p)[0] + 32
        draw.rounded_rectangle([cx, 315, cx + pw, 351], radius=10, fill=CARD_BG, outline=CARD_BORDER, width=1)
        draw.rounded_rectangle([cx + 5, 323, cx + 8, 343], radius=2, fill=CYAN_ACCENT)
        draw.text((cx + 16, 323), p, font=font_pill, fill=TEXT_WHITE)
        cx += pw + 12

    pc_mock = create_pc_window_mockup_max(pc_window, target_width=440, glow_accent=CYAN_ACCENT)
    phone_mock = create_phone_mockup_max(img_trackpad, is_horizontal=False, target_size=470, glow_accent=CYAN_ACCENT)

    canvas.paste(pc_mock, (410, 70), pc_mock)
    canvas.paste(phone_mock, (665, 10), phone_mock)

    out_file = os.path.join(OUTPUT_DIR, "Feature_Graphic_1024x500.png")
    canvas.convert("RGB").save(out_file, quality=95)
    print(f"OK: Generated Feature Graphic '{out_file}'")


if __name__ == "__main__":
    generate_all_refined()
