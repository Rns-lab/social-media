#!/usr/bin/env python3
"""
master_pipeline.py — One command to produce all media for a topic.

Produces:
  • LinkedIn post + article → Notion pages
  • 5-slide carousel → assets/post/{slug}/carousel/slide_01-05.png

Pipeline:
  1. Load research JSON
  2. Auto-crop infographic → nlm_infographic_carousel.png
  3. Draft LinkedIn post from research (Llama)
  4. MiroFish Round 1  — 20 agents, 8 rounds (real audience simulation)
  5. Scoring loop max 3x:
       - Llama scores audience report 1-5 + identifies content gaps
       - If score < 4: improve post + humanize → re-run MiroFish
  6. Write full article + finalize LinkedIn post (Llama)
  7. Write carousel JSON (Pietro's 5-slide structure, Llama)
  8. Run carousel generator
  9. Create Notion pages (article + LinkedIn entry)
 10. Print full summary

Usage:
    cd "/Users/pietropiga/Desktop/Claude Code/Social Media"
    python3 scripts/master_pipeline.py <slug>
    python3 scripts/master_pipeline.py <slug> --auto            # no approval gate (fully automated)
    python3 scripts/master_pipeline.py <slug> --resume 8        # resume from step 8 (e.g. after Playwright crash)
    python3 scripts/master_pipeline.py <slug> --skip-mirofish   # skip audience sim (fast test)
    python3 scripts/master_pipeline.py <slug> --skip-carousel   # skip slide generation
    python3 scripts/master_pipeline.py <slug> --skip-notion     # skip Notion page creation

Resume steps:
  1=load_research  2=crop_infographic  3=draft_post  4=mirofish_round1
  6=write_article  7=write_carousel    8=run_carousel  9=create_notion

State is auto-saved to /tmp/{slug}_pipeline_state.json after each step.

Requirements:
  .env must have: OPENROUTER_API_KEY, NOTION_TOKEN
  MiroFish must be running at MIROFISH_URL (default http://localhost:5001)
    → cd MiroFish/backend && python run.py
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import openai
import requests
from dotenv import load_dotenv
from PIL import Image, ImageStat

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE    = Path(__file__).parent.parent
SCRIPTS = BASE / "scripts"
ASSETS  = BASE / "assets"
SHARED  = BASE.parent / "shared"     # /Users/pietropiga/Desktop/Claude Code/shared

load_dotenv(BASE / ".env")

OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
LLM_MODEL      = os.environ.get("LLM_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
NOTION_TOKEN   = os.environ.get("NOTION_TOKEN", "")
MIROFISH_URL   = os.environ.get("MIROFISH_URL", "http://localhost:5001")
CONTENT_CAL_DB = "923eeb74-6673-43ef-873e-1e3d51aec24a"

sys.path.insert(0, str(SHARED))


# ── LLM client (Llama via OpenRouter) ─────────────────────────────────────────

def llm(system: str, user: str, max_tokens: int = 2000) -> str:
    client = openai.OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_KEY)
    for attempt in range(8):
        try:
            msg = client.chat.completions.create(
                model=LLM_MODEL,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
            )
            return msg.choices[0].message.content.strip()
        except openai.RateLimitError:
            wait = 30 * (2 ** attempt)
            print(f"  ⏳ Rate limit — waiting {wait}s (attempt {attempt+1}/8)…")
            time.sleep(wait)
    raise RuntimeError("LLM rate limit exceeded after 8 retries")


def llm_json(system: str, user: str, max_tokens: int = 2000) -> dict | list:
    from json_repair import repair_json
    raw = llm(system, user, max_tokens)
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:]).rstrip("`").strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()
    return json.loads(repair_json(raw))


# ── Step 1: Load research ──────────────────────────────────────────────────────

def load_research(slug: str) -> dict:
    path = BASE / "research" / "topics" / f"{slug}.json"
    if not path.exists():
        print(f"❌ Research not found: {path}")
        print(f"   Run: python3 scripts/research_pipeline.py \"{slug}\"")
        sys.exit(1)
    with open(path) as f:
        data = json.load(f)
    print(f"  ✅ Research loaded: {data.get('topic', slug)}")
    return data


# ── Step 2: Auto-crop infographic ─────────────────────────────────────────────

def auto_crop_infographic(slug: str) -> str | None:
    src = ASSETS / "post" / slug / "nlm_infographic.png"
    out = ASSETS / "post" / slug / "nlm_infographic_carousel.png"

    if not src.exists():
        print(f"  ⚠ Infographic not found, skipping crop: {src}")
        return None

    img = Image.open(src)
    w, h = img.size
    print(f"  Infographic: {w}×{h}px — generating strips…")

    n = 4
    strip_h = h // n
    strips = []
    for i in range(n):
        y0 = i * strip_h
        y1 = y0 + strip_h if i < n - 1 else h
        crop = img.crop((0, y0, w, y1))
        tmp  = Path(f"/tmp/{slug}_strip_{i}.png")
        crop.save(tmp)
        stat     = ImageStat.Stat(crop.convert("L"))
        variance = stat.var[0]
        strips.append({"index": i, "y0": y0, "y1": y1, "variance": variance, "path": str(tmp)})
        print(f"    Strip {i}: y={y0}–{y1}  variance={variance:.0f}  → {tmp}")

    # Skip strip 0 (title/header — low density), pick highest variance among rest
    candidates = [s for s in strips if s["index"] > 0]
    best = max(candidates, key=lambda s: s["variance"])
    print(f"  → Best strip: {best['index']}  (variance={best['variance']:.0f})")

    # Crop with slight upward padding for context
    pad = max(0, best["y0"] - int((best["y1"] - best["y0"]) * 0.05))
    final = img.crop((0, pad, w, best["y1"]))
    final.save(out)
    print(f"  ✅ Saved: {out}  ({final.size[0]}×{final.size[1]}px)")
    print(f"  📋 Strip previews: /tmp/{slug}_strip_0.png … _strip_3.png")
    return str(out)


# ── Step 3: Draft LinkedIn post ───────────────────────────────────────────────

DRAFT_SYSTEM = """\
You are Pietro Piga's content writer. Pietro is an AI Sales Advisor targeting
CEOs, PE operators, management consultants, and real estate professionals on LinkedIn.

