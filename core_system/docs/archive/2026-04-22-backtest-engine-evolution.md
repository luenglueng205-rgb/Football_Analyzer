# 4-Core Lottery Backtest Engine Evolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the historical backtesting engine to automatically evaluate and settle the 4 core lottery types (WDL, GOALS, SXDS, Zucai) across 220,000 matches instead of just basic 1X2.

**Architecture:** Modify `run_blind_backtest.py` to use `LotteryMathEngine.calculate_all_markets()` and `SettlementEngine.determine_all_play_types_results()`. Update `historical_database.py` to extract `ht_score` for accurate HT/FT and SXDS analysis if needed.

**Tech Stack:** Python 3.10+

---

### Task 1: Enhance Historical Data Extraction

**Files:**
- Modify: `standalone_workspace/data/historical_database.py`

- [ ] **Step 1: Write the failing test**

```python
# standalone_workspace/tests/test_historical_extraction.py
import pytest
from data.historical_database import HistoricalDatabase

def test_extract_ht_scores():
    db = HistoricalDatabase(lazy_load=False) # Load minimal sample if possible, or mock
    
    # We will test that a match record returned by db has ht_home_score and ht_away_score
    matches = db.raw_data().get("data", [])
    if matches:
        match = matches[0]
        # Should now extract HT scores from raw JSON if they exist
        assert "ht_home_score" in match or "ht_score" in match
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest standalone_workspace/tests/test_historical_extraction.py -v`
Expected: FAIL or PASS depending on if `ht_score` already exists in raw dict. (Since `raw_data` returns the raw JSON, it might exist, but the `get_team_stats` method needs to use it).

- [ ] **Step 3: Write implementation**

Modify `standalone_workspace/data/historical_database.py`:
In `get_team_stats` or `_calculate_all_league_stats`, ensure we extract `ht_score` if available for future modeling.

```python
    # In _calculate_all_league_stats
    # ... existing ...
    ht_score = match.get("ht_score", "0-0")
    try:
        ht_home, ht_away = map(int, ht_score.split("-"))
    except ValueError:
        ht_home, ht_away = 0, 0
    # ... existing ...
```
*(Note: Since `historical_database.py` just loads the JSON, and `run_blind_backtest.py` uses the raw match dict, we mainly need to ensure `run_blind_backtest.py` parses `ht_score` correctly.)*

### Task 2: Integrate 4-Core Market EV Scanner into Backtest

**Files:**
- Modify: `standalone_workspace/tests/run_blind_backtest.py`

- [ ] **Step 1: Refactor `run_blind_backtest.py` EV Scanning**

We will update the `main()` function in `run_blind_backtest.py` to calculate probabilities for all 4 core markets (WDL, GOALS, SXDS) and find the best EV. Since historical data only has WDL odds (`odds_h`, `odds_d`, `odds_a`), we will simulate odds for GOALS and SXDS based on standard market vig (e.g., 1 / prob * 0.89).

