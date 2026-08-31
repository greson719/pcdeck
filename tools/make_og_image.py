"""Generate the Open Graph / Twitter preview card for pcdeck.vercel.app.

The site previously pointed og:image at a 256x256 square logo while declaring
twitter:card=summary_large_image. That combination does not render: Twitter wants
roughly 1.91:1 and rejects anything under 300x157, and Facebook/LinkedIn want at
least 1200x630 for a large preview. So shared links showed either a cropped blob
or no artwork at all.

This renders a real 1200x630 card in the same design language as the page:
cool paper ground, hairline grid, ink headline, one cobalt accent.

Run from the repo root:
    python tools/make_og_image.py
"""

from __future__ import annotations

import os
from PIL import Image, ImageDraw, ImageFont

# --- design tokens, mirrored from website/index.html -------------------------
PAPER = (238, 240, 243)
INK = (18, 22, 28)
GRAPHITE = (74, 83, 97)
MUTED = (107, 116, 128)
GRID = (213, 218, 225)
SIGNAL = (27, 68, 216)
PANEL = (255, 255, 255)

W, H = 1200, 630
PAD = 72

FONTS = "C:/Windows/Fonts"
OUT = os.path.join(os.path.dirname(__file__), "..", "website", "og-image.png")
LOGO = os.path.join(os.path.dirname(__file__), "..", "website", "icon-512.png")


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(os.path.join(FONTS, name), size)


def width_of(d: ImageDraw.ImageDraw, text: str, f: ImageFont.FreeTypeFont) -> int:
    return int(d.textlength(text, font=f))


def fit_font(d: ImageDraw.ImageDraw, lines: list[str], name: str,
             max_w: int, start: int, floor: int = 28) -> ImageFont.FreeTypeFont:
    """Largest size at which every line fits max_w.

    Measured rather than guessed: the headline copy changes, and eyeballing a
    size means it silently overruns the card the next time the wording grows.
    """
    for size in range(start, floor - 1, -2):
        f = font(name, size)
        if all(width_of(d, ln, f) <= max_w for ln in lines):
            return f
    return font(name, floor)


def main() -> None:
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)

    usable = W - 2 * PAD

    # Faint engineering grid, same 64px module as the page.
    for x in range(0, W, 64):
        d.line([(x, 0), (x, H)], fill=GRID, width=1)
    for y in range(0, H, 64):
        d.line([(0, y), (W, y)], fill=GRID, width=1)

    f_eyebrow = font("consola.ttf", 21)
    f_body = font("segoeui.ttf", 29)
    f_meta = font("consola.ttf", 22)
    f_brand = font("arialbd.ttf", 34)

    # The headline mirrors the page: name the hardware, so nobody arrives with a
    # dead keyboard and concludes the product is only for broken monitors.
    head = ["The mouse, keyboard and screen", "your PC is missing."]
    # Fit against a slightly narrow column: filling the usable width exactly is
    # technically inside the margin but reads as though the type is jammed against
    # the edge, and social platforms sometimes shave a pixel row when re-encoding.
    f_title = fit_font(d, head, "arialbd.ttf", usable - 40, 66)

    # --- brand row ----------------------------------------------------------
    y = PAD
    try:
        logo = Image.open(LOGO).convert("RGBA").resize((52, 52), Image.LANCZOS)
        # The icon art is dark with feathered edges, drawn for a dark ground, so
        # it needs its own tile here too or it dissolves into the paper.
        tile = Image.new("RGB", (60, 60), (22, 28, 36))
        tile.paste(logo, (4, 4), logo)
        img.paste(tile, (PAD, y - 8))
        brand_x = PAD + 76
    except Exception:
        brand_x = PAD
    d.text((brand_x, y + 6), "PCDeck", font=f_brand, fill=INK)

    # --- eyebrow ------------------------------------------------------------
    y += 104
    d.text((PAD, y), "WINDOWS 10 / 11   ·   ANDROID 5.0+", font=f_eyebrow, fill=MUTED)

    # --- headline -----------------------------------------------------------
    y += 46
    step = int(f_title.size * 1.16)
    d.text((PAD, y), head[0], font=f_title, fill=INK)
    y += step
    d.text((PAD, y), head[1], font=f_title, fill=MUTED)

    # --- supporting line ----------------------------------------------------
    y += step + 22
    d.text(
        (PAD, y),
        "Trackpad, keyboard, second screen, PC audio and\ncable-free file transfer. Over your own Wi-Fi.",
        font=f_body,
        fill=GRAPHITE,
        spacing=10,
    )

    # --- bottom rule + meta strip ------------------------------------------
    ry = H - PAD - 54
    d.line([(PAD, ry), (W - PAD, ry)], fill=GRID, width=2)
    d.text((PAD, ry + 16), "Fully offline   ·   No account   ·   Free + $3.99 Pro",
           font=f_meta, fill=MUTED)

    # --- the one accent: a cobalt cursor, echoing the page's live demo ------
    cx, cy = W - PAD - 176, H - PAD - 236
    d.polygon(
        [(cx, cy), (cx + 96, cy + 62), (cx + 51, cy + 70),
         (cx + 68, cy + 118), (cx + 47, cy + 126), (cx + 30, cy + 78), (cx, cy + 104)],
        fill=SIGNAL,
    )

    img.save(OUT, "PNG", optimize=True)
    print(f"wrote {os.path.normpath(OUT)}  {img.size[0]}x{img.size[1]}")
    print(f"headline set at {f_title.size}px; widest line "
          f"{max(width_of(d, ln, f_title) for ln in head)}px of {usable}px usable")
    print(f"size: {os.path.getsize(OUT) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
