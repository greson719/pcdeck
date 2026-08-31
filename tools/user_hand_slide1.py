"""
PCDeck — Slide 1 Luminous Holographic Ghost Hand Interaction
"""

from PIL import Image, ImageDraw, ImageFilter
import numpy as np

def draw_user_provided_hand_slide1(s1_box, tip_target=(710, 680), hand_scale=200):
    img_path = r'C:/Users/GRESON/.gemini/antigravity/brain/2d46a58c-baa8-41df-9298-244019d6e827/.user_uploaded/media_1788078642762.png'
    img = Image.open(img_path).convert('RGBA')

    # 1. Clean mask extraction
    arr = np.array(img, dtype=float)
    r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
    dist_from_white = np.sqrt((255 - r)**2 + (255 - g)**2 + (255 - b)**2)
    alpha = np.clip((dist_from_white - 24) * 20.0, 0, 255).astype(np.uint8)

    mask_pil = Image.fromarray(alpha, mode='L').filter(ImageFilter.GaussianBlur(radius=0.8))
    img.putalpha(mask_pil)

    # Crop to hand
    bbox = img.getbbox()
    hand_cropped = img.crop(bbox)

    # 2. Smooth scaling
    target_w = hand_scale
    aspect = hand_cropped.size[1] / hand_cropped.size[0]
    target_h = int(target_w * aspect)
    hand_hd = hand_cropped.resize((target_w, target_h), Image.Resampling.LANCZOS)

    # 3. Rotate (-18 deg)
    rotated_hand = hand_hd.rotate(-18, expand=True, resample=Image.Resampling.BICUBIC)

    # 4. Generate Luminous Ghost Effect
    w, h = rotated_hand.size
    h_arr = np.array(rotated_hand, dtype=float)
    gray = (h_arr[:,:,0]*0.299 + h_arr[:,:,1]*0.587 + h_arr[:,:,2]*0.114)
    base_alpha = h_arr[:,:,3]

    y_coords = np.linspace(0, 1, h)[:, None]
    fade_gradient = np.clip(1.2 - y_coords * 0.45, 0.35, 1.0)

    # Bright luminous cyan & white highlights
    ghost_r = np.clip(gray * 0.5 + 40 * fade_gradient, 0, 255)
    ghost_g = np.clip(gray * 0.95 + 215 * fade_gradient, 0, 255)
    ghost_b = np.clip(gray * 1.05 + 250 * fade_gradient, 0, 255)
    ghost_a = np.clip(base_alpha * 0.62 * fade_gradient, 0, 255)

    ghost_fill = Image.fromarray(np.stack([ghost_r, ghost_g, ghost_b, ghost_a], axis=2).astype(np.uint8), mode='RGBA')

    # 5. Vivid Neon Rim Contour & Ambient Glow
    mask_img = Image.fromarray(base_alpha.astype(np.uint8), mode='L')
    edges = mask_img.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(radius=1.0))
    edge_arr = np.array(edges)

    rim_r = np.full((h, w), 80, dtype=np.uint8)
    rim_g = np.full((h, w), 250, dtype=np.uint8)
    rim_b = np.full((h, w), 255, dtype=np.uint8)
    rim_a = np.clip(edge_arr * 2.6 * fade_gradient, 0, 255).astype(np.uint8)

    rim_layer = Image.fromarray(np.stack([rim_r, rim_g, rim_b, rim_a], axis=2), mode='RGBA')

    bloom_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bloom_layer.paste(rim_layer, (0, 0), rim_layer)
    bloom_layer = bloom_layer.filter(ImageFilter.GaussianBlur(radius=8))

    ghost_combined = Image.alpha_composite(bloom_layer, ghost_fill)
    ghost_combined = Image.alpha_composite(ghost_combined, rim_layer)

    # 6. Target Touch Position
    r_arr = np.array(rotated_hand.split()[3])
    y_indices, x_indices = np.where(r_arr > 120)
    min_y_idx = np.argmin(y_indices)
    tip_local_x = x_indices[min_y_idx]
    tip_local_y = y_indices[min_y_idx]

    target_tip_x, target_tip_y = tip_target

    hx = target_tip_x - tip_local_x
    hy = target_tip_y - tip_local_y

    tip_x = target_tip_x
    tip_y = target_tip_y

    # 7. Concentric Touch Wave Ripples on Phone Screen
    wave_layer = Image.new("RGBA", s1_box.size, (0, 0, 0, 0))
    w_draw = ImageDraw.Draw(wave_layer)

    ripples = [
        (85, 45, 1),
        (60, 85, 2),
        (38, 145, 2),
        (20, 210, 2),
        (8, 255, 3)
    ]
    for radius, alpha_val, stroke_w in ripples:
        w_draw.ellipse(
            [tip_x - radius, tip_y - radius, tip_x + radius, tip_y + radius],
            outline=(0, 240, 255, alpha_val),
            width=stroke_w
        )
    
    glow_under = Image.new("RGBA", s1_box.size, (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(glow_under)
    for r in range(48, 5, -8):
        g_draw.ellipse([tip_x - r, tip_y - r, tip_x + r, tip_y + r], fill=(0, 240, 255, int(50 * (1 - r/48))))
    glow_under = glow_under.filter(ImageFilter.GaussianBlur(radius=10))

    s1_box.paste(Image.alpha_composite(s1_box.crop((0, 0, s1_box.size[0], s1_box.size[1])), glow_under))
    s1_box.paste(Image.alpha_composite(s1_box.crop((0, 0, s1_box.size[0], s1_box.size[1])), wave_layer))

    # 8. Soft Ghost Shadow & Paste Luminous Hand
    shadow = Image.new("RGBA", s1_box.size, (0, 0, 0, 0))
    s_mask = mask_img.filter(ImageFilter.GaussianBlur(radius=8))
    shadow.paste((0, 0, 0, 110), (hx + 6, hy + 12), mask=s_mask)
    s1_box.paste(Image.alpha_composite(s1_box.crop((0, 0, s1_box.size[0], s1_box.size[1])), shadow))

    s1_box.paste(ghost_combined, (hx, hy), ghost_combined)