Voice: Educational, direct, no hype. Data-driven. Business outcomes. First-person.
Active verbs: reads, checks, pulls, generates, sends, replaces, automates.
NEVER use: "leveraging", "game-changer", "revolutionary", "unlock", "harness".

Hook formula (YouTube-proven): [Known Tool/Pain] + [Business Action] + [$ or Time] + [Urgency/Exclusivity]
Character limit: 600-900 chars total. Hook must land in first 2 lines (< 220 chars).

Return ONLY the post text, no preamble."""


def draft_linkedin_post(topic: str, insights: str) -> str:
    return llm(
        DRAFT_SYSTEM,
        f"Topic: \"{topic}\"\n\nKey insights from research:\n{insights[:4000]}\n\n"
        "Write a LinkedIn post (600-900 chars). Lead with the strongest stat or risk.",
        max_tokens=600,
    )


# ── Step 4-5: MiroFish audience simulation + scoring loop ─────────────────────

MIROFISH_QUESTION = """\
As a senior PE operator or management consultant on LinkedIn:
1. Rate this post 1-5 (1=would not engage, 5=would save and share)
2. What specific information is missing that would make you engage more?
Answer concisely — rating first, then gaps."""

SCORING_SYSTEM = """\
You are analyzing a MiroFish audience simulation report for a LinkedIn post targeting
PE operators and management consultants. Extract:
1. A numeric score 1-5 (1=poor, 5=excellent) — infer from engagement signals
2. The top 2-3 content gaps the audience wants answered
3. One specific improvement suggestion

Return ONLY JSON: {"score": 3.5, "gaps": ["gap1", "gap2"], "suggestion": "..."}"""

BATCH_SCORE_SYSTEM = """\
You are analyzing MiroFish agent responses (YES/NO + comments) for a LinkedIn post.
Each response is from a simulated PE operator or management consultant.
Extract:
1. A numeric score 1-5 (infer from YES rate and comment sentiment)
2. The top 2-3 content gaps mentioned most often
3. One specific improvement suggestion

