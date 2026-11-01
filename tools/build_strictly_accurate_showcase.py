"""
PCDeck — Master Showcase Generator (Updated with QR In-Scanner Overlay, Zoomed Audio UI, and Screen Streaming Banner)
"""

import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from hand_renderer import draw_realistic_hand_operating_phone

OUTPUT_DIR = "playstore_assets"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Obsidian Cyber-Neon Palette
BG_OBSIDIAN = (10, 14, 23)
SURFACE_CARD = (19, 25, 38, 252)
CARD_BORDER = (45, 60, 90, 255)
CYAN = (0, 240, 255)
LIME = (0, 255, 102)
PURPLE = (168, 85, 247)
YELLOW = (255, 220, 0)
WHITE = (255, 255, 255)
TEXT_MUTED = (165, 180, 205)


def get_font(size, bold=False):
    font_path = "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"
    if not os.path.exists(font_path):
        font_path = "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"
    return ImageFont.truetype(font_path, size)


def create_base_canvas(width, height, accent_color=CYAN, glow_center=(0.75, 0.5)):
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


def make_phone_frame(screen_img, is_horizontal=False, target_size=980, accent=CYAN):
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


def make_pc_window_frame(window_img, target_width=760, accent=CYAN):
    orig_w, orig_h = window_img.size
    target_h = int(target_width * (orig_h / orig_w))

    resized = window_img.convert("RGB").resize((target_width, target_h), Image.Resampling.LANCZOS).convert("RGBA")
    corner_r = 16

    mask = Image.new("L", (target_width, target_h), 0)
    m_draw = ImageDraw.Draw(mask)
    m_draw.rounded_rectangle([0, 0, target_width, target_h], radius=corner_r, fill=255)

    frame = Image.new("RGBA", (target_width, target_h), (0, 0, 0, 0))
    frame.paste(resized, (0, 0), mask)

    f_draw = ImageDraw.Draw(frame)
    f_draw.rounded_rectangle([0, 0, target_width - 1, target_h - 1], radius=corner_r, outline=accent, width=2)

    pad = 50
    total_w = target_width + (pad * 2)
    total_h = target_h + (pad * 2)
    container = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))

    halo = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
    h_draw = ImageDraw.Draw(halo)
    h_draw.rounded_rectangle([pad - 14, pad - 10, pad + target_width + 14, pad + target_h + 18], radius=corner_r + 12, fill=(accent[0], accent[1], accent[2], 65))
    halo = halo.filter(ImageFilter.GaussianBlur(radius=28))
    container = Image.alpha_composite(container, halo)

    shadow = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
    sh_draw = ImageDraw.Draw(shadow)
    sh_draw.rounded_rectangle([pad + 8, pad + 18, pad + target_width + 8, pad + target_h + 30], radius=corner_r, fill=(0, 0, 0, 230))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=24))
    container = Image.alpha_composite(container, shadow)

    container.paste(frame, (pad, pad), frame)
    return container


def draw_clean_windows_cursor(canvas, x, y):
    pts = [
        (x, y),
        (x, y + 36),
        (x + 9, y + 27),
        (x + 18, y + 43),
        (x + 25, y + 39),
        (x + 16, y + 24),
        (x + 28, y + 24)
    ]
    draw = ImageDraw.Draw(canvas)
    shadow_pts = [(px + 3, py + 3) for (px, py) in pts]
    draw.polygon(shadow_pts, fill=(0, 0, 0, 180))
    draw.polygon(pts, fill=(255, 255, 255, 255), outline=(0, 0, 0, 255))


