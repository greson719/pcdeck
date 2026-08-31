"""
Script to craft the realistic hand/finger touch interaction for Slide 2.
"""

import os
from PIL import Image, ImageDraw, ImageFilter

def draw_realistic_hand_operating_phone(canvas, tip_x, tip_y, scale=1.0):
    """
    Renders a clean, modern hand / index finger operating the smartphone trackpad
    with realistic shading, soft drop shadow onto the glass, and glowing touch pulse.
    """
    # Create hand overlay canvas
    w, h = canvas.size
    hand_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    h_draw = ImageDraw.Draw(hand_img)

    # 1. Contact point glow & ripple on glass
    glow_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(glow_layer)
    for r in range(90, 15, -10):
        alpha = int(90 * (1.0 - (r / 90) ** 1.3))
        g_draw.ellipse([tip_x - r, tip_y - r, tip_x + r, tip_y + r], fill=(0, 240, 255, alpha))
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=12))
    canvas.paste(Image.alpha_composite(canvas.crop((0, 0, w, h)), glow_layer))

    # 2. Hand Shadow on the screen
    shadow_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow_layer)
    
    # Shadow polygon slightly offset
    sx, sy = tip_x + 12, tip_y + 18
    s_pts = [
        (sx, sy),
        (sx + 35, sy + 30),
        (sx + 85, sy + 110),
        (sx + 160, sy + 220),
        (sx + 240, sy + 340),
        (sx + 340, sy + 440),
        (sx + 260, sy + 500),
        (sx + 100, sy + 420),
        (sx - 10, sy + 180),
        (sx - 20, sy + 60),
    ]
    s_draw.polygon(s_pts, fill=(0, 0, 0, 140))
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=18))
    canvas.paste(Image.alpha_composite(canvas.crop((0, 0, w, h)), shadow_layer))

    # 3. Main Finger & Hand Polygon with 3D gradient shading
    # Index finger pointing to (tip_x, tip_y)
    hand_color_base = (232, 192, 170, 255)
    hand_color_shadow = (195, 150, 130, 255)
    hand_color_highlight = (250, 220, 205, 255)

    # Hand shape points
    # Tip at (tip_x, tip_y), extending down-right
    pts = [
        (tip_x, tip_y),                       # Fingertip center-top
        (tip_x + 22, tip_y + 12),              # Right tip curve
        (tip_x + 38, tip_y + 38),              # First knuckle right
        (tip_x + 58, tip_y + 90),              # Second knuckle right
        (tip_x + 95, tip_y + 180),             # Palm transition right
        (tip_x + 180, tip_y + 300),            # Hand side
        (tip_x + 300, tip_y + 440),            # Wrist bottom right
        (tip_x + 180, tip_y + 520),            # Wrist bottom left
        (tip_x + 40,  tip_y + 340),            # Palm left
        (tip_x - 12,  tip_y + 190),            # Second knuckle left
        (tip_x - 22,  tip_y + 95),             # First knuckle left
        (tip_x - 18,  tip_y + 35),             # Left tip curve
        (tip_x - 8,   tip_y + 8),              # Tip curve top-left
    ]

    # Draw base hand
    h_draw.polygon(pts, fill=hand_color_base)

    # Shading on right side (darker edge)
    shade_pts = [
        (tip_x + 15, tip_y + 20),
        (tip_x + 38, tip_y + 38),
        (tip_x + 58, tip_y + 90),
        (tip_x + 95, tip_y + 180),
        (tip_x + 180, tip_y + 300),
        (tip_x + 300, tip_y + 440),
        (tip_x + 240, tip_y + 450),
        (tip_x + 140, tip_y + 300),
        (tip_x + 70, tip_y + 180),
        (tip_x + 40, tip_y + 90),
        (tip_x + 22, tip_y + 35),
    ]
    h_draw.polygon(shade_pts, fill=hand_color_shadow)

    # Highlight streak along finger ridge
    hl_pts = [
        (tip_x - 2, tip_y + 6),
        (tip_x + 8, tip_y + 6),
        (tip_x + 22, tip_y + 80),
        (tip_x + 38, tip_y + 160),
        (tip_x + 26, tip_y + 160),
        (tip_x + 12, tip_y + 80),
    ]
    h_draw.polygon(hl_pts, fill=hand_color_highlight)

    # Fingernail
    nail_pts = [
        (tip_x - 8, tip_y + 12),
        (tip_x + 14, tip_y + 14),
        (tip_x + 18, tip_y + 34),
        (tip_x - 6, tip_y + 32),
    ]
    h_draw.polygon(nail_pts, fill=(255, 235, 230, 240), outline=(220, 180, 165, 255))

    # Knuckle skin crease lines
    h_draw.arc([tip_x - 14, tip_y + 60, tip_x + 30, tip_y + 74], start=200, end=340, fill=(180, 140, 120, 200), width=2)
    h_draw.arc([tip_x - 4, tip_y + 130, tip_x + 50, tip_y + 148], start=200, end=340, fill=(180, 140, 120, 200), width=2)

    # Smooth the hand rendering
    canvas.paste(Image.alpha_composite(canvas.crop((0, 0, w, h)), hand_img))

    # 4. Glowing contact beacon at the very fingertip
    beacon = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    b_draw = ImageDraw.Draw(beacon)
    b_draw.ellipse([tip_x - 14, tip_y - 14, tip_x + 14, tip_y + 14], fill=(255, 255, 255, 255), outline=(0, 240, 255, 255), width=3)
    b_draw.ellipse([tip_x - 30, tip_y - 30, tip_x + 30, tip_y + 30], outline=(0, 240, 255, 180), width=2)
    b_draw.ellipse([tip_x - 48, tip_y - 48, tip_x + 48, tip_y + 48], outline=(0, 240, 255, 100), width=1)
    canvas.paste(Image.alpha_composite(canvas.crop((0, 0, w, h)), beacon))
