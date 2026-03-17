#!/usr/bin/env python3
"""
Screenshot the NotebookLM Video Overview player.
"""
import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright

NOTEBOOK_URL = "https://notebooklm.google.com/notebook/3244c36e-0b17-44cd-8878-420081e549f0"
STORAGE_STATE = str(Path.home() / ".notebooklm" / "storage_state.json")
OUT_PATH = "/Users/pietropiga/Desktop/Claude Code/Social Media/assets/post/perplexity-computer-vs-manus-ai-computer-agents/nlm_video.png"


async def main():
    async with async_playwright() as p:
        print("1) Launching Chrome...")
        browser = await p.chromium.launch(
            headless=False,
            channel="chrome",
            slow_mo=150,
        )
        context = await browser.new_context(storage_state=STORAGE_STATE)
        page = await context.new_page()

        print("2) Navigating to notebook...")
        await page.goto(NOTEBOOK_URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
        print(f"   Title: {await page.title()}")

        print("3) Looking for Video Overview button...")
        # Use .first to avoid strict-mode error (may match 2 elements)
        video_btn = page.get_by_role("button", name="Video Overview").first
        if not await video_btn.count():
            video_btn = page.locator("[aria-label='Video Overview']").first
        await video_btn.wait_for(timeout=15000)
        await video_btn.click()
        print("   Clicked Video Overview")
        await page.wait_for_timeout(2000)

        print("4) Waiting for video to be ready (up to 3min)...")
        # Poll for Play button — appears once generation completes
        play_found = False
        for attempt in range(36):  # 36 * 5s = 180s
            await page.wait_for_timeout(5000)
            for sel in ["[aria-label='Play']", "[aria-label='play']", "button:has-text('Play')"]:
                count = await page.locator(sel).count()
                if count:
                    print(f"   Play button appeared after {(attempt+1)*5}s ({sel})")
                    play_found = True
                    break
            if play_found:
                break
            if attempt % 6 == 5:
                print(f"   Still generating... {(attempt+1)*5}s elapsed")

        print("5) Clicking Play...")
        # Try all known Play button selectors
        play_btn = None
        for sel in ["[aria-label='Play']", "[aria-label='play']", "button:has-text('Play')", "[aria-label*='lay']"]:
            loc = page.locator(sel).first
            if await loc.count():
                play_btn = loc
                print(f"   Found Play with selector: {sel}")
                break
        if play_btn is None:
            # Fallback: snapshot and look manually
            snap_path = OUT_PATH.replace("nlm_video.png", "debug_no_play.png")
            await page.screenshot(path=snap_path)
            print(f"   Play button not found — debug screenshot at {snap_path}")
            await browser.close()
            return
        await play_btn.click()
        print("   Clicked Play")

        print("6) Waiting 20 seconds...")
        await page.wait_for_timeout(20000)

        print("7) Screenshotting video element...")
        video_el = page.locator("video").first
        await video_el.wait_for(timeout=10000)
        box = await video_el.bounding_box()
        if box:
            print(f"   Video bounding box: {box}")
            Path(OUT_PATH).parent.mkdir(parents=True, exist_ok=True)
            await page.screenshot(
                path=OUT_PATH,
                clip={
                    "x": box["x"],
                    "y": box["y"],
                    "width": box["width"],
                    "height": box["height"],
                },
            )
            print(f"8) Saved → {OUT_PATH}")
        else:
            print("   No bounding box found — taking full page screenshot")
            await page.screenshot(path=OUT_PATH)
            print(f"8) Saved (full page) → {OUT_PATH}")

        await browser.close()
        print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
