#!/usr/bin/env python3
"""
Create Notion Pages from Research Output.

Creates:
  1. Lead magnet article page  — standalone Notion page (guide/checklist/playbook)
  2. X text post entry         — in Content Calendar DB
  3. LinkedIn text post entry  — in Content Calendar DB (with Italian first comment in Notes)

One-time setup:
  1. Go to https://www.notion.so/my-integrations → create "Pietro Social Media" integration
  2. Copy token → set NOTION_TOKEN in .env
  3. Open the Content Calendar DB → Share → invite the integration
  4. Open any parent page where lead magnet articles should live → Share → invite the integration
     (or set NOTION_ARTICLES_PARENT_ID to a page ID in .env)

Usage:
  python3 create_notion_pages.py research/topics/slug.json
  python3 create_notion_pages.py research/topics/slug.json --dry-run   # print only, no API calls

Requires: NOTION_TOKEN, ANTHROPIC_API_KEY
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import anthropic
import requests

# ── Config ────────────────────────────────────────────────────────────────────

NOTION_API     = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
CONTENT_CAL_DB = "2ce71a32-538b-4ce0-b830-29d88ab5bc1c"

# Optional: page ID to nest lead magnet articles under.
# If not set, articles are created at workspace root.
ARTICLES_PARENT = os.environ.get("NOTION_ARTICLES_PARENT_ID", "")


# ── Notion API helpers ────────────────────────────────────────────────────────

def _headers(token: str) -> dict:
    return {
        "Authorization":  f"Bearer {token}",
        "Content-Type":   "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def create_page(token: str, payload: dict) -> dict:
    r = requests.post(f"{NOTION_API}/pages", json=payload, headers=_headers(token), timeout=30)
    if not r.ok:
        print(f"  Notion API error: {r.status_code} {r.text[:300]}")
        r.raise_for_status()
    return r.json()


def append_blocks(token: str, page_id: str, blocks: list) -> None:
    """Append blocks in batches of 100 (Notion API hard limit)."""
    for i in range(0, len(blocks), 100):
        batch = blocks[i:i + 100]
        r = requests.patch(
            f"{NOTION_API}/blocks/{page_id}/children",
            json={"children": batch},
            headers=_headers(token),
            timeout=30,
        )
        if not r.ok:
            print(f"  Block append error: {r.status_code} {r.text[:300]}")
            r.raise_for_status()


# ── Markdown → Notion blocks ──────────────────────────────────────────────────

def _inline(text: str) -> list[dict]:
    """Parse inline markdown (**bold**, `code`, [text](url)) → Notion rich_text list."""
    if not text:
        return [{"type": "text", "text": {"content": ""}}]
    parts = []
    pat = re.compile(r"\*\*(.+?)\*\*|`(.+?)`|\[(.+?)\]\((.+?)\)|([^*`\[]+)", re.DOTALL)
    for m in pat.finditer(text):
        if m.group(1):
            parts.append({"type": "text", "text": {"content": m.group(1)},
                          "annotations": {"bold": True}})
        elif m.group(2):
            parts.append({"type": "text", "text": {"content": m.group(2)},
                          "annotations": {"code": True}})
        elif m.group(3):
            parts.append({"type": "text", "text": {"content": m.group(3),
                          "link": {"url": m.group(4)}}})
        elif m.group(5):
            chunk = m.group(5)
            # split at 2000-char Notion limit
            while chunk:
                parts.append({"type": "text", "text": {"content": chunk[:2000]}})
                chunk = chunk[2000:]
    return parts or [{"type": "text", "text": {"content": text[:2000]}}]


def _para(text: str)   -> dict: return {"object": "block", "type": "paragraph",    "paragraph":    {"rich_text": _inline(text)}}
def _h2(text: str)     -> dict: return {"object": "block", "type": "heading_2",    "heading_2":    {"rich_text": _inline(text), "is_toggleable": False}}
def _h3(text: str)     -> dict: return {"object": "block", "type": "heading_3",    "heading_3":    {"rich_text": _inline(text), "is_toggleable": False}}
def _bullet(text: str) -> dict: return {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": _inline(text)}}
def _numbered(text: str) -> dict: return {"object": "block", "type": "numbered_list_item", "numbered_list_item": {"rich_text": _inline(text)}}
def _divider()         -> dict: return {"object": "block", "type": "divider",       "divider":      {}}
def _code(text: str, lang: str = "plain text") -> dict:
    return {"object": "block", "type": "code", "code": {
        "rich_text": [{"type": "text", "text": {"content": text[:2000]}}],
        "language": lang,
    }}
def _image(url: str) -> dict:
    return {"object": "block", "type": "image", "image": {"type": "external", "external": {"url": url}}}


def md_to_blocks(text: str) -> list[dict]:
    """Convert markdown to Notion block list."""
    blocks = []
    lines  = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        if not line.strip():
            i += 1
            continue

        # Code block
        if line.strip().startswith("```"):
            lang = line.strip()[3:].strip() or "plain text"
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            blocks.append(_code("\n".join(code_lines), lang))

        # H2
        elif line.startswith("## "):
            blocks.append(_h2(line[3:].strip()))

        # H3
        elif line.startswith("### "):
            blocks.append(_h3(line[4:].strip()))

        # Bullet
        elif line.startswith("- ") or line.startswith("* "):
            blocks.append(_bullet(line[2:]))

        # Numbered list  (1. / 2. etc.)
        elif re.match(r"^\d+\.\s", line):
            dot = line.index(". ")
            blocks.append(_numbered(line[dot + 2:]))

        # Divider
        elif line.strip().startswith("---"):
            blocks.append(_divider())

        # Image  ![alt](url)
        elif line.strip().startswith("!["):
            m = re.match(r"!\[.*?\]\((.+?)\)", line.strip())
            if m:
                blocks.append(_image(m.group(1)))

        # Italic-only line  *text*  → paragraph italic (used for footer)
        elif re.match(r"^\*[^*].+[^*]\*$", line.strip()):
            inner = line.strip()[1:-1]
            blocks.append({"object": "block", "type": "paragraph",
                           "paragraph": {"rich_text": [{"type": "text",
                               "text": {"content": inner},
                               "annotations": {"italic": True}}]}})

        # Regular paragraph — collect continuation lines
        else:
            para_lines = [line.strip()]
            i += 1
            while (i < len(lines)
                   and lines[i].strip()
                   and not lines[i].startswith("#")
                   and not lines[i].startswith("-")
                   and not lines[i].startswith("*")
                   and not lines[i].strip().startswith("```")
                   and not re.match(r"^\d+\.\s", lines[i])):
                para_lines.append(lines[i].strip())
                i += 1
            para_text = " ".join(para_lines)
            while para_text:
                blocks.append(_para(para_text[:2000]))
                para_text = para_text[2000:]
            continue

        i += 1
    return blocks


# ── Scheduling ────────────────────────────────────────────────────────────────

def next_posting_dt(platform: str, start_days_ahead: int = 1) -> str:
    """Return ISO-8601 UTC datetime for the next Tue/Wed/Thu posting slot."""
    # CET = UTC+1 before March 29, CEST = UTC+2 from March 29
    now = datetime.now(timezone.utc)
    is_cest = now.month > 3 or (now.month == 3 and now.day >= 29)
    tz_offset = 2 if is_cest else 1

    local_hours = {"linkedin": 8, "x": 9}
    utc_hour = local_hours.get(platform, 8) - tz_offset

    candidate = now + timedelta(days=start_days_ahead)
    while candidate.weekday() not in (1, 2, 3):   # 1=Tue 2=Wed 3=Thu
        candidate += timedelta(days=1)

    dt = candidate.replace(hour=utc_hour, minute=0, second=0, microsecond=0)
    return dt.isoformat().replace("+00:00", ".000Z")


# ── Content generation ────────────────────────────────────────────────────────

CONTENT_SYSTEM = """\
You are Pietro Piga's content writer. Pietro is an AI Sales Advisor targeting
CEOs, PE operators, management consultants, and real estate professionals.

