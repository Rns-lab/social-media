#!/usr/bin/env python3
"""
Generate topic-specific diagrams from carousel JSON diagram_data field.
Replaces the hardcoded 3-diagram system in generate_diagrams.py.

Each diagram in carousel JSON:
  "diagram_data": [
    { "name": "router_layer", "inputs": [...], "center": {...}, "outputs": [...] },
    ...
  ]

Falls back to generate_diagrams.py if no diagram_data found.

Usage:
  python3 generate_topic_diagrams.py scripts/{slug}_carousel.json
"""

import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ASSETS = Path(__file__).parent.parent / "assets"
CLAUDE_LOGO_PATH = str(ASSETS / "resources" / "logos" / "Claude Logo Compact.png")

PERPLEXITY_LOGO = str(ASSETS / "resources" / "logos" / "perplexity.png")
GEMINI_LOGO     = str(ASSETS / "resources" / "logos" / "gemini.png")
MANUS_LOGO      = str(ASSETS / "resources" / "logos" / "manus.png")
CLAUDE_LOGO     = str(ASSETS / "resources" / "Claude Logo Compact.png")

def logo_img(path: str, size: int = 40) -> str:
    """Return an <img> tag for a real logo PNG, or empty string if missing."""
    if Path(path).exists():
        return f'<img src="file://{path}" width="{size}" height="{size}" style="object-fit:contain;border-radius:6px;"/>'
    return f'<div style="width:{size}px;height:{size}px;background:#333;border-radius:6px;"></div>'

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
  display: flex; align-items: center;
  height: 100%; padding: 36px 44px; gap: 20px;
}
.inputs { display: flex; flex-direction: column; gap: 9px; flex-shrink: 0; width: 198px; }
.input-node {
  display: flex; align-items: center; gap: 11px;
  padding: 11px 14px;
  background: #111111; border: 1px solid rgba(255,255,255,0.07); border-radius: 10px;
}
.dot {
  width: 26px; height: 26px; border-radius: 7px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
}
.node-label { font-size: 14px; font-weight: 600; color: #B8BCBF; letter-spacing: -0.01em; }
.connector {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; gap: 5px; flex-shrink: 0; width: 64px;
}
.conn-label {
  font-size: 9px; font-weight: 700; color: rgba(230,92,0,0.65);
  letter-spacing: 1.6px; text-transform: uppercase; text-align: center; line-height: 1.3;
}
.ai-node {
  flex-shrink: 0; width: 154px;
  background: linear-gradient(145deg, #140800, #1F0E00);
  border: 1.5px solid #E65C00; border-radius: 18px;
  padding: 22px 14px; display: flex; flex-direction: column;
  align-items: center; gap: 9px;
  box-shadow: 0 0 0 1px rgba(230,92,0,0.1), 0 0 30px rgba(230,92,0,0.18), 0 0 70px rgba(230,92,0,0.07);
}
.ai-label { font-size: 11px; font-weight: 800; color: #E65C00; letter-spacing: 2.5px; text-align: center; text-transform: uppercase; }
.ai-sublabel { font-size: 10px; color: rgba(255,255,255,0.28); text-align: center; line-height: 1.4; letter-spacing: 0.2px; }
.outputs { display: flex; flex-direction: column; gap: 9px; flex: 1; }
.out-card { padding: 13px 16px; background: #111111; border: 1px solid rgba(255,255,255,0.07); border-radius: 11px; }
.out-card.primary { border-color: rgba(230,92,0,0.28); background: rgba(230,92,0,0.04); }
.out-eyebrow { font-size: 9px; font-weight: 700; color: rgba(255,255,255,0.25); letter-spacing: 1.8px; text-transform: uppercase; margin-bottom: 5px; }
.out-title { font-size: 17px; font-weight: 700; color: #E7E9EA; letter-spacing: -0.02em; }
.out-sub { font-size: 12px; color: rgba(255,255,255,0.35); margin-top: 3px; }
.time-chip {
  display: flex; align-items: center; gap: 8px; padding: 10px 14px;
  border: 1px solid rgba(230,92,0,0.25); border-radius: 9px;
}
.pulse { width: 7px; height: 7px; border-radius: 50%; background: #E65C00; flex-shrink: 0; box-shadow: 0 0 8px rgba(230,92,0,0.7); }
.time-main { font-size: 14px; font-weight: 700; color: #E65C00; letter-spacing: -0.01em; }
.time-sub { font-size: 11px; color: rgba(255,255,255,0.3); margin-top: 1px; }
.spec-row { display: flex; align-items: center; gap: 10px; padding: 8px 12px; background: #111111; border: 1px solid rgba(255,255,255,0.07); border-radius: 8px; }
.spec-tag { font-size: 10px; font-weight: 800; color: #E65C00; letter-spacing: 1px; text-transform: uppercase; min-width: 54px; }
.spec-label { font-size: 13px; font-weight: 600; color: #C9CDD0; }
.badge-pill {
  display: inline-flex; align-items: center; gap: 5px;
  background: #E65C00; color: #fff; font-size: 11px; font-weight: 700;
  padding: 3px 9px; border-radius: 5px; letter-spacing: 0.3px;
}
.divider { border: none; border-top: 1px solid rgba(255,255,255,0.07); margin: 8px 0; }
"""

def arrow_svg(grad_id="g1"):
    return f"""<svg viewBox="0 0 56 20" width="56" height="20" fill="none">
  <defs>
    <linearGradient id="{grad_id}" x1="0" y1="0" x2="56" y2="0" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="rgba(230,92,0,0.25)"/>
      <stop offset="100%" stop-color="#E65C00"/>
    </linearGradient>
  </defs>
  <line x1="0" y1="10" x2="44" y2="10" stroke="url(#{grad_id})" stroke-width="1.5"/>
  <path d="M36 3 L51 10 L36 17" stroke="#E65C00" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
</svg>"""

def dot(color: str, letter: str = "") -> str:
    if letter:
        return f"""<div class="dot" style="background:{color}22; border: 1px solid {color}55;">
  <svg viewBox="0 0 14 14" width="14" height="14">
    <text x="7" y="11" text-anchor="middle" font-size="10" font-weight="700" fill="{color}" font-family="-apple-system,sans-serif">{letter}</text>
  </svg>
</div>"""
    return f'<div class="dot" style="background:{color}22; border: 1px solid {color}55;"></div>'


# ── Topic-specific diagram builders ──────────────────────────────────────────

def build_router_layer_html():
    """Diagram 1: Perplexity Router Layer — one prompt, 19 specialists."""
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"/>
<style>{SHARED_CSS}
.outputs {{ gap: 7px; }}
.spec-row {{ padding: 7px 12px; }}
</style></head><body>
<div class="wrap">

  <div class="inputs">
    <div class="input-node">{dot('#E65C00','→')}<span class="node-label">Your Prompt</span></div>
    <div style="padding:8px 0; text-align:center; font-size:10px; color:rgba(255,255,255,0.2); letter-spacing:1px; text-transform:uppercase;">1 sentence<br/>= entire project</div>
    <div class="out-card" style="margin-top:4px;">
      <div class="out-eyebrow">Models active</div>
      <div style="font-size:26px;font-weight:800;color:#E65C00;line-height:1;">19</div>
      <div style="font-size:10px;color:rgba(255,255,255,0.3);margin-top:2px;">in parallel</div>
    </div>
  </div>

  <div class="connector">
    <span class="conn-label">Routes<br/>tasks</span>
    {arrow_svg('g1')}
  </div>

  <div class="ai-node">
    {logo_img(PERPLEXITY_LOGO, 46)}
    <div class="ai-label">Router</div>
    <div class="ai-sublabel">Conductor model<br/>assigns specialists</div>
  </div>

  <div class="connector">
    {arrow_svg('g2')}
    <span class="conn-label">Parallel</span>
  </div>

  <div class="outputs">
    <div class="spec-row">{logo_img(GEMINI_LOGO, 26)}<span class="spec-tag">Research</span><span class="spec-label">Gemini</span></div>
    <div class="spec-row">{logo_img(CLAUDE_LOGO, 26)}<span class="spec-tag">Reasoning</span><span class="spec-label">Claude Opus</span></div>
    <div class="spec-row">{dot('#A78BFA','N')}<span class="spec-tag">Visuals</span><span class="spec-label">Nano Banana</span></div>
    <div class="spec-row">{dot('#4ADE80','◈')}<span class="spec-tag">Deploy</span><span class="spec-label">Code Model</span></div>
    <div class="time-chip">
      <div class="pulse"></div>
      <div>
        <div class="time-main">All running simultaneously</div>
        <div class="time-sub">Not sequentially — in parallel</div>
      </div>
    </div>
  </div>

</div>
</body></html>"""


def build_cloud_24_7_html():
    """Diagram 2: Cloud vs Local — 24/7 even when laptop is closed."""
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"/>
<style>{SHARED_CSS}
.vs-badge {{
  font-size: 10px; font-weight: 800; color: rgba(255,255,255,0.3);
  letter-spacing: 2px; text-transform: uppercase; text-align: center;
}}
</style></head><body>
<div class="wrap">

  <div class="inputs" style="gap:12px;">
    <div class="input-node" style="flex-direction:column;align-items:flex-start;gap:4px;padding:12px 14px;">
      <div style="display:flex;align-items:center;gap:8px;">{logo_img(PERPLEXITY_LOGO, 26)}<span class="node-label">Perplexity Cloud</span></div>
      <div style="font-size:11px;color:rgba(255,255,255,0.35);padding-left:34px;">Runs in hosted servers</div>
    </div>
    <div class="vs-badge">vs</div>
    <div class="input-node" style="flex-direction:column;align-items:flex-start;gap:4px;padding:12px 14px;">
      <div style="display:flex;align-items:center;gap:8px;">{logo_img(MANUS_LOGO, 26)}<span class="node-label">Manus Local</span></div>
      <div style="font-size:11px;color:rgba(255,255,255,0.35);padding-left:34px;">Runs on your machine</div>
    </div>
  </div>

  <div class="connector">
    <span class="conn-label">Close<br/>laptop</span>
    {arrow_svg('g1')}
  </div>

  <div class="ai-node">
    {logo_img(PERPLEXITY_LOGO, 46)}
    <div class="ai-label">Cloud</div>
    <div class="ai-sublabel">Laptop off?<br/>Still running</div>
  </div>

  <div class="connector">
    {arrow_svg('g2')}
    <span class="conn-label">Result</span>
  </div>

  <div class="outputs">
    <div class="out-card primary">
      <div class="out-eyebrow">Cloud Agent (24/7)</div>
      <div class="out-title">Keeps executing overnight</div>
      <div class="out-sub">Scheduled tasks, deployments, briefings</div>
    </div>
    <div class="time-chip">
      <div class="pulse"></div>
      <div>
        <div class="time-main">Wake up to finished work</div>
        <div class="time-sub">Not a paused process</div>
      </div>
    </div>
    <div class="out-card" style="border-color:rgba(248,113,113,0.2);">
      <div class="out-eyebrow">Local Agent</div>
      <div style="font-size:13px;font-weight:600;color:rgba(248,113,113,0.8);">Stops when laptop closes</div>
    </div>
  </div>

</div>
</body></html>"""


def build_manus_local_html():
    """Diagram 3: Manus — zero setup, full terminal control."""
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"/>
<style>{SHARED_CSS}
.outputs {{ gap: 7px; }}
.cmd-row {{
  display: flex; align-items: center; gap: 10px;
  padding: 8px 12px; background: #0D1117;
  border: 1px solid rgba(74,222,128,0.15); border-radius: 8px;
  font-family: "SF Mono", "Fira Code", monospace;
}}
.cmd-prompt {{ font-size: 12px; color: #4ADE80; font-weight: 700; }}
.cmd-text {{ font-size: 12px; color: rgba(255,255,255,0.55); }}
</style></head><body>
<div class="wrap">

  <div class="inputs">
    <div class="input-node">{dot('#F59E0B','F')}<span class="node-label">10,000 Files</span></div>
    <div class="input-node">{dot('#A78BFA','P')}<span class="node-label">Python / Xcode</span></div>
    <div class="input-node">{dot('#60A5FA','T')}<span class="node-label">Terminal Access</span></div>
    <div class="input-node">{dot('#4ADE80','D')}<span class="node-label">Local Drive</span></div>
  </div>

  <div class="connector">
    <span class="conn-label">Zero<br/>setup</span>
    {arrow_svg('g1')}
  </div>

  <div class="ai-node">
    {logo_img(MANUS_LOGO, 46)}
    <div class="ai-label">Manus</div>
    <div class="ai-sublabel">Sees file content<br/>visually, not names</div>
  </div>

  <div class="connector">
    {arrow_svg('g2')}
    <span class="conn-label">Executes</span>
  </div>

  <div class="outputs">
    <div class="cmd-row"><span class="cmd-prompt">$</span><span class="cmd-text">mkdir renovated_kitchen/</span></div>
    <div class="cmd-row"><span class="cmd-prompt">$</span><span class="cmd-text">mv img_4821.jpg roof_damage/</span></div>
    <div class="cmd-row"><span class="cmd-prompt">$</span><span class="cmd-text">python3 build.py --deploy</span></div>
    <div class="out-card primary" style="margin-top:2px;">
      <div class="out-eyebrow">Result</div>
      <div class="out-title">Done in minutes</div>
      <div class="out-sub">No IDE. No Docker. No config.</div>
    </div>
  </div>

</div>
</body></html>"""


def build_decision_matrix_html():
    """Decision matrix: which AI agent wins for which PE/consulting workflow."""
    rows = [
        ("Deal room docs",       "Dispatch",   "#E65C00", "Sandboxed VM — files never leave Mac"),
        ("NDA file analysis",    "Dispatch",   "#E65C00", "Local execution, compliance-ready"),
        ("Client QA (Excel/PPT)","Dispatch",   "#E65C00", "Passes context across Office apps"),
        ("Overnight research",   "Perplexity", "#22D3EE", "Cloud multi-model, queue & walk away"),
        ("Competitor dashboard", "Perplexity", "#22D3EE", "100+ sources, 7 search types parallel"),
        ("Property photo sort",  "Manus",      "#A78BFA", "Visual file analysis, free, fully local"),
    ]
    row_html = ""
    for workflow, tool, color, reason in rows:
        row_html += f"""
        <div class="row">
          <div class="cell wf">{workflow}</div>
          <div class="cell tool" style="color:{color};">{tool}</div>
          <div class="cell why">{reason}</div>
        </div>"""
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"/>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  width: 1000px; height: 460px;
  background: #0A0A0A;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Helvetica Neue", "Inter", sans-serif;
  overflow: hidden; color: #E7E9EA;
  display: flex; flex-direction: column; padding: 28px 40px; gap: 14px;
}}
.title {{
  font-size: 13px; font-weight: 800; letter-spacing: 2.5px; text-transform: uppercase;
  color: #E65C00; margin-bottom: 2px;
}}
.header, .row {{
  display: grid;
  grid-template-columns: 220px 130px 1fr;
  gap: 0;
}}
.header .cell {{
  font-size: 10px; font-weight: 700; letter-spacing: 1.8px; text-transform: uppercase;
  color: rgba(255,255,255,0.28); padding: 0 0 6px 12px;
}}
.row {{
  background: #111111; border: 1px solid rgba(255,255,255,0.07);
  border-radius: 9px; margin-bottom: 5px;
}}
.cell {{ padding: 11px 12px; font-size: 13px; display: flex; align-items: center; }}
.cell.wf {{ font-weight: 600; color: #E7E9EA; border-right: 1px solid rgba(255,255,255,0.06); }}
.cell.tool {{ font-weight: 800; font-size: 12px; border-right: 1px solid rgba(255,255,255,0.06); letter-spacing: 0.3px; }}
.cell.why {{ color: rgba(255,255,255,0.45); font-size: 12px; }}
</style></head><body>
  <div class="title">Decision Matrix — Which Agent Wins</div>
  <div class="header">
    <div class="cell">Workflow</div>
    <div class="cell">Best Tool</div>
    <div class="cell">Why</div>
  </div>
  {row_html}
</body></html>"""


def build_dispatch_channels_flow_html():
    """Diagram: Claude Code Dispatch + Channels — async overnight workflow."""
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"/>
<style>
{SHARED_CSS}
.wrap {{ gap: 16px; padding: 32px 38px; }}
.inputs {{ width: 178px; gap: 10px; }}
.ai-node {{ width: 148px; padding: 18px 12px; gap: 8px; }}
.right-col {{
  flex: 1; display: flex; flex-direction: column; gap: 9px;
}}
.task-grid {{
  display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 7px;
}}
.task-card {{
  background: rgba(230,92,0,0.06); border: 1px solid rgba(230,92,0,0.22);
  border-radius: 9px; padding: 10px 11px;
}}
.task-num {{
  font-size: 9px; font-weight: 800; color: #E65C00;
  letter-spacing: 1.6px; text-transform: uppercase; margin-bottom: 4px;
}}
.task-label {{
  font-size: 12px; font-weight: 700; color: #E7E9EA; line-height: 1.3;
}}
.channels-bar {{
  background: #111111; border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px; padding: 11px 14px;
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
}}
.ch-label {{
  font-size: 9px; font-weight: 800; color: rgba(255,255,255,0.28);
  letter-spacing: 2px; text-transform: uppercase; margin-bottom: 5px;
}}
.ch-icons {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }}
.ch-badge {{
  display: inline-flex; align-items: center; gap: 5px;
  background: #1A1A1A; border: 1px solid rgba(255,255,255,0.1);
  border-radius: 6px; padding: 4px 9px;
  font-size: 11px; font-weight: 600; color: rgba(255,255,255,0.55);
}}
.ch-dot {{ width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }}
.delivered-chip {{
  display: flex; align-items: center; gap: 8px;
  padding: 9px 13px; border: 1px solid rgba(74,222,128,0.25);
  border-radius: 8px; white-space: nowrap; flex-shrink: 0;
}}
.delivered-dot {{ width: 7px; height: 7px; border-radius: 50%; background: #4ADE80; box-shadow: 0 0 8px rgba(74,222,128,0.7); }}
.delivered-text {{ font-size: 12px; font-weight: 700; color: #4ADE80; }}
.delivered-sub {{ font-size: 10px; color: rgba(255,255,255,0.28); margin-top: 1px; }}
</style></head><body>
<div class="wrap">

  <div class="inputs">
    <div class="input-node">{dot('#60A5FA','→')}<span class="node-label">Task sent<br/><span style="font-size:11px;color:rgba(255,255,255,0.3);">9:00 PM</span></span></div>
    <div class="input-node">{dot('#F87171','!')}<span class="node-label">CI alert<br/><span style="font-size:11px;color:rgba(255,255,255,0.3);">2:00 AM</span></span></div>
    <div style="padding:6px 0; text-align:center;">
      <div style="font-size:9px;font-weight:700;color:rgba(255,255,255,0.18);letter-spacing:1.6px;text-transform:uppercase;">You're asleep</div>
    </div>
    <div class="out-card" style="padding:10px 12px;">
      <div class="out-eyebrow">Agents spawned</div>
      <div style="font-size:28px;font-weight:800;color:#E65C00;line-height:1;">3</div>
      <div style="font-size:10px;color:rgba(255,255,255,0.3);margin-top:1px;">in parallel</div>
    </div>
  </div>

  <div class="connector">
    <span class="conn-label">Dispatch<br/>routes</span>
    {arrow_svg('g1')}
  </div>

  <div class="ai-node">
    {logo_img(CLAUDE_LOGO_PATH, 44)}
    <div class="ai-label">Claude Code</div>
    <div class="ai-sublabel">Dispatch +<br/>Channels</div>
  </div>

  <div class="connector">
    {arrow_svg('g2')}
    <span class="conn-label">Runs</span>
  </div>

  <div class="right-col">
    <div class="task-grid">
      <div class="task-card">
        <div class="task-num">Task 01</div>
        <div class="task-label">Fix CI failure</div>
      </div>
      <div class="task-card">
        <div class="task-num">Task 02</div>
        <div class="task-label">Run test suite</div>
      </div>
      <div class="task-card">
        <div class="task-num">Task 03</div>
        <div class="task-label">Write PR summary</div>
      </div>
    </div>
    <div class="channels-bar">
      <div>
        <div class="ch-label">Channels — delivers results via</div>
        <div class="ch-icons">
          <div class="ch-badge"><div class="ch-dot" style="background:#5865F2;"></div>Discord</div>
          <div class="ch-badge"><div class="ch-dot" style="background:#4A154B;"></div>Slack</div>
          <div class="ch-badge"><div class="ch-dot" style="background:#EA4335;"></div>Email</div>
        </div>
      </div>
      <div class="delivered-chip">
        <div class="delivered-dot"></div>
        <div>
          <div class="delivered-text">7:00 AM ✓</div>
          <div class="delivered-sub">Summary delivered</div>
        </div>
      </div>
    </div>
  </div>

</div>
</body></html>"""


TOPIC_DIAGRAMS = {
    "router_layer":             build_router_layer_html,
    "cloud_24_7":               build_cloud_24_7_html,
    "manus_local":              build_manus_local_html,
    "decision_matrix":          build_decision_matrix_html,
    "dispatch_channels_flow":   build_dispatch_channels_flow_html,
}


def render_diagrams(slug: str, diagram_names: list[str]):
    out_dir = ASSETS / "post" / slug / "diagrams"
    out_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1000, "height": 460})

        results = []
        for i, name in enumerate(diagram_names):
            if name not in TOPIC_DIAGRAMS:
                print(f"  ⚠ Unknown diagram: {name}")
                continue
            html = TOPIC_DIAGRAMS[name]()
            tmp = out_dir / f"_tmp_{name}.html"
            tmp.write_text(html)
            out_path = out_dir / f"{name}.png"
            page.goto(f"file://{tmp.absolute()}")
            page.wait_for_timeout(400)
            page.screenshot(path=str(out_path), clip={"x": 0, "y": 0, "width": 1000, "height": 460})
            tmp.unlink()
            print(f"  ✓ {name} → {out_path}")
            results.append(str(out_path))

        browser.close()

    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("content", help="Path to carousel JSON")
    ap.add_argument("--diagrams", nargs="+", help="Override diagram names")
    args = ap.parse_args()

    with open(args.content) as f:
        data = json.load(f)

    slug = data.get("slug", "carousel")

    # Get diagram names from JSON or CLI override
    if args.diagrams:
        names = args.diagrams
    elif "diagram_names" in data:
        names = data["diagram_names"]
    else:
        # No diagram_names in JSON → fall back to generic generate_diagrams.py
        import subprocess, sys as _sys
        print(f"  ⚠ No diagram_names in carousel JSON — falling back to generate_diagrams.py")
        r = subprocess.run([_sys.executable, str(Path(__file__).parent / "generate_diagrams.py"), "--slug", slug])
        _sys.exit(r.returncode)

    print(f"Generating {len(names)} diagrams for '{slug}':")
    paths = render_diagrams(slug, names)
    print(f"\n✅ {len(paths)} diagrams → assets/post/{slug}/diagrams/")