```python
# Modify standalone_workspace/tests/run_blind_backtest.py
# In the `for i in range(10):` loop:

        # 1. 赛前数据收集
        match = db.get_random_match()
        # ... existing ...
        
        # 3. 核心数学推演 (使用全景概率引擎)
        engine = LotteryMathEngine(mu_home=mu_home, mu_away=mu_away)
        all_markets = engine.calculate_all_markets()
        
        # We now have WDL, GOALS, and we can calculate SXDS
        from core_system.tools.math.advanced_lottery_math import calculate_beidan_sxds_matrix
        sxds_probs = calculate_beidan_sxds_matrix(engine.matrix)
        
        # 4. EV 扫描 (WDL 真实赔率 + GOALS/SXDS 模拟赔率)
        best_bet = None
        highest_ev = -1.0
        
        # WDL
        prob_h, prob_d, prob_a = all_markets["WDL"]["胜"], all_markets["WDL"]["平"], all_markets["WDL"]["负"]
        ev_h = evaluate_betting_value(prob_h, odds_h).get("ev", -1)
        ev_d = evaluate_betting_value(prob_d, odds_d).get("ev", -1)
        ev_a = evaluate_betting_value(prob_a, odds_a).get("ev", -1)
        
        for ev, outcome, odds, prob in [(ev_h, "主胜", odds_h, prob_h), (ev_d, "平局", odds_d, prob_d), (ev_a, "客胜", odds_a, prob_a)]:
            if ev > highest_ev and ev > 0.05:
                highest_ev = ev
                best_bet = {"market": "WDL", "outcome": outcome, "odds": odds, "ev": ev, "prob": prob}
                
        # Simulated GOALS & SXDS EV (assuming standard 89% return rate odds)
        for goal, prob in all_markets["GOALS"].items():
            if prob > 0.1:
                sim_odds = 0.89 / prob
                ev = (prob * sim_odds) - 1
                if ev > highest_ev and ev > 0.05:
                    highest_ev = ev
                    best_bet = {"market": "GOALS", "outcome": f"{goal}球", "odds": round(sim_odds, 2), "ev": ev, "prob": prob}
                    
        for sxds, prob in sxds_probs.items():
            if prob > 0.1:
                sim_odds = 0.65 / prob # Beidan 65% return rate
                ev = (prob * sim_odds) - 1
                if ev > highest_ev and ev > 0.05:
                    highest_ev = ev
                    best_bet = {"market": "SXDS", "outcome": sxds, "odds": round(sim_odds, 2), "ev": ev, "prob": prob}
```

- [ ] **Step 2: Commit**

```bash
git add standalone_workspace/tests/run_blind_backtest.py
git commit -m "feat(backtest): expand historical scanner to evaluate EV across WDL, GOALS, and Beidan SXDS markets"
```

### Task 3: Integrate Settlement Engine

**Files:**
- Modify: `standalone_workspace/tests/run_blind_backtest.py`

- [ ] **Step 1: Refactor `run_blind_backtest.py` Settlement**

```python
# Modify standalone_workspace/tests/run_blind_backtest.py
# Under `# 5. 揭晓真实赛果并结算`

        actual_h = match.get('home_score', 0)
        actual_a = match.get('away_score', 0)
        actual_score = f"{actual_h}-{actual_a}"
        
        # Use the real Settlement Engine
        from tests.test_destructive_math import SettlementEngine
        settlement = SettlementEngine.determine_all_play_types_results(actual_score, "0-0", {})
        
        print(f"    真实的 16 维赛果映射: {settlement}")
        
        if best_bet:
            is_win = False
            if best_bet["market"] == "WDL":
                actual_res = "主胜" if actual_h > actual_a else "平局" if actual_h == actual_a else "客胜"
                is_win = (best_bet["outcome"] == actual_res)
            elif best_bet["market"] == "GOALS":
                total_goals = actual_h + actual_a
                goal_str = f"{total_goals}" if total_goals < 7 else "7+"
                is_win = (best_bet["outcome"] == f"{goal_str}球")
            elif best_bet["market"] == "SXDS":
                is_win = (best_bet["outcome"] == settlement.get("UP_DOWN_ODD_EVEN"))
                
            if is_win:
                print(f"    ✅ 盲测命中！[{best_bet['market']}] {best_bet['outcome']} (赔率: {best_bet['odds']})")
                pnl += best_bet['odds'] - 1
            else:
                print(f"    ❌ 盲测失败。投注: [{best_bet['market']}] {best_bet['outcome']}, 真实: {actual_h}-{actual_a}")
                pnl -= 1
        else:
            print(f"    ⏩ 放弃投注 (最高 EV < 0.05)")
```

- [ ] **Step 2: Commit**

```bash
git add standalone_workspace/tests/run_blind_backtest.py
git commit -m "feat(backtest): integrate 16-dimensional Settlement Engine into blind backtest loop"
```