Return ONLY JSON: {"score": 3.5, "gaps": ["gap1", "gap2"], "suggestion": "..."}"""


def _get_mirofish_client():
    try:
        from mirofish_client import MiroFishClient
    except ImportError:
        print(f"  ⚠ MiroFishClient not importable from {SHARED}")
        return None
    client = MiroFishClient(base_url=MIROFISH_URL)
    if not client.is_running():
        print(f"  ⚠ MiroFish not running at {MIROFISH_URL}")
        print(f"    Start: cd '/Users/pietropiga/Desktop/Claude Code/MiroFish/backend' && python run.py")
        return None
    return client


def mirofish_full(content: str, project_id: str, n_agents: int = 20, n_rounds: int = 8) -> dict | None:
    """FIX 3: Full pipeline — build graph + simulate. Returns result including sim_id for reuse."""
    client = _get_mirofish_client()
    if not client:
        return None
    try:
        result = client.run_full_pipeline(
            text=content,
            question=MIROFISH_QUESTION,
            project_id=project_id,
            n_agents=n_agents,
            n_rounds=n_rounds,
        )
        return result
    except Exception as e:
        print(f"  ⚠ MiroFish error: {e}")
        return None


def mirofish_batch(sim_id: str, content: str) -> dict | None:
    """FIX 2: Fast batch interview on existing simulation — seconds, not minutes.
    Reuses the graph and agents from the original simulation.
    Used for scoring loop iterations 2+ and carousel Round 2 validation."""
    client = _get_mirofish_client()
    if not client:
        return None
    try:
        question = f"Here is the updated post to evaluate:\n\n{content}\n\n{MIROFISH_QUESTION}"
        responses = client.interview_agents(sim_id, question)
        if not responses:
            return None
        # Build a readable report from responses for Llama to parse
        report_lines = [f"Agent {r.get('agent_id','?')}: {r.get('response','')}" for r in responses[:20]]
        report = "\n".join(report_lines)
        print(f"  Batch interview: {len(responses)} agents responded")
        return {"report": report, "simulation_id": sim_id, "n_agents": len(responses)}
    except Exception as e:
        print(f"  ⚠ MiroFish batch error: {e}")
        return None


def parse_score(report: str, batch: bool = False) -> dict:
    system = BATCH_SCORE_SYSTEM if batch else SCORING_SYSTEM
    try:
        return llm_json(system, f"Agent responses:\n{report[:3000]}")
    except Exception:
        return {"score": 3.0, "gaps": [], "suggestion": ""}


HUMANIZE_SYSTEM = """\
Rewrite the following LinkedIn post to sound completely human — remove all AI writing patterns.
Rules:
- Vary sentence length (mix short punchy + longer explanatory)
- Use contractions naturally (you're, I've, it's, don't)
- Replace passive constructions with direct active voice
- Remove any "journey", "framework", "leverage", "unlock", "harness"
- Keep all specific numbers, stats, and names unchanged
- Keep total length within 10% of original
Return ONLY the rewritten post, no preamble."""


def humanize(text: str) -> str:
    return llm(HUMANIZE_SYSTEM, text, max_tokens=800)


def scoring_loop(post: str, topic: str, insights: str, slug: str,
                 n_agents: int = 20, n_rounds: int = 8,
                 max_iterations: int = 3) -> tuple[str, str | None]:
    """
    FIX 2 + FIX 3: MiroFish scoring loop.
    - Iteration 1: full simulation (builds graph, runs agents) → saves sim_id
    - Iterations 2-3: fast batch interview on same sim_id (seconds, not minutes)
    Returns (best_post, sim_id) — sim_id passed to Round 2 for graph reuse.
    """
    sim_id = None

    for i in range(max_iterations):
        print(f"\n  ── MiroFish iteration {i+1}/{max_iterations} ──")

        if i == 0:
            # First iteration: full pipeline — build graph + simulate
            uid    = hashlib.md5(f"{slug}_{post[:80]}".encode()).hexdigest()[:8]
            result = mirofish_full(post, project_id=f"social_{uid}",
                                   n_agents=n_agents, n_rounds=n_rounds)
            if result is None:
                print("  → MiroFish unavailable, skipping simulation")
                return post, None
            sim_id = result["simulation_id"]
            report = result["report"]
            batch  = False
            print(f"  Full simulation complete  |  sim_id={sim_id}  |  Agents: {result.get('n_agents','?')}")
        else:
            # Iterations 2+: fast batch interview on same simulation (graph reused)
            print(f"  Fast batch interview on sim {sim_id}…")
            result = mirofish_batch(sim_id, post)
            if result is None:
                print("  → Batch interview failed, stopping loop")
                break
            report = result["report"]
            batch  = True

        print(f"  Report preview: {report[:200]}…")
        analysis = parse_score(report, batch=batch)
        score    = analysis.get("score", 3.0)
        gaps     = analysis.get("gaps", [])
        suggest  = analysis.get("suggestion", "")

        print(f"  Audience score: {score:.1f}/5")
        if gaps:
            print(f"  Gaps: {', '.join(gaps)}")
        if suggest:
            print(f"  Suggestion: {suggest}")

        if score >= 4.0:
            print(f"  ✅ Score {score:.1f} ≥ 4.0 — content validated")
            break

        if i < max_iterations - 1:
            print(f"  → Improving content…")
            improve_prompt = (
                f"Original LinkedIn post:\n{post}\n\n"
                f"Audience gaps: {', '.join(gaps)}\n"
                f"Improvement suggestion: {suggest}\n\n"
                f"Research insights to draw from:\n{insights[:2000]}\n\n"
                "Rewrite the LinkedIn post addressing the gaps. Keep 600-900 chars. "
                "Same brand voice: educational, direct, data-backed."
            )
            post = llm(DRAFT_SYSTEM, improve_prompt, max_tokens=700)
            post = humanize(post)
            print(f"  → Improved + humanized ({len(post)} chars)")

    return post, sim_id


# ── Step 6: Write article ──────────────────────────────────────────────────────

ARTICLE_SYSTEM = """\
You are Pietro Piga's content writer. Write a lead magnet article for LinkedIn.
Target: PE operators, management consultants, real estate and wealth management professionals.
Voice: Educational, direct, data-backed. First-person where appropriate.
NEVER use: "leveraging", "game-changer", "revolutionary", "unlock".
Structure with ## headings. Include concrete numbers and named examples."""


