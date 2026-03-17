#!/usr/bin/env python3
"""
Generate HTML/CSS diagram images for carousel value slides.
Each diagram is a self-contained HTML file rendered via Playwright at 1000x460px.

Design system: OLED dark (#0A0A0A), orange accent (#E65C00), premium SF Pro/Inter typography.
No emojis — SVG arrows, colored platform dots, glow effects on AI node.

Usage:
  python3 generate_diagrams.py --slug claude-code-scheduled-tasks
"""

import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright

ASSETS = Path(__file__).parent.parent / "assets"

# ── SHARED CSS ───────────────────────────────────────────────────────────────
SHARED_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  width: 1000px; height: 460px;
  background: #0A0A0A;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Helvetica Neue", "Inter", sans-serif;
  overflow: hidden;
  color: #E7E9EA;
}

.wrap {
  display: flex;
  align-items: center;
  height: 100%;
  padding: 36px 44px;
  gap: 20px;
}

/* ── Input column ── */
.inputs {
  display: flex;
  flex-direction: column;
  gap: 9px;
  flex-shrink: 0;
  width: 198px;
}

.input-node {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 11px 14px;
  background: #111111;
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 10px;
}

.dot {
  width: 26px; height: 26px;
  border-radius: 7px;
  flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
}

.dot svg { display: block; }

.node-label {
  font-size: 14px;
  font-weight: 600;
  color: #B8BCBF;
  letter-spacing: -0.01em;
}

/* ── Connector arrow ── */
.connector {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 5px;
  flex-shrink: 0;
  width: 64px;
}

.conn-label {
  font-size: 9px;
  font-weight: 700;
  color: rgba(230,92,0,0.65);
  letter-spacing: 1.6px;
  text-transform: uppercase;
  text-align: center;
  line-height: 1.3;
}

/* ── AI center node ── */
.ai-node {
  flex-shrink: 0;
  width: 154px;
  background: linear-gradient(145deg, #140800, #1F0E00);
  border: 1.5px solid #E65C00;
  border-radius: 18px;
  padding: 22px 14px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 9px;
  box-shadow:
    0 0 0 1px rgba(230,92,0,0.1),
    0 0 30px rgba(230,92,0,0.18),
    0 0 70px rgba(230,92,0,0.07);
}

.ai-logo { display: block; }

.ai-label {
  font-size: 11px;
  font-weight: 800;
  color: #E65C00;
  letter-spacing: 2.5px;
  text-align: center;
  text-transform: uppercase;
}

.ai-sublabel {
  font-size: 10px;
  color: rgba(255,255,255,0.28);
  text-align: center;
  line-height: 1.4;
  letter-spacing: 0.2px;
}

/* ── Output column ── */
.outputs {
  display: flex;
  flex-direction: column;
  gap: 9px;
  flex: 1;
}

.out-card {
  padding: 13px 16px;
  background: #111111;
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 11px;
}

.out-card.primary {
  border-color: rgba(230,92,0,0.28);
  background: rgba(230,92,0,0.04);
}

.out-eyebrow {
  font-size: 9px;
  font-weight: 700;
  color: rgba(255,255,255,0.25);
  letter-spacing: 1.8px;
  text-transform: uppercase;
  margin-bottom: 5px;
}

.out-title {
  font-size: 17px;
  font-weight: 700;
  color: #E7E9EA;
  letter-spacing: -0.02em;
}

.out-sub {
  font-size: 12px;
  color: rgba(255,255,255,0.35);
  margin-top: 3px;
}

.time-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border: 1px solid rgba(230,92,0,0.25);
  border-radius: 9px;
  background: transparent;
}

.pulse {
  width: 7px; height: 7px;
  border-radius: 50%;
  background: #E65C00;
  flex-shrink: 0;
  box-shadow: 0 0 8px rgba(230,92,0,0.7);
}