def render_slide(filename, badge_text, line1, line2, subtitle, bullet_points, mockup_container, mockup_pos=(750, 25), accent=CYAN):
    W, H = 1920, 1080
    canvas = create_base_canvas(W, H, accent_color=accent)
    draw = ImageDraw.Draw(canvas)

    left_x = 75
    cur_y = 90

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
    cur_y += bh + 26

    # 2. Headline
    font_t1 = get_font(56, bold=True)
    font_t2 = get_font(56, bold=True)
    draw.text((left_x, cur_y), line1, font=font_t1, fill=WHITE)
    cur_y += 68
    draw.text((left_x, cur_y), line2, font=font_t2, fill=accent)
    cur_y += 84

    # 3. Subtitle
    font_sub = get_font(23, bold=False)
    words = subtitle.split()
    lines = []
    curr = []
    for w in words:
        curr.append(w)
        if font_sub.getbbox(" ".join(curr))[2] > 680:
            curr.pop()
            lines.append(" ".join(curr))
            curr = [w]
    if curr:
        lines.append(" ".join(curr))

    for line in lines:
        draw.text((left_x, cur_y), line, font=font_sub, fill=TEXT_MUTED)
        cur_y += 34
    cur_y += 40

    # 4. Feature Cards
    font_pill = get_font(19, bold=True)
    for bp in bullet_points:
        p_bbox = font_pill.getbbox(bp)
        pw = p_bbox[2] - p_bbox[0] + 50
        ph = 52

        card = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        c_draw = ImageDraw.Draw(card)
        c_draw.rounded_rectangle([0, 0, pw - 1, ph - 1], radius=14, fill=SURFACE_CARD, outline=CARD_BORDER, width=1)
        c_draw.rounded_rectangle([6, 12, 10, ph - 12], radius=2, fill=accent)
        c_draw.text((24, 14), bp, font=font_pill, fill=WHITE)
        canvas.paste(card, (left_x, cur_y), card)
        cur_y += ph + 16

    # 5. Mockup
    canvas.paste(mockup_container, mockup_pos, mockup_container)

    out_path = os.path.join(OUTPUT_DIR, filename)
    canvas.convert("RGB").save(out_path, quality=95)
    print(f"OK: Saved {out_path}")