def write_article(topic: str, insights: str, infographic_url: str | None, video_url: str | None) -> dict:
    deep_dive = "\n---\n## Research Deep Dive\n\n*An article by Pietro Piga — AI Sales Advisor*\n\n"
    if video_url:
        deep_dive += f"[Watch the AI-generated Video Overview →]({video_url})\n\n"
    if infographic_url:
        deep_dive += f"---\n\n![{topic} Infographic]({infographic_url})\n"

    prompt = f"""\
Topic: "{topic}"

RESEARCH INSIGHTS:
{insights[:5000]}

Write a 1500-2000 word lead magnet article. Structure:
- Opening (2-3 sentences, lead with biggest insight)
## What [Topic] Actually Is
## The Key Mechanics
## The Risk No One Talks About
## Industry Playbooks
### 🏦 Private Equity / Family Offices
### 🔍 Boutique Management Consulting
### 🏗️ Real Estate
### 💼 Wealth Management
{deep_dive}

Return ONLY JSON:
{{"article_title": "...", "article_body": "...", "hook": "...", "italian_comment": "..."}}"""

    return llm_json(ARTICLE_SYSTEM, prompt, max_tokens=4000)


# ── Step 7: Write carousel JSON ───────────────────────────────────────────────

CAROUSEL_SYSTEM = """\
You write LinkedIn carousel JSON for Pietro Piga (AI Sales Advisor).
Target: PE operators, management consultants, C-suite.
Voice: Educational, punchy, data-driven.

CONFIRMED 5-SLIDE STRUCTURE (follow exactly):
Slide 1 — Hook: LinkedIn post opening (2 punchy lines, ~150-200 chars total)
Slide 2 — "The shift is already happening." (bold_line) + 2 paragraphs showing impact + 3 KPI boxes
Slide 3 — Contrarian/risk insight (bold_line) + 3 paragraphs filling the slide (each 80-120 chars)
Slide 4 — Research proof (bold_line) + 1 short stat paragraph (60-80 chars, the scariest number)
Slide 5 — CTA: 2 paragraphs — tease the article, then "Link in bio."

RULES:
- bold_line: max 50 chars, punchy
- paragraphs: always humanized, no AI patterns
- kpi_boxes (slide 2 only): 3 boxes with {label, value} — real stats from research
- Return ONLY valid JSON, no markdown fences"""


def write_carousel_json(topic: str, slug: str, insights: str, linkedin_post: str,
                        diagram_path: str | None, infographic_path: str | None,
                        video_path: str | None) -> dict:
    kpi_hint = (
        "For the KPI boxes on slide 2, pick 3 concrete stats from the research "
        "(e.g., '80%', '2-3×', '45%') — real numbers only."
    )

    schema = {
        "slug": slug,
        "cover": {
            "headline": "2-3 ALL-CAPS WORDS capturing core number/outcome",
            "subline": "SHORT ALL-CAPS PHRASE (max 25 chars total)",
            "topic": "1-2 ALL-CAPS WORDS (domain label)",
        },
        "logos": "assets/resources/logos/Claude Logo Compact.png:Claude",
        "diagram_names": [],
        "slides": [
            {"image": f"COVER_THUMBNAIL_PATH", "paragraphs": ["Hook line 1.", "Hook line 2."]},
            {"bold_line": "The shift is already happening.", "paragraphs": ["p1", "p2"],
             "kpi_boxes": [{"label": "LABEL", "value": "X%"}, {"label": "LABEL", "value": "Xx"}, {"label": "LABEL", "value": "X%"}]},
            {"bold_line": "Contrarian insight title.", "paragraphs": ["p1.", "p2.", "p3."]},
            {"bold_line": "Research proof headline.", "paragraphs": ["One scariest stat sentence."]},
            {"paragraphs": ["Tease the full article (1 sentence).", "Link in bio."]},
        ],
    }

    prompt = f"""\
Topic: "{topic}"

LINKEDIN POST (use opening lines for slide 1 hook):
{linkedin_post[:500]}

KEY RESEARCH INSIGHTS:
{insights[:3000]}

{kpi_hint}

Fill in the carousel JSON following the schema exactly.
Slide 1 hook = first 2 lines of the LinkedIn post adapted (~150-200 chars total).
Keep subline under 25 chars (fits on cover thumbnail without overlapping face).

Schema to fill:
{json.dumps(schema, indent=2)}"""

    data = llm_json(CAROUSEL_SYSTEM, prompt, max_tokens=1500)

    # --- Fix image paths (script-injected, not LLM-guessed) ---
    cover_thumb = str(ASSETS / "post" / slug / "cover_thumbnail.png")
    slides = data.get("slides", [])

    if slides:
        slides[0]["image"] = cover_thumb

    if len(slides) >= 2 and diagram_path:
        slides[1]["image"] = diagram_path

    if len(slides) >= 4 and infographic_path:
        slides[3]["image"] = infographic_path

    if len(slides) >= 5 and video_path:
        slides[4]["image"] = video_path

    return data


