#!/usr/bin/env python3
"""
Carousel Generator — Twitter/X post format
Usage:
  python3 generate_carousel.py <content.json> [--output-dir <dir>]

Layout (matches Tyler Germain's format exactly):
  - VERTICAL STACK: compact header row (avatar + name/handle) THEN body text
  - Body text starts at the SAME left edge as the avatar (full width)
  - Header: avatar center-aligned with Name ✓ @handle on ONE line
  - Body: large text, full slide width minus left/right padding

JSON slide fields:
  "paragraphs": ["text 1", "text 2", ...]     required
  "bold_line":  "1. Daily standup summary"    optional first bold line
  "image":      "path/to/image.png"           optional bottom media
  "image_bg":   "#1a1a2e"                     optional placeholder bg color
  "image_label": "Diagram placeholder"        optional placeholder label
"""

import json
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR   = Path(__file__).parent
TEMPLATE   = BASE_DIR / "carousel_template.html"
ASSETS_DIR = BASE_DIR.parent / "assets"
OUTPUT_DIR = ASSETS_DIR / "post"
PROFILE    = ASSETS_DIR / "profile" / "profile.jpg"

AUTHOR = {
    "name":   "Pietro Piga",
    "handle": "@PietroPiga_AI",
}

VERIFIED_SVG = """<svg viewBox="0 0 24 24" width="25" height="25" style="flex-shrink:0">
  <path d="M20.396 11c-.018-.646-.215-1.275-.57-1.816-.354-.54-.852-.972-1.438-1.246.223-.607.27-1.264.14-1.897-.131-.634-.437-1.218-.882-1.687-.47-.445-1.053-.75-1.687-.882-.633-.13-1.29-.083-1.897.14-.273-.587-.704-1.086-1.245-1.44S11.647 1.62 11 1.604c-.646.017-1.273.213-1.813.568s-.969.854-1.24 1.44c-.608-.223-1.267-.272-1.902-.14-.635.13-1.22.436-1.69.882-.445.47-.749 1.055-.878 1.688-.13.633-.08 1.29.144 1.896-.587.274-1.087.705-1.443 1.245-.356.54-.555 1.17-.574 1.817.02.647.218 1.276.574 1.817.356.54.856.972 1.443 1.245-.224.606-.274 1.263-.144 1.896.13.634.433 1.218.877 1.688.47.443 1.054.747 1.687.878.633.132 1.29.084 1.897-.136.274.586.705 1.084 1.246 1.439.54.354 1.17.551 1.816.569.647-.016 1.276-.213 1.817-.567s.972-.854 1.245-1.44c.604.239 1.266.296 1.903.164.636-.132 1.22-.447 1.68-.907.46-.46.776-1.044.908-1.681s.075-1.299-.165-1.903c.586-.274 1.084-.705 1.439-1.246.354-.54.551-1.17.569-1.816zM9.662 14.85l-3.429-3.428 1.293-1.302 2.072 2.072 4.4-4.794 1.347 1.246z" fill="#1D9BF0"/>
</svg>"""


def header_html() -> str:
    if PROFILE.exists():
        avatar = f'<img src="file://{PROFILE}" alt="avatar"/>'
    else:
        avatar = '<div style="width:64px;height:64px;background:#444;border-radius:50%"></div>'

    return f"""<div class="header">
      <div class="avatar">{avatar}</div>
      <div class="meta">
        <span class="author-name">{AUTHOR["name"]}</span>
        {VERIFIED_SVG}
        <span class="author-handle">{AUTHOR["handle"]}</span>
      </div>
    </div>"""


def media_html(slide: dict, output_dir: Path) -> str:
    img_path = slide.get("image", "")
    if img_path:
        p = Path(img_path)
        if not p.is_absolute():
            p = output_dir / img_path
        if p.exists():
            return f'<div class="media"><img src="file://{p.absolute()}" alt=""/></div>'

    bg    = slide.get("image_bg", "#0D1117")
    label = slide.get("image_label", "")
    if label or slide.get("show_placeholder", False):
        return f'<div class="media"><div class="media-placeholder" style="background:{bg}">{label}</div></div>'

    return ""


def build_slide(slide: dict, idx: int, total: int, output_dir: Path) -> str:
    bold_line  = slide.get("bold_line", "")
    paragraphs = slide.get("paragraphs", [])

    bold_html  = f'<span class="bold-line">{bold_line}</span>' if bold_line else ""
    paras_html = "".join(f"<p>{p}</p>" for p in paragraphs)
    counter    = f'<div class="counter">{idx}/{total}</div>' if total > 1 else ""

    # Scale font size down for longer content
    total_chars = sum(len(p) for p in paragraphs) + len(bold_line)
    has_image   = bool(slide.get("image") or slide.get("image_label"))

    if has_image:
        if total_chars > 250: font_size = "40px"
        elif total_chars > 160: font_size = "44px"
        else: font_size = "48px"
    else:
        if total_chars > 320: font_size = "44px"
        elif total_chars > 220: font_size = "50px"
        else: font_size = "57px"

    return f"""
    <div class="slide">
      {counter}
      {header_html()}
      <div class="body">
        <div class="tweet-text" style="font-size:{font_size}">
          {bold_html}{paras_html}
        </div>
        {media_html(slide, output_dir)}
      </div>
    </div>"""


def generate_carousel(content_file: str, output_dir: str = None):
    with open(content_file) as f:
        data = json.load(f)

    slug   = data.get("slug", "carousel")
    slides = data.get("slides", [])
    total  = len(slides)

    out = Path(output_dir) if output_dir else OUTPUT_DIR / slug / "carousel"
    out.mkdir(parents=True, exist_ok=True)

    template = TEMPLATE.read_text()

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page    = browser.new_page(viewport={"width": 1080, "height": 1080})

        files = []
        for i, slide_data in enumerate(slides, 1):
            slide_html = build_slide(slide_data, i, total, out)
            full_html  = template.replace("{{SLIDES}}", slide_html)

            tmp = out / f"_tmp_{i}.html"
            tmp.write_text(full_html)

            page.goto(f"file://{tmp.absolute()}")
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
            page.wait_for_timeout(300)

            dest = str(out / f"slide_{i:02d}.png")
            page.screenshot(path=dest, clip={"x": 0, "y": 0, "width": 1080, "height": 1080})
            tmp.unlink()

            files.append(dest)
            print(f"  ✓ {i}/{total} → {dest}")

        browser.close()

    print(f"\n✅ '{slug}' — {len(files)} slides → {out}")
    return files


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("content", help="Path to carousel JSON")
    ap.add_argument("--output-dir", help="Output directory")
    args = ap.parse_args()
    generate_carousel(args.content, args.output_dir)
