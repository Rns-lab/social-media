#!/usr/bin/env python3
"""
NotebookLM Video Overview — pure API generator + downloader.
No Playwright. Uses notebooklm-py to generate, poll, and download directly.

Usage:
  python3 screenshot_notebooklm.py --notebook-id <ID> --slug <slug>
  python3 screenshot_notebooklm.py --research-json research/topics/{slug}.json
  python3 screenshot_notebooklm.py --notebook-id <ID> --slug <slug> --style ANIME
  python3 screenshot_notebooklm.py --notebook-id <ID> --slug <slug> --regenerate
  python3 screenshot_notebooklm.py --notebook-id <ID> --slug <slug> --no-push

Outputs:
  assets/post/{slug}/nlm_video_overview.mp4   — downloaded MP4
  assets/post/{slug}/nlm_video.png            — keyframe for carousel (requires ffmpeg)
  research/topics/{slug}.json                 — updated with nlm_video_url
"""
import argparse
import asyncio
import json
import subprocess
from pathlib import Path

GITHUB_REPO     = "Rns-lab/social-media"
GITHUB_BRANCH   = "main"
GITHUB_RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}"

ASSETS       = Path(__file__).parent.parent / "assets"
RESEARCH_DIR = Path(__file__).parent.parent / "research" / "topics"

STYLE_MAP = {
    "AUTO":       "AUTO_SELECT",
    "CLASSIC":    "CLASSIC",
    "WHITEBOARD": "WHITEBOARD",
    "KAWAII":     "KAWAII",
    "ANIME":      "ANIME",
    "WATERCOLOR": "WATERCOLOR",
    "RETRO":      "RETRO_PRINT",
    "HERITAGE":   "HERITAGE",
    "PAPER":      "PAPER_CRAFT",
}


