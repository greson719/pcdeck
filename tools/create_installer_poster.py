from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

# Dimensions for Inno Setup
BANNER_W, BANNER_H = 164, 314
canvas = Image.new("RGB", (BANNER_W, BANNER_H), (11, 15, 23))
draw = ImageDraw.Draw(canvas)

# 1. Background vertical subtle cyber gradient
for y in range(BANNER_H):
    ratio = y / BANNER_H
    # Top: deep navy slate (15, 23, 42) -> Middle: dark cyber (10, 16, 26) -> Bottom: deep void (7, 10, 15)
    if ratio < 0.5:
        sub_ratio = ratio / 0.5
        r = int(18 * (1 - sub_ratio) + 11 * sub_ratio)
        g = int(28 * (1 - sub_ratio) + 17 * sub_ratio)
        b = int(46 * (1 - sub_ratio) + 28 * sub_ratio)
    else:
        sub_ratio = (ratio - 0.5) / 0.5
        r = int(11 * (1 - sub_ratio) + 6 * sub_ratio)
        g = int(17 * (1 - sub_ratio) + 9 * sub_ratio)
        b = int(28 * (1 - sub_ratio) + 15 * sub_ratio)
    draw.line([(0, y), (BANNER_W, y)], fill=(r, g, b))

# 2. Radial neon glow behind the logo
glow_canvas = Image.new("RGBA", (BANNER_W, BANNER_H), (0, 0, 0, 0))
glow_draw = ImageDraw.Draw(glow_canvas)
center_x = BANNER_W // 2
center_y = 135
glow_radius = 65
glow_draw.ellipse(
    [center_x - glow_radius, center_y - glow_radius, center_x + glow_radius, center_y + glow_radius],
    fill=(0, 242, 254, 40)
)
glow_canvas = glow_canvas.filter(ImageFilter.GaussianBlur(25))
canvas.paste(Image.composite(glow_canvas, Image.new("RGBA", (BANNER_W, BANNER_H), (0,0,0,0)), glow_canvas).convert("RGB"), (0, 0), glow_canvas)

# 3. Paste the authentic bright mouse logo
logo_source = Image.open("playstore_assets/App_Icon_512x512.png").convert("RGBA")
# Target logo size in banner: 110x110
logo_size = 110
logo_resized = logo_source.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
logo_x = (BANNER_W - logo_size) // 2
logo_y = center_y - (logo_size // 2) - 10
canvas.paste(logo_resized, (logo_x, logo_y), logo_resized)

# 4. Typography & Branding
try:
    font_brand = ImageFont.truetype("arialbd.ttf", 22)
    font_sub = ImageFont.truetype("arialbd.ttf", 8)
    font_features = ImageFont.truetype("arial.ttf", 9)
except Exception:
    font_brand = ImageFont.load_default()
    font_sub = ImageFont.load_default()
    font_features = ImageFont.load_default()

# "PCDECK" Title with subtle shadow
brand_text = "PCDECK"
bbox = draw.textbbox((0, 0), brand_text, font=font_brand)
bw = bbox[2] - bbox[0]
bx = (BANNER_W - bw) // 2
by = logo_y + logo_size + 8
draw.text((bx + 1, by + 1), brand_text, fill=(0, 0, 0), font=font_brand)
draw.text((bx, by), brand_text, fill=(255, 255, 255), font=font_brand)

# Subtle neon cyan accent line
line_w = 46
line_x1 = (BANNER_W - line_w) // 2
line_y = by + 26
draw.line([(line_x1, line_y), (line_x1 + line_w, line_y)], fill=(0, 242, 254), width=2)

# Tagline
sub_text = "WIRELESS PC CONTROLLER"
bbox_sub = draw.textbbox((0, 0), sub_text, font=font_sub)
sw = bbox_sub[2] - bbox_sub[0]
sx = (BANNER_W - sw) // 2
sy = line_y + 8
draw.text((sx, sy), sub_text, fill=(0, 242, 254), font=font_sub)

# Feature bullet badges at the bottom
bullets = [
    "Multi-Touch Trackpad",
    "Screen Mirroring",
    "Zero Cloud Account"
]
b_start_y = sy + 28
for idx, b in enumerate(bullets):
    bbox_b = draw.textbbox((0, 0), b, font=font_features)
    bbw = bbox_b[2] - bbox_b[0]
    bbx = (BANNER_W - bbw) // 2
    bby = b_start_y + idx * 16
    draw.text((bbx, bby), b, fill=(156, 163, 175), font=font_features)

# Subtle border highlight on right edge
draw.line([(BANNER_W - 1, 0), (BANNER_W - 1, BANNER_H)], fill=(30, 41, 59), width=1)

canvas.save("WizardImage.bmp", format="BMP")
print("[+] Successfully generated professional poster: WizardImage.bmp (164x314)")

# Small wizard image (55x55)
wiz_small = Image.new("RGB", (55, 55), (15, 23, 42))
logo_small = logo_source.resize((48, 48), Image.Resampling.LANCZOS)
wiz_small.paste(logo_small, ((55 - 48) // 2, (55 - 48) // 2), logo_small)
wiz_small.save("WizardSmallImage.bmp", format="BMP")
print("[+] Successfully generated WizardSmallImage.bmp (55x55)")
