# Social Media Audience Builder

## What this is
An automated content system for Pietro Piga — AI Sales Advisor.
Platforms: LinkedIn (English), Instagram (Italian), X (English).
Goal: 3 posts/week per platform (Tue/Wed/Thu) targeting PE, Consulting, Real Estate, Wealth Mgmt.

## Folder
`/Users/pietropiga/Social Media/`
GitHub: https://github.com/Rns-lab/social-media (public — used for image hosting)

## Brand Voice
- Educational, direct. No fluff. Cuts through AI hype for CEOs and decision-makers.
- Italian perspective, global relevance. Always data-driven (numbers, sources, studies).
- Short and to the point.

## Language Rules
- LinkedIn: English + first comment in Italian
- Instagram: Italian only
- X: English only

## Posting Schedule (Tue/Wed/Thu)
User is in CET (UTC+1), CEST (UTC+2) from March 29.
- LinkedIn: 08:00 local → 07:00 UTC (CET) / 06:00 UTC (CEST)
- Instagram: 11:00 local → 10:00 UTC (CET) / 09:00 UTC (CEST)
- X: 09:00 local → 08:00 UTC (CET) / 07:00 UTC (CEST)
Always store Notion datetimes in UTC.

## Content Framework (per topic — 5-post sequence)
1. Explainer (LinkedIn + X) — no lead magnet
2. Contrarian/Risk (LinkedIn + X) — lead magnet: checklist/guide
3. PE/Consulting use case (LinkedIn) — lead magnet: playbook
4. Real Estate use case (Instagram Italian + LinkedIn) — lead magnet: Italian guide
5. Wealth Management use case (LinkedIn) — lead magnet: setup guide

## Research Pipeline
```bash
python scripts/research_pipeline.py "topic" [--yt N] [--urls url1 url2 ...]
```
Outputs: `research/topics/{slug}.json` + `{slug}.md`
After running → say "pipeline done" → Claude creates Notion pages + Calendar entries automatically.

## Notion
- Content Calendar DB: notion.so/923eeb74667343ef873e1e3d51aec24a
- Fields: Title, Platform, Status, Post Type, Publish Date, Hook, Caption, CTA, Tags, Source URL, Notes

## Notion Formatting Rules (critical)
- NEVER blank lines inside blockquotes — creates "Empty quote" blocks
- Footer: `*From Pietro Piga AI Sales Advisor*`
- NO Sources section, NO NotebookLM attribution in page content

## Infographic hosting
Raw URL: `https://raw.githubusercontent.com/Rns-lab/social-media/main/assets/infographics/{slug}.png`

## Progress
- [x] Brand voice, folder structure, Notion DB, research pipeline
- [ ] Blotato setup (deferred)
- [ ] Remotion scaffold (if video confirmed)
- [ ] End-to-end test run
