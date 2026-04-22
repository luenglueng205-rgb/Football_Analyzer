# Chinese Lottery Analytics Evolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement advanced mathematical analytics specifically tailored for Chinese lotteries (JINGCAI, BEIDAN) including Tail-Probability Poisson, Parlay Kelly, and Last-Leg Hedging.

**Architecture:** Create `standalone_workspace/skills/advanced_lottery_math.py` to hold these specialized calculations. It will include functions for mapping Poisson matrices to Jingcai's specific score buckets, calculating EV/Kelly for N-leg parlays, and calculating the exact hedge amounts for the final leg of a parlay.

**Tech Stack:** Python 3.10+, `scipy.stats`

---

### Task 1: Tail-Probability Poisson Mapper (Jingcai)

**Files:**
- Create: `standalone_workspace/skills/advanced_lottery_math.py`
- Test: `standalone_workspace/tests/test_advanced_math.py`

- [ ] **Step 1: Write the failing test**

```python
# standalone_workspace/tests/test_advanced_math.py
import pytest
from skills.advanced_lottery_math import map_poisson_to_jingcai_scores

def test_map_poisson_to_jingcai_scores():
    # Mock a 10x10 poisson matrix where probabilities are just dummy values
    matrix = [[0.01 for _ in range(10)] for _ in range(10)]
    # Make 5-0 (home win other) have a specific value
    matrix[5][0] = 0.05
    # Make 4-3 (home win other) have a specific value
    matrix[4][3] = 0.05
    
    result = map_poisson_to_jingcai_scores(matrix)
    
    assert "胜其他" in result
    assert "平其他" in result
    assert "负其他" in result
    assert result["1:0"] == 0.01
    assert result["胜其他"] >= 0.10 # 5-0 and 4-3 plus others
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest standalone_workspace/tests/test_advanced_math.py::test_map_poisson_to_jingcai_scores -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Write minimal implementation**

```python
# standalone_workspace/skills/advanced_lottery_math.py
from typing import List, Dict

def map_poisson_to_jingcai_scores(poisson_matrix: List[List[float]]) -> Dict[str, float]:
    """
    将 N x N 的泊松矩阵映射为竞彩官方的 31 个比分选项。
    包含长尾概率的折叠（胜其他、平其他、负其他）。
    """
    jingcai_scores = {
        "1:0": 0.0, "2:0": 0.0, "2:1": 0.0, "3:0": 0.0, "3:1": 0.0, "3:2": 0.0, "4:0": 0.0, "4:1": 0.0, "4:2": 0.0, "5:0": 0.0, "5:1": 0.0, "5:2": 0.0, "胜其他": 0.0,
        "0:0": 0.0, "1:1": 0.0, "2:2": 0.0, "3:3": 0.0, "平其他": 0.0,
        "0:1": 0.0, "0:2": 0.0, "1:2": 0.0, "0:3": 0.0, "1:3": 0.0, "2:3": 0.0, "0:4": 0.0, "1:4": 0.0, "2:4": 0.0, "0:5": 0.0, "1:5": 0.0, "2:5": 0.0, "负其他": 0.0
    }
    
    max_goals = len(poisson_matrix)
    for h in range(max_goals):
        for a in range(max_goals):
            prob = poisson_matrix[h][a]
            if prob == 0: continue
            
            score_str = f"{h}:{a}"
            if h > a:
                if score_str in jingcai_scores:
                    jingcai_scores[score_str] += prob
                else:
                    jingcai_scores["胜其他"] += prob
            elif h == a:
                if score_str in jingcai_scores:
                    jingcai_scores[score_str] += prob
                else:
                    jingcai_scores["平其他"] += prob
            else:
                if score_str in jingcai_scores:
                    jingcai_scores[score_str] += prob
                else:
                    jingcai_scores["负其他"] += prob
                    
    return jingcai_scores
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest standalone_workspace/tests/test_advanced_math.py::test_map_poisson_to_jingcai_scores -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add standalone_workspace/skills/advanced_lottery_math.py standalone_workspace/tests/test_advanced_math.py
git commit -m "feat(math): implement Poisson tail-probability mapping for Jingcai specific score buckets"
```

### Task 2: Parlay Kelly Calculator (M串N)

**Files:**
- Modify: `standalone_workspace/skills/advanced_lottery_math.py`
- Modify: `standalone_workspace/tests/test_advanced_math.py`

- [ ] **Step 1: Write the failing test**

```python
# standalone_workspace/tests/test_advanced_math.py
# Append:
from skills.advanced_lottery_math import calculate_parlay_kelly

