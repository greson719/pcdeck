"""
PCDeck — Helper for drawing natural, crisp Windows mouse cursor with subtle hover beacon.
"""

from PIL import ImageDraw

def draw_prominent_windows_cursor(canvas, x, y, scale=1.0):
    """
    Draws a natural, crisp Windows 11 mouse cursor scaled realistically to desktop icons.
    """
    draw = ImageDraw.Draw(canvas)

    # Subtle cyan radar beacon around cursor tip
    beacon_r = int(16 * scale)
    draw.ellipse([x - beacon_r, y - beacon_r, x + beacon_r, y + beacon_r], outline=(0, 240, 255, 100), width=1)
    draw.ellipse([x - beacon_r//2, y - beacon_r//2, x + beacon_r//2, y + beacon_r//2], outline=(0, 240, 255, 180), width=2)

    # Standard Windows Cursor Points (Height ~ 32px)
    base_pts = [
        (0, 0),
        (0, 26),
        (6, 20),
        (12, 33),
        (17, 30),
        (11, 18),
        (20, 18)
    ]
    scaled_pts = [(x + int(px * scale), y + int(py * scale)) for (px, py) in base_pts]

    # Drop shadow
    shadow_pts = [(px + 3, py + 3) for (px, py) in scaled_pts]
    draw.polygon(shadow_pts, fill=(0, 0, 0, 180))

    # Cursor body & outline
    draw.polygon(scaled_pts, fill=(255, 255, 255, 255), outline=(0, 0, 0, 255))
