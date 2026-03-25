"""
mirofish_content_tester.py — Test content resonance with MiroFish crowd simulation

Simulates how Pietro's target audience (PE operators, consultants, real estate pros)
would react to a post or article before publishing.

Usage:
    python scripts/mirofish_content_tester.py --post "post text here" --platform linkedin
    python scripts/mirofish_content_tester.py --file assets/post/slug/draft.md --platform linkedin

Output:
    - Resonance score (0–10)
    - Predicted engagement signals (saves, shares, comments)
    - Crowd reaction summary
    - Suggestions from simulated audience
"""

import argparse
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared"))
from mirofish_client import MiroFishClient

BASE = Path(__file__).parent.parent

# ── Audience profiles per platform ─────────────────────────────────────────
AUDIENCE_CONTEXT = {
    "linkedin": """
Target audience: PE operators, management consultants, C-suite executives at mid-market companies,
real estate asset managers. Italian and international professionals. Senior decision-makers.
They are skeptical of AI hype. They value specific ROI data, named risks, and practical implementation.
They reward educational content that respects their intelligence.
They ignore posts that are generic, vague, or overly promotional.
""",
    "instagram": """
Target audience: Italian entrepreneurs, small business owners, and professionals (25-45).
Platform: Instagram (Italian language content).
They respond to practical, visual, story-driven content about AI tools in business.
They value concrete examples over abstract concepts.
""",
    "x": """
Target audience: AI practitioners, tech-forward business professionals, founders.
Platform: X (Twitter). English language.
They value contrarian takes, specific data points, and brevity.
They engage with content that challenges conventional wisdom or shares insider knowledge.
""",
}

RESONANCE_QUESTION = """
As a member of this target audience:
1. Would you stop scrolling for this post? (YES/NO)
2. Would you save or share it? (YES/NO)
3. Does it make Pietro seem credible and worth following? (YES/NO)
Answer each question separately, then give one sentence of honest feedback.
"""


def test_content(post_text: str, platform: str = "linkedin", fast: bool = True) -> dict:
    client = MiroFishClient()

    if not client.is_running():
        print("❌ MiroFish is not running.")
        print("   Start it: cd '/Users/pietropiga/Desktop/Claude Code/MiroFish/backend' && python run.py")
        sys.exit(1)

    audience = AUDIENCE_CONTEXT.get(platform, AUDIENCE_CONTEXT["linkedin"])

    context = f"""
{audience}

Pietro Piga is an AI Sales Advisor posting on {platform.capitalize()}.
His brand voice: educational, direct, data-backed, no hype.
Italian perspective, global relevance.

Here is the post to evaluate:
---
{post_text}
---
"""

    import hashlib
    project_id = "content_" + hashlib.md5(post_text[:100].encode()).hexdigest()[:8]

    n_agents = 20 if fast else 50
    n_rounds = 8 if fast else 20

    result = client.run_full_pipeline(
        text=context,
        question=RESONANCE_QUESTION,
        project_id=project_id,
        n_agents=n_agents,
        n_rounds=n_rounds,
    )

    # Map score to 0-10 resonance scale
    resonance = round(result["score"] * 10, 1)
    verdict = (
        "🔥 Strong — publish as-is" if resonance >= 7.5
        else "✅ Good — minor tweaks" if resonance >= 6.0
        else "⚠️  Weak — rework hook/angle" if resonance >= 4.0
        else "❌ Poor — major rewrite needed"
    )

    return {
        "resonance_score": resonance,
        "verdict": verdict,
        "confidence": result["confidence"],
        "n_agents": result["n_agents"],
        "crowd_report": result["report"],
        "simulation_id": result["simulation_id"],
    }


def main():
    ap = argparse.ArgumentParser(description="Test content resonance with MiroFish crowd simulation")
    ap.add_argument("--post",     help="Post text (inline)")
    ap.add_argument("--file",     help="Path to draft file (.md or .txt)")
    ap.add_argument("--platform", default="linkedin", choices=["linkedin", "instagram", "x"])
    ap.add_argument("--thorough", action="store_true", help="Run thorough simulation (slower)")
    args = ap.parse_args()

    if args.file:
        post_text = Path(args.file).read_text()
    elif args.post:
        post_text = args.post
    else:
        print("❌ Provide --post 'text' or --file path/to/draft.md")
        sys.exit(1)

    print(f"\n🧪 Testing {args.platform.upper()} post with MiroFish...")
    print(f"   Agents: {'50 (thorough)' if args.thorough else '20 (fast)'}")
    print(f"   Post preview: {post_text[:100].strip()}...\n")

    result = test_content(post_text, args.platform, fast=not args.thorough)

    print(f"{'─'*50}")
    print(f"Resonance Score : {result['resonance_score']} / 10")
    print(f"Verdict         : {result['verdict']}")
    print(f"Confidence      : {result['confidence']:.0%}")
    print(f"Agents polled   : {result['n_agents']}")
    print(f"{'─'*50}")
    print(f"\nCrowd Report:\n{result['crowd_report'][:1000]}")
    if len(result['crowd_report']) > 1000:
        print(f"\n[... full report: {len(result['crowd_report'])} chars]")


if __name__ == "__main__":
    main()
