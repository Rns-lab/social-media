#!/usr/bin/env python3
"""
Master Carousel Runner — one command to build all assets and assemble slides.

Steps (run in parallel where independent):
  1. generate_diagrams.py    — process flow images for value slides
  2. generate_cover_thumbnail.py — YouTube-style cover with face photo
  3. notebooklm_screenshot.py   — (optional, --notebooklm flag) Video Overview screenshot
  Then:
  4. generate_carousel.py    — assemble final 1080×1080 slides

Usage:
  python3 scripts/run_carousel.py scripts/example_carousel.json
  python3 scripts/run_carousel.py scripts/example_carousel.json --notebooklm
  python3 scripts/run_carousel.py scripts/my_carousel.json --face assets/photos/Shock.JPG --output-dir assets/images/my_slug
"""

import argparse
import json
import subprocess
import sys
import threading
from pathlib import Path

BASE   = Path(__file__).parent
ASSETS = BASE.parent / "assets"

DEFAULT_FACE = ASSETS / "profile" / "Shock.JPG"


def run_step(label: str, cmd: list, results: dict, key: str):
    """Run a subprocess, store True/False in results[key]."""
    print(f"⏳ {label}...")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0:
        print(f"✅ {label}")
        results[key] = True
    else:
        print(f"❌ {label}")
        if r.stderr.strip():
            print(f"   {r.stderr.strip()[:300]}")
        results[key] = False


def main():
    ap = argparse.ArgumentParser(description="Build all carousel assets and assemble slides.")
    ap.add_argument("content",          help="Path to carousel JSON")
    ap.add_argument("--output-dir",     help="Output directory for final slides (default: assets/images/carousel_final)")
    ap.add_argument("--face",           default=str(DEFAULT_FACE), help="Face photo for cover thumbnail")
    ap.add_argument("--cover-headline", default="SCHEDULED TASKS",  help="Cover thumbnail headline")
    ap.add_argument("--cover-subline",  default="3 REAL USE CASES", help="Cover thumbnail subline")
    ap.add_argument("--cover-topic",    default="Claude Code",       help="Cover thumbnail topic label")
    ap.add_argument("--notebooklm",     action="store_true",         help="Retake NotebookLM Video Overview screenshot")
    ap.add_argument("--nlm-wait",       type=int, default=20,        help="Seconds to wait after pressing play (default: 20)")
    ap.add_argument("--no-diagrams",    action="store_true",         help="Skip diagram generation")
    ap.add_argument("--no-cover",       action="store_true",         help="Skip cover thumbnail generation")
    ap.add_argument("--logos",          default=None,                help="Topic logos for thumbnail: 'path:label,path:label' (up to 3)")
    args = ap.parse_args()

    content_path = Path(args.content)
    if not content_path.exists():
        print(f"❌ Content file not found: {content_path}")
        sys.exit(1)

    with open(content_path) as f:
        data = json.load(f)
    slug = data.get("slug", "carousel")
    # logos: CLI flag takes priority, then carousel JSON field, then fallback to Claude logo
    logos_resolved = args.logos or data.get("logos") or None

    out_dir = args.output_dir or str(ASSETS / "images" / "carousel_final")

    print(f"\n🚀 Building carousel: '{slug}'")
    print(f"   Content : {content_path}")
    print(f"   Output  : {out_dir}\n")

    # ── Parallel asset generation ──────────────────────────────────────────────
    threads = []
    results = {}

    # 1. Diagrams (topic-specific generator — reads carousel JSON for diagram registry)
    if not args.no_diagrams:
        t = threading.Thread(
            target=run_step,
            args=("Diagrams", [sys.executable, str(BASE / "generate_topic_diagrams.py"), str(content_path)], results, "diagrams")
        )
        threads.append(t)

    # 2. Cover thumbnail — saved to slug's asset folder for carousel slide 1
    face_path = Path(args.face)
    cover_out = ASSETS / "post" / slug / "cover_thumbnail.png"
    cover_out.parent.mkdir(parents=True, exist_ok=True)
    if not args.no_cover:
        if face_path.exists():
            cover_cmd = [
                sys.executable, str(BASE / "generate_cover_thumbnail.py"),
                "--face",     str(face_path),
                "--topic",    args.cover_topic,
                "--headline", args.cover_headline,
                "--subline",  args.cover_subline,
                "--out",      str(cover_out),
            ]
            if logos_resolved:
                cover_cmd += ["--logos", logos_resolved]
            t = threading.Thread(
                target=run_step,
                args=("Cover thumbnail", cover_cmd, results, "cover")
            )
            threads.append(t)
        else:
            print(f"⚠️  Face photo not found: {face_path} — skipping cover thumbnail")

    # 3. NotebookLM screenshot (optional)
    if args.notebooklm:
        t = threading.Thread(
            target=run_step,
            args=("NotebookLM screenshot", [
                sys.executable, str(BASE / "notebooklm_screenshot.py"),
                "--wait", str(args.nlm_wait),
            ], results, "notebooklm")
        )
        threads.append(t)

    # Start + wait
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    failed = [k for k, v in results.items() if not v]
    if failed:
        print(f"\n⚠️  Some steps failed: {failed}")
        print("   Proceeding with carousel assembly using available assets...\n")
    else:
        print()

    # ── Assemble carousel (must run after all assets) ──────────────────────────
    cmd = [sys.executable, str(BASE / "generate_carousel.py"), str(content_path), "--output-dir", out_dir]
    r = subprocess.run(cmd, capture_output=False)  # let carousel output stream live

    if r.returncode == 0:
        print(f"\n🎯 All done! Slides → {out_dir}")
    else:
        print(f"\n❌ Carousel assembly failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
