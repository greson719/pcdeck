"""
PCDeck — High-Visibility PC Monitor Frame with Robust Thick Bezels and Authentic Desktop Chassis.
"""

from PIL import Image, ImageDraw, ImageFilter

def make_prominent_pc_monitor(desktop_img, target_width=700, accent=(0, 240, 255)):
    """
    Renders a robust PC desktop monitor with prominent, thick bezels:
    - 32px top and side bezels
    - 64px thick bottom chin bezel with power LED and logo badge
    - Multi-layered metallic chassis with chamfered inner bevel
    - Substantial stand neck and wide pedestal base
    """
    screen_w = target_width
    screen_h = int(target_width * 0.5625) # 16:9 -> ~394px

    bezel_t = 30
    bezel_s = 30
    bezel_b = 60 # Extra thick bottom chin

    mon_w = screen_w + (bezel_s * 2)
    mon_h = screen_h + bezel_t + bezel_b

    neck_w_top = 100
    neck_w_bot = 140
    neck_h = 105

    base_w = 380
    base_h = 42

    pad = 40
    total_w = mon_w + (pad * 2)
    total_h = mon_h + neck_h + base_h + (pad * 2)

    canvas = Image.new('RGBA', (total_w, total_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    ox = pad
    oy = pad
    cx = ox + mon_w // 2

    # 1. Base Pedestal (curved oval desk stand)
    base_top_y = oy + mon_h + neck_h - 14
    draw.ellipse(
        [cx - base_w // 2, base_top_y, cx + base_w // 2, base_top_y + base_h],
        fill=(25, 34, 52, 255),
        outline=accent,
        width=2
    )
    # Inner metallic ring on base
    draw.ellipse(
        [cx - base_w // 2 + 14, base_top_y + 6, cx + base_w // 2 - 14, base_top_y + base_h - 10],
        outline=(50, 70, 105, 200),
        width=1
    )

    # 2. Angled Trapezoid Stand Neck
    neck_top_y = oy + mon_h - 6
    draw.polygon([
        (cx - neck_w_top // 2, neck_top_y),
        (cx + neck_w_top // 2, neck_top_y),
        (cx + neck_w_bot // 2, base_top_y + 14),
        (cx - neck_w_bot // 2, base_top_y + 14)
    ], fill=(18, 26, 40, 255), outline=accent, width=2)
    # Neck shadow / depth crease
    draw.line([(cx, neck_top_y), (cx, base_top_y + 14)], fill=(35, 48, 72, 255), width=2)

    # 3. Main Monitor Chassis (Solid, distinct slate body with thick bezels)
    draw.rounded_rectangle(
        [ox, oy, ox + mon_w, oy + mon_h],
        radius=20,
        fill=(22, 30, 48, 255),
        outline=accent,
        width=3
    )

    # Inner chassis chamfer groove (inset by 8px)
    draw.rounded_rectangle(
        [ox + 8, oy + 8, ox + mon_w - 8, oy + mon_h - 8],
        radius=14,
        outline=(45, 62, 92, 255),
        width=1
    )

    # 4. Insert PC Desktop Wallpaper
    resized_screen = desktop_img.convert('RGB').resize((screen_w, screen_h), Image.Resampling.LANCZOS).convert('RGBA')
    canvas.paste(resized_screen, (ox + bezel_s, oy + bezel_t))

    # 5. Inner screen border
    draw.rectangle([ox + bezel_s, oy + bezel_t, ox + bezel_s + screen_w, oy + bezel_t + screen_h], outline=(0, 240, 255, 180), width=2)
    
    # Chin accent divider line
    draw.line([(ox + 24, oy + mon_h - bezel_b + 6), (ox + mon_w - 24, oy + mon_h - bezel_b + 6)], fill=(50, 72, 105, 255), width=1)

    # 6. Top Center Webcam + Sensor
    cam_x = cx
    draw.ellipse([cam_x - 5, oy + 10, cam_x + 5, oy + 20], fill=(5, 8, 12, 255), outline=(0, 240, 255, 200), width=1)
    draw.ellipse([cam_x + 14, oy + 13, cam_x + 18, oy + 17], fill=(0, 240, 255, 180)) # LED indicator

    # 7. Monitor Brand Logo & Power LED on Chin
    draw.rounded_rectangle([cx - 24, oy + mon_h - 38, cx + 24, oy + mon_h - 22], radius=4, fill=(12, 16, 26, 255), outline=(0, 240, 255, 140), width=1)
    # Tiny glowing PC logo inside badge
    draw.ellipse([cx - 4, oy + mon_h - 32, cx + 4, oy + mon_h - 28], fill=(0, 240, 255, 220))
    # Bottom right power LED
    draw.ellipse([ox + mon_w - 38, oy + mon_h - 32, ox + mon_w - 32, oy + mon_h - 26], fill=(0, 255, 102, 220))

    # 8. Ambient outer bloom halo
    halo = Image.new('RGBA', (total_w, total_h), (0, 0, 0, 0))
    h_draw = ImageDraw.Draw(halo)
    h_draw.rounded_rectangle([ox - 10, oy - 8, ox + mon_w + 10, oy + mon_h + 12], radius=26, fill=(accent[0], accent[1], accent[2], 60))
    halo = halo.filter(ImageFilter.GaussianBlur(radius=24))

    return Image.alpha_composite(halo, canvas)
