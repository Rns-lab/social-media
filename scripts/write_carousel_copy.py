#!/usr/bin/env python3
"""
Carousel Copy Writer
Generates a ready-to-use carousel JSON from research pipeline output.

Applies:
  - Tyler Germain 5-slide format (hook → 3 value → CTA)
  - YouTube title patterns from top-performing AI videos
  - Pietro's brand voice (CEOs, PE, Consulting, RE)

Usage:
  python3 write_carousel_copy.py research/topics/slug.json
  python3 write_carousel_copy.py research/topics/slug.json --output-dir scripts/

Output: scripts/{slug}_carousel.json  (ready for run_carousel.py)

Requires: ANTHROPIC_API_KEY
"""

import argparse
import json
import os
import sys
from pathlib import Path

import anthropic

ASSETS  = Path(__file__).parent.parent / "assets"
SCRIPTS = Path(__file__).parent

# Brand detection registry: keyword (lowercase) → (logo path relative to project root, display label)
# Add new brands here as logos become available in assets/resources/logos/
BRAND_REGISTRY = {
    "perplexity":   ("assets/resources/logos/perplexity.png",   "Perplexity"),
    "manus":        ("assets/resources/logos/manus.png",         "Manus"),
    "gemini":       ("assets/resources/logos/gemini.png",        "Gemini"),
    "claude":       ("assets/resources/Claude Logo Compact.png", "Claude"),
    "anthropic":    ("assets/resources/Claude Logo Compact.png", "Anthropic"),
    "openai":       ("assets/resources/logos/openai.png",        "OpenAI"),
    "chatgpt":      ("assets/resources/logos/openai.png",        "ChatGPT"),
    "gpt-4":        ("assets/resources/logos/openai.png",        "GPT-4"),
    "gpt-5":        ("assets/resources/logos/openai.png",        "GPT-5"),
    "deepseek":     ("assets/resources/logos/deepseek.png",      "DeepSeek"),
    "grok":         ("assets/resources/logos/grok.png",          "Grok"),
    "mistral":      ("assets/resources/logos/mistral.png",       "Mistral"),
    "llama":        ("assets/resources/logos/meta.png",          "Meta/Llama"),
    "cursor":       ("assets/resources/logos/cursor.png",        "Cursor"),
    "copilot":      ("assets/resources/logos/copilot.png",       "Copilot"),
    "notion":       ("assets/resources/logos/notion.png",        "Notion"),
    "zapier":       ("assets/resources/logos/zapier.png",        "Zapier"),
    "make.com":     ("assets/resources/logos/make.png",          "Make"),
    "n8n":          ("assets/resources/logos/n8n.png",           "n8n"),
    "github":       ("assets/resources/logos/github.png",        "GitHub"),
}

SYSTEM_PROMPT = """\
You are a social media content writer for Pietro Piga, an AI Sales Advisor.
Target: CEOs, PE operators, management consultants, real estate professionals on X (Twitter).

You write carousels in Tyler Germain's exact format. You use the language of top-performing
YouTube videos on Claude/AI — proven by 100K+ views.

WINNING HOOK FORMULAS (apply to slide 1):
- Economic value:     "Claude Code Replaced My Team ($5k/month saved)"
- Disruption:         "Claude Code Changed How I Run My Business Forever"
- Exclusivity:        "99% of CEOs Don't Know This Claude Automation Exists"
- Speed + outcome:    "I Automated My Weekly Report in 11 Minutes With Claude"
- Insider past-tense: "I Tried Claude Code for 30 Days. Here's What Happened."

Ideal formula: [Known Tool/Pain] + [Business Action] + [$ or Time Number] + [Urgency/Exclusivity]

SLIDE FORMAT (5 slides):

Slide 1 — Hook (no bold_line):
  Two short sentences. Total < 100 chars.
  Pattern: [Big claim matching formula above] + [Here are N [things] I [did/found/use]:]

Slides 2-4 — Value (bold_line + 2 paragraphs):
  bold_line:   "N. Short Title" — 3-5 words, no period
  paragraph 1: WHEN + WHAT + HOW. Specific. Data-driven. ~100 chars.
  paragraph 2: The payoff/result. Short, punchy. ~50 chars.
  Total chars (bold_line + both paragraphs) MUST be < 220.

Slide 5 — CTA (no bold_line):
  paragraph 1: Tease a video/deep-dive resource. ~80 chars.
  paragraph 2: Comment trigger. EXACT format: Comment "KEYWORD" and I'll send it over.

LANGUAGE RULES:
- Active first-person: "I", "my", "Claude reads my..."
- Digits not words: "3 ways", "8am", "$5k", "11 minutes"
- Business outcomes: time saved, cost cut, team replaced, revenue impact
- Strong action verbs: reads, checks, pulls, generates, sends, replaces, automates
- NEVER use: "leveraging", "game-changer", "revolutionary", "unlock", "harness"

OUTPUT: Return ONLY valid JSON matching the schema. No markdown fences, no explanation.\
"""