def _get_ffmpeg() -> str:
    """Return ffmpeg binary path — bundled via imageio-ffmpeg, no brew needed."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return "ffmpeg"  # fall back to system ffmpeg if available


def extract_frame(mp4_path: Path, output_path: Path) -> bool:
    """Extract a keyframe from MP4 using bundled ffmpeg. Tries multiple timestamps."""
    ffmpeg = _get_ffmpeg()
    for ts in [8, 4, 2, 1]:
        try:
            subprocess.run(
                [ffmpeg, "-y", "-ss", str(ts), "-i", str(mp4_path),
                 "-vframes", "1", "-q:v", "2", str(output_path)],
                capture_output=True, timeout=30,
            )
            if output_path.exists() and output_path.stat().st_size > 0:
                print(f"  ✅ Keyframe extracted at {ts}s → {output_path.name}")
                return True
        except subprocess.TimeoutExpired:
            continue
    return False


async def run(args):
    from notebooklm import NotebookLMClient
    from notebooklm.rpc.types import VideoStyle, VideoFormat

    post_dir = ASSETS / "post" / args.slug
    post_dir.mkdir(parents=True, exist_ok=True)
    mp4_path = post_dir / "nlm_video_overview.mp4"
    png_path = post_dir / "nlm_video.png"

    # Resolve VideoStyle enum
    style_key = args.style.upper()
    style_name = STYLE_MAP.get(style_key, style_key)
    try:
        video_style = VideoStyle[style_name]
    except KeyError:
        print(f"  ⚠️  Unknown style '{args.style}' — using WHITEBOARD")
        video_style = VideoStyle.WHITEBOARD

    async with await NotebookLMClient.from_storage(timeout=180.0) as client:

        # Check for existing completed video
        art = None
        if not args.regenerate:
            print("→ Checking for existing Video Overview...")
            existing = await client.artifacts.list_video(args.notebook_id)
            completed = [a for a in existing if a.is_completed]
            if completed:
                art = completed[-1]
                print(f"  Found completed video (id: {art.id}) — skipping generation")

        # Generate if needed
        if art is None:
            print(f"→ Generating Video Overview (style: {video_style.name})...")
            await client.artifacts.generate_video(
                args.notebook_id,
                instructions=args.instructions or (
                    "Create a professional visual explainer. "
                    "Lead with the most surprising number or cost comparison. "
                    "Audience: PE operators, management consultants, C-suite. "
                    "Tone: data-driven, direct, no buzzwords."
                ),
                video_format=VideoFormat.EXPLAINER,
                video_style=video_style,
            )

            print("  Polling for completion (up to 45 min)", end="", flush=True)
            for _ in range(270):  # 270 × 10s = 45 min max
                await asyncio.sleep(10)
                videos = await client.artifacts.list_video(args.notebook_id)
                if videos:
                    art = videos[-1]
                    if art.is_completed:
                        print(" done.")
                        break
                    if art.status == 4:  # failed
                        print(" FAILED.")
                        print("❌ Video generation failed.")
                        return
                print(".", end="", flush=True)
            else:
                print(" timed out.")
                print("❌ Video generation timed out after 45 min.")
                return

        # Download MP4
        print("→ Downloading MP4...")
        await client.artifacts.download_video(
            args.notebook_id, str(mp4_path), artifact_id=art.id
        )
        size_mb = mp4_path.stat().st_size / 1024 / 1024
        print(f"  ✅ {size_mb:.1f} MB → {mp4_path.name}")

    # Extract keyframe for carousel
    print("→ Extracting keyframe for carousel PNG...")
    extract_frame(mp4_path, png_path)

    # Update research JSON
    github_url = f"{GITHUB_RAW_BASE}/assets/post/{args.slug}/nlm_video_overview.mp4"
    research_json = RESEARCH_DIR / f"{args.slug}.json"
    if research_json.exists():
        with open(research_json) as f:
            data = json.load(f)
        data["nlm_video_url"] = github_url
        with open(research_json, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  ✅ research JSON updated: nlm_video_url set")

    # Git push
    if not args.no_push:
        print("→ Pushing to GitHub...")
        repo = Path(__file__).parent.parent
        files_to_add = [str(mp4_path)]
        if png_path.exists():
            files_to_add.append(str(png_path))
        if research_json.exists():
            files_to_add.append(str(research_json))
        try:
            subprocess.run(["git", "-C", str(repo), "add"] + files_to_add, check=True)
            subprocess.run(
                ["git", "-C", str(repo), "commit", "-m",
                 f"Add Video Overview MP4 + keyframe for {args.slug}"],
                check=True,
            )
            subprocess.run(["git", "-C", str(repo), "push"], check=True)
            print("  ✅ Pushed to GitHub")
        except subprocess.CalledProcessError as e:
            print(f"  ⚠️  Git push failed: {e}")

    print("\nDone.")
    print(f"  MP4:        {mp4_path}")
    if png_path.exists():
        print(f"  Carousel:   {png_path}")
    print(f"  GitHub URL: {github_url}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Generate + download NotebookLM Video Overview via API (no Playwright)"
    )
    ap.add_argument("--research-json",  help="Path to research JSON — auto-fills --notebook-id and --slug")
    ap.add_argument("--notebook-id",    help="NotebookLM notebook UUID")
    ap.add_argument("--slug",           help="Post slug")
    ap.add_argument("--style",          default="WHITEBOARD",
                    help=f"Video style: {', '.join(STYLE_MAP.keys())} (default: WHITEBOARD)")
    ap.add_argument("--instructions",   default=None,
                    help="Custom instructions for the video generator")
    ap.add_argument("--regenerate",     action="store_true",
                    help="Force regeneration even if a completed video exists")
    ap.add_argument("--no-push",        action="store_true",
                    help="Skip git push after download")
    # Legacy arg kept for backwards compat — no longer used
    ap.add_argument("--wait",           type=int, default=None,
                    help="(Deprecated — ignored)")
    ap.add_argument("--download-video", action="store_true",
                    help="(Deprecated — always downloads now)")
    args = ap.parse_args()

    if args.research_json:
        with open(args.research_json) as f:
            _r = json.load(f)
        args.notebook_id = args.notebook_id or _r.get("notebook_id")
        args.slug        = args.slug        or _r.get("slug")

    if not args.notebook_id or not args.slug:
        ap.error("Provide --research-json OR both --notebook-id and --slug")

    asyncio.run(run(args))