def generate_all():
    transfers_dir = os.path.expanduser("~/Downloads/PCDeck_Transfers")

    # Load Actual Assets
    pc_screen_full = Image.open(r"C:/Users/GRESON/.gemini/antigravity/brain/2d46a58c-baa8-41df-9298-244019d6e827/.user_uploaded/media_1787933647713.png")
    pc_server_window = pc_screen_full.crop((226, 38, 870, 529))

    # User uploaded desktop
    pc_desktop_hd = Image.open(r"C:/Users/GRESON/.gemini/antigravity/brain/2d46a58c-baa8-41df-9298-244019d6e827/.user_uploaded/media_1787948672035.jpg")

    # User uploaded QR scanner viewfinder
    phone_qr_viewfinder = Image.open(r"C:/Users/GRESON/.gemini/antigravity/brain/2d46a58c-baa8-41df-9298-244019d6e827/.user_uploaded/media_1787947871359.png").convert("RGBA")

    img_trackpad_raw = Image.open(os.path.join(transfers_dir, "Screenshot_20260828-214542.png"))
    img_screen_stream = Image.open(os.path.join(transfers_dir, "Screenshot_20260828-214630.png"))
    img_typing = Image.open(os.path.join(transfers_dir, "Screenshot_20260828-214558.png"))
    img_files = Image.open(os.path.join(transfers_dir, "Screenshot_20260828-214521.png"))
    img_media_full = Image.open(os.path.join(transfers_dir, "Screenshot_20260828-214527.png"))

    # =========================================================================
    # SLIDE 1: HERO SUITE (PC Server + Phone Trackpad)
    # =========================================================================
    pc_mock = make_pc_window_frame(pc_server_window, target_width=760, accent=CYAN)
    phone_hero = make_phone_frame(img_trackpad_raw, is_horizontal=False, target_size=880, accent=CYAN)
    s1_box = Image.new("RGBA", (1180, 1020), (0, 0, 0, 0))
    s1_box.paste(pc_mock, (0, 180), pc_mock)
    s1_box.paste(phone_hero, (550, 20), phone_hero)

    render_slide(
        "1_Hero_Suite_1920x1080.png",
        "PCDECK SUITE • WINDOWS & ANDROID",
        "WIRELESS PC CONTROL",
        "REDEFINED FOR ANDROID",
        "Turn your Android smartphone into an ultra-low-latency wireless trackpad, 60 FPS desktop screen mirror, and high-speed local file transfer hub.",
        [
            "Sub-Millisecond Input Latency",
            "100% Offline Local Wi-Fi & Hotspot",
            "Instant 1-Tap QR Code Pairing"
        ],
        s1_box,
        mockup_pos=(750, 25),
        accent=CYAN
    )

    # =========================================================================
    # SLIDE 2: MULTI-TOUCH TRACKPAD (ZOOMED DESKTOP + HAND OPERATING PHONE)
    # =========================================================================
    w_hd, h_hd = pc_desktop_hd.size
    zoomed_desktop = pc_desktop_hd.crop((0, int(h_hd * 0.15), int(w_hd * 0.75), int(h_hd * 0.95)))
    pc_zoomed_mock = make_pc_window_frame(zoomed_desktop, target_width=760, accent=CYAN)
    draw_clean_windows_cursor(pc_zoomed_mock, 340, 210)
    
    phone_trackpad_mock = make_phone_frame(img_trackpad_raw, is_horizontal=False, target_size=960, accent=CYAN)

    s2_box = Image.new("RGBA", (1180, 1020), (0, 0, 0, 0))
    s2_box.paste(pc_zoomed_mock, (0, 180), pc_zoomed_mock)
    s2_box.paste(phone_trackpad_mock, (540, 15), phone_trackpad_mock)
    draw_realistic_hand_operating_phone(s2_box, tip_x=765, tip_y=585)

    render_slide(
        "2_MultiTouch_Trackpad_1920x1080.png",
        "BALLISTIC CURSOR ENGINE",
        "MULTI-TOUCH",
        "PRECISION TRACKPAD",
        "Touch gestures on your phone instantly drive the Windows cursor with smooth ballistic acceleration and sub-pixel Win32 accumulator precision.",
        [
            "1-Finger Drag: Ballistic Motion & Left Click",
            "2-Finger Tap: Instant Right Click Menu",
            "Dedicated Scroll Strip with Kinetic Inertia"
        ],
        s2_box,
        mockup_pos=(740, 25),
        accent=CYAN
    )

    # =========================================================================
    # SLIDE 3: 60 FPS REAL-TIME SCREEN STREAMING
    # =========================================================================
    phone_stream = make_phone_frame(img_screen_stream, is_horizontal=True, target_size=1080, accent=LIME)
    render_slide(
        "3_Screen_Mirroring_1920x1080.png",
        "60 FPS DESKTOP MIRRORING",
        "REAL-TIME ZERO-LAG",
        "PC SCREEN STREAMING",
        "Stream your Windows desktop directly to your phone at 60 FPS with 1:1 physical direct touch tracking and kinetic fling momentum.",
        [
            "60 FPS Low-Latency Adaptive JPEG Stream",
            "1:1 Direct Touch Velocity & Scroll Physics",
            "Full-Resolution Desktop Viewport"
        ],
        phone_stream,
        mockup_pos=(750, 220),
        accent=LIME
    )

    # =========================================================================
    # SLIDE 4: LIVE ON-SCREEN KEYBOARD & TYPING
    # =========================================================================
    phone_typing = make_phone_frame(img_typing, is_horizontal=True, target_size=1080, accent=PURPLE)
    render_slide(
        "4_Live_Keyboard_Typing_1920x1080.png",
        "REAL-TIME TEXT INPUT",
        "LIVE ON-SCREEN",
        "KEYBOARD & TYPING",
        "Type on your mobile keyboard and dispatch keystrokes directly into active Windows applications, browsers, or games.",
        [
            "Real-Time Unicode Keystroke Sync",
            "Slide-Up Quick Type Input Bar",
            "Full Functional & Navigation Keys"
        ],
        phone_typing,
        mockup_pos=(750, 220),
        accent=PURPLE
    )

    # =========================================================================
    # SLIDE 5: HIGH-SPEED LOCAL FILE TRANSFER
    # =========================================================================
    phone_files = make_phone_frame(img_files, is_horizontal=False, target_size=980, accent=CYAN)
    render_slide(
        "5_File_Transfer_1920x1080.png",
        "CABLE-FREE LOCAL STORAGE",
        "HIGH-SPEED LOCAL",
        "FILE SHARING & STORAGE",
        "Transfer 4K videos, documents, and archives directly between your PC and phone at full Wi-Fi speeds with auto-resume support.",
        [
            "Gigabit Local Wi-Fi Chunk Streaming",
            "Automatic Range Header Resume Support",
            "Dedicated PC & Phone File Explorers"
        ],
        phone_files,
        mockup_pos=(980, 20),
        accent=CYAN
    )

    # =========================================================================
    # SLIDE 6: LIVE STEREO AUDIO & MEDIA DECK (ZOOMED TO CORE FUNCTIONALITIES)
    # =========================================================================
    # Crop to focus purely on the Audio Card + Media Deck + Windows Shortcuts
    # Removing empty background and bottom thumbnails
    audio_zoomed = img_media_full.crop((0, 100, 1080, 1920))
    phone_media_zoomed = make_phone_frame(audio_zoomed, is_horizontal=False, target_size=980, accent=YELLOW)
    render_slide(
        "6_Audio_Streaming_1920x1080.png",
        "48kHz LOSSLESS AUDIO RELAY",
        "LIVE STEREO AUDIO",
        "STREAMED TO EARBUDS",
        "Listen to PC games, YouTube, Spotify, and movies privately through your wireless earbuds over Wi-Fi with zero audio cables.",
        [
            "High-Fidelity 48kHz Stereo PCM Relay",
            "Real-Time Zero-Lag Audio Loopback",
            "Full Media Playback & Hotkey Deck"
        ],
        phone_media_zoomed,
        mockup_pos=(980, 20),
        accent=YELLOW
    )

    # =========================================================================
    # SLIDE 7: 1-TAP QR CODE PAIRING (WITH QR CODE INSIDE SCANNER VIEWFINDER)
    # =========================================================================
    # Extract the PC server's QR code (from pc_screen_full)
    qr_code_crop = pc_screen_full.crop((406, 178, 574, 346)).convert("RGBA")
    
    # In phone_qr_viewfinder (460x1024), the reticle box is at (92, 365, 368, 641)
    # Size is 276x276. Let's resize QR code to fit inside reticle:
    qr_placed = qr_code_crop.resize((230, 230), Image.Resampling.LANCZOS)
    
    # Create composite phone scanner image
    scanner_with_qr = phone_qr_viewfinder.copy()
    scanner_with_qr.paste(qr_placed, (115, 388), qr_placed)

    # Add vibrant cyan laser scanning beam with glow across the QR code
    laser_overlay = Image.new("RGBA", scanner_with_qr.size, (0, 0, 0, 0))
    l_draw = ImageDraw.Draw(laser_overlay)
    beam_y = 480
    # Wide ambient glow
    l_draw.line([(96, beam_y), (364, beam_y)], fill=(0, 240, 255, 120), width=8)
    # Intense core laser
    l_draw.line([(96, beam_y), (364, beam_y)], fill=(255, 255, 255, 255), width=3)
    laser_overlay = laser_overlay.filter(ImageFilter.GaussianBlur(radius=3))
    scanner_with_qr = Image.alpha_composite(scanner_with_qr, laser_overlay)

    phone_qr_mock = make_phone_frame(scanner_with_qr, is_horizontal=False, target_size=920, accent=YELLOW)
    pc_qr_mock = make_pc_window_frame(pc_server_window, target_width=720, accent=CYAN)

    s7_box = Image.new("RGBA", (1150, 1020), (0, 0, 0, 0))
    s7_box.paste(pc_qr_mock, (0, 180), pc_qr_mock)
    s7_box.paste(phone_qr_mock, (520, 20), phone_qr_mock)

    render_slide(
        "7_Instant_QR_Pairing_1920x1080.png",
        "OPTICAL PAIRING ENGINE",
        "QUICK 3-SECOND",
        "QR CODE PAIRING",
        "Point your phone camera at the QR code on your PC screen to pair instantly over local Wi-Fi or mobile hotspot — zero typing required.",
        [
            "Instant Optical QR Auto-Connect",
            "Seamless Local Wi-Fi & Hotspot LAN",
            "100% Offline — Zero Cloud Accounts"
        ],
        s7_box,
        mockup_pos=(750, 25),
        accent=YELLOW
    )

    # =========================================================================
    # SLIDE 8: OFFICIAL FEATURE GRAPHIC BANNER (1024x500)
    # (Desktop Background + Phone Screen Streaming in Foreground)
    # =========================================================================
    generate_feature_graphic_screen_mirror(pc_desktop_hd, img_screen_stream)