def detect_logos(data: dict, slug: str) -> str | None:
    """
    Scan carousel slide text for brand mentions, map to logo files (max 3).
    - Found brands with existing logo files → included in logos string
    - Found brands WITHOUT logo files → warning printed, asks Pietro to provide
    - Returns None if nothing found (falls back to Claude logo in thumbnail)
    """
    project_root = ASSETS.parent

    # Collect all text from slides (hook + value slides; skip CTA which is generic)
    text = " ".join(
        " ".join(slide.get("paragraphs", [])) + " " + slide.get("bold_line", "")
        for slide in data.get("slides", [])
    ).lower()

    seen_paths: set[str] = set()
    found: list[tuple[str, str]] = []   # (absolute_path, label)
    missing: list[str] = []

    for keyword, (rel_path, label) in BRAND_REGISTRY.items():
        if keyword not in text:
            continue
        if rel_path in seen_paths:          # same logo already added (e.g. openai + chatgpt)
            continue
        seen_paths.add(rel_path)
        abs_path = project_root / rel_path
        if abs_path.exists():
            found.append((rel_path, label))
        else:
            missing.append(f"{label} (keyword: '{keyword}')")

    if missing:
        print(f"\n⚠️  Brands detected in copy but no logo file found:")
        for m in missing:
            print(f"     • {m}")
        print(f"   → Please add the PNG to assets/resources/logos/ and re-run,")
        print(f"     OR manually set \"logos\" in scripts/{slug}_carousel.json")

    if not found:
        return None  # will fall back to Claude logo

    # Cap at 3 most prominent (preserve detection order, which follows registry priority)
    result = ",".join(f"{path}:{label}" for path, label in found[:3])
    print(f"\n✅ Auto-detected logos: {result}")
    return result


def find_diagram_paths(slug: str) -> list:
    """Return up to 3 diagram PNG absolute paths for the slug, or None placeholders."""
    diagrams_dir = ASSETS / "post" / slug / "diagrams"
    if not diagrams_dir.exists():
        return [None, None, None]
    pngs = sorted(diagrams_dir.glob("*.png"))
    result = [str(p) for p in pngs[:3]]
    while len(result) < 3:
        result.append(None)
    return result


def find_cta_image(slug: str) -> str | None:
    """Return NLM video screenshot path, falling back to infographic carousel crop."""
    for name in ("nlm_video.png", "nlm_infographic_carousel.png"):
        p = ASSETS / "post" / slug / name
        if p.exists():
            return str(p)
    return None