# ── Step 8: Run carousel ───────────────────────────────────────────────────────

def run_carousel(slug: str, carousel_json_path: Path) -> bool:
    face = ASSETS / "profile" / "Shock.JPG"
    cmd = [
        sys.executable, str(SCRIPTS / "run_carousel.py"), str(carousel_json_path),
        "--face", str(face),
    ]
    print(f"  Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(BASE))
    return result.returncode == 0


# ── Step 9: Create Notion pages ───────────────────────────────────────────────

NOTION_API     = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def _notion_headers() -> dict:
    return {
        "Authorization":  f"Bearer {NOTION_TOKEN}",
        "Content-Type":   "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def _inline(text: str) -> list:
    if not text:
        return [{"type": "text", "text": {"content": ""}}]
    parts = []
    for chunk in [text[i:i+2000] for i in range(0, len(text), 2000)]:
        parts.append({"type": "text", "text": {"content": chunk}})
    return parts


def _para(text: str)   -> dict: return {"object": "block", "type": "paragraph",    "paragraph":    {"rich_text": _inline(text)}}
def _h2(text: str)     -> dict: return {"object": "block", "type": "heading_2",    "heading_2":    {"rich_text": _inline(text), "is_toggleable": False}}
def _divider()         -> dict: return {"object": "block", "type": "divider",       "divider":      {}}


def md_to_blocks(text: str) -> list:
    import re as _re
    blocks = []
    lines  = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip():
            i += 1; continue
        if line.startswith("## "):
            blocks.append(_h2(line[3:].strip()))
        elif line.startswith("### "):
            blocks.append({"object": "block", "type": "heading_3",
                           "heading_3": {"rich_text": _inline(line[4:].strip()), "is_toggleable": False}})
        elif line.startswith("- ") or line.startswith("* "):
            blocks.append({"object": "block", "type": "bulleted_list_item",
                           "bulleted_list_item": {"rich_text": _inline(line[2:])}})
        elif line.strip() == "---":
            blocks.append(_divider())
        elif line.strip().startswith("!["):
            m = _re.match(r"!\[.*?\]\((.+?)\)", line.strip())
            if m:
                blocks.append({"object": "block", "type": "image",
                               "image": {"type": "external", "external": {"url": m.group(1)}}})
        elif line.strip().startswith("[") and "→" in line:
            m = _re.match(r"\[(.+?)\]\((.+?)\)", line.strip())
            if m:
                blocks.append({"object": "block", "type": "paragraph",
                               "paragraph": {"rich_text": [{"type": "text",
                                   "text": {"content": m.group(1), "link": {"url": m.group(2)}}}]}})
        else:
            para_lines = [line.strip()]
            i += 1
            while (i < len(lines) and lines[i].strip()
                   and not lines[i].startswith("#")
                   and not lines[i].startswith("-")
                   and not lines[i].startswith("*")
                   and not lines[i].strip() == "---"):
                para_lines.append(lines[i].strip())
                i += 1
            text_chunk = " ".join(para_lines)
            while text_chunk:
                blocks.append(_para(text_chunk[:2000]))
                text_chunk = text_chunk[2000:]
            continue
        i += 1
    return blocks


def _next_posting_dt(platform: str) -> str:
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    is_cest = now.month > 3 or (now.month == 3 and now.day >= 29)
    tz_offset = 2 if is_cest else 1
    local_hours = {"linkedin": 8, "x": 9}
    utc_hour = local_hours.get(platform, 8) - tz_offset
    candidate = now + timedelta(days=2)
    while candidate.weekday() not in (1, 2, 3):
        candidate += timedelta(days=1)
    dt = candidate.replace(hour=utc_hour, minute=0, second=0, microsecond=0)
    return dt.isoformat().replace("+00:00", ".000Z")


def create_notion_pages(topic: str, slug: str, article_title: str, article_body: str,
                        hook: str, linkedin_post: str, italian_comment: str,
                        tags: list, article_url_hint: str = "") -> dict:
    if not NOTION_TOKEN:
        print("  ⚠ NOTION_TOKEN not set — skipping Notion page creation")
        return {}

    def _create(payload: dict) -> dict:
        r = requests.post(f"{NOTION_API}/pages", json=payload, headers=_notion_headers(), timeout=30)
        if not r.ok:
            print(f"  Notion error: {r.status_code} {r.text[:200]}")
            r.raise_for_status()
        return r.json()

    def _append(page_id: str, blocks: list) -> None:
        for j in range(0, len(blocks), 100):
            r = requests.patch(f"{NOTION_API}/blocks/{page_id}/children",
                               json={"children": blocks[j:j+100]},
                               headers=_notion_headers(), timeout=30)
            r.raise_for_status()

    # Article page
    blocks = md_to_blocks(article_body)
    art_payload = {
        "parent": {"database_id": CONTENT_CAL_DB},
        "properties": {"Title": {"title": [{"text": {"content": article_title}}]}},
        "children": blocks[:100],
    }
    print(f"  → Creating article page: '{article_title}'")
    art_page = _create(art_payload)
    art_id   = art_page["id"]
    art_url  = art_page["url"]
    if len(blocks) > 100:
        _append(art_id, blocks[100:])
    print(f"  ✅ Article: {art_url}")

    # LinkedIn calendar entry
    li_date = _next_posting_dt("linkedin")
    li_payload = {
        "parent": {"database_id": CONTENT_CAL_DB},
        "properties": {
            "Title":        {"title":     [{"text": {"content": f"{topic} — LinkedIn"}}]},
            "Platform":     {"select":    {"name": "LinkedIn"}},
            "Post Type":    {"select":    {"name": "Carousel"}},
            "Status":       {"select":    {"name": "Ready"}},
            "Publish Date": {"date":      {"start": li_date, "time_zone": None}},
            "Hook":         {"rich_text": [{"text": {"content": hook[:2000]}}]},
            "Caption":      {"rich_text": [{"text": {"content": linkedin_post[:2000]}}]},
            "Source URL":   {"url":       art_url},
            "Tags":         {"multi_select": [{"name": t} for t in tags]},
            "Notes":        {"rich_text": [{"text": {"content": italian_comment[:2000]}}]},
        },
    }
    print(f"  → Creating LinkedIn calendar entry → {li_date}")
    li_page = _create(li_payload)
    li_url  = li_page["url"]
    print(f"  ✅ LinkedIn: {li_url}")

    return {"article": art_url, "linkedin": li_url}


# ── State persistence (for --resume) ──────────────────────────────────────────

def _state_path(slug: str) -> Path:
    return Path(f"/tmp/{slug}_pipeline_state.json")


def save_state(slug: str, state: dict) -> None:
    path = _state_path(slug)
    with open(path, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    print(f"  [state → {path}  step={state.get('step_completed', '?')}]")


def load_state(slug: str) -> dict:
    path = _state_path(slug)
    if not path.exists():
        print(f"❌ No saved state found at {path}")
        print(f"   Run without --resume first so the pipeline can save state.")
        sys.exit(1)
    with open(path) as f:
        data = json.load(f)
    print(f"  [state loaded from {path}  —  last completed step: {data.get('step_completed', '?')}]")
    return data


# ── Main orchestrator ──────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Full content pipeline: research → Notion + carousel")
    ap.add_argument("slug", help="Topic slug (must match research/topics/{slug}.json)")
    ap.add_argument("--auto",           action="store_true", help="Skip approval gate — run fully automated")
    ap.add_argument("--resume",         type=int, metavar="STEP",
                    help="Resume from step N (1-9). Loads /tmp/{slug}_pipeline_state.json")
    ap.add_argument("--skip-mirofish",  action="store_true", help="Skip audience simulation")
    ap.add_argument("--skip-carousel",  action="store_true", help="Skip carousel generation")
    ap.add_argument("--skip-notion",    action="store_true", help="Skip Notion page creation")
    ap.add_argument("--mirofish-agents", type=int, default=20)
    ap.add_argument("--mirofish-rounds", type=int, default=8)
    args = ap.parse_args()

    if not OPENROUTER_KEY:
        print("❌ OPENROUTER_API_KEY not set in .env")
        sys.exit(1)

    slug        = args.slug
    resume_from = args.resume or 0

    print(f"\n{'='*60}")
    print(f"  MASTER PIPELINE  —  {slug}")
    print(f"  Model: {LLM_MODEL}")
    if resume_from:
        print(f"  Resuming from step {resume_from}")
    print(f"{'='*60}\n")

    # Load saved state when resuming (steps 1-7 outputs)
    state = load_state(slug) if resume_from > 1 else {}

    # Initialise all variables from state; each step may overwrite them
    topic                  = state.get("topic", slug)
    insights               = state.get("insights", "")
    infographic_github_url = state.get("infographic_github_url")
    video_github_url       = state.get("video_github_url")
    infographic_carousel_path = state.get("infographic_carousel_path")
    post                   = state.get("post", "")
    sim_id                 = state.get("sim_id")
    article_title          = state.get("article_title", f"The {slug} Guide")
    article_body           = state.get("article_body", "")
    italian_comment        = state.get("italian_comment", "")
    hook                   = state.get("hook", "")
    tags                   = state.get("tags", ["AI", "Automation", "Strategy"])
    diagram_path           = state.get("diagram_path")
    video_path             = state.get("video_path")

    # Carousel JSON path is always deterministic — no need to store in state
    carousel_json_path = SCRIPTS / f"{slug}_carousel.json"

    # ── 1. Load research ──────────────────────────────────────────────────────
    if resume_from <= 1:
        print("STEP 1 — Load research")
        research = load_research(slug)
        topic    = research.get("topic", slug)
        insights = research.get("insights", "")
        infographic_github_url = research.get("infographic_url")
        video_github_url       = research.get("nlm_video_url")
        state.update({"step_completed": 1, "topic": topic, "insights": insights,
                      "infographic_github_url": infographic_github_url,
                      "video_github_url": video_github_url})
        save_state(slug, state)
    else:
        print(f"STEP 1 — [SKIPPED — resuming from {resume_from}]  topic={topic}")

    # ── 2. Auto-crop infographic ──────────────────────────────────────────────
    if resume_from <= 2:
        print("\nSTEP 2 — Crop infographic")
        infographic_carousel_path = auto_crop_infographic(slug)
        state.update({"step_completed": 2, "infographic_carousel_path": infographic_carousel_path})
        save_state(slug, state)
    else:
        print(f"\nSTEP 2 — [SKIPPED]  infographic={infographic_carousel_path}")

    # ── 3. Draft LinkedIn post ────────────────────────────────────────────────
    if resume_from <= 3:
        print("\nSTEP 3 — Draft LinkedIn post")
        post = draft_linkedin_post(topic, insights)
        post = humanize(post)
        print(f"  Draft ({len(post)} chars):\n  {post[:200]}…")
        state.update({"step_completed": 3, "post": post})
        save_state(slug, state)
    else:
        print(f"\nSTEP 3 — [SKIPPED]  post={len(post)} chars")

    # ── 4-5. MiroFish audience simulation + scoring loop ─────────────────────
    if resume_from <= 4:
        if not args.skip_mirofish:
            print("\nSTEP 4-5 — MiroFish audience simulation (Round 1 + scoring loop)")
            post, sim_id = scoring_loop(
                post, topic, insights, slug,
                n_agents=args.mirofish_agents,
                n_rounds=args.mirofish_rounds,
                max_iterations=3,
            )
            state.update({"step_completed": 4, "post": post, "sim_id": sim_id})
            save_state(slug, state)
        else:
            print("\nSTEP 4-5 — [SKIPPED] MiroFish simulation")
    else:
        print(f"\nSTEP 4-5 — [SKIPPED]  sim_id={sim_id}")

    print(f"\n  ✅ Final LinkedIn post ({len(post)} chars):\n  {post[:300]}…")

    # ── 6. Write article ──────────────────────────────────────────────────────
    if resume_from <= 6:
        print("\nSTEP 6 — Write article + Italian comment")
        content = write_article(topic, insights, infographic_github_url, video_github_url)
        article_title   = content.get("article_title", f"The {topic} Guide")
        article_body    = content.get("article_body", "")
        italian_comment = content.get("italian_comment", "")
        hook            = content.get("hook", post[:200])
        tags            = ["AI", "Automation", "Strategy"]
        print(f"  Article: '{article_title}'  ({len(article_body)} chars)")
        state.update({"step_completed": 6, "article_title": article_title,
                      "article_body": article_body, "italian_comment": italian_comment,
                      "hook": hook, "tags": tags})
        save_state(slug, state)
    else:
        print(f"\nSTEP 6 — [SKIPPED]  article='{article_title}'")

    # ── 7. Write carousel JSON ────────────────────────────────────────────────
    if resume_from <= 7:
        print("\nSTEP 7 — Write carousel JSON")
        diagrams_dir = ASSETS / "post" / slug / "diagrams"
        if diagrams_dir.exists():
            pngs = sorted(diagrams_dir.glob("*.png"))
            if pngs:
                diagram_path = str(pngs[0])
                print(f"  Diagram found: {diagram_path}")

        for vname in ("nlm_video.png", "nlm_video_keyframe.png"):
            vp = ASSETS / "post" / slug / vname
            if vp.exists():
                video_path = str(vp)
                break

        carousel_data = write_carousel_json(
            topic, slug, insights, post,
            diagram_path, infographic_carousel_path, video_path,
        )

        with open(carousel_json_path, "w") as f:
            json.dump(carousel_data, f, indent=2, ensure_ascii=False)
        print(f"  ✅ Saved: {carousel_json_path}")

        state.update({"step_completed": 7, "diagram_path": diagram_path,
                      "video_path": video_path})
        save_state(slug, state)

        # ── MiroFish Round 2 — validate carousel copy ─────────────────────
        if not args.skip_mirofish:
            print("\nSTEP 7b — MiroFish Round 2 (carousel copy validation)")
            carousel_text = "\n".join(
                (slide.get("bold_line", "") + " " + " ".join(slide.get("paragraphs", [])))
                for slide in carousel_data.get("slides", [])
            )
            if sim_id:
                print(f"  Reusing sim {sim_id} — fast batch interview…")
                result2 = mirofish_batch(sim_id, carousel_text)
                batch2  = True
            else:
                uid2    = hashlib.md5(f"{slug}_r2_{carousel_text[:80]}".encode()).hexdigest()[:8]
                result2 = mirofish_full(carousel_text, project_id=f"carousel_{uid2}",
                                        n_agents=args.mirofish_agents, n_rounds=args.mirofish_rounds)
                batch2  = False
            if result2:
                analysis2 = parse_score(result2["report"], batch=batch2)
                print(f"  Carousel validation score: {analysis2.get('score', '?')}/5")
                if analysis2.get("gaps"):
                    print(f"  Gaps: {', '.join(analysis2['gaps'])}")
    else:
        print(f"\nSTEP 7 — [SKIPPED]  carousel JSON at {carousel_json_path}")

    # ── Approval gate — show Pietro everything before generating slides ────────
    # Skipped if: --auto flag, OR resuming from step 8+ (already approved before crash)
    if not args.auto and resume_from < 8:
        print(f"\n{'='*60}")
        print("  APPROVAL GATE — review before generating slides + Notion")
        print(f"{'='*60}")
        print(f"\n  LinkedIn post ({len(post)} chars):\n  {'-'*40}")
        print(f"  {post}")
        print(f"  {'-'*40}")
        print(f"\n  Article: '{article_title}'  ({len(article_body)} chars)")
        print(f"\n  Carousel JSON: {carousel_json_path}")
        print(f"\n  Strip previews: /tmp/{slug}_strip_0-3.png")
        print()
        try:
            input("  Press Enter to generate carousel + Notion pages, or Ctrl+C to abort…\n")
        except KeyboardInterrupt:
            print("\n  Aborted. Edit carousel JSON or re-run with --auto to bypass gate.")
            sys.exit(0)

    # ── 8. Run carousel ───────────────────────────────────────────────────────
    if resume_from <= 8:
        if not args.skip_carousel:
            print("\nSTEP 8 — Generate carousel slides")
            ok = run_carousel(slug, carousel_json_path)
            if ok:
                print("  ✅ Carousel slides generated")
                state.update({"step_completed": 8})
                save_state(slug, state)
            else:
                print("  ⚠ Carousel generation had errors — check output above")
                print(f"  Tip: fix the issue then re-run with --resume 8")
        else:
            print("\nSTEP 8 — [SKIPPED] Carousel generation")
    else:
        print(f"\nSTEP 8 — [SKIPPED — resuming from {resume_from}]")

    # ── 9. Create Notion pages ────────────────────────────────────────────────
    if resume_from <= 9:
        if not args.skip_notion:
            print("\nSTEP 9 — Create Notion pages")
            urls = create_notion_pages(
                topic, slug, article_title, article_body,
                hook, post, italian_comment, tags,
            )
            state.update({"step_completed": 9})
            save_state(slug, state)
        else:
            print("\nSTEP 9 — [SKIPPED] Notion page creation")
            urls = {}
    else:
        print(f"\nSTEP 9 — [SKIPPED — resuming from {resume_from}]")
        urls = {}

    # ── Summary ───────────────────────────────────────────────────────────────
    carousel_dir = ASSETS / "post" / slug / "carousel"
    slides_done  = len(list(carousel_dir.glob("*.png"))) if carousel_dir.exists() else 0

    print(f"\n{'='*60}")
    print(f"  ✅ PIPELINE COMPLETE — {slug}")
    print(f"{'='*60}")
    print(f"  Slides     : {slides_done}/5  →  {carousel_dir}")
    if urls.get("article"):
        print(f"  Article    : {urls['article']}")
    if urls.get("linkedin"):
        print(f"  LinkedIn   : {urls['linkedin']}")
    if italian_comment:
        print(f"\n  Italian comment:\n  {italian_comment}")
    print(f"\n  State file : /tmp/{slug}_pipeline_state.json")


if __name__ == "__main__":
    main()
