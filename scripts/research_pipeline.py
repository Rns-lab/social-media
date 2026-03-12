#!/usr/bin/env python3
"""
Research Pipeline — Social Media Audience Builder

Usage:
  python3 research_pipeline.py "topic" [--yt N] [--urls url1 url2 ...]

Flags (combinable):
  --yt N        Scrape top N YouTube videos (default 15 if no flags given)
  --urls u...   Explicit URLs to add as sources (web articles, pages, videos)

Output:
  research/topics/{slug}.json   Structured data for downstream Notion creation
  research/topics/{slug}.md     Human-readable reference
  assets/infographics/{slug}.png  Pushed to GitHub for public embedding
"""

import argparse
import asyncio
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import yt_dlp

GITHUB_REPO = "Rns-lab/social-media"
GITHUB_BRANCH = "main"


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text


def scrape_youtube(topic: str, count: int = 15) -> list[dict]:
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "playlist_items": f"1:{count}",
    }
    search_url = f"ytsearch{count}:{topic}"
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(search_url, download=False)
        videos = []
        for entry in result.get("entries", []):
            vid_id = entry.get("id", "")
            if not vid_id:
                continue
            videos.append({
                "title": entry.get("title", "N/A"),
                "url": f"https://www.youtube.com/watch?v={vid_id}",
                "channel": entry.get("uploader") or entry.get("channel", "N/A"),
                "views": entry.get("view_count") or 0,
                "duration_seconds": entry.get("duration") or 0,
            })
    videos.sort(key=lambda v: v["views"], reverse=True)
    return videos


async def run_notebooklm(topic: str, source_urls: list[str]) -> dict:
    from notebooklm import NotebookLMClient

    notebook_name = f"Research: {topic} [{date.today()}]"

    async with await NotebookLMClient.from_storage(timeout=180.0) as client:
        print(f"  Creating notebook: {notebook_name}")
        nb = await client.notebooks.create(notebook_name)
        print(f"  Notebook ID: {nb.id}")

        for url in source_urls:
            label = url[:70] + "..." if len(url) > 70 else url
            print(f"  Adding source: {label}")
            try:
                await client.sources.add_url(nb.id, url, wait=True)
            except Exception as e:
                print(f"    Warning: could not add source: {e}")

        print("  Querying for deep insights (pass 1 — facts & mechanics)...")
        raw1 = await client.chat.ask(
            nb.id,
            f"""You are a world-class analyst extracting intelligence from expert sources on "{topic}".

Your job: find what most people DON'T know. Surface the specific, counter-intuitive, and non-obvious.

EXTRACT THE FOLLOWING — be ruthlessly specific, cite exact numbers whenever available:

## 1. SURPRISING STATS
List 5–7 data points that would stop a CEO mid-scroll. Not generic stats — the ones that reframe how smart people think about this topic. Include the source name for each.

## 2. THE THING EXPERTS GET WRONG
What is the single most common misconception or mistake even experienced practitioners make? What do the sources reveal that contradicts conventional wisdom?

## 3. THE HIDDEN MECHANIC
What is the underlying mechanism or root cause that, once understood, makes everything else click? The insight that makes you say "oh, that's why."

## 4. WHAT ACTUALLY KILLS RESULTS
Not generic risks — the specific failure modes from the sources. What do people do that looks right but kills the outcome? Give exact examples if available.

## 5. THE COUNTER-INTUITIVE MOVE
What is one action that seems wrong but produces dramatically better results? If the sources show a technique that goes against gut instinct, surface it here.

## 6. EXACT STEP-BY-STEP (most valuable section)
Extract the most actionable process from the sources. Not "implement X" — the actual sequence of steps a practitioner would follow. Number them. Be specific enough that someone could execute immediately.

## 7. INDUSTRY-SPECIFIC ANGLES (with real numbers or outcomes where available)
For each industry below, what is the specific, concrete application — not generic advice:
- Private Equity / Family Offices
- Boutique Management Consulting
- Real Estate (commercial/development)
- Wealth Management / Financial Advisory

## 8. THE LEAD MAGNET HOOK
What is the single most valuable piece of insight from these sources — the thing someone would pay for, that we can give away for free to build authority? One sentence."""
        )

        if hasattr(raw1, "text"):
            insights_pass1 = raw1.text
        elif hasattr(raw1, "answer"):
            insights_pass1 = raw1.answer
        else:
            insights_pass1 = str(raw1)

        print("  Querying for content angles (pass 2 — Hormozi hooks)...")
        raw2 = await client.chat.ask(
            nb.id,
            f"""Based on everything in the sources about "{topic}", generate 5 LinkedIn post hooks following these exact rules:

HOOK RULES (Alex Hormozi style):
- Open with a specific number or counter-intuitive claim — never a question
- Make the reader feel like they're about to learn something they can't unlearn
- The hook must work without context — a stranger scrolling must stop
- No buzzwords: no "game-changer", "revolutionary", "unlock", "leverage"
- Max 2 lines. The more specific, the better.

For each hook also provide:
- The ONE core insight that post would be built around (from the sources, not invented)
- The industry angle it targets (PE / Consulting / RE / Wealth Mgmt / General)
- The lead magnet it would link to (what resource would make someone DM you)

Format each as:
HOOK: [the hook]
CORE INSIGHT: [the insight]
TARGET: [industry]
LEAD MAGNET: [resource type]"""
        )

        if hasattr(raw2, "text"):
            insights_pass2 = raw2.text
        elif hasattr(raw2, "answer"):
            insights_pass2 = raw2.answer
        else:
            insights_pass2 = str(raw2)

        insights = f"{insights_pass1}\n\n---\n\n## CONTENT HOOKS (Hormozi Style)\n\n{insights_pass2}"

        return {
            "notebook_id": nb.id,
            "notebook_name": notebook_name,
            "insights": insights,
        }


