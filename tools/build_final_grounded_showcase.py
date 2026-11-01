"""
PCDeck — Master Showcase Generator with User's Requested PC Monitor Template Outline
"""

import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from gesture_visualizer import draw_clean_touch_gesture
from cursor_helper import draw_prominent_windows_cursor

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


def make_iconic_pc_monitor(desktop_img, target_width=820, accent=CYAN):
    """
    Renders an authentic PC Desktop Monitor matching user's requested template:
    Sleek rounded bezel, top webcam, wide chin bezel, angled neck, and curved oval desktop stand.
    """
    screen_w = target_width
    screen_h = int(target_width * 0.5625)

    bezel_t = 16
    bezel_s = 16
    bezel_b = 32

    mon_w = screen_w + (bezel_s * 2)
    mon_h = screen_h + bezel_t + bezel_b

    neck_w_top = int(target_width * 0.12)
    neck_w_bot = int(target_width * 0.19)
    neck_h = int(target_width * 0.18)

    base_w = int(target_width * 0.48)
    base_h = int(target_width * 0.06)

    total_w = mon_w + 60
    total_h = mon_h + neck_h + base_h + 30

    canvas = Image.new('RGBA', (total_w, total_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    ox, oy = 30, 10
    base_cx = ox + mon_w // 2
    base_top_y = oy + mon_h + neck_h - 16

    # 1. Base Stand (curved oval pedestal)
    draw.ellipse([base_cx - base_w // 2, base_top_y, base_cx + base_w // 2, base_top_y + base_h], fill=(20, 28, 42, 255), outline=accent, width=2)

    # 2. Angled Trapezoid Stand Neck
    neck_top_y = oy + mon_h - 4
    draw.polygon([
        (base_cx - neck_w_top // 2, neck_top_y),
        (base_cx + neck_w_top // 2, neck_top_y),
        (base_cx + neck_w_bot // 2, base_top_y + base_h // 2),
        (base_cx - neck_w_bot // 2, base_top_y + base_h // 2)
    ], fill=(16, 22, 34, 255), outline=(45, 60, 90, 255))

    # 3. Main Monitor Chassis
    draw.rounded_rectangle([ox, oy, ox + mon_w, oy + mon_h], radius=16, fill=(18, 24, 38, 255), outline=accent, width=2)
    draw.line([(ox + 16, oy + mon_h - bezel_b), (ox + mon_w - 16, oy + mon_h - bezel_b)], fill=(35, 48, 70, 255), width=1)

    # 4. Insert PC Desktop Screen
    resized_screen = desktop_img.convert('RGB').resize((screen_w, screen_h), Image.Resampling.LANCZOS).convert('RGBA')
    canvas.paste(resized_screen, (ox + bezel_s, oy + bezel_t))

    # 5. Inner screen border
    draw.rectangle([ox + bezel_s, oy + bezel_t, ox + bezel_s + screen_w, oy + bezel_t + screen_h], outline=(0, 240, 255, 120), width=1)

    # 6. Top Center Webcam
    cam_x = ox + mon_w // 2
    draw.ellipse([cam_x - 3, oy + 5, cam_x + 3, oy + 11], fill=(5, 8, 12, 255), outline=(0, 240, 255, 150), width=1)

    # 7. Ambient glow
    halo = Image.new('RGBA', (total_w, total_h), (0, 0, 0, 0))
    h_draw = ImageDraw.Draw(halo)
    h_draw.rounded_rectangle([ox - 10, oy - 6, ox + mon_w + 10, oy + mon_h + 12], radius=24, fill=(accent[0], accent[1], accent[2], 50))
    halo = halo.filter(ImageFilter.GaussianBlur(radius=20))

    final_mon = Image.alpha_composite(halo, canvas)
    return final_mon


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

    # 1. Category Badge
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

    # User uploaded dedicated clean QR code
    user_qr_clean = Image.open(r"C:/Users/GRESON/.gemini/antigravity/brain/2d46a58c-baa8-41df-9298-244019d6e827/.user_uploaded/media_1788088742637.png" if os.path.exists(r"C:/Users/GRESON/.gemini/antigravity/brain/2d46a58c-baa8-41df-9298-244019d6e827/.user_uploaded/media_1788088742637.png") else r"C:/Users/GRESON/.gemini/antigravity/brain/2d46a58c-baa8-41df-9298-244019d6e827/.user_uploaded/media_1787988742637.png").convert("RGBA")

    img_trackpad_raw = Image.open(os.path.join(transfers_dir, "Screenshot_20260828-214542.png"))
    img_screen_stream = Image.open(os.path.join(transfers_dir, "Screenshot_20260828-214630.png"))
    img_typing = Image.open(os.path.join(transfers_dir, "Screenshot_20260828-214558.png"))
    img_files = Image.open(os.path.join(transfers_dir, "Screenshot_20260828-214521.png"))
    img_media_full = Image.open(os.path.join(transfers_dir, "Screenshot_20260828-214527.png"))

    # =========================================================================
    # SLIDE 1: HERO OVERVIEW (Zoomed & Right-Bottom Positioned PC Monitor + Foreground Phone)
    # =========================================================================
    from prominent_monitor import make_prominent_pc_monitor
    pc_hero_mon = make_prominent_pc_monitor(pc_desktop_hd, target_width=820, accent=CYAN)
    
    # Prominent natural Windows cursor with hover beacon on PC monitor
    draw_prominent_windows_cursor(pc_hero_mon, 400 + 40, 180 + 40, scale=1.0)

    # Phone showing the live mirrored desktop in foreground
    phone_hero_stream = make_phone_frame(img_screen_stream, is_horizontal=True, target_size=760, accent=CYAN)

    s1_box = Image.new("RGBA", (1180, 1020), (0, 0, 0, 0))
    # Zoomed PC Monitor positioned more to the right and bottom
    s1_box.paste(pc_hero_mon, (110, 45), pc_hero_mon)
    # Foreground Phone placed in lower-right
    s1_box.paste(phone_hero_stream, (320, 500), phone_hero_stream)

    # Luminous Ghost Hand Touch on Phone Screen
    from user_hand_slide1 import draw_user_provided_hand_slide1
    draw_user_provided_hand_slide1(s1_box, tip_target=(805, 695), hand_scale=190)

    render_slide(
        "1_Hero_Suite_1920x1080.png",
        "PCDECK UTILITY • WINDOWS & ANDROID",
        "WIRELESS PC CONTROL",
        "FROM YOUR SMARTPHONE",
        "Control and mirror your Windows desktop directly from your smartphone over local Wi-Fi with ultra-low latency touch and remote tools.",
        [
            "Multi-Touch Trackpad & Screen Mirror",
            "100% Offline Local Wi-Fi & Hotspot",
            "Direct 3-Second QR Code Pairing"
        ],
        s1_box,
        mockup_pos=(760, 15),
        accent=CYAN
    )

    # =========================================================================
    # SLIDE 2: MULTI-TOUCH TRACKPAD (PC Window + Phone Trackpad with Luminous Ghost Hand)
    # =========================================================================
    w_hd, h_hd = pc_desktop_hd.size
    zoomed_desktop = pc_desktop_hd.crop((0, int(h_hd * 0.15), int(w_hd * 0.75), int(h_hd * 0.95)))
    pc_zoomed_mock = make_pc_window_frame(zoomed_desktop, target_width=760, accent=CYAN)
    draw_clean_windows_cursor(pc_zoomed_mock, 340, 210)
    
    phone_trackpad_mock = make_phone_frame(img_trackpad_raw, is_horizontal=False, target_size=960, accent=CYAN)

    s2_box = Image.new("RGBA", (1180, 1020), (0, 0, 0, 0))
    s2_box.paste(pc_zoomed_mock, (0, 180), pc_zoomed_mock)
    s2_box.paste(phone_trackpad_mock, (540, 15), phone_trackpad_mock)

    # Kinetic link curve from PC cursor to trackpad touch point
    cursor_x = 340 + 50
    cursor_y = 210 + 180 + 50
    touch_x = 790
    touch_y = 470

    # Draw sleek kinetic dashed connection arc
    link_layer = Image.new("RGBA", s2_box.size, (0, 0, 0, 0))
    l_draw = ImageDraw.Draw(link_layer)
    pts = []
    for t in range(0, 101, 2):
        u = t / 100.0
        # Quadratic bezier control point
        ctrl_x, ctrl_y = (cursor_x + touch_x) // 2, min(cursor_y, touch_y) - 80
        px = (1 - u)**2 * cursor_x + 2 * (1 - u) * u * ctrl_x + u**2 * touch_x
        py = (1 - u)**2 * cursor_y + 2 * (1 - u) * u * ctrl_y + u**2 * touch_y
        pts.append((px, py))
    
    for i in range(len(pts) - 1):
        if (i // 2) % 2 == 0:
            l_draw.line([pts[i], pts[i+1]], fill=(0, 240, 255, 140), width=2)
    
    # Cursor target pulse on PC window
    l_draw.ellipse([cursor_x - 14, cursor_y - 14, cursor_x + 14, cursor_y + 14], outline=(0, 240, 255, 200), width=2)
    s2_box.paste(Image.alpha_composite(s2_box.crop((0, 0, s2_box.size[0], s2_box.size[1])), link_layer))

    # Luminous Ghost Hand Touch on Trackpad Phone Screen
    from user_hand_slide1 import draw_user_provided_hand_slide1
    draw_user_provided_hand_slide1(s2_box, tip_target=(touch_x, touch_y), hand_scale=210)

    render_slide(
        "2_MultiTouch_Trackpad_1920x1080.png",
        "INPUT CONTROLLER",
        "MULTI-TOUCH",
        "PRECISION TRACKPAD",
        "Move your finger on the phone trackpad to drive the Windows mouse cursor with smooth acceleration, tap clicks, and dedicated vertical scrolling.",
        [
            "1-Finger Drag: Smooth Cursor Motion",
            "Tap Gestures: Left & Right Click",
            "Dedicated Scroll Strip with Inertia"
        ],
        s2_box,
        mockup_pos=(740, 25),
        accent=CYAN
    )

    # =========================================================================
    # SLIDE 3: SCREEN MIRRORING & DIRECT TOUCH
    # =========================================================================
    phone_stream = make_phone_frame(img_screen_stream, is_horizontal=True, target_size=1080, accent=LIME)
    render_slide(
        "3_Screen_Mirroring_1920x1080.png",
        "DESKTOP SCREEN STREAM",
        "DESKTOP SCREEN",
        "MIRRORING & TOUCH",
        "Stream your Windows desktop directly to your phone screen over local Wi-Fi with direct touch and smooth 30/60 FPS display modes.",
        [
            "30 FPS & 60 FPS Stream Modes",
            "Direct Touch & Scroll on Desktop",
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
        "TEXT INPUT",
        "LIVE ON-SCREEN",
        "TYPING TO PC",
        "Type on your mobile keyboard to send text, keystrokes, and shortcuts directly into active Windows applications and browser tabs.",
        [
            "Live Text Input Directly to PC",
            "Slide-Up Quick Typing Input Bar",
            "Windows Shortcut Hotkey Actions"
        ],
        phone_typing,
        mockup_pos=(750, 220),
        accent=PURPLE
    )

    # =========================================================================
    # SLIDE 5: LOCAL FILE MANAGER & SHARING
    # =========================================================================
    phone_files = make_phone_frame(img_files, is_horizontal=False, target_size=980, accent=CYAN)
    render_slide(
        "5_File_Transfer_1920x1080.png",
        "LOCAL STORAGE",
        "LOCAL WI-FI",
        "FILE SHARING & STORAGE",
        "Browse PC folders, download documents and media to your phone, and send files to your PC over local Wi-Fi without USB cables.",
        [
            "Browse PC Desktop & Downloads Folders",
            "Direct Wi-Fi File Uploads & Downloads",
            "Dedicated PC & Phone File Lists"
        ],
        phone_files,
        mockup_pos=(980, 20),
        accent=CYAN
    )

    # =========================================================================
    # SLIDE 6: LIVE STEREO AUDIO & MEDIA CONTROLS (ZOOMED UI)
    # =========================================================================
    audio_zoomed = img_media_full.crop((0, 100, 1080, 1920))
    phone_media_zoomed = make_phone_frame(audio_zoomed, is_horizontal=False, target_size=980, accent=YELLOW)
    render_slide(
        "6_Audio_Streaming_1920x1080.png",
        "AUDIO & MEDIA",
        "PC AUDIO STREAMING",
        "& MEDIA DECK",
        "Listen to PC audio directly on your phone earphones over Wi-Fi, control playback with media buttons, and use Windows shortcuts.",
        [
            "Stream PC Audio to Phone Earphones",
            "Volume Slider & Visualizer Waves",
            "Play, Pause, Skip & Windows Hotkeys"
        ],
        phone_media_zoomed,
        mockup_pos=(980, 20),
        accent=YELLOW
    )

    # =========================================================================
    # SLIDE 7: 3-SECOND QR CODE PAIRING (USING USER'S EXACT CLEAN QR CODE)
    # =========================================================================
    qr_reticle_size = 230
    qr_resized = user_qr_clean.resize((qr_reticle_size, qr_reticle_size), Image.Resampling.LANCZOS)

    scanner_composite = phone_qr_viewfinder.copy()
    scanner_composite.paste(qr_resized, (115, 388), qr_resized)

    laser_img = Image.new("RGBA", scanner_composite.size, (0, 0, 0, 0))
    l_draw = ImageDraw.Draw(laser_img)
    laser_y = 500
    l_draw.line([(100, laser_y), (360, laser_y)], fill=(0, 240, 255, 130), width=6)
    l_draw.line([(100, laser_y), (360, laser_y)], fill=(255, 255, 255, 255), width=2)
    laser_img = laser_img.filter(ImageFilter.GaussianBlur(radius=2))
    scanner_composite = Image.alpha_composite(scanner_composite, laser_img)

    phone_qr_mock = make_phone_frame(scanner_composite, is_horizontal=False, target_size=920, accent=YELLOW)
    pc_qr_mock = make_pc_window_frame(pc_server_window, target_width=720, accent=CYAN)

    s7_box = Image.new("RGBA", (1150, 1020), (0, 0, 0, 0))
    s7_box.paste(pc_qr_mock, (0, 180), pc_qr_mock)
    s7_box.paste(phone_qr_mock, (520, 20), phone_qr_mock)

    render_slide(
        "7_Instant_QR_Pairing_1920x1080.png",
        "INSTANT PAIRING",
        "QUICK 3-SECOND",
        "QR CODE CONNECT",
        "Scan the QR code displayed on your PC screen with your phone camera to connect instantly over local Wi-Fi or mobile hotspot.",
        [
            "Instant Optical QR Auto-Connect",
            "Works on Local Wi-Fi & Hotspots",
            "100% Offline — Zero Cloud Accounts"
        ],
        s7_box,
        mockup_pos=(750, 25),
        accent=YELLOW
    )

    # =========================================================================
    # SLIDE 8: OFFICIAL FEATURE GRAPHIC BANNER (1024x500)
    # =========================================================================
    generate_feature_graphic_monitor_outline(pc_desktop_hd, img_screen_stream)


def generate_feature_graphic_monitor_outline(pc_desktop_hd, img_screen_stream):
    W, H = 1024, 500
    canvas = create_base_canvas(W, H, accent_color=CYAN, glow_center=(0.7, 0.5))
    draw = ImageDraw.Draw(canvas)

    font_badge = get_font(13, bold=True)
    font_t1 = get_font(42, bold=True)
    font_t2 = get_font(42, bold=True)
    font_sub = get_font(18, bold=False)
    font_pill = get_font(14, bold=True)

    # Badge Pill
    b_text = "100% OFFLINE LOCAL WI-FI UTILITY"
    b_bbox = font_badge.getbbox(b_text)
    bw = b_bbox[2] - b_bbox[0] + 44
    bh = 32
    b_layer = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    bl_draw = ImageDraw.Draw(b_layer)
    bl_draw.rounded_rectangle([0, 0, bw - 1, bh - 1], radius=16, fill=(0, 240, 255, 30), outline=(0, 240, 255, 180), width=1)
    bl_draw.ellipse([12, 11, 20, 19], fill=CYAN)
    bl_draw.text((28, 6), b_text, font=font_badge, fill=CYAN)
    canvas.paste(b_layer, (48, 55), b_layer)

    # Title
    draw.text((48, 102), "PC DECK", font=font_t1, fill=WHITE)
    draw.text((48, 150), "WIRELESS REMOTE", font=font_t2, fill=CYAN)

    # Subtitle
    draw.text((48, 218), "Multi-Touch Trackpad • Desktop Screen Mirror", font=font_sub, fill=TEXT_MUTED)
    draw.text((48, 245), "PC Audio Stream • Local File Sharing", font=font_sub, fill=TEXT_MUTED)

    # Pills
    pills = ["Wi-Fi Trackpad", "Screen Mirror", "Audio & Files"]
    cx = 48
    for p in pills:
        pw = font_pill.getbbox(p)[2] - font_pill.getbbox(p)[0] + 32
        draw.rounded_rectangle([cx, 315, cx + pw, 351], radius=10, fill=SURFACE_CARD, outline=CARD_BORDER, width=1)
        draw.rounded_rectangle([cx + 5, 323, cx + 8, 343], radius=2, fill=CYAN)
        draw.text((cx + 16, 323), p, font=font_pill, fill=WHITE)
        cx += pw + 12

    # Background Iconic PC Monitor
    pc_monitor = make_iconic_pc_monitor(pc_desktop_hd, target_width=450, accent=CYAN)
    draw_clean_windows_cursor(pc_monitor, 220, 130)

    # Foreground Phone streaming
    phone_mirror_mock = make_phone_frame(img_screen_stream, is_horizontal=True, target_size=460, accent=LIME)

    canvas.paste(pc_monitor, (430, 45), pc_monitor)
    canvas.paste(phone_mirror_mock, (510, 175), phone_mirror_mock)

    out_file = os.path.join(OUTPUT_DIR, "Feature_Graphic_1024x500.png")
    canvas.convert("RGB").save(out_file, quality=95)
    print(f"OK: Saved {out_file}")


if __name__ == "__main__":
    generate_all()
