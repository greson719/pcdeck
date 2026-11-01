"""
Refined positioning for the photorealistic hand on Slide 1.
"""

from PIL import Image, ImageDraw, ImageFilter

def draw_photorealistic_hand_slide1(s1_box):
    # Load original hand
    img_path = r'C:\Users\GRESON\.gemini\antigravity\brain\2d46a58c-baa8-41df-9298-244019d6e827\finger_touch_isolated_1788077550829.jpg'
    orig = Image.open(img_path).convert('RGB')
    
    # Precise alpha mask
    import numpy as np
    arr = np.array(orig, dtype=float)
    r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
    brightness = np.maximum(r, np.maximum(g, b))
    
    # Smooth cutout
    alpha = np.clip((brightness - 24) * 8.0, 0, 255).astype(np.uint8)
    # Mask out table
    alpha[874:, :] = 0

    mask_pil = Image.fromarray(alpha, mode='L')
    mask_pil = mask_pil.filter(ImageFilter.GaussianBlur(radius=1.5))

    hand_rgba = orig.copy().convert('RGBA')
    hand_rgba.putalpha(mask_pil)

    # Crop to bounding box of hand
    bbox = hand_rgba.getbbox()
    hand_cropped = hand_rgba.crop(bbox)

    # Resize hand to fit naturally on the phone
    target_w = 480
    aspect = hand_cropped.size[1] / hand_cropped.size[0]
    target_h = int(target_w * aspect)
    hand_resized = hand_cropped.resize((target_w, target_h), Image.Resampling.LANCZOS)

    # Smoothly fade out the upper-right wrist edge so there is zero abrupt line
    w_res, h_res = hand_resized.size
    fade_mask = Image.new("L", (w_res, h_res), 255)
    f_draw = ImageDraw.Draw(fade_mask)
    for y in range(0, 70):
        alpha_val = int(255 * (y / 70.0))
        f_draw.line([(0, y), (w_res, y)], fill=alpha_val)
    
    current_alpha = hand_resized.split()[3]
    combined_alpha = Image.composite(current_alpha, Image.new("L", (w_res, h_res), 0), fade_mask)
    hand_resized.putalpha(combined_alpha)

    # Position on s1_box
    # Phone frame is placed at (180, 440), width is ~880, height is ~470
    # Fingertip in hand_resized is at bottom-left (~(15, target_h - 15))
    hx, hy = 620, 360

    # Soft drop shadow beneath finger onto phone screen
    shadow = Image.new("RGBA", s1_box.size, (0, 0, 0, 0))
    s_mask = hand_resized.split()[3]
    shadow.paste((0, 0, 0, 160), (hx + 12, hy + 20), mask=s_mask)
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=16))
    s1_box.paste(Image.alpha_composite(s1_box.crop((0, 0, s1_box.size[0], s1_box.size[1])), shadow))

    # Paste hand
    s1_box.paste(hand_resized, (hx, hy), hand_resized)

    # Glowing touch ripple at fingertip contact
    tip_x, tip_y = hx + 18, hy + target_h - 18
    ripple = Image.new("RGBA", s1_box.size, (0, 0, 0, 0))
    r_draw = ImageDraw.Draw(ripple)
    for r in range(45, 8, -5):
        r_draw.ellipse([tip_x - r, tip_y - r, tip_x + r, tip_y + r], fill=(0, 240, 255, int(90 * (1 - r/45))))
    r_draw.ellipse([tip_x - 14, tip_y - 14, tip_x + 14, tip_y + 14], fill=(0, 240, 255, 230), outline=(255, 255, 255, 255), width=2)
    r_draw.ellipse([tip_x - 5, tip_y - 5, tip_x + 5, tip_y + 5], fill=(255, 255, 255, 255))
    ripple = ripple.filter(ImageFilter.GaussianBlur(radius=2))
    
    s1_box.paste(Image.alpha_composite(s1_box.crop((0, 0, s1_box.size[0], s1_box.size[1])), ripple))