Voice: Educational, direct, no hype. Data-driven. Business outcomes. First-person.
Active verbs: reads, checks, pulls, generates, sends, replaces, automates.
NEVER: "leveraging", "game-changer", "revolutionary", "unlock".

Hook formula (YouTube-proven): [Known Tool/Pain] + [Business Action] + [$ or Time] + [Urgency/Exclusivity]\
"""


def generate_content(topic: str, slug: str, insights: str, infographic_url: str | None) -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    infographic_line = (
        f"## 📊 Key Stats at a Glance\n\n![{topic} Infographic]({infographic_url})\n\n"
        if infographic_url else ""
    )

    prompt = f"""\
Topic: "{topic}"

RESEARCH INSIGHTS:
{insights[:6000]}

TASK: Create all content for this topic. Return a single JSON object.

1. LEAD MAGNET ARTICLE (detailed guide, 1800-2200 words, markdown)
   - Title: "The [Topic] [Resource]" — where [Resource] is Checklist/Guide/Framework/Playbook
   - Structure:
       Opening paragraph (2-3 sentences, lead with the biggest insight)
       ## What [Topic] Actually Is  (definition + why it matters right now)
       ## The [N] Types / Levels / Steps  (taxonomy or framework)
       ## Part 1 — [Core mechanic or process]
       ## Part 2 — [Optimization or advanced use]
       ## The Expert's Mistake  (counter-intuitive insight from research)
       ## Industry Playbooks
       ### 🏦 Private Equity / Family Offices
       ### 🔍 Boutique Management Consulting
       ### 🏗️ Real Estate (Commercial / Development)
       ### 💼 Wealth Management / Financial Advisory
       ---
       {infographic_line}*From Pietro Piga AI Sales Advisor*
   - Rules: NO Sources section. NO NotebookLM attribution. Tables and code blocks allowed.

