#!/usr/bin/env python3
"""
Screenshot NotebookLM Video Overview player.
Flow: load auth → homepage → click notebook → click Video Overview → Play → 20s → screenshot.
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

STORAGE_STATE = Path.home() / ".notebooklm" / "storage_state.json"
NOTEBOOK_URL  = "https://notebooklm.google.com/notebook/c5229b8e-f0a7-4472-a5c2-7be7a0323924"
NOTEBOOK_NAME = "Claude Code Skills"   # partial match
BASE          = Path(__file__).parent.parent / "assets"
SLUG          = "claude-code-scheduled-tasks"   # override per run
OUTPUT        = BASE / "post" / SLUG / "nlm_video.png"


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


async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False,
            channel="chrome",
            slow_mo=100,
        )
        ctx = await browser.new_context(
            storage_state=str(STORAGE_STATE),
            viewport={"width": 1440, "height": 900},
        )
        page = await ctx.new_page()

        # ── 1. Navigate directly to the notebook ────────────────────────────
        print(f"→ Opening notebook…")
        await page.goto(NOTEBOOK_URL)
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(6000)  # NotebookLM takes time to fully render

        title = await page.title()
        print(f"  Page: {title}  |  URL: {page.url[:80]}")
        if "Sign in" in title:
            print("❌ Not authenticated. Run: notebooklm login")
            await browser.close()
            return

        # ── 3. Find & click "Video Overview" ────────────────────────────────
        print("→ Looking for Video Overview…")

        # Dump what's on screen for debugging
        buttons = await page.evaluate("""() => {
            const els = [...document.querySelectorAll('button, [role="button"], [role="tab"]')];
            return els.map(el => ({
                text: el.textContent?.trim().slice(0, 60),
                aria: el.getAttribute('aria-label') || '',
            })).filter(e => e.text || e.aria).slice(0, 40);
        }""")
        print(f"  Found {len(buttons)} buttons:")
        for b in buttons:
            if any(k in (b['text']+b['aria']).lower() for k in ['video','audio','studio','overview','generate']):
                print(f"    >> [{b['text']}] aria='{b['aria']}'")

        video_locators = [
            page.get_by_role("button", name="Video Overview"),
            page.get_by_text("Video Overview"),
            page.locator("[aria-label='Video Overview']"),
            page.locator("button:has-text('Video')"),
            page.get_by_role("tab", name="Video Overview"),
        ]
        await click_first_visible(page, video_locators, "Video Overview", timeout=6000)

        # ── 4a. Handle Generate state (video not yet created) ────────────────
        print("→ Checking if video needs to be generated…")
        await page.wait_for_timeout(3000)

        generate_locators = [
            page.get_by_role("button", name="Generate"),
            page.locator("button:has-text('Generate')"),
        ]
        gen_clicked = await click_first_visible(page, generate_locators, "Generate button", timeout=3000)
        if gen_clicked:
            print("  ⏳ Video generating — waiting up to 3 minutes…")
            # Wait for play button to appear (means generation done)
            try:
                await page.wait_for_selector("[aria-label='Play'], button:has-text('Play')", timeout=180000)
                print("  ✅ Video generated")
            except Exception:
                print("  ⚠️  Generation timeout — proceeding anyway")

        await page.wait_for_timeout(5000)

        # ── 4b. Click Play ───────────────────────────────────────────────────
        print("→ Looking for Play button…")

        # Dump buttons near the player for debugging
        btns = await page.evaluate("""() => {
            const els = [...document.querySelectorAll('button, [role="button"]')];
            return els.map(el => ({
                text: el.textContent?.trim().slice(0, 50),
                aria: el.getAttribute('aria-label') || '',
            })).filter(e => e.text || e.aria).slice(0, 60);
        }""")
        for b in btns:
            combined = (b['text'] + b['aria']).lower()
            if any(k in combined for k in ['play', 'pause', 'video', 'overview', 'watch']):
                print(f"    >> [{b['text']}] aria='{b['aria']}'")

        # Use .first to avoid multi-match issues, click directly
        try:
            play = page.locator("[aria-label='Play']").first
            await play.wait_for(state="visible", timeout=8000)
            await play.click()
            print("  ✅ Clicked Play button")
        except Exception as e:
            print(f"  ⚠️  Play button not clicked: {e}")

        # ── 5. Wait 20s ──────────────────────────────────────────────────────
        print("→ Waiting 20 seconds for video to play…")
        await page.wait_for_timeout(20000)

        # ── 6. Screenshot ────────────────────────────────────────────────────
        print("→ Capturing screenshot…")

        # Try <video> element first
        box = None
        try:
            video_el = page.locator("video").first
            await video_el.wait_for(state="visible", timeout=5000)
            box = await video_el.bounding_box()
            print(f"  Found <video> at {box}")
        except Exception:
            print("  No <video> element — trying VIDEO-PLAYER custom element")

        if not box:
            try:
                vp = page.locator("video-player").first
                box = await vp.bounding_box()
                print(f"  Found video-player at {box}")
            except Exception:
                pass

        if box:
            # Crop to video content only — no controls, no player frame
            clip = {
                "x": box["x"],
                "y": box["y"],
                "width": box["width"],
                "height": box["height"],
            }
            await page.screenshot(path=str(OUTPUT), clip=clip)
            print(f"  ✅ Saved: {OUTPUT}  ({int(clip['width'])}×{int(clip['height'])}px)")
        else:
            # Fallback: screenshot full visible viewport
            print("  ⚠️  No video element — saving full viewport")
            await page.screenshot(path=str(OUTPUT.parent / "debug_notebooklm_full.png"))
            debug_path = OUTPUT.parent / "debug_nlm.png"
            await page.screenshot(path=str(debug_path))
            print(f"  Saved debug screenshot → {debug_path}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