async def generate_infographic_step(notebook_id: str, slug: str, project_root: Path) -> str | None:
    """
    Generate a NotebookLM infographic, push to GitHub, return public raw URL.
    Returns None if generation fails.
    """
    from notebooklm import NotebookLMClient
    from notebooklm.rpc.types import InfographicOrientation, InfographicDetail

    assets_dir = project_root / "assets" / "infographics"
    assets_dir.mkdir(parents=True, exist_ok=True)
    local_path = assets_dir / f"{slug}.png"

    async with await NotebookLMClient.from_storage(timeout=180.0) as client:
        # Prime visual style before generating (required for quality output)
        print("  Priming visual style...")
        await client.chat.ask(
            notebook_id,
            "Summarize the key statistics and business insights in a visual-friendly format. "
            "Focus on numbers, percentages, and concrete outcomes. "
            "Structure as: headline stat, 3-5 supporting data points, one key takeaway. "
            "Professional, clean, no decorative elements."
        )

        print("  Generating infographic...")
        await client.artifacts.generate_infographic(
            notebook_id,
            orientation=InfographicOrientation.PORTRAIT,
            detail_level=InfographicDetail.DETAILED,
        )

        # Poll until completed (max 5 min = 30 x 10s)
        print("  Waiting for infographic", end="", flush=True)
        art = None
        for _ in range(30):
            await asyncio.sleep(10)
            arts = await client.artifacts.list_infographics(notebook_id)
            if arts:
                art = arts[-1]
                if art.is_completed:
                    print(" done.")
                    break
                if art.status == 4:  # failed
                    print(" FAILED.")
                    return None
            print(".", end="", flush=True)

        if not art or not art.is_completed:
            print(" Timed out.")
            return None

        print(f"  Downloading to {local_path}...")
        await client.artifacts.download_infographic(
            notebook_id, str(local_path), artifact_id=art.id
        )

    # Push to GitHub
    print("  Pushing infographic to GitHub...")
    rel_path = f"assets/infographics/{slug}.png"
    try:
        subprocess.run(["git", "add", rel_path], cwd=str(project_root), check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", f"feat: add infographic for {slug}"],
            cwd=str(project_root), check=True, capture_output=True
        )
        subprocess.run(["git", "push"], cwd=str(project_root), check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode().strip() if e.stderr else str(e)
        print(f"  Warning: git push failed — {stderr}")
        print(f"  Infographic saved locally at: {local_path}")
        return None

    raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/{rel_path}"
    print(f"  Infographic URL: {raw_url}")
    return raw_url


def format_duration(seconds) -> str:
    if not seconds or seconds == "N/A":
        return "N/A"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def save_outputs(
    topic: str,
    source_urls: list[str],
    yt_videos: list[dict],
    notebooklm_result: dict,
    output_dir: Path,
    infographic_url: str | None = None,
):
    slug = slugify(topic)
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- JSON output (for downstream Notion creation) ---
    json_data = {
        "topic": topic,
        "slug": slug,
        "date": str(date.today()),
        "notebook_id": notebooklm_result["notebook_id"],
        "notebook_name": notebooklm_result["notebook_name"],
        "infographic_url": infographic_url,
        "insights": notebooklm_result["insights"],
        "source_urls": source_urls,
    }
    json_path = output_dir / f"{slug}.json"
    json_path.write_text(json.dumps(json_data, indent=2, ensure_ascii=False), encoding="utf-8")

    # --- Markdown output (human-readable reference) ---
    lines = [
        f"# Research: {topic}",
        f"**Date:** {date.today()}  ",
        f"**NotebookLM ID:** {notebooklm_result['notebook_id']}  ",
    ]
    if infographic_url:
        lines.append(f"**Infographic:** {infographic_url}  ")

    lines += ["", "---", ""]

    if infographic_url:
        lines += [
            "## Infographic",
            "",
            f"![Research Infographic]({infographic_url})",
            "",
            "---",
            "",
        ]

    lines += [
        "## NotebookLM Insights",
        "",
        notebooklm_result["insights"],
        "",
        "---",
        "",
        "## Sources",
        "",
    ]

    if yt_videos:
        lines += [
            f"### YouTube ({len(yt_videos)} videos scraped)",
            "",
            "| # | Title | Channel | Views | Duration | URL |",
            "|---|---|---|---|---|---|",
        ]
        for i, v in enumerate(yt_videos, 1):
            views = f"{v['views']:,}" if v["views"] else "N/A"
            dur = format_duration(v["duration_seconds"])
            title = v["title"].replace("|", "\\|")[:60]
            lines.append(f"| {i} | {title} | {v['channel']} | {views} | {dur} | {v['url']} |")
        lines.append("")

    explicit_web = [u for u in source_urls if u not in {v["url"] for v in yt_videos}]
    if explicit_web:
        lines += ["### Web Sources", ""]
        for url in explicit_web:
            lines.append(f"- {url}")
        lines.append("")

    lines += ["---", "", f"*Generated by research_pipeline.py on {date.today()}*"]

    md_path = output_dir / f"{slug}.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")

    return json_path, md_path


