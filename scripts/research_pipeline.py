#!/usr/bin/env python3
"""
Research Pipeline — Social Media Audience Builder
Usage: python3 research_pipeline.py "topic" [count]

Steps:
  1. Scrape top YouTube videos via yt-dlp
  2. Create NotebookLM notebook + add top video sources
  3. Query NotebookLM for insights, stats, angles
  4. Save structured research to research/topics/{slug}.md
"""

import asyncio
import json
import re
import sys
import os
from datetime import date
from pathlib import Path

import yt_dlp


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
                "upload_date": entry.get("upload_date", "N/A"),
            })
    # Sort by views descending, pick most relevant
    videos.sort(key=lambda v: v["views"], reverse=True)
    return videos


async def run_notebooklm(topic: str, videos: list[dict], top_n: int = 8) -> dict:
    from notebooklm import NotebookLMClient

    notebook_name = f"Research: {topic} [{date.today()}]"
    top_videos = videos[:top_n]

    async with await NotebookLMClient.from_storage(timeout=180.0) as client:
        print(f"  Creating notebook: {notebook_name}")
        nb = await client.notebooks.create(notebook_name)
        print(f"  Notebook ID: {nb.id}")

        for v in top_videos:
            print(f"  Adding source: {v['title'][:60]}...")
            try:
                await client.sources.add_url(nb.id, v["url"], wait=True)
            except Exception as e:
                print(f"    Warning: could not add {v['url']}: {e}")

        print("  Querying for insights...")
        raw = await client.chat.ask(
            nb.id,
            f"""Analyze all sources about "{topic}" and provide:
1. TOP 5 KEY STATS or numbers (with sources if available)
2. CORE INSIGHT: What is the single most important thing a business leader must understand about this topic?
3. CONTROVERSY or RISK: What is the most important concern, failure mode, or contrarian view?
4. INDUSTRY USE CASES: Specific, concrete applications for:
   - Private Equity / Family Offices
   - Management Consulting (boutique/mid-tier)
   - Real Estate (commercial/development)
   - Wealth Management / Financial Advisory
5. CONTENT ANGLES: 5 compelling post hooks for a LinkedIn audience of CEOs and decision-makers

Be specific. Use numbers. Avoid vague claims."""
        )

        # AskResult may expose .text, .answer, or str()
        if hasattr(raw, "text"):
            insights = raw.text
        elif hasattr(raw, "answer"):
            insights = raw.answer
        else:
            insights = str(raw)

        return {
            "notebook_id": nb.id,
            "notebook_name": notebook_name,
            "insights": insights,
        }


def format_duration(seconds) -> str:
    if not seconds or seconds == "N/A":
        return "N/A"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def save_research(topic: str, videos: list[dict], notebooklm_result: dict, output_dir: Path):
    slug = slugify(topic)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{slug}.md"

    lines = [
        f"# Research: {topic}",
        f"**Date:** {date.today()}  ",
        f"**NotebookLM ID:** {notebooklm_result['notebook_id']}  ",
        "",
        "---",
        "",
        "## NotebookLM Insights",
        "",
        notebooklm_result["insights"],
        "",
        "---",
        "",
        "## YouTube Sources",
        "",
        f"Scraped {len(videos)} videos, top {min(8, len(videos))} added to NotebookLM.",
        "",
        "| # | Title | Channel | Views | Duration | URL |",
        "|---|---|---|---|---|---|",
    ]

    for i, v in enumerate(videos, 1):
        views = f"{v['views']:,}" if v["views"] else "N/A"
        dur = format_duration(v["duration_seconds"])
        title = v["title"].replace("|", "\\|")[:60]
        lines.append(f"| {i} | {title} | {v['channel']} | {views} | {dur} | {v['url']} |")

    lines += ["", "---", "", f"*Generated by research_pipeline.py on {date.today()}*"]

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n  Saved to: {output_path}")
    return output_path


async def main():
    if len(sys.argv) < 2:
        print("Usage: python3 research_pipeline.py \"topic\" [count]")
        sys.exit(1)

    topic = sys.argv[1]
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 15

    project_root = Path(__file__).parent.parent
    output_dir = project_root / "research" / "topics"

    print(f"\n=== Research Pipeline ===")
    print(f"Topic: {topic}")
    print(f"YouTube count: {count}")
    print()

    print("[ Step 1 ] Scraping YouTube...")
    videos = scrape_youtube(topic, count)
    print(f"  Found {len(videos)} videos.")

    print("\n[ Step 2 ] NotebookLM analysis...")
    notebooklm_result = await run_notebooklm(topic, videos)

    print("\n[ Step 3 ] Saving research...")
    output_path = save_research(topic, videos, notebooklm_result, output_dir)

    print("\n=== Done ===")
    print(f"Research file: {output_path}")
    print(f"NotebookLM notebook ID: {notebooklm_result['notebook_id']}")


if __name__ == "__main__":
    asyncio.run(main())
