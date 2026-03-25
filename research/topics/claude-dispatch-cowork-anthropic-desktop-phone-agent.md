# Research: Claude Dispatch Cowork Anthropic desktop phone agent
**Date:** 2026-03-19  
**NotebookLM ID:** 672f7620-a9f2-4042-9f2a-c5b4c493072b  
**Infographic:** https://raw.githubusercontent.com/Rns-lab/social-media/main/assets/post/claude-dispatch-cowork-anthropic-desktop-phone-agent/nlm_infographic.png  

---

## Infographic

![Research Infographic](https://raw.githubusercontent.com/Rns-lab/social-media/main/assets/post/claude-dispatch-cowork-anthropic-desktop-phone-agent/nlm_infographic.png)

---

## NotebookLM Insights

The following intelligence is extracted from the provided sources regarding the latest advancements in **Claude Dispatch**, **Cowork**, and the **Opus 4.6 agent ecosystem**.

## 1. SURPRISING STATS
*   **$52 Billion:** The projected global market value for AI agents by the year 2030 [1]. *(Source: สาระEveryDay)*
*   **$4,000–$5,000:** The estimated monthly API cost to run complex agentic workflows in OpenClaw, compared to the flat **$20–$200/month** subscription cost for Claude’s native tools [2, 3]. *(Source: Kevin Jeppesen)*
*   **50%:** The current success rate for Claude Dispatch in its "research preview" phase; while it excels at finding files and reading emails, it often fails at third-party authorizations or opening new apps [4, 5]. *(Source: AI Application / MacStories)*
*   **20,000–50,000 Tokens:** The amount of context consumed by "vibe-coded" agents for a single message exchange, compared to the efficiency of native orchestration [6]. *(Source: Kevin Jeppesen)*
*   **12 Hours:** The exact lifespan of a dedicated **Agent Sandbox** instance before it expires [7]. *(Source: IndyDevDan)*
*   **60 Tool Calls:** The number of operations a single Opus 4.6 agent can execute within a **60-second** window when scaling compute [8]. *(Source: IndyDevDan)*

## 2. THE THING EXPERTS GET WRONG
Experienced practitioners often treat "Agent Teams" as a simple evolution of "Sub-agents." This is a mistake. **Sub-agents** operate within a single context window and are transactional, whereas **Agent Teams** spool up **isolated, dedicated sessions** for each member [9]. This allows teammates (e.g., a "UI Builder" and a "JS Developer") to communicate directly with each other to unblock tasks without constantly involving the user, effectively creating a "multi-department" environment rather than a linear task-runner [9-11].

## 3. THE HIDDEN MECHANIC
The "root cause" that makes the system click is **Context Engineering through Sandbox Architecture**. Instead of giving an AI remote access to your entire OS, the system creates a "playpen" (sandbox) where the agent only sees specific folders you approve [12]. By running **multi-agent orchestration** inside these sandboxes, you are "scaling compute to scale impact"—allowing parallel processing across different "brains" that each hold a specialized subset of the project context [8, 13].

## 4. WHAT ACTUALLY KILLS RESULTS
*   **Host Sleep Mode:** The most common failure for Dispatch is the desktop Mac falling asleep. Dispatch requires the machine to be awake and the Claude app open to execute phone-sent tasks [4, 14].
*   **Conversation Compaction:** In standard 1M context windows, if too many messages accumulate, the chat "crunches" the history, leading to a loss of nuance. Using **Opus 4.6 with 1M context** is required to maintain high-fidelity long threads [15].
*   **Temporary Token Reliance:** Many developers use temporary WhatsApp access tokens that expire in 24 hours. For production-ready agents, you must create a **Permanent System User** in the Meta Business console [16].

## 5. THE COUNTER-INTUITIVE MOVE
**Ruthless Deletion:** It seems wrong to destroy your agents after they finish a task, but the sources reveal that **deleting the agent team immediately after completion** is a superior workflow [17]. This forces a "clean reset" for the next task, preventing "context baggage" or hallucination-drift from previous sub-tasks from polluting the next stage of engineering [18].

## 6. EXACT STEP-BY-STEP (How to Enable Dispatch)
1.  **Update Desktop:** Ensure your Mac Claude app is updated to at least version **1.1.17203** [19, 20].
2.  **Toggle Settings:** Open Claude Cowork on the desktop, go to Settings, and enable the **Dispatch** feature [15, 21].
3.  **Prevent Sleep:** In the Dispatch setup menu, check the box **"Prevent sleep while dispatch is running"** [22].
4.  **Pair Mobile:** Open the Claude app on your phone, navigate to the sidebar, and select **Dispatch** [15, 23].
5.  **QR Authentication:** Scan the QR code displayed on your desktop with your phone to pair the devices [23, 24].
6.  **Authorize Browser:** If performing web tasks, ensure **"Allow all browser actions"** is toggled on in the desktop Dispatch settings [25].

## 7. INDUSTRY-SPECIFIC ANGLES
*   **Private Equity / Family Offices:** Use "Mission Briefing" dashboards. Agents can be dispatched to monitor portfolio data across Excel and PowerPoint, automatically generating slide decks from raw financial analysis without manual data entry [26, 27].
*   **Boutique Management Consulting:** Deploy specialized **"Code/Document Review Teams."** Assign one agent to "thematic analysis," another to "compliance check," and a third to "executive summary" to ensure diverse perspectives that a single agent would otherwise miss [28].
*   **Real Estate (Commercial/Development):** Integrate **Superbase MCP** with Opus 4.6 to build custom "Dealership Portals." This allows field agents to use Dispatch to create new customer entries, jobs, and tasks in a central database directly from a property site [29].
*   **Wealth Management / Financial Advisory:** Leverage the **Sandboxed VM** for HIPAA-ready data privacy. Agents can summarize sensitive client emails or Notion-based notes locally on the desktop, with the advisor only receiving the high-level summary on their phone via Dispatch [30, 31].

## 8. THE LEAD MAGNET HOOK
The most valuable insight is that you can now **"scale your compute to scale your impact"** by turning a single prompt into a multi-agent "digital agency" that communicates in parallel across isolated sandboxes to finish weeks of engineering work in minutes [8, 32].

---

## CONTENT HOOKS (Hormozi Style)

HOOK: Custom AI agents are currently costing firms $5,000 a month in API fees. 
Claude Dispatch runs those same complex tasks for a flat $20 subscription [1, 2].
CORE INSIGHT: Claude Cowork provides a predictable cost model with no usage fees, unlike open-source or API-based agents that can consume 50,000 tokens in a single message [1, 3, 4].
TARGET: General
LEAD MAGNET: The AI Agent Cost Comparison Spreadsheet

HOOK: You are wasting 10 hours a week sitting at your desk waiting for AI outputs. 
I just summarized a 30-minute meeting into Notion from my phone while on the subway [5].
CORE INSIGHT: Dispatch allows your phone to act as a remote control for your desktop Claude session, executing high-power commands on your local Mac while you are physically away from your desk [5-7].
TARGET: Consulting
LEAD MAGNET: The "Subway to Office" Mobile Workflow Guide

HOOK: Cloud-based AI is a compliance liability for firms handling sensitive client data. 
Claude Dispatch keeps your files in a local desktop sandbox that never touches a third-party cloud [8, 9].
CORE INSIGHT: Unlike cloud orchestrators, Claude Cowork runs in a sandboxed virtual machine on your local hardware, keeping data local and requiring user approval before the AI touches files [8-10].
TARGET: PE
LEAD MAGNET: The Local AI Privacy & Compliance Checklist

HOOK: AI officially moved out of the browser tab and into your local hard drive on March 17th. 
You can now text your computer to find local files and fill complex forms from anywhere in the world [5, 7].
CORE INSIGHT: The shift to Dispatch expands the operational radius of AI from a simple browser window to the entire desktop infrastructure, allowing for cross-device independent work [5, 11].
TARGET: General
LEAD MAGNET: 12 Desktop Tasks You Can Now Dispatch from Your Phone

HOOK: 50% of document-heavy knowledge work can now be delegated via a mobile text message. 
I just ran a competitive research analysis on my office Mac while eating lunch three miles away [12, 13].
CORE INSIGHT: Claude Cowork specializes in document-centric tasks like reports, spreadsheets, and data analysis, and Dispatch allows these to be triggered remotely via a mobile chat [12-14].
TARGET: Wealth Mgmt
LEAD MAGNET: The Remote Document Automation Blueprint

---

## Sources

### YouTube (10 videos scraped)

| # | Title | Channel | Views | Duration | URL |
|---|---|---|---|---|---|
| 1 | Introducing Cowork: Claude Code for the rest of your work | Anthropic | 408,070 | 1:09 | https://www.youtube.com/watch?v=UAmKyyZ-b9E |
| 2 | Claude Code's New Agent Teams Are Insane (Opus 4.6) | Bart Slodyczka | 183,464 | 13:55 | https://www.youtube.com/watch?v=VWngYUC63po |
| 3 | Claude Code Multi-Agent Orchestration with Opus 4.6, Tmux an | IndyDevDan | 42,164 | 24:03 | https://www.youtube.com/watch?v=RpUTF_U4kiw |
| 4 | Build A WhatsApp Sales Agent with Claude Code (It's F***ING  | Folu ilori | Ai Automations | 13,644 | 22:45 | https://www.youtube.com/watch?v=KrVZnRqz428 |
| 5 | NEW Claude Dispatch Just Killed OpenClaw | Kevin Jeppesen - The Operator Vault | 4,649 | 13:06 | https://www.youtube.com/watch?v=tq4t62gO0i4 |
| 6 | Claude Cowork Dispatch, Minimax M2.7 + Google Stitch's INSAN | Julian Goldie SEO | 1,011 | 1:18:14 | https://www.youtube.com/watch?v=2lNzTe-p68I |
| 7 | Claude Cowork Dispatch Control Your PC From Your | KiS | 474 | 8:15 | https://www.youtube.com/watch?v=RKEtbKJQD9g |
| 8 | Claude Cowork Dispatch: Control Your Desktop AI From Your Ph | Engr Mejba Ahmed | 8 | 1:24 | https://www.youtube.com/watch?v=xLcnTEf7pPg |
| 9 | Claude Dispatch: เปลี่ยนมือถือเป็นรีโมทสั่ง AI สุดล้ำ (Anthr | สาระEveryDay | N/A | 6:31 | https://www.youtube.com/watch?v=Alh8Q_3iWWI |
| 10 | Dispatch  The Cross Device AI Leap | AI Application (paper summaries or stories) | N/A | 2:47 | https://www.youtube.com/watch?v=SOHa_7T10n8 |

### Web Sources

- https://x.com/felixrieseberg/status/2034005731457044577
- https://mlq.ai/news/anthropic-launches-claude-dispatch-for-remote-desktop-ai-control/
- https://www.macstories.net/stories/hands-on-with-claude-dispatch-for-cowork/
- https://petrvojacek.cz/en/blog/claude-cowork-dispatch/
- https://www.trysliq.com/blog/manus-vs-claude-cowork-vs-perplexity-computer

---

*Generated by research_pipeline.py on 2026-03-19*