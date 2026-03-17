#!/usr/bin/env python3
"""
Trending AI Topics Scraper
Pulls top posts from AI-focused Reddit communities (no API key needed).
Outputs a clean JSON list of trending topics for carousel/post ideas.

Usage:
  python3 trending_topics.py [--limit 20] [--output topics.json]
"""

import json
import argparse
import urllib.request
import urllib.error
import ssl
from datetime import datetime, timezone

# macOS Python often lacks system certs — use unverified context for public API scraping
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

SUBREDDITS = [
    "artificial",
    "singularity",
    "ChatGPT",
    "OpenAI",
    "LocalLLaMA",
    "MachineLearning",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; TrendingScraper/1.0)",
}

FILTER_KEYWORDS = [
    "ai", "llm", "gpt", "claude", "gemini", "openai", "anthropic",
    "model", "agent", "automation", "neural", "machine learning",
    "artificial intelligence", "deep learning", "generative", "chatbot",
    "benchmark", "inference", "training", "fine-tun",
]


def fetch_top_posts(subreddit: str, limit: int = 10) -> list:
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10, context=_SSL_CTX) as resp:
            data = json.loads(resp.read())
        posts = data.get("data", {}).get("children", [])
        return [p["data"] for p in posts]
    except Exception as e:
        print(f"  ⚠ Could not fetch r/{subreddit}: {e}")
        return []


def score_relevance(title: str) -> int:
    tl = title.lower()
    return sum(1 for kw in FILTER_KEYWORDS if kw in tl)


def get_trending(limit: int = 20) -> list:
    all_posts = []
    for sub in SUBREDDITS:
        posts = fetch_top_posts(sub, limit=15)
        for p in posts:
            all_posts.append({
                "title": p.get("title", ""),
                "subreddit": p.get("subreddit", sub),
                "score": p.get("score", 0),
                "comments": p.get("num_comments", 0),
                "url": f"https://reddit.com{p.get('permalink', '')}",
                "relevance": score_relevance(p.get("title", "")),
            })

    # Deduplicate by title similarity (simple)
    seen = set()
    unique = []
    for p in all_posts:
        key = p["title"][:60].lower()
        if key not in seen:
            seen.add(key)
            unique.append(p)

    # Sort: relevance first, then Reddit score
    unique.sort(key=lambda x: (x["relevance"], x["score"]), reverse=True)

    return unique[:limit]


def format_for_display(topics: list) -> str:
    lines = [f"\n{'='*60}", f"  TRENDING AI TOPICS — {datetime.now().strftime('%Y-%m-%d %H:%M')}", f"{'='*60}\n"]
    for i, t in enumerate(topics, 1):
        lines.append(f"{i:2}. [{t['subreddit']}] {t['title']}")
        lines.append(f"    ↑{t['score']:,} | 💬{t['comments']} | {t['url']}\n")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20, help="Number of topics to return")
    parser.add_argument("--output", help="Save JSON output to file")
    parser.add_argument("--json", action="store_true", help="Print JSON only")
    args = parser.parse_args()

    print(f"Fetching trending AI topics from {len(SUBREDDITS)} subreddits...")
    topics = get_trending(limit=args.limit)

    if args.json:
        print(json.dumps(topics, indent=2))
    else:
        print(format_for_display(topics))

    if args.output:
        with open(args.output, "w") as f:
            json.dump({
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "topics": topics,
            }, f, indent=2)
        print(f"\n✅ Saved to {args.output}")


if __name__ == "__main__":
    main()