.time-main {
  font-size: 14px;
  font-weight: 700;
  color: #E65C00;
  letter-spacing: -0.01em;
}

.time-sub {
  font-size: 11px;
  color: rgba(255,255,255,0.3);
  margin-top: 1px;
}

/* Metric row */
.metric-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 6px;
}

.metric-label { font-size: 13px; color: rgba(255,255,255,0.45); }
.metric-val   { font-size: 14px; font-weight: 700; }
.metric-val.up   { color: #4ADE80; }
.metric-val.down { color: #F87171; }

.divider {
  border: none;
  border-top: 1px solid rgba(255,255,255,0.07);
  margin: 8px 0;
}

.badge-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: #E65C00;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  padding: 3px 9px;
  border-radius: 5px;
  letter-spacing: 0.3px;
}

/* Idea list */
.idea-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 12px;
  background: #111111;
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  color: #C9CDD0;
}

.idea-num {
  font-size: 12px;
  font-weight: 800;
  color: rgba(230,92,0,0.85);
  min-width: 14px;
}

.big-count {
  padding: 9px 14px;
  border: 1px solid rgba(230,92,0,0.3);
  border-radius: 9px;
  text-align: center;
  background: rgba(230,92,0,0.04);
}

.big-num {
  font-size: 28px;
  font-weight: 800;
  color: #E65C00;
  letter-spacing: -1px;
  line-height: 1;
}

.big-sub {
  font-size: 10px;
  color: rgba(255,255,255,0.3);
  margin-top: 2px;
  letter-spacing: 0.5px;
}
"""

# ── SVG arrow helper ─────────────────────────────────────────────────────────
def arrow_svg(grad_id="g1"):
    return f"""<svg viewBox="0 0 56 20" width="56" height="20" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="{grad_id}" x1="0" y1="0" x2="56" y2="0" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="rgba(230,92,0,0.25)"/>
      <stop offset="100%" stop-color="#E65C00"/>
    </linearGradient>
  </defs>
  <line x1="0" y1="10" x2="44" y2="10" stroke="url(#{grad_id})" stroke-width="1.5"/>
  <path d="M36 3 L51 10 L36 17" stroke="#E65C00" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
</svg>"""

# ── Claude asterisk logo SVG ─────────────────────────────────────────────────
CLAUDE_LOGO_PATH = str(Path(__file__).parent.parent / "assets" / "resources" / "Claude Logo Compact.png")
CLAUDE_SVG = f'<img class="ai-logo" src="file://{CLAUDE_LOGO_PATH}" width="46" height="46" style="object-fit:contain;"/>'

# ── Platform dot helper ───────────────────────────────────────────────────────
def dot(color: str, letter: str = "") -> str:
    """Colored rounded square with optional letter."""
    if letter:
        return f"""<div class="dot" style="background:{color}22; border: 1px solid {color}55;">
  <svg viewBox="0 0 14 14" width="14" height="14">
    <text x="7" y="11" text-anchor="middle" font-size="10" font-weight="700" fill="{color}" font-family="-apple-system,sans-serif">{letter}</text>
  </svg>
