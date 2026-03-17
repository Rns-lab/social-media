#!/usr/bin/env python3
"""
Topic Proposer — surfaces the top trending AI topics for Pietro to choose.

Sources:
  1. YouTube: top 10 videos across "claude code", "AI automation business", "claude code 2026"
  2. Reddit: hot posts from r/artificial, r/singularity, r/ChatGPT, r/OpenAI, r/LocalLLaMA
  → Ranked and synthesized by Claude into concrete topic proposals with hook angles.

Usage:
  python3 propose_topics.py              # display top 5 topics
  python3 propose_topics.py --count 8   # more topics
  python3 propose_topics.py --json       # raw JSON output
  python3 propose_topics.py --save topics.json

Requires: ANTHROPIC_API_KEY (for ranking/synthesis)
"""

import argparse
import json
import os
import ssl
import sys
import urllib.request
from datetime import datetime, timezone

import yt_dlp
import anthropic

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode  = ssl.CERT_NONE

REDDIT_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; TopicProposer/1.0)"}
REDDIT_SUBS    = ["artificial", "singularity", "ChatGPT", "OpenAI", "LocalLLaMA"]
YT_QUERIES     = ["claude code 2026", "AI automation business", "claude code skills"]


# ── Data gathering ────────────────────────────────────────────────────────────

def scrape_youtube(count: int = 10) -> list[dict]:
    """Return top YouTube videos across all queries, deduplicated and sorted by views."""
    seen, videos = set(), []
    for query in YT_QUERIES:
        opts = {"quiet": True, "no_warnings": True, "extract_flat": True, "playlist_items": f"1:{count}"}
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                result = ydl.extract_info(f"ytsearch{count}:{query}", download=False)
            for e in result.get("entries", []):
                vid_id = e.get("id", "")
                if not vid_id or vid_id in seen:
                    continue
                seen.add(vid_id)
                videos.append({
                    "title":   e.get("title", ""),
                    "url":     f"https://www.youtube.com/watch?v={vid_id}",
                    "views":   e.get("view_count") or 0,
                    "channel": e.get("uploader") or e.get("channel", ""),
                })
        except Exception as exc:
            print(f"  ⚠ YouTube query '{query}' failed: {exc}")
    videos.sort(key=lambda v: v["views"], reverse=True)
    return videos[:count]


def scrape_reddit(limit: int = 12) -> list[dict]:
    """Return hot Reddit posts from AI subs, sorted by score."""
    posts = []
    for sub in REDDIT_SUBS:
        url = f"https://www.reddit.com/r/{sub}/hot.json?limit=10"
        req = urllib.request.Request(url, headers=REDDIT_HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=8, context=_SSL_CTX) as resp:
                data = json.loads(resp.read())
            for p in data.get("data", {}).get("children", []):
                d = p["data"]
                posts.append({
                    "title":     d.get("title", ""),
                    "score":     d.get("score", 0),
                    "subreddit": sub,
                })
        except Exception:
            continue
    posts.sort(key=lambda p: p["score"], reverse=True)
    return posts[:limit]


# ── Ranking ───────────────────────────────────────────────────────────────────

def rank_with_claude(yt: list[dict], reddit: list[dict], count: int) -> list[dict]:
    """Synthesize YouTube + Reddit signals into concrete topic proposals."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        # Fallback: return raw YouTube titles as proposals
        return [
            {"rank": i+1, "topic": v["title"][:60], "hook_angle": v["title"],
             "angle": "Explainer", "score": min(99, v["views"] // 3000), "evidence": f"{v['views']:,} views"}
            for i, v in enumerate(yt[:count])
        ]

    client = anthropic.Anthropic(api_key=api_key)

    yt_lines     = "\n".join(f"- [{v['views']:,} views] {v['title']}" for v in yt)
    reddit_lines = "\n".join(f"- [{p['score']:,}↑ r/{p['subreddit']}] {p['title'][:80]}" for p in reddit[:10])

    prompt = f"""\
You help Pietro Piga (AI Sales Advisor) choose his next social media content topics.
Target: CEOs, PE operators, management consultants, real estate professionals.
Platform: X carousel — educational, direct, data-driven, no hype.

TRENDING YOUTUBE VIDEOS (sorted by views):
{yt_lines}

TRENDING REDDIT POSTS:
{reddit_lines}

TASK: Synthesize into {count} concrete topic proposals for Pietro's next carousels.

Rules:
- Focus on the BUSINESS problem/opportunity, not just the tech feature
- Hook uses this formula: [Known Tool/Pain] + [Business Action] + [$ or Time] + [Urgency]
- Score 0-100 based on trending evidence + fit for Pietro's CEO/PE/Consulting audience
- Angle options: Explainer / Contrarian / Use Case / Tutorial

Return a JSON array ONLY (no markdown, no explanation):
[
  {{
    "rank": 1,
    "topic": "5-8 word topic for research_pipeline.py",
    "hook_angle": "YouTube-style hook sentence following the formula",
    "angle": "Contrarian",
    "score": 92,
    "evidence": "147K views + Reddit r/singularity trending"
  }}
]"""

    msg = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text.strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:]).rstrip("`").strip()
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)


# ── Output ────────────────────────────────────────────────────────────────────

def display(proposals: list[dict]) -> None:
    print(f"\n{'='*62}")
    print(f"  TRENDING AI TOPICS — {datetime.now().strftime('%Y-%m-%d')}")
    print(f"{'='*62}")
    for p in proposals:
        print(f"\n{p['rank']}. [{p.get('score', '?')}/100] {p['topic']}")
        print(f"   Hook    : {p.get('hook_angle', '')}")
        print(f"   Angle   : {p.get('angle', '')}  |  Evidence: {p.get('evidence', '')}")
    print(f"\n{'─'*62}")
    print("→ Choose a topic, then run:")
    print('   python3 scripts/research_pipeline.py "chosen topic" --yt 10')
    print(f"{'─'*62}\n")


def main():
    ap = argparse.ArgumentParser(description="Propose trending AI topics for content creation")
    ap.add_argument("--count", type=int, default=5, help="Number of proposals (default: 5)")
    ap.add_argument("--json",  action="store_true",  help="Print raw JSON")
    ap.add_argument("--save",  help="Save proposals to JSON file")
    args = ap.parse_args()

    print("Fetching YouTube trending videos…")
    yt = scrape_youtube(count=10)
    print(f"  → {len(yt)} videos")

    print("Fetching Reddit trending posts…")
    reddit = scrape_reddit()
    print(f"  → {len(reddit)} posts")

    print(f"Ranking with Claude → top {args.count} topics…")
    proposals = rank_with_claude(yt, reddit, args.count)

    if args.json:
        print(json.dumps(proposals, indent=2))
    else:
        display(proposals)

    if args.save:
        out = {"generated_at": datetime.now(timezone.utc).isoformat(), "proposals": proposals}
        with open(args.save, "w") as f:
            json.dump(out, f, indent=2)
        print(f"✅ Saved → {args.save}")


if __name__ == "__main__":
    main()
