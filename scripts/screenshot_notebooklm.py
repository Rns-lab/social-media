#!/usr/bin/env python3
"""
Screenshot NotebookLM Video Overview player.
Optionally downloads the MP4 and updates the research JSON with nlm_video_url.

Usage:
  python3 screenshot_notebooklm.py --notebook-id <ID> --slug <slug>
  python3 screenshot_notebooklm.py --notebook-id <ID> --slug <slug> --download-video
  python3 screenshot_notebooklm.py --notebook-id <ID> --slug <slug> --download-video --no-push
"""
import argparse
import asyncio
import json
import subprocess
import requests
from pathlib import Path
from playwright.async_api import async_playwright

STORAGE_STATE   = Path.home() / ".notebooklm" / "storage_state.json"
ASSETS          = Path(__file__).parent.parent / "assets"
RESEARCH_DIR    = Path(__file__).parent.parent / "research" / "topics"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/Rns-lab/social-media/main"


async def click_first_visible(page, locators, label="element", timeout=5000):
    for loc in locators:
        try:
            await loc.wait_for(state="visible", timeout=timeout)
            await loc.click()
            print(f"  ✅ Clicked {label}")
            return True
        except Exception:
            continue
    print(f"  ⚠️  {label} not found")
    return False


async def run(args):
    notebook_url = f"https://notebooklm.google.com/notebook/{args.notebook_id}"
    post_dir     = ASSETS / "post" / args.slug
    post_dir.mkdir(parents=True, exist_ok=True)
    output       = post_dir / "nlm_video.png"

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False, channel="chrome", slow_mo=100)
        ctx = await browser.new_context(
            storage_state=str(STORAGE_STATE),
            viewport={"width": 1440, "height": 900},
        )
        page = await ctx.new_page()

        # 1. Navigate
        print(f"→ Opening notebook…")
        await page.goto(notebook_url)
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(6000)

        title = await page.title()
        print(f"  Page: {title[:80]}")
        if "Sign in" in title:
            print("❌ Not authenticated. Run: notebooklm login")
            await browser.close()
            return

        # 2. Click Video Overview
        print("→ Clicking Video Overview…")
        await click_first_visible(page, [
            page.get_by_role("button", name="Video Overview").first,
            page.locator("[aria-label='Video Overview']").first,
            page.locator("button:has-text('Video')").first,
        ], "Video Overview", timeout=6000)

        # 3. Generate if needed
        await page.wait_for_timeout(3000)
        gen_clicked = await click_first_visible(page, [
            page.get_by_role("button", name="Generate").first,
            page.locator("button:has-text('Generate')").first,
        ], "Generate button", timeout=3000)
        if gen_clicked:
            print("  ⏳ Generating — waiting up to 3 min…")
            try:
                await page.wait_for_selector("[aria-label='Play'], button:has-text('Play')", timeout=180000)
                print("  ✅ Generated")
            except Exception:
                print("  ⚠️  Generation timeout — proceeding anyway")

        await page.wait_for_timeout(5000)

        # 4. Click Play
        print("→ Clicking Play…")
        try:
            play = page.locator("[aria-label='Play']").first
            await play.wait_for(state="visible", timeout=8000)
            await play.click()
            print("  ✅ Play clicked")
        except Exception as e:
            print(f"  ⚠️  Play not clicked: {e}")

        # 5. Wait
        print(f"→ Waiting {args.wait}s…")
        await page.wait_for_timeout(args.wait * 1000)

        # 6. Screenshot video element
        print("→ Capturing screenshot…")
        box = None
        for sel in ["video", "video-player"]:
            try:
                el = page.locator(sel).first
                await el.wait_for(state="visible", timeout=5000)
                box = await el.bounding_box()
                if box:
                    print(f"  Found <{sel}> at {box}")
                    break
            except Exception:
                continue

        if box:
            await page.screenshot(path=str(output), clip={
                "x": box["x"], "y": box["y"],
                "width": box["width"], "height": box["height"],
            })
            print(f"  ✅ Screenshot → {output}  ({int(box['width'])}×{int(box['height'])}px)")
        else:
            print("  ⚠️  No video element found — saving full viewport debug screenshot")
            await page.screenshot(path=str(post_dir / "debug_nlm.png"))

        # 7. Download video MP4 (optional)
        if args.download_video:
            print("→ Extracting video URL…")
            video_src = await page.evaluate(
                "document.querySelector('video')?.src || document.querySelector('video')?.currentSrc || ''"
            )
            if not video_src:
                print("  ⚠️  No video src found — skipping download")
            else:
                print(f"  src: {video_src[:80]}…")
                mp4_path = post_dir / "nlm_video_overview.mp4"
                print("→ Downloading MP4…")
                with open(STORAGE_STATE) as f:
                    state = json.load(f)
                sess = requests.Session()
                for c in state["cookies"]:
                    sess.cookies.set(c["name"], c["value"], domain=c.get("domain", "").lstrip("."))
                resp = sess.get(video_src, headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                    "Referer": "https://notebooklm.google.com/",
                }, stream=True, timeout=120)
                if resp.status_code == 200:
                    size = 0
                    with open(mp4_path, "wb") as f:
                        for chunk in resp.iter_content(65536):
                            f.write(chunk)
                            size += len(chunk)
                    print(f"  ✅ Downloaded: {size/1024/1024:.1f} MB → {mp4_path}")

                    # Update research JSON with GitHub raw URL
                    github_url = f"{GITHUB_RAW_BASE}/assets/post/{args.slug}/nlm_video_overview.mp4"
                    research_json = RESEARCH_DIR / f"{args.slug}.json"
                    if research_json.exists():
                        with open(research_json) as f:
                            data = json.load(f)
                        data["nlm_video_url"] = github_url
                        with open(research_json, "w") as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)
                        print(f"  ✅ Updated research JSON: nlm_video_url set")
                    else:
                        print(f"  ⚠️  Research JSON not found: {research_json}")

                    # Git push
                    if not args.no_push:
                        print("→ Pushing to GitHub…")
                        repo = Path(__file__).parent.parent
                        try:
                            subprocess.run(["git", "-C", str(repo), "add", str(mp4_path)], check=True)
                            if research_json.exists():
                                subprocess.run(["git", "-C", str(repo), "add", str(research_json)], check=True)
                            subprocess.run(["git", "-C", str(repo), "commit", "-m",
                                f"Add Video Overview MP4 + nlm_video_url for {args.slug}"], check=True)
                            subprocess.run(["git", "-C", str(repo), "push"], check=True)
                            print("  ✅ Pushed to GitHub")
                        except subprocess.CalledProcessError as e:
                            print(f"  ⚠️  Git push failed: {e}")
                else:
                    print(f"  ❌ Download failed: HTTP {resp.status_code}")

        await browser.close()
        print("Done.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--notebook-id",    required=True, help="NotebookLM notebook UUID")
    ap.add_argument("--slug",           required=True, help="Post slug (e.g. my-topic)")
    ap.add_argument("--wait",           type=int, default=20, help="Seconds to wait after Play (default: 20)")
    ap.add_argument("--download-video", action="store_true", help="Download MP4 + update research JSON + push")
    ap.add_argument("--no-push",        action="store_true", help="Skip git push after video download")
    args = ap.parse_args()
    asyncio.run(run(args))