</div>"""
    return f'<div class="dot" style="background:{color}22; border: 1px solid {color}55;"></div>'

# ── DIAGRAM 1: Daily standup digest ─────────────────────────────────────────
STANDUP_HTML = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"/>
<style>{SHARED_CSS}</style></head><body>
<div class="wrap">

  <!-- INPUTS -->
  <div class="inputs">
    {dot('#4A154B','S')}
    <div class="input-node">{dot('#4A154B','S')}<span class="node-label">Slack</span></div>
    <div class="input-node">{dot('#7B68EE','C')}<span class="node-label">ClickUp</span></div>
    <div class="input-node">{dot('#64748B','@')}<span class="node-label">Email</span></div>
    <div class="input-node">{dot('#374151','N')}<span class="node-label">Project Notes</span></div>
  </div>

  <!-- ARROW 1 -->
  <div class="connector">
    <span class="conn-label">Every<br/>8 AM</span>
    {arrow_svg('g1')}
  </div>

  <!-- AI NODE -->
  <div class="ai-node">
    {CLAUDE_SVG}
    <div class="ai-label">Claude</div>
    <div class="ai-sublabel">Reads &amp; summarizes<br/>everything overnight</div>
  </div>

  <!-- ARROW 2 -->
  <div class="connector">
    {arrow_svg('g2')}
    <span class="conn-label">Digest</span>
  </div>

  <!-- OUTPUT -->
  <div class="outputs">
    <div class="out-card primary">
      <div class="out-eyebrow">Telegram Digest</div>
      <div class="out-title">Morning Brief</div>
      <div class="out-sub">Waiting when you wake up</div>
    </div>
    <div class="time-chip">
      <div class="pulse"></div>
      <div>
        <div class="time-main">8:00 AM — Daily</div>
        <div class="time-sub">Fully automated, zero effort</div>
      </div>
    </div>
    <div class="out-card">
      <div class="out-eyebrow">Includes</div>
      <div style="display:flex; gap:6px; margin-top:4px; flex-wrap:wrap;">
        <span style="font-size:11px;font-weight:600;color:#B8BCBF;background:#1A1A1A;border:1px solid rgba(255,255,255,0.1);padding:3px 9px;border-radius:5px;">Blockers</span>
        <span style="font-size:11px;font-weight:600;color:#B8BCBF;background:#1A1A1A;border:1px solid rgba(255,255,255,0.1);padding:3px 9px;border-radius:5px;">Updates</span>
        <span style="font-size:11px;font-weight:600;color:#B8BCBF;background:#1A1A1A;border:1px solid rgba(255,255,255,0.1);padding:3px 9px;border-radius:5px;">Priorities</span>
      </div>
    </div>
  </div>

</div>
</body></html>"""

# ── DIAGRAM 2: Daily content ideas ──────────────────────────────────────────
CONTENT_HTML = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"/>
<style>{SHARED_CSS}
.outputs {{ gap: 7px; }}
.idea-row {{ padding: 6px 11px; }}
</style></head><body>
<div class="wrap">

  <!-- INPUTS -->
  <div class="inputs">
    <div class="input-node">{dot('#1DA1F2','X')}<span class="node-label">Competitor Posts</span></div>
    <div class="input-node">{dot('#FF6B35','N')}<span class="node-label">Niche News</span></div>
    <div class="input-node">{dot('#FF0050','T')}<span class="node-label">Trending Topics</span></div>
    <div class="input-node">{dot('#0A66C2','L')}<span class="node-label">Industry Reports</span></div>
  </div>

  <!-- ARROW 1 -->
  <div class="connector">
    <span class="conn-label">Daily<br/>Noon</span>
    {arrow_svg('g3')}
  </div>

  <!-- AI NODE -->
  <div class="ai-node">
    {CLAUDE_SVG}
    <div class="ai-label">Claude</div>
    <div class="ai-sublabel">Cross-references<br/>your content pillars</div>
  </div>

  <!-- ARROW 2 -->
  <div class="connector">
    {arrow_svg('g4')}
    <span class="conn-label">Output</span>
  </div>

  <!-- OUTPUT -->
  <div class="outputs">
    <div class="idea-row"><span class="idea-num">1</span> LinkedIn Thread Idea</div>
    <div class="idea-row"><span class="idea-num">2</span> X Carousel Hook</div>
    <div class="idea-row"><span class="idea-num">3</span> Reel Script Angle</div>
    <div class="idea-row"><span class="idea-num">4</span> Case Study Post</div>
    <div class="idea-row"><span class="idea-num">5</span> Contrarian Take</div>
    <div class="big-count">
      <div class="big-num">10</div>
      <div class="big-sub">fresh ideas / day</div>
    </div>
  </div>