async def main():
    parser = argparse.ArgumentParser(
        description="Research pipeline: YouTube + web → NotebookLM → infographic → JSON"
    )
    parser.add_argument("topic", help="Research topic")
    parser.add_argument("--yt", type=int, metavar="N", help="Scrape top N YouTube videos")
    parser.add_argument("--urls", nargs="+", metavar="URL", help="Explicit URLs to add as sources")
    args = parser.parse_args()

    # Default to --yt 15 if no source flags given
    yt_count = args.yt if args.yt is not None else (15 if not args.urls else 0)
    explicit_urls = args.urls or []

    project_root = Path(__file__).parent.parent
    output_dir = project_root / "research" / "topics"
    slug = slugify(args.topic)

    print(f"\n=== Research Pipeline ===")
    print(f"Topic:    {args.topic}")
    if yt_count:
        print(f"YouTube:  top {yt_count} videos")
    if explicit_urls:
        print(f"Web URLs: {len(explicit_urls)} provided")
    print()

    # --- Step 1: Gather sources ---
    yt_videos = []
    source_urls = list(explicit_urls)

    if yt_count > 0:
        print("[ Step 1 ] Scraping YouTube...")
        yt_videos = scrape_youtube(args.topic, yt_count)
        print(f"  Found {len(yt_videos)} videos.")
        # Add YouTube URLs to sources (top 8 for NotebookLM)
        source_urls = [v["url"] for v in yt_videos[:8]] + explicit_urls
    else:
        print("[ Step 1 ] Using provided URLs only.")

    if not source_urls:
        print("Error: no sources to process. Use --yt or --urls.")
        sys.exit(1)

    print(f"  Total sources for NotebookLM: {len(source_urls)}")

    # --- Step 2: NotebookLM analysis ---
    print("\n[ Step 2 ] NotebookLM analysis...")
    notebooklm_result = await run_notebooklm(args.topic, source_urls)

    # --- Step 3: Generate infographic ---
    print("\n[ Step 3 ] Generating infographic...")
    infographic_url = await generate_infographic_step(
        notebooklm_result["notebook_id"], slug, project_root
    )

    # --- Step 4: Save outputs ---
    print("\n[ Step 4 ] Saving outputs...")
    json_path, md_path = save_outputs(
        args.topic, source_urls, yt_videos, notebooklm_result, output_dir, infographic_url
    )

    print("\n=== Done ===")
    print(f"JSON output:     {json_path}")
    print(f"Markdown:        {md_path}")
    print(f"NotebookLM ID:   {notebooklm_result['notebook_id']}")
    if infographic_url:
        print(f"Infographic URL: {infographic_url}")
    print()
    print("Next step: give Claude the JSON path to create Notion lead magnet pages.")


if __name__ == "__main__":
    asyncio.run(main())