2. X POST (contrarian angle, < 260 chars total caption)
   - Hook: follow the formula [Tool/Pain] + [Business Action] + [$ or Time] + [Urgency]
   - Caption: hook + 3 specific data points (arrows →), 1 CTA line. Use <br> for line breaks.

3. LINKEDIN POST (same contrarian angle, 600-900 chars)
   - Caption: expanded version of X, bullets with →, ends with CTA. Use <br> for line breaks.
   - Italian comment (for Notes): Italian translation of the 3 key points + CTA.

4. METADATA
   - tags: 2-3 from ["AI", "Automation", "Strategy", "Leadership", "Tools"]
   - cta_keyword: one word (CHECKLIST/PLAYBOOK/FRAMEWORK/GUIDE/SYSTEM)

Return ONLY this JSON (no markdown fences):
{{
  "article_title": "...",
  "article_body": "...",
  "hook": "...",
  "x_caption": "...",
  "x_cta": "...",
  "linkedin_caption": "...",
  "linkedin_cta": "...",
  "linkedin_italian_comment": "...",
  "tags": ["AI", "Tools"],
  "cta_keyword": "CHECKLIST"
}}"""

    msg = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=6000,
        system=CONTENT_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = msg.content[0].text.strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:]).rstrip("`").strip()
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)


# ── Page creation ─────────────────────────────────────────────────────────────

def create_article_page(token: str, title: str, blocks: list, dry_run: bool) -> str:
    """Create the standalone lead magnet article page. Returns page URL."""
    parent = (
        {"type": "page_id", "page_id": ARTICLES_PARENT}
        if ARTICLES_PARENT
        else {"type": "workspace", "workspace": True}
    )
    payload = {
        "parent": parent,
        "properties": {
            "title": {"title": [{"text": {"content": title}}]}
        },
        "children": blocks[:100],   # first batch; rest appended below
    }
    if dry_run:
        print(f"  [dry-run] Would create article: '{title}'  ({len(blocks)} blocks)")
        return "https://notion.so/dry-run-article"

    page = create_page(token, payload)
    page_id  = page["id"]
    page_url = page["url"]

    # Append remaining blocks in batches
    if len(blocks) > 100:
        append_blocks(token, page_id, blocks[100:])

    return page_url


def create_calendar_entry(
    token: str,
    title: str,
    platform: str,          # "X" | "LinkedIn"
    hook: str,
    caption: str,
    cta: str,
    tags: list[str],
    source_url: str,
    notes: str,
    publish_dt: str,
    dry_run: bool,
) -> str:
    """Create one Content Calendar entry. Returns page URL."""
    post_type = "Text"
    payload = {
        "parent":     {"database_id": CONTENT_CAL_DB},
        "properties": {
            "Title":        {"title":      [{"text": {"content": title}}]},
            "Platform":     {"select":     {"name": platform}},
            "Post Type":    {"select":     {"name": post_type}},
            "Status":       {"select":     {"name": "Ready"}},
            "Publish Date": {"date":       {"start": publish_dt, "time_zone": None}},
            "Hook":         {"rich_text":  [{"text": {"content": hook[:2000]}}]},
            "Caption":      {"rich_text":  [{"text": {"content": caption[:2000]}}]},
            "CTA":          {"rich_text":  [{"text": {"content": cta[:2000]}}]},
            "Tags":         {"multi_select": [{"name": t} for t in tags]},
            "Source URL":   {"url":        source_url},
            "Notes":        {"rich_text":  [{"text": {"content": notes[:2000]}}]},
        },
    }
    if dry_run:
        print(f"  [dry-run] Would create {platform} entry: '{title}'  → {publish_dt}")
        return f"https://notion.so/dry-run-{platform.lower()}"

    page = create_page(token, payload)
    return page["url"]


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Create Notion pages from research output")
    ap.add_argument("research_json", help="Path to research JSON (e.g., research/topics/slug.json)")
    ap.add_argument("--dry-run", action="store_true", help="Print what would be created without calling Notion API")
    args = ap.parse_args()

    token = os.environ.get("NOTION_TOKEN", "")
    if not token and not args.dry_run:
        print("❌ NOTION_TOKEN not set. See setup instructions in the script docstring.")
        print("   Run with --dry-run to test without Notion credentials.")
        sys.exit(1)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY not set.")
        sys.exit(1)

    src = Path(args.research_json)
    if not src.exists():
        print(f"❌ File not found: {src}")
        sys.exit(1)

    with open(src) as f:
        research = json.load(f)

    topic          = research["topic"]
    slug           = research["slug"]
    insights       = research.get("insights", "")
    infographic_url = research.get("infographic_url")

    print(f"\n=== Notion Page Creator ===")
    print(f"Topic  : {topic}")
    print(f"Slug   : {slug}")
    if args.dry_run:
        print("  ⚠ DRY RUN — no pages will be created\n")

    # ── Generate content ──────────────────────────────────────────────────────
    print("→ Generating content with Claude Opus…")
    content = generate_content(topic, slug, insights, infographic_url)

    article_title = content["article_title"]
    article_body  = content["article_body"]
    hook          = content["hook"]
    x_caption     = content["x_caption"]
    x_cta         = content["x_cta"]
    li_caption    = content["linkedin_caption"]
    li_cta        = content["linkedin_cta"]
    li_notes      = content["linkedin_italian_comment"]
    tags          = content.get("tags", ["AI", "Tools"])
    cta_kw        = content.get("cta_keyword", "CHECKLIST")

    print(f"  Article : '{article_title}'")
    print(f"  Hook    : {hook[:80]}…")
    print(f"  CTA KW  : {cta_kw}")

    # ── Article page ──────────────────────────────────────────────────────────
    print("→ Converting markdown to Notion blocks…")
    blocks = md_to_blocks(article_body)
    print(f"  {len(blocks)} blocks")

    print("→ Creating lead magnet article page…")
    article_url = create_article_page(token, article_title, blocks, args.dry_run)
    print(f"  ✅ Article: {article_url}")

    # ── Scheduling ────────────────────────────────────────────────────────────
    x_date  = next_posting_dt("x",        start_days_ahead=2)
    li_date = next_posting_dt("linkedin", start_days_ahead=2)

    # ── X entry ───────────────────────────────────────────────────────────────
    print("→ Creating X Content Calendar entry…")
    x_title = f"{topic} — Contrarian (X)"
    x_url = create_calendar_entry(
        token=token,
        title=x_title,
        platform="X",
        hook=hook,
        caption=x_caption,
        cta=x_cta,
        tags=tags,
        source_url=article_url,
        notes="",
        publish_dt=x_date,
        dry_run=args.dry_run,
    )
    print(f"  ✅ X post: {x_url}  → {x_date}")

    # ── LinkedIn entry ────────────────────────────────────────────────────────
    print("→ Creating LinkedIn Content Calendar entry…")
    li_title = f"{topic} — Contrarian (LinkedIn)"
    li_url = create_calendar_entry(
        token=token,
        title=li_title,
        platform="LinkedIn",
        hook=hook,
        caption=li_caption,
        cta=li_cta,
        tags=tags,
        source_url=article_url,
        notes=li_notes,
        publish_dt=li_date,
        dry_run=args.dry_run,
    )
    print(f"  ✅ LinkedIn post: {li_url}  → {li_date}")

    # ── Save URLs back to research JSON ──────────────────────────────────────
    if not args.dry_run:
        research["notion_article_url"] = article_url
        research["notion_x_url"]       = x_url
        research["notion_linkedin_url"] = li_url
        src.write_text(json.dumps(research, indent=2, ensure_ascii=False))
        print(f"\n  URLs saved back to {src}")

    print(f"\n=== Done ===")
    print(f"  Article  : {article_url}")
    print(f"  X post   : {x_url}")
    print(f"  LinkedIn : {li_url}")


if __name__ == "__main__":
    main()