def generate_feature_graphic_screen_mirror(pc_desktop_hd, img_screen_stream):
    W, H = 1024, 500
    canvas = create_base_canvas(W, H, accent_color=CYAN, glow_center=(0.7, 0.5))
    draw = ImageDraw.Draw(canvas)

    font_badge = get_font(14, bold=True)
    font_t1 = get_font(42, bold=True)
    font_t2 = get_font(42, bold=True)
    font_sub = get_font(18, bold=False)
    font_pill = get_font(14, bold=True)

    # Badge Pill
    b_text = "100% OFFLINE PC UTILITY SUITE"
    draw.rounded_rectangle([48, 55, 310, 87], radius=16, fill=(0, 240, 255, 30), outline=(0, 240, 255, 180), width=1)
    draw.ellipse([60, 67, 68, 75], fill=CYAN)
    draw.text((76, 63), b_text, font=font_badge, fill=CYAN)

    # Title
    draw.text((48, 102), "PC DECK", font=font_t1, fill=WHITE)
    draw.text((48, 150), "WIRELESS REMOTE", font=font_t2, fill=CYAN)

    # Subtitle
    draw.text((48, 218), "60 FPS Screen Mirror • Precision Trackpad", font=font_sub, fill=TEXT_MUTED)
    draw.text((48, 245), "48kHz Stereo Audio • Gigabit File Transfers", font=font_sub, fill=TEXT_MUTED)

    # Pills
    pills = ["60 FPS Mirror", "0ms Latency", "100% Offline"]
    cx = 48
    for p in pills:
        pw = font_pill.getbbox(p)[2] - font_pill.getbbox(p)[0] + 32
        draw.rounded_rectangle([cx, 315, cx + pw, 351], radius=10, fill=SURFACE_CARD, outline=CARD_BORDER, width=1)
        draw.rounded_rectangle([cx + 5, 323, cx + 8, 343], radius=2, fill=CYAN)
        draw.text((cx + 16, 323), p, font=font_pill, fill=WHITE)
        cx += pw + 12

    # In Background: PC Desktop Monitor Window
    pc_bg_window = make_pc_window_frame(pc_desktop_hd, target_width=460, accent=CYAN)
    draw_clean_windows_cursor(pc_bg_window, 280, 160)

    # In Foreground: Phone streaming the screen in landscape
    phone_mirror_mock = make_phone_frame(img_screen_stream, is_horizontal=True, target_size=480, accent=LIME)

    canvas.paste(pc_bg_window, (420, 60), pc_bg_window)
    canvas.paste(phone_mirror_mock, (510, 175), phone_mirror_mock)

    out_file = os.path.join(OUTPUT_DIR, "Feature_Graphic_1024x500.png")
    canvas.convert("RGB").save(out_file, quality=95)
    print(f"OK: Saved {out_file}")


if __name__ == "__main__":
    generate_all()
