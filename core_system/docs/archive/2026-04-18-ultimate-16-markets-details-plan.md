# Ultimate 16 Markets Detailed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Embed 100% official rules for Jingcai, Beidan, and Zucai into the AI's cognitive framework and quantitative engine, leaving no detail behind (Handicap Draw, Beidan 0.5 rules, Parlay Bucket Effect, Zucai EV).

**Architecture:** 
1. Rewrite `16_MARKETS_RULES.md` to include all deep details.
2. Update `market_deep_analyzer.py` to calculate EV for these specific edge cases (like Handicap Draw and Beidan W/L Parlay).
3. Hardcode the Parlay limits into the AI Prompt so it doesn't make illegal recommendations.

**Tech Stack:** Markdown, Python.

---

### Task 1: Rewrite 16 Markets Rules Knowledge Base

**Files:**
- Modify: `standalone_workspace/docs/16_MARKETS_RULES.md`

- [ ] **Step 1: Write the updated markdown**
Overwrite the file with the comprehensive rules derived from the recent search, including the Parlay limits, Beidan 0.5 exception, and Zucai strategies.

- [ ] **Step 2: Commit**
```bash
git add standalone_workspace/docs/16_MARKETS_RULES.md
git commit -m "docs: deeply overhaul 16_MARKETS_RULES with official constraints"
```

### Task 2: Upgrade Market Deep Analyzer Tool

**Files:**
- Modify: `standalone_workspace/tools/market_deep_analyzer.py`

- [ ] **Step 1: Modify the python implementation**
Update the `deep_evaluate_all_markets` function to include calculations for Handicap Draw (竞彩), W/L Parlay (胜负过关), and Zucai Ren9 filtering.

- [ ] **Step 2: Commit**
```bash
git add standalone_workspace/tools/market_deep_analyzer.py
git commit -m "feat(ai-native): upgrade market_deep_analyzer to calculate extreme edge cases"
```

### Task 3: Upgrade AI Core Prompt with Hard Constraints

**Files:**
- Modify: `standalone_workspace/agents/ai_native_core.py`

- [ ] **Step 1: Update the system prompt**
Inject the "Bucket Effect" and "Single Match Sales" rules directly into the AI's active memory prompt.

- [ ] **Step 2: Commit**
```bash
git add standalone_workspace/agents/ai_native_core.py
git commit -m "feat(ai-native): inject hard parlay constraints into AI core prompt"
```