def test_calculate_parlay_kelly():
    # 2-leg parlay: 
    # Leg 1: Prob 60%, Odds 1.8
    # Leg 2: Prob 50%, Odds 2.1
    legs = [{"prob": 0.6, "odds": 1.8}, {"prob": 0.5, "odds": 2.1}]
    
    result = calculate_parlay_kelly(legs)
    
    # Combined Prob = 0.3
    # Combined Odds = 3.78
    # EV = 0.3 * 3.78 - 1 = 1.134 - 1 = 0.134
    # Kelly = (p*b - q) / b where b = 2.78, p = 0.3, q = 0.7
    # Kelly = (0.3*2.78 - 0.7) / 2.78 = (0.834 - 0.7) / 2.78 = 0.134 / 2.78 = ~0.048
    
    assert "ev" in result
    assert "kelly_fraction" in result
    assert abs(result["ev"] - 0.134) < 0.001
    assert abs(result["kelly_fraction"] - 0.048) < 0.005
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest standalone_workspace/tests/test_advanced_math.py::test_calculate_parlay_kelly -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# standalone_workspace/skills/advanced_lottery_math.py
# Append:
def calculate_parlay_kelly(legs: List[Dict[str, float]], fraction: float = 0.25) -> Dict[str, float]:
    """
    计算 N 串 1 混合过关的期望值 (EV) 和凯利仓位。
    legs 格式: [{"prob": 0.6, "odds": 1.8}, ...]
    """
    if not legs:
        return {"ev": 0.0, "kelly_fraction": 0.0}
        
    combined_prob = 1.0
    combined_odds = 1.0
    
    for leg in legs:
        combined_prob *= leg["prob"]
        combined_odds *= leg["odds"]
        
    ev = (combined_prob * combined_odds) - 1.0
    
    if ev <= 0 or combined_odds <= 1.0:
        return {"ev": ev, "kelly_fraction": 0.0, "combined_odds": combined_odds, "combined_prob": combined_prob}
        
    b = combined_odds - 1.0 # Net odds
    p = combined_prob
    q = 1.0 - p
    
    full_kelly = (b * p - q) / b
    fractional_kelly = full_kelly * fraction
    
    # Cap at 10% for parlay safety
    fractional_kelly = min(max(fractional_kelly, 0.0), 0.10)
    
    return {
        "ev": ev,
        "kelly_fraction": full_kelly, # Return full, let caller scale
        "fractional_kelly": fractional_kelly,
        "combined_odds": combined_odds,
        "combined_prob": combined_prob
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest standalone_workspace/tests/test_advanced_math.py::test_calculate_parlay_kelly -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add standalone_workspace/skills/advanced_lottery_math.py standalone_workspace/tests/test_advanced_math.py
git commit -m "feat(math): implement N-leg Parlay EV and Kelly Criterion calculator for Jingcai"
```

### Task 3: Last-Leg Hedger (Jingcai)

**Files:**
- Modify: `standalone_workspace/skills/advanced_lottery_math.py`
- Modify: `standalone_workspace/tests/test_advanced_math.py`

- [ ] **Step 1: Write the failing test**

```python
# standalone_workspace/tests/test_advanced_math.py
# Append:
from skills.advanced_lottery_math import calculate_last_leg_hedge

def test_calculate_last_leg_hedge():
    # We have a 4-leg parlay ticket. 3 legs have won.
    # Original bet: 100 RMB. Potential payout: 1000 RMB.
    # Last leg is Team A vs Team B. Our parlay needs Team A to Win.
    # Current odds for Draw: 3.0, Away Win: 4.0
    
    result = calculate_last_leg_hedge(
        original_bet=100,
        potential_payout=1000,
        hedge_odds={"Draw": 3.0, "Away": 4.0}
    )
    
    # To guarantee equal profit across all outcomes:
    # Let x = bet on Draw, y = bet on Away
    # If Home wins: Profit = 1000 - 100 - x - y
    # If Draw wins: Profit = 3.0*x - 100 - x - y = 2.0*x - 100 - y
    # If Away wins: Profit = 4.0*y - 100 - x - y = 3.0*y - 100 - x
    # Equating them:
    # 1000 - x - y = 3.0x - x - y => 1000 = 3.0x => x = 333.33
    # 1000 - x - y = 4.0y - x - y => 1000 = 4.0y => y = 250
    # Total investment = 100 + 333.33 + 250 = 683.33
    # Guaranteed return = 1000. Profit = 316.67
    
    assert "hedge_bets" in result
    assert abs(result["hedge_bets"]["Draw"] - 333.33) < 0.1
    assert abs(result["hedge_bets"]["Away"] - 250.0) < 0.1
    assert abs(result["guaranteed_profit"] - 316.67) < 0.1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest standalone_workspace/tests/test_advanced_math.py::test_calculate_last_leg_hedge -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# standalone_workspace/skills/advanced_lottery_math.py
# Append:
def calculate_last_leg_hedge(original_bet: float, potential_payout: float, hedge_odds: Dict[str, float]) -> Dict[str, Any]:
    """
    计算竞彩串关“最后一关”的物理防守打水金额。
    目标是实现所有赛果的收益绝对均等（Arbitrage Lock）。
    
    :param original_bet: 原始投注本金 (如 100)
    :param potential_payout: 原始彩票的全红奖金 (如 1000)
    :param hedge_odds: 最后一关需要防守的其他选项赔率 (如 {"平": 3.0, "负": 4.0})
    """
    hedge_bets = {}
    total_hedge_cost = 0.0
    
    # 公式: 防守金额 = 预期总奖金 / 防守赔率
    for outcome, odds in hedge_odds.items():
        if odds <= 1.0:
            return {"error": "Invalid odds"}
        bet_amount = potential_payout / odds
        hedge_bets[outcome] = round(bet_amount, 2)
        total_hedge_cost += bet_amount
        
    total_investment = original_bet + total_hedge_cost
    guaranteed_profit = potential_payout - total_investment
    
    return {
        "hedge_bets": hedge_bets,
        "total_hedge_cost": round(total_hedge_cost, 2),
        "total_investment": round(total_investment, 2),
        "guaranteed_payout": potential_payout,
        "guaranteed_profit": round(guaranteed_profit, 2),
        "is_profitable": guaranteed_profit > 0
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest standalone_workspace/tests/test_advanced_math.py::test_calculate_last_leg_hedge -v`
Expected: PASS

- [ ] **Step 5: Sync to OpenClaw Workspace and Commit**

```bash
cp standalone_workspace/skills/advanced_lottery_math.py openclaw_workspace/runtime/football_analyzer/skills/
git add .
git commit -m "feat(math): implement Last-Leg Parlay Hedger for structural risk management in Chinese lotteries"
```
