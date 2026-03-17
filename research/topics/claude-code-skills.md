# Research: Claude Code Skills
**Date:** 2026-03-13  
**NotebookLM ID:** c7bde44b-3113-4945-b716-f43f0e1d47a6  

---

## NotebookLM Insights

## 1. SURPRISING STATS
*   **60,000+** published skills exist in the Claude Code ecosystem, yet the vast majority are considered "garbage," making curation the primary hurdle for developers [1].
*   **500+ zero-day vulnerabilities** were discovered in the Mozilla browser by Claude Opus 4.6, with **22** of those found in just **two weeks** [2].
*   **7,000+ IoT devices** (DJI vacuum robots) across 24 countries were accidentally made accessible to a single hobbyist using Claude Code to "hack" his own device [3, 4].
*   **30% reduction** in revision rounds is reported by practitioners who implement a "structured thinking phase" via the Ora superpower brainstorming skill before writing code [5].
*   **100,000+ installs** have been logged for Anthropic’s official "front-end design" skill, indicating a massive shift toward specialized UI/UX prompts over native model outputs [6].

## 2. THE THING EXPERTS GET WRONG
Experienced practitioners often assume that **more skills lead to better results.** In reality, "capability uplift" skills—those designed to fix a model's current weaknesses (like poor UI design)—can actually **degrade performance** or cause "skill drift" when the underlying model (e.g., a shift from Opus 4.6 to 5.0) improves [7, 8]. Experts fail to "pension off" skills that the base model has natively outgrown, leading to redundant processing and potential quality regression [7, 9, 10].

## 3. THE HIDDEN MECHANIC
The core mechanism for reliable automation is the **100-word skill description.** Claude Code does not "preload" every skill into its system prompt; instead, it scans a list of titles and short descriptions to decide what to trigger [11]. If the description is too broad, you get **false triggers**; if it is too narrow, the skill **never fires** [11]. Mastery of Claude Code is essentially a "balancing act" of threading the needle on these metadata descriptions [11].

## 4. WHAT ACTUALLY KILLS RESULTS
The most common outcome-killer is **"Vibe Coding" without an interrogation phase.** Most developers allow Claude to "charge ahead" and execute immediately, which results in "AI slop"—generic websites with white backgrounds and blue buttons that lack personality [5, 6, 12]. Results are also killed by becoming an **"accept monkey,"** where the user blindly hits "yes" to every Claude suggestion without using the **Skill Creator** to run AB tests and benchmarks to see what is actually happening "under the hood" [13, 14].

## 5. THE COUNTER-INTUITIVE MOVE
**Force the AI to interview you.** Instead of providing a massive prompt, practitioners should use a brainstorming skill to shift Claude into **"interrogation mode"** [5, 15]. This forces the agent to ask "hard questions" and surface considerations the human missed *before* a single line of code is written [5, 16]. It turns the relationship from a "command-and-control" dynamic into a collaborative design process [17].

## 6. EXACT STEP-BY-STEP: THE SKILL OPTIMIZATION LOOP
This is the process for transforming a "maybe-works" skill into a production-grade automation:
1.  **Install the Meta-Tools:** Run `/plugin` in the terminal and search for **`skill-creator`** to install the official Anthropic testing framework [18, 19].
2.  **Define the Logic:** Use `/skill-creator` to define whether the task is a **Capability Uplift** (new skill) or an **Encoded Preference** (specific workflow/recipe) [20-22].
3.  **Spawn Parallel Agents:** Have the Skill Creator launch **simultaneous agents** to run AB tests (one with the skill, one without/baseline) [10, 23, 24].
4.  **Analyze the Eval Report:** Review the `evals.json` output for three specific metrics: **Pass Rate**, **Token Consumption**, and **Execution Time** [9, 25, 26].
5.  **Refine Triggering:** If the skill works but doesn't fire, use the tool to **tune the 100-word description** for reliable triggering [11, 19].
6.  **Benchmark for Model Updates:** Whenever a new model (like Opus 5.0) is released, re-run the loop to see if the skill should be **"pensioned off"** because the base model now handles it natively [7-9].

