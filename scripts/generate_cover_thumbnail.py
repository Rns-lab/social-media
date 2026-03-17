#!/usr/bin/env python3
"""
Cover Thumbnail Generator
Creates a YouTube-thumbnail-style image for carousel slide 1.

Usage:
  python3 generate_cover_thumbnail.py --topic "Claude Code" --headline "3 AUTOMATIONS" \
      --subline "WHILE YOU SLEEP" --face assets/photos/shocked_1.jpg \
      --out assets/images/cover_thumbnail.png \
      --logos "assets/resources/logos/perplexity.png:Perplexity,assets/resources/logos/manus.png:Manus"

  --logos is a comma-separated list of path:label pairs (up to 3).
  If omitted, falls back to the Claude logo.

Layout (1000×460px, dark):
  LEFT  (~520px): colored accent bar + bold headline + subline + logos row
  RIGHT (~480px): Pietro's face, cropped and composited on dark bg
"""

import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import sys

ASSETS = Path(__file__).parent.parent / "assets"

CLAUDE_LOGO_PNG = ASSETS / "resources" / "Claude Logo Compact.png"


def parse_logos(logos_arg: str | None) -> list[tuple[str, str]]:
    """Parse --logos 'path:label,path:label' into [(path, label), ...]."""
    if not logos_arg:
        return []
    result = []
    for entry in logos_arg.split(","):
        entry = entry.strip()
        if ":" in entry:
            path, label = entry.split(":", 1)
        else:
            path, label = entry, ""
        result.append((path.strip(), label.strip()))
    return result[:3]  # max 3


def load_face(face_path: str, target_h: int = 440) -> Image.Image:
    """Load and prepare the face photo: crop to portrait, resize."""
    img = Image.open(face_path).convert("RGBA")
    w, h = img.size

    # Crop to roughly top 80% height (cut some bottom/chest area)
    crop_h = int(h * 0.85)
    face = img.crop((0, 0, w, crop_h))

    # Resize to target height, keeping aspect ratio
    ratio = target_h / face.size[1]
    new_w = int(face.size[0] * ratio)
    face = face.resize((new_w, target_h), Image.LANCZOS)

    return face


def build_thumbnail(
    topic: str,
    headline: str,
    subline: str,
    face_path: str,
    out_path: str,
    logos: list[tuple[str, str]] | None = None,
    accent_color: tuple = (230, 92, 0),   # orange
    bg_color: tuple = (10, 10, 10),
):
    W, H = 1000, 460
    canvas = Image.new("RGB", (W, H), bg_color)
    draw = ImageDraw.Draw(canvas)

    # ── Subtle gradient overlay on left half ──
    for x in range(W // 2):
        alpha = int(25 * (1 - x / (W // 2)))
        draw.line([(x, 0), (x, H)], fill=(
            min(255, bg_color[0] + alpha),
            min(255, bg_color[1] + alpha),
            min(255, bg_color[2] + alpha),
        ))

    # ── Left accent bar ──
    draw.rectangle([(0, 0), (7, H)], fill=accent_color)

    # ── Face photo (right side) ──
    try:
        face = load_face(face_path, target_h=H + 20)
        # Position: right-aligned, slight bleed
        fx = W - face.size[0] + 20
        fy = -10
        if face.size[0] > W // 2 + 100:
            # Too wide — crop left side to fit
            crop_x = face.size[0] - (W // 2 + 120)
            face = face.crop((crop_x, 0, face.size[0], face.size[1]))
            fx = W - face.size[0]
        canvas.paste(face, (fx, fy), face if face.mode == "RGBA" else None)

        # Shadow/vignette on left edge of face area to blend
        vignette_w = 120
        for vx in range(vignette_w):
            alpha = int(200 * (1 - vx / vignette_w))
            r = int(bg_color[0] * alpha / 255 + canvas.getpixel((fx + vx, H // 2))[0] * (1 - alpha / 255))
            draw.line([(fx + vx, 0), (fx + vx, H)],
                      fill=(bg_color[0], bg_color[0], bg_color[0]))
        # Redo with proper blend
        for vx in range(vignette_w):
            blend = 1 - (vx / vignette_w) ** 0.5
            for vy in range(H):
                px = canvas.getpixel((fx + vx, vy))
                blended = tuple(int(bg * blend + px_c * (1 - blend))
                                for bg, px_c in zip(bg_color, px[:3]))
                draw.point((fx + vx, vy), fill=blended)
    except Exception as e:
        print(f"Face load failed: {e}")

    # ── Text (left area, x=28 to ~500) ──
    # Topic label (small, muted)
    try:
        font_topic = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
        font_headline = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 88)
        font_subline = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 52)
    except:
        font_topic = font_headline = font_subline = ImageFont.load_default()

    # Topic
    draw.text((30, 38), topic.upper(), fill=(113, 119, 123), font=font_topic)

    # Headline (very large, bold-like via stroke)
    draw.text((28, 70), headline, fill=(231, 233, 234), font=font_headline, stroke_width=2, stroke_fill=(231, 233, 234))

    # Subline (accent color)
    draw.text((30, 175), subline, fill=accent_color, font=font_subline, stroke_width=1, stroke_fill=accent_color)

    # ── Logo row (bottom left) ──
    LOGO_SIZE = 56
    logo_entries = logos or []
    # Fallback to Claude logo if nothing provided
    if not logo_entries:
        logo_entries = [(str(CLAUDE_LOGO_PNG), "Claude Code")]

    lx, ly = 28, H - 80
    for logo_path, logo_label in logo_entries:
        try:
            lg = Image.open(logo_path).convert("RGBA")
            lg = lg.resize((LOGO_SIZE, LOGO_SIZE), Image.LANCZOS)
            canvas.paste(lg, (lx, ly), lg)
            lx += LOGO_SIZE + 12
        except Exception as e:
            print(f"  ⚠ Logo not loaded ({logo_path}): {e}")

    # Save
    canvas.save(out_path, quality=95)
    print(f"✅ Cover thumbnail → {out_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic",    default="Claude Code")
    ap.add_argument("--headline", default="3 AUTOMATIONS")
    ap.add_argument("--subline",  default="WHILE YOU SLEEP")
    ap.add_argument("--face",     default=str(ASSETS / "profile" / "Shock.JPG"))
    ap.add_argument("--out",      default=str(ASSETS / "images" / "cover_thumbnail.png"))
    ap.add_argument("--logos",    default=None,
                    help="Comma-separated path:label pairs, e.g. logos/perplexity.png:Perplexity,logos/manus.png:Manus")
    args = ap.parse_args()

    if not Path(args.face).exists():
        print(f"⚠️  Face photo not found: {args.face}")
        print("Save your shocked photo to assets/photos/shocked_1.jpg first.")
        sys.exit(1)

    build_thumbnail(
        topic=args.topic,
        headline=args.headline,
        subline=args.subline,
        face_path=args.face,
        out_path=args.out,
        logos=parse_logos(args.logos),
    )