</div>
</body></html>"""

# ── DIAGRAM 3: Weekly analytics report ──────────────────────────────────────
ANALYTICS_HTML = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"/>
<style>{SHARED_CSS}</style></head><body>
<div class="wrap">

  <!-- INPUTS -->
  <div class="inputs">
    <div class="input-node">{dot('#4ADE80','S')}<span class="node-label">Social Analytics</span></div>
    <div class="input-node">{dot('#A78BFA','A')}<span class="node-label">Ad Performance</span></div>
    <div class="input-node">{dot('#F59E0B','R')}<span class="node-label">Revenue Data</span></div>
    <div class="input-node">{dot('#60A5FA','T')}<span class="node-label">Traffic &amp; Leads</span></div>
  </div>

  <!-- ARROW 1 -->
  <div class="connector">
    <span class="conn-label">Every<br/>Friday</span>
    {arrow_svg('g5')}
  </div>

  <!-- AI NODE -->
  <div class="ai-node">
    {CLAUDE_SVG}
    <div class="ai-label">Claude</div>
    <div class="ai-sublabel">Pattern detection<br/>&amp; recommendations</div>
  </div>

  <!-- ARROW 2 -->
  <div class="connector">
    {arrow_svg('g6')}
    <span class="conn-label">Report</span>
  </div>

  <!-- OUTPUT -->
  <div class="outputs">
    <div class="out-card primary">
      <div class="out-eyebrow">Weekly Report</div>
      <div class="metric-row"><span class="metric-label">Reach</span><span class="metric-val up">↑ 34%</span></div>
      <div class="metric-row"><span class="metric-label">Leads</span><span class="metric-val up">↑ 12 new</span></div>
      <div class="metric-row"><span class="metric-label">Ad CPA</span><span class="metric-val down">↓ 8%</span></div>
      <div class="metric-row"><span class="metric-label">Revenue</span><span class="metric-val up">↑ €2.4k</span></div>
      <hr class="divider"/>
      <div style="display:flex;align-items:center;gap:8px;">
        <span class="badge-pill">PDF</span>
        <span style="font-size:12px;color:rgba(255,255,255,0.35);">Ready before weekend</span>
      </div>
    </div>
    <div class="time-chip">
      <div class="pulse"></div>
      <div>
        <div class="time-main">Friday AM — Auto</div>
        <div class="time-sub">Shared with team automatically</div>
      </div>
    </div>
  </div>

</div>
</body></html>"""

# Fix: remove the orphan dot div from STANDUP_HTML
STANDUP_HTML = STANDUP_HTML.replace(
    f"\n    {dot('#4A154B','S')}\n    <div",
    "\n    <div"
)

DIAGRAMS = {
    "standup_digest":   STANDUP_HTML,
    "content_ideas":    CONTENT_HTML,
    "analytics_report": ANALYTICS_HTML,
}


def render_diagram(name: str, html: str, out_dir: Path):
    out_path = out_dir / f"{name}.png"
    tmp = out_dir / f"_tmp_{name}.html"
    tmp.write_text(html)
    return str(out_path), str(tmp.absolute())


def generate_all_diagrams(slug: str):
    out_dir = ASSETS / "post" / slug / "diagrams"
    out_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1000, "height": 460})

        for name, html in DIAGRAMS.items():
            out_path, tmp_path = render_diagram(name, html, out_dir)
            page.goto(f"file://{tmp_path}")
            page.wait_for_timeout(500)
            page.screenshot(path=out_path, clip={"x": 0, "y": 0, "width": 1000, "height": 460})
            Path(tmp_path).unlink()
            print(f"  ✓ {name} → {out_path}")

        browser.close()

    print(f"\n✅ All diagrams → {out_dir}")
    return out_dir


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", default="claude-code-scheduled-tasks")
    args = ap.parse_args()
    generate_all_diagrams(args.slug)
