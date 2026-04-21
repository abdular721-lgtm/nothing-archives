#!/usr/bin/env python3
"""Generate PWA icons for Voice Assistant dashboard."""
from PIL import Image, ImageDraw

def generate_icon(size, filepath):
    img = Image.new('RGB', (size, size), '#0a0a0a')
    draw = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2
    r = int(size * 0.35)

    # Outer white circle
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill='#ffffff')
    # Inner dark circle
    ir = int(r * 0.7)
    draw.ellipse([cx - ir, cy - ir, cx + ir, cy + ir], fill='#0a0a0a')
    # Small white dot in center (mic indicator)
    dr = int(r * 0.2)
    draw.ellipse([cx - dr, cy - dr, cx + dr, cy + dr], fill='#ffffff')

    img.save(filepath)
    print(f"Generated {filepath} ({size}x{size})")

generate_icon(512, '/data/data/com.termux/files/home/dashboard/icon-512.png')
generate_icon(192, '/data/data/com.termux/files/home/dashboard/icon-192.png')
