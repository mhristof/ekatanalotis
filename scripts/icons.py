#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
"""Draw the extension icons into the directory given (extension/icons):
three white bars (one product's price in different stores) on the accent
blue, at 16, 32, 48 and 128 px.

    scripts/icons.py extension/icons"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

BLUE = (42, 120, 214, 255)  # --accent, #2a78d6
WHITE = (255, 255, 255, 255)
out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)

for size in (16, 32, 48, 128):
    k = 8  # draw large, scale down for smooth edges
    s = size * k
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # 128 px icons should have ~16 px of transparent padding (Chrome docs)
    pad = round(s * (16 / 128)) if size == 128 else round(s * 0.03)
    d.rounded_rectangle([pad, pad, s - pad, s - pad], radius=(s - 2 * pad) * 0.22, fill=BLUE)
    inner = s - 2 * pad
    bw = inner * 0.16
    gap = inner * 0.09
    x0 = pad + (inner - (3 * bw + 2 * gap)) / 2
    base = pad + inner * 0.78
    for i, h in enumerate((0.38, 0.58, 0.28)):
        x = x0 + i * (bw + gap)
        d.rounded_rectangle([x, base - inner * h, x + bw, base], radius=bw * 0.3, fill=WHITE)
    img.resize((size, size), Image.LANCZOS).save(out / f"icon{size}.png")
    print(out / f"icon{size}.png")
