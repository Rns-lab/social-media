#!/usr/bin/env python3
"""
Record a browser demo session as .webm for carousel video banners.

The recorded .webm can be used directly in carousel JSON as:
  "video_banner": "assets/post/{slug}/demo_perplexity.webm"

generate_carousel.py will render it as a <video autoplay muted loop> element
and screenshot a live frame — not a static thumbnail.

Usage:
  python3 record_demo.py --url "https://perplexity.ai" --out assets/post/{slug}/demo.webm
  python3 record_demo.py --url "https://..." --out demo.webm --wait 8 --scroll
  python3 record_demo.py --url "https://..." --out demo.webm --no-headless  # show browser
  python3 record_demo.py --url "https://..." --out demo.webm --frame-at 4   # screenshot at 4s
"""
import argparse
import asyncio
import shutil
import subprocess
import tempfile
from pathlib import Path

from playwright.async_api import async_playwright


def _get_ffmpeg() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return "ffmpeg"


def extract_frame(webm_path: Path, output_path: Path, timestamp: int = 4) -> bool:
    """Extract a still frame from the webm for preview/debug."""
    ffmpeg = _get_ffmpeg()
    for ts in [timestamp, 2, 1]:
        try:
            subprocess.run(
                [ffmpeg, "-y", "-ss", str(ts), "-i", str(webm_path),
                 "-vframes", "1", "-q:v", "2", str(output_path)],
                capture_output=True, timeout=30,
            )
            if output_path.exists() and output_path.stat().st_size > 0:
                return True
        except subprocess.TimeoutExpired:
            continue
    return False


async def record(args):
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)

    # Viewport: match carousel video_banner slot (1080 wide, cinematic height)
    width  = args.width
    height = args.height

    with tempfile.TemporaryDirectory() as tmp:
        async with async_playwright() as pw:
            launch_kwargs = {"headless": args.headless}
            if not args.headless:
                launch_kwargs["channel"] = "chrome"

            browser = await pw.chromium.launch(**launch_kwargs)
            context = await browser.new_context(
                viewport={"width": width, "height": height},
                record_video_dir=tmp,
                record_video_size={"width": width, "height": height},
            )
            page = await context.new_page()

            print(f"→ Recording {width}×{height} — navigating to {args.url}...")
            await page.goto(args.url)
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(2000)

            if args.scroll:
                print("→ Scrolling...")
                for _ in range(4):
                    await page.mouse.wheel(0, 350)
                    await page.wait_for_timeout(700)

            print(f"→ Recording for {args.wait}s...")
            await page.wait_for_timeout(args.wait * 1000)

            # Capture path BEFORE closing — unavailable after
            video_path = page.video.path
            await context.close()  # video finalizes here

        # Copy out of temp dir before it's deleted
        shutil.copy(video_path, output)

    size_mb = output.stat().st_size / 1024 / 1024
    print(f"✅ {output}  ({size_mb:.1f} MB, {width}×{height})")

    # Optionally extract a preview frame
    if args.frame_at is not None:
        preview = output.with_suffix(".preview.png")
        if extract_frame(output, preview, timestamp=args.frame_at):
            print(f"   Preview frame → {preview}")

    print()
    print("Use in carousel JSON:")
    print(f'  "video_banner": "{output}"')


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Record a browser session as .webm for carousel video banners"
    )
    ap.add_argument("--url",        required=True, help="URL to navigate to")
    ap.add_argument("--out",        required=True, help="Output .webm path")
    ap.add_argument("--wait",       type=int, default=8,
                    help="Recording duration in seconds after page load (default: 8)")
    ap.add_argument("--width",      type=int, default=1080,
                    help="Viewport width (default: 1080 — matches carousel)")
    ap.add_argument("--height",     type=int, default=560,
                    help="Viewport height (default: 560 — matches video_banner slot)")
    ap.add_argument("--scroll",     action="store_true",
                    help="Slowly scroll down during recording")
    ap.add_argument("--frame-at",   type=int, default=None,
                    help="Extract a preview PNG at this timestamp (seconds)")
    ap.add_argument("--no-headless", dest="headless", action="store_false",
                    help="Show the browser window during recording")
    ap.set_defaults(headless=True)
    args = ap.parse_args()

    asyncio.run(record(args))