def generate_copy(topic: str, slug: str, insights: str) -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    schema = json.dumps({
        "slug": slug,
        "cta_keyword": "KEYWORD",
        "slides": [
            {"paragraphs": ["Hook line 1.", "Hook line 2 (here are N things):"]},
            {"bold_line": "1. Title", "paragraphs": ["Mechanic ~100 chars.", "Payoff ~50 chars."]},
            {"bold_line": "2. Title", "paragraphs": ["Mechanic ~100 chars.", "Payoff ~50 chars."]},
            {"bold_line": "3. Title", "paragraphs": ["Mechanic ~100 chars.", "Payoff ~50 chars."]},
            {"paragraphs": ["Tease resource ~80 chars.", "Comment \"KEYWORD\" and I'll send it over."]},
        ],
    }, indent=2)

    prompt = f"""Research topic: "{topic}"

INSIGHTS FROM NOTEBOOKLM (source material — use these, do not invent):
{insights[:5000]}

TASK:
Write a 5-slide carousel about this topic.

For the 3 value slides, pick the 3 most powerful insights:
  1. The insight with the strongest concrete data point (stat, number, named outcome)
  2. The counter-intuitive insight ("thing experts get wrong")
  3. The most immediately actionable step-by-step insight

Pick a CTA keyword relevant to the topic (e.g., CHECKLIST, PLAYBOOK, FRAMEWORK, GUIDE, SYSTEM).

Return JSON matching this schema exactly:
{schema}"""

    msg = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1200,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = msg.content[0].text.strip()
    # Strip markdown code fences if model wraps output
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:])
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rstrip("`").strip()

    return json.loads(raw)


def inject_images(data: dict, slug: str) -> dict:
    """Add image paths to slides where assets exist on disk."""
    diagrams = find_diagram_paths(slug)
    cta_img  = find_cta_image(slug)

    slides = data.get("slides", [])

    # Slides 2-4 (index 1-3) → diagrams
    for i, path in enumerate(diagrams):
        idx = i + 1
        if idx < len(slides) and path:
            slides[idx]["image"] = path

    # Slide 5 (index 4) → NLM video or infographic crop
    if len(slides) >= 5 and cta_img:
        slides[4]["image"] = cta_img

    return data


def print_review(data: dict) -> None:
    """Print char counts for each slide so Pietro can spot overflows."""
    print("\n─── Slide review ───────────────────────────────")
    for i, slide in enumerate(data.get("slides", []), 1):
        total = sum(len(p) for p in slide.get("paragraphs", [])) + len(slide.get("bold_line", ""))
        has_img = "image" in slide
        flag = "⚠️ LONG" if total > 220 and "bold_line" in slide else ""
        img_tag = " [image]" if has_img else ""
        print(f"  Slide {i}: {total} chars{img_tag} {flag}")
        if slide.get("bold_line"):
            print(f"    bold: {slide['bold_line']}")
        for p in slide.get("paragraphs", []):
            print(f"    ¶  {p[:80]}{'…' if len(p) > 80 else ''}")
    print("────────────────────────────────────────────────")


def main():
    ap = argparse.ArgumentParser(description="Generate carousel JSON from research output")
    ap.add_argument("research_json", help="Path to research JSON (e.g., research/topics/slug.json)")
    ap.add_argument("--output-dir", help="Where to save the carousel JSON (default: scripts/)")
    args = ap.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY not set. Add it to .env or export it.")
        sys.exit(1)

    src = Path(args.research_json)
    if not src.exists():
        print(f"❌ File not found: {src}")
        sys.exit(1)

    with open(src) as f:
        research = json.load(f)

    topic    = research["topic"]
    slug     = research["slug"]
    insights = research.get("insights", "")

    print(f"\n=== Carousel Copy Writer ===")
    print(f"Topic : {topic}")
    print(f"Slug  : {slug}")
    print("→ Calling Claude Opus to draft copy…")

    data = generate_copy(topic, slug, insights)
    data = inject_images(data, slug)
    # Auto-detect logos from slide text; fall back to research JSON if set manually
    data["logos"] = research.get("logos") or detect_logos(data, slug)
    print_review(data)

    out_dir  = Path(args.output_dir) if args.output_dir else SCRIPTS
    out_path = out_dir / f"{slug}_carousel.json"
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Saved: {out_path}")
    print(f"   Next:  python3 scripts/run_carousel.py {out_path}")


if __name__ == "__main__":
    main()