## 7. INDUSTRY-SPECIFIC ANGLES
*   **Private Equity / Family Offices:** Utilize the **"Trail of Bits" skill** for technical due diligence. It performs professional-grade **vulnerability scanning**, malware analysis, and static analysis of target company codebases or smart contracts directly in the terminal [27, 28].
*   **Boutique Management Consulting:** Use a **multi-agent research pipeline** (chaining X, Reddit, and YouTube skills) to extract "pain points" from 50+ relevant community threads [29-31]. This allows consultants to use the target audience's **"own language"** back to them in strategy decks [30].
*   **Real Estate (Commercial/Development):** Deploy a **PDF Form-Filling skill** to automate the population of complex interactive lease documents and HR forms [26, 32, 33]. One agent can read the form fields and a second agent can accurately map data into the PDF, avoiding the alignment errors common in generic AI [32-34].
*   **Wealth Management / Financial Advisory:** Implement the **Obsidian skill** to build a node-based **interconnected knowledge base** of client history and market research [35, 36]. This allows the agent to automatically link research notes via wiki-links and callouts, ensuring no "disconnected" thoughts exist in a RAG system [35-37].

## 8. THE LEAD MAGNET HOOK
The single most valuable insight is that you can stop being an "accept monkey" by using **automated AB testing** to prove exactly when an AI skill is outperforming the base model—and more importantly, exactly when it's time to delete it [7, 9, 13].

---

## CONTENT HOOKS (Hormozi Style)

**HOOK:** 522 zero-day security flaws found in 14 days by one AI agent.  
**CORE INSIGHT:** Claude Code detected over 500 zero-day vulnerabilities—including 14 high-severity flaws—in the Mozilla browser within two weeks, proving it can identify severe security gaps with extreme speed [1].  
**TARGET:** Consulting  
**LEAD MAGNET:** AI Vulnerability Audit Checklist

**HOOK:** Revision rounds drop 30% the moment you force your AI into "interrogation mode" before letting it execute.  
**CORE INSIGHT:** Using the "Ora superpower" brainstorming skill inserts a structured thinking phase that forces Claude to ask hard questions and surface unconsidered variables before writing code [2].  
**TARGET:** PE  
**LEAD MAGNET:** The "Interrogation Mode" Prompt Sequence

**HOOK:** Most AI users are prompt monkeys while 1% use "encoded preference" skills to chain 6 tools into a single terminal command.  
**CORE INSIGHT:** Encoded preference skills allow you to systemize complex multi-step workflows—like YouTube research, NotebookLM analysis, and slide deck creation—into a single repeatable command [3, 4].  
**TARGET:** General  
**LEAD MAGNET:** Workflow Chain SOP

**HOOK:** 60,000 pre-built AI skills already exist to do your job and you can install them with a single line of terminal code.  
**CORE INSIGHT:** The "find skill" meta-skill allows users to search a massive ecosystem of over 60,000 published skills and install them globally without leaving the terminal [5, 6].  
**TARGET:** Wealth Mgmt  
**LEAD MAGNET:** Top 10 "Hidden" Finance Skills Directory

**HOOK:** Your custom AI skills are likely producing worse results than the base model after the latest update.  
**CORE INSIGHT:** "Capability uplift" skills can become redundant or even degrade performance as models (like Opus) improve, requiring AB benchmarking to determine if a skill should be retired [7-9].  
**TARGET:** Consulting  
**LEAD MAGNET:** Skill Benchmarking Framework (Evals)

---

## Sources

### YouTube (3 videos scraped)

| # | Title | Channel | Views | Duration | URL |
|---|---|---|---|---|---|
| 1 | Claude Code Skills Just Got a MASSIVE Upgrade | Chase AI | 94,300 | 12:19 | https://www.youtube.com/watch?v=UxfeF4bSBYI |
| 2 | Claude Code Skills 2.0: I try the new Skill Creator | Simone Rizzo | 8,586 | 24:06 | https://www.youtube.com/watch?v=nTEjL5h0wYs |
| 3 | 10 Hidden Claude Code Skills Most Developers Don't Know | Duncan Rogoff | AI Automation | 8,132 | 18:25 | https://www.youtube.com/watch?v=gm8Ci8X2mpo |

---

*Generated by research_pipeline.py on 2026-03-13*