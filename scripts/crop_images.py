#!/usr/bin/env python3
"""
Image crop utilities for the Social Media pipeline.

Commands:
  infographic-carousel  Scale NLM portrait infographic to 1000×460px for carousel media slot.
                        Takes the top portion — NLM infographics are top-loaded (title + stats first).
  trim                  Auto-trim whitespace borders from any image (content-aware, via PIL diff).

Usage:
  python3 crop_images.py infographic-carousel assets/post/slug/nlm_infographic.png \
      --out assets/post/slug/nlm_infographic_carousel.png

  python3 crop_images.py trim assets/post/slug/diagrams/flow.png \
      --out assets/post/slug/diagrams/flow_clean.png
"""

import argparse
import re
import sys
from pathlib import Path

from PIL import Image, ImageChops

CAROUSEL_W = 1000
CAROUSEL_H = 460
OLED_BLACK = (10, 10, 10)   # #0A0A0A — matches diagram/carousel background


def crop_for_carousel(src: Path, dst: Path) -> None:
    """
    Crop a portrait NLM infographic to landscape 1000×460 for the carousel media slot.
    Strategy: scale to 1000px wide, take top 460px — content is always top-loaded in NLM infographics.
    Pad with OLED black if the image is shorter than 460px after scaling.
    """
    img = Image.open(src).convert("RGB")
    w, h = img.size

    scale = CAROUSEL_W / w
    new_h = int(h * scale)
    img = img.resize((CAROUSEL_W, new_h), Image.LANCZOS)

    if img.height >= CAROUSEL_H:
        result = img.crop((0, 0, CAROUSEL_W, CAROUSEL_H))
    else:
        # Image shorter than target — pad bottom with OLED black
        result = Image.new("RGB", (CAROUSEL_W, CAROUSEL_H), OLED_BLACK)
        result.paste(img, (0, 0))

    dst.parent.mkdir(parents=True, exist_ok=True)
    result.save(str(dst), quality=95)
    print(f"✅ Carousel crop → {dst}  ({CAROUSEL_W}×{CAROUSEL_H}px)")


def trim_whitespace(src: Path, dst: Path, padding: int = 4) -> None:
    """
    Auto-trim whitespace borders from an image.
    Background color is auto-detected from the top-left corner pixel.
    """
    img = Image.open(src).convert("RGBA")

    # Detect background from top-left pixel
    bg_pixel = img.getpixel((0, 0))
    bg_img = Image.new("RGBA", img.size, bg_pixel)
    diff = ImageChops.difference(img, bg_img)
    bbox = diff.getbbox()

    if bbox:
        x0 = max(0, bbox[0] - padding)
        y0 = max(0, bbox[1] - padding)
        x1 = min(img.width, bbox[2] + padding)
        y1 = min(img.height, bbox[3] + padding)
        result = img.crop((x0, y0, x1, y1))
    else:
        result = img  # nothing to trim

    dst.parent.mkdir(parents=True, exist_ok=True)
    result.save(str(dst))
    print(f"✅ Trimmed → {dst}  ({result.width}×{result.height}px)")


def main():
    ap = argparse.ArgumentParser(description="Image crop utilities for Social Media pipeline")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser(
        "infographic-carousel",
        help="Crop NLM portrait infographic to 1000×460 landscape for carousel",
    )
    p1.add_argument("src", help="Source image path")
    p1.add_argument("--out", required=True, help="Output path")

    p2 = sub.add_parser("trim", help="Auto-trim whitespace borders")
    p2.add_argument("src", help="Source image path")
    p2.add_argument("--out", required=True, help="Output path")
    p2.add_argument("--padding", type=int, default=4, help="Padding after trim in px (default: 4)")

    args = ap.parse_args()
    src = Path(args.src)

    if not src.exists():
        print(f"❌ File not found: {src}")
        sys.exit(1)

    dst = Path(args.out)

    if args.cmd == "infographic-carousel":
        crop_for_carousel(src, dst)
    elif args.cmd == "trim":
        trim_whitespace(src, dst, padding=args.padding)


if __name__ == "__main__":
    main()
