#!/usr/bin/env python3
"""
auto_crop_infographic.py — Smart-crop NLM infographic for carousel slide 4.

Generates 4 horizontal strips from the full portrait infographic,
picks the most data-dense section by pixel variance analysis,
and saves the crop as nlm_infographic_carousel.png.

Usage:
    python3 scripts/auto_crop_infographic.py <slug>
    python3 scripts/auto_crop_infographic.py <slug> --strip 1   # force strip 0-3
    python3 scripts/auto_crop_infographic.py <slug> --y-from 1050 --y-to 1900  # custom range

Output:
    assets/post/{slug}/nlm_infographic_carousel.png
    /tmp/{slug}_strip_0.png … _strip_3.png   (for visual review)
"""

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageStat


BASE   = Path(__file__).parent.parent
ASSETS = BASE / "assets"


def load_infographic(slug: str) -> tuple[Image.Image, Path]:
    path = ASSETS / "post" / slug / "nlm_infographic.png"
    if not path.exists():
        print(f"❌ Not found: {path}")
        sys.exit(1)
    return Image.open(path), path


def generate_strips(img: Image.Image, slug: str, n: int = 4) -> list[dict]:
    """Split image into n horizontal strips, save previews, compute variance."""
    w, h = img.size
    strip_h = h // n
    strips = []
    for i in range(n):
        y0 = i * strip_h
        y1 = y0 + strip_h if i < n - 1 else h
        crop = img.crop((0, y0, w, y1))
        tmp  = Path(f"/tmp/{slug}_strip_{i}.png")
        crop.save(tmp)
        # Pixel variance as proxy for information density
        stat = ImageStat.Stat(crop.convert("L"))
        variance = stat.var[0]
        strips.append({"index": i, "y0": y0, "y1": y1, "variance": variance, "path": str(tmp)})
        print(f"  Strip {i}  y={y0}–{y1}  variance={variance:.0f}  → {tmp}")
    return strips


def pick_best_strip(strips: list[dict]) -> dict:
    """
    Pick the strip with highest variance (most visual complexity = most data).
    Strip 0 (title/header) is often plain text — downweight it.
    """
    candidates = [s for s in strips if s["index"] > 0]   # skip header strip
    if not candidates:
        candidates = strips
    best = max(candidates, key=lambda s: s["variance"])
    print(f"\n  → Auto-selected strip {best['index']}  (variance={best['variance']:.0f})")
    return best


def crop_and_save(img: Image.Image, y0: int, y1: int, slug: str) -> Path:
    """Crop image vertically and save as nlm_infographic_carousel.png."""
    w = img.width
    # Add 5% padding above selected strip for context
    pad = max(0, y0 - int((y1 - y0) * 0.05))
    crop = img.crop((0, pad, w, y1))
    out = ASSETS / "post" / slug / "nlm_infographic_carousel.png"
    crop.save(out)
    print(f"  ✅ Saved: {out}  ({crop.size[0]}×{crop.size[1]}px)")
    return out


def main():
    ap = argparse.ArgumentParser(description="Smart-crop NLM infographic for carousel")
    ap.add_argument("slug", help="Post slug (e.g. claude-code-dispatch-channels)")
    ap.add_argument("--strip",  type=int, help="Force a specific strip index (0-3)")
    ap.add_argument("--y-from", type=int, help="Manual crop start Y")
    ap.add_argument("--y-to",   type=int, help="Manual crop end Y")
    ap.add_argument("--n-strips", type=int, default=4, help="Number of strips (default: 4)")
    args = ap.parse_args()

    slug = args.slug
    img, src = load_infographic(slug)
    w, h = img.size
    print(f"\n=== Auto Crop Infographic ===")
    print(f"  Source : {src}  ({w}×{h}px)")
    print(f"  Slug   : {slug}\n")

    # Manual override
    if args.y_from is not None and args.y_to is not None:
        print(f"  Manual range: y={args.y_from}–{args.y_to}")
        crop_and_save(img, args.y_from, args.y_to, slug)
        return

    # Generate strips
    print(f"  Generating {args.n_strips} strips…")
    strips = generate_strips(img, slug, n=args.n_strips)

    # Pick best
    if args.strip is not None:
        chosen = next((s for s in strips if s["index"] == args.strip), strips[0])
        print(f"\n  → Forced strip {chosen['index']}")
    else:
        chosen = pick_best_strip(strips)

    # Save crop
    crop_and_save(img, chosen["y0"], chosen["y1"], slug)

    print(f"\n  Strip previews → /tmp/{slug}_strip_*.png")
    print(f"  Review them and re-run with --strip N if you prefer a different section.")


if __name__ == "__main__":
    main()
