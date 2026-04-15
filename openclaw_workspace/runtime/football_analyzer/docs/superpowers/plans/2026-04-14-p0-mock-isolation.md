# P0 - 2. Mock Strong Isolation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Explicitly mark `meta.mock=true` in tools that use mock data, and handle it gracefully without polluting decision making.

**Architecture:** We already added `meta: {"mock": mock_flag}` in `ensure_protocol`. We now need to verify that the mock tools actually return `meta.mock=true` (we did this for `scrape_beidan_sp`, `capture_and_analyze_trend`, `analyze_dark_intel`). 
Now we update `ai_native_core.py` prompt to instruct the LLM: "If a tool returns 'meta': {'mock': true}, you MUST treat this data as simulated/unreliable. Do NOT use it for heavy capital allocation."

**Tech Stack:** Python 3.

---

### Task 1: Update AI Native Core Prompt

**Files:**
- Modify: `agents/ai_native_core.py`

- [ ] **Step 1: Modify Prompt**

In `agents/ai_native_core.py`, inside the `system_prompt` or user instructions, add:
"【MOCK 数据隔离】：如果你调用的工具返回了 `\"meta\": {\"mock\": true}`，说明该数据为模拟/离线数据，不可信。你在最终决策时，必须对这类数据降权，或者直接拒绝基于该数据进行大额下注（仅输出观察不下注）。"

- [ ] **Step 2: Commit**
Run: `git commit -am "feat: enforce mock data isolation via LLM instructions"`
