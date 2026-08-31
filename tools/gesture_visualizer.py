"""
PCDeck — Slide 2 Gesture & Multi-Touch Visualizer
Renders clean, professional touch contact rings, glide motion trail, and kinetic cursor link.
"""

from PIL import Image, ImageDraw, ImageFilter

def draw_clean_touch_gesture(canvas, phone_origin, tip_x, tip_y, cursor_pc_x, cursor_pc_y):
    """
    Renders clean, Apple/Material-grade multi-touch gesture ripples and 
    a kinetic connection between phone trackpad and PC mouse cursor.
    """
    w, h = canvas.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # 1. Primary Touch Point (Finger 1 Contact)
    # Glide Trail (Curved motion path showing movement)
    trail_pts = [
        (tip_x + 70, tip_y + 90),
        (tip_x + 50, tip_y + 55),
        (tip_x + 25, tip_y + 25),
        (tip_x, tip_y)
    ]
    for i in range(len(trail_pts) - 1):
        alpha = int(40 + (i / len(trail_pts)) * 140)
        draw.line([trail_pts[i], trail_pts[i+1]], fill=(0, 240, 255, alpha), width=5)

    # Primary Contact Rings & Glow
    for r in range(45, 10, -5):
        alpha = int(80 * (1.0 - (r / 45) ** 1.2))
        draw.ellipse([tip_x - r, tip_y - r, tip_x + r, tip_y + r], fill=(0, 240, 255, alpha))

    draw.ellipse([tip_x - 16, tip_y - 16, tip_x + 16, tip_y + 16], fill=(0, 240, 255, 200), outline=(255, 255, 255, 255), width=3)
    draw.ellipse([tip_x - 6, tip_y - 6, tip_x + 6, tip_y + 6], fill=(255, 255, 255, 255))

    # 2. Secondary Touch Point (Finger 2 Contact for Multi-Touch Gestures)
    f2_x, f2_y = tip_x + 45, tip_y - 35
    for r in range(30, 8, -4):
        alpha = int(60 * (1.0 - (r / 30) ** 1.2))
        draw.ellipse([f2_x - r, f2_y - r, f2_x + r, f2_y + r], fill=(0, 255, 150, alpha))

    draw.ellipse([f2_x - 12, f2_y - 12, f2_x + 12, f2_y + 12], fill=(0, 255, 150, 180), outline=(255, 255, 255, 230), width=2)
    draw.ellipse([f2_x - 4, f2_y - 4, f2_x + 4, f2_y + 4], fill=(255, 255, 255, 255))

    # 3. Gesture Label Tag on Phone Screen
    tag_x, tag_y = tip_x - 95, tip_y + 45
    draw.rounded_rectangle([tag_x, tag_y, tag_x + 190, tag_y + 32], radius=16, fill=(15, 22, 35, 230), outline=(0, 240, 255, 180), width=1)
    
    # 4. Subtle Kinetic Connection Line to PC Cursor
    # Dotted curve from phone touch point to PC desktop cursor
    ctrl_x = (tip_x + cursor_pc_x) // 2
    ctrl_y = min(tip_y, cursor_pc_y) - 60

    # Draw smooth quadratic bezier curve
    num_steps = 30
    curve_points = []
    for step in range(num_steps + 1):
        t = step / num_steps
        px = (1 - t) ** 2 * cursor_pc_x + 2 * (1 - t) * t * ctrl_x + t ** 2 * tip_x
        py = (1 - t) ** 2 * cursor_pc_y + 2 * (1 - t) * t * ctrl_y + t ** 2 * tip_y
        curve_points.append((px, py))

    # Draw dotted glowing link
    for i in range(0, len(curve_points) - 1, 2):
        draw.line([curve_points[i], curve_points[i+1]], fill=(0, 240, 255, 140), width=2)

    canvas.paste(Image.alpha_composite(canvas.crop((0, 0, w, h)), overlay))
