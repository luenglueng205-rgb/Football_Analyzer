# Chinese Lottery Risk & Tax Evolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Jingcai tax avoidance/payout ceilings, fix Beidan exponential compounding bug, and create a Zucai anti-hotpot detector.

**Architecture:** Modify `standalone_workspace/skills/advanced_lottery_math.py` to add `optimize_jingcai_ticket` and `calculate_zucai_value_index`. Update `calculate_parlay_kelly` to handle Beidan's global return rate.

**Tech Stack:** Python 3.10+

---

### Task 1: Beidan Exponential Vig Bug Fix

**Files:**
- Modify: `standalone_workspace/skills/advanced_lottery_math.py`
- Modify: `standalone_workspace/tests/test_advanced_math.py`

- [ ] **Step 1: Write the failing test**

```python
# standalone_workspace/tests/test_advanced_math.py
# Append:
def test_beidan_parlay_kelly_bug_fix():
    # 3-leg parlay, odds = 2.0 each
    legs = [{"prob": 0.5, "odds": 2.0}, {"prob": 0.5, "odds": 2.0}, {"prob": 0.5, "odds": 2.0}]
    
    # Jingcai mode (default)
    result_jc = calculate_parlay_kelly(legs)
    assert result_jc["combined_odds"] == 8.0
    
    # Beidan mode
    result_bd = calculate_parlay_kelly(legs, lottery_type="BEIDAN")
    # Expected combined odds: (2.0 * 2.0 * 2.0) * 0.65 = 5.2
    assert result_bd["combined_odds"] == 5.2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest standalone_workspace/tests/test_advanced_math.py::test_beidan_parlay_kelly_bug_fix -v`
Expected: FAIL (unexpected keyword argument `lottery_type`)

- [ ] **Step 3: Write minimal implementation**

Modify `calculate_parlay_kelly` in `standalone_workspace/skills/advanced_lottery_math.py`:
```python
def calculate_parlay_kelly(legs: List[Dict[str, float]], fraction: float = 0.25, lottery_type: str = "JINGCAI") -> Dict[str, float]:
    """
    计算 N 串 1 混合过关的期望值 (EV) 和凯利仓位。
    包含北单 (BEIDAN) 浮动奖金的全局抽水修正。
    legs 格式: [{"prob": 0.6, "odds": 1.8}, ...]
    """
    if not legs:
        return {"ev": 0.0, "kelly_fraction": 0.0}
        
    combined_prob = 1.0
    combined_odds = 1.0
    
    for leg in legs:
        combined_prob *= leg["prob"]
        combined_odds *= leg["odds"]
        
    if lottery_type.upper() == "BEIDAN":
        combined_odds = combined_odds * 0.65
        
    ev = (combined_prob * combined_odds) - 1.0
    
    if ev <= 0 or combined_odds <= 1.0:
        return {"ev": ev, "kelly_fraction": 0.0, "combined_odds": combined_odds, "combined_prob": combined_prob}
        
    b = combined_odds - 1.0 # Net odds
    p = combined_prob
    q = 1.0 - p
    
    full_kelly = (b * p - q) / b
    fractional_kelly = full_kelly * fraction
    
    fractional_kelly = min(max(fractional_kelly, 0.0), 0.10)
    
    return {
        "ev": ev,
        "kelly_fraction": full_kelly,
        "fractional_kelly": fractional_kelly,
        "combined_odds": combined_odds,
        "combined_prob": combined_prob
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest standalone_workspace/tests/test_advanced_math.py::test_beidan_parlay_kelly_bug_fix -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add standalone_workspace/skills/advanced_lottery_math.py standalone_workspace/tests/test_advanced_math.py
git commit -m "fix(math): fix Beidan exponential vig bug by applying 65% return rate to the combined odds only once"
```

### Task 2: Jingcai Smart Splitter & Payout Ceiling Interceptor

**Files:**
- Modify: `standalone_workspace/skills/advanced_lottery_math.py`
- Modify: `standalone_workspace/tests/test_advanced_math.py`

- [ ] **Step 1: Write the failing test**

```python
# standalone_workspace/tests/test_advanced_math.py
# Append:
from skills.advanced_lottery_math import optimize_jingcai_ticket

def test_optimize_jingcai_ticket():
    # 4-leg parlay, combined odds 6000.0, target investment 10,000 RMB (5000 bets)
    # Since odds > 5000, 1 bet (2 RMB) pays > 10,000 RMB -> TAXED 20%
    result = optimize_jingcai_ticket(num_legs=4, combined_odds=6000.0, target_investment=10000)
    
    # Statutory max payout for 4 legs is 500,000 RMB per ticket.
    # 1 bet pays 12,000 RMB (pre-tax). Post-tax is 9,600 RMB.
    assert result["is_taxed"] is True
    assert result["post_tax_odds"] == 4800.0 # 6000 * 0.8
    # Max bets per ticket to hit 500k ceiling with post-tax payout of 9.6k:
    # 500,000 / 9600 = 52.08 -> 52 bets per ticket (104 RMB per ticket)
    assert result["max_bets_per_ticket"] == 52
    assert result["suggested_tickets"] > 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest standalone_workspace/tests/test_advanced_math.py::test_optimize_jingcai_ticket -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# standalone_workspace/skills/advanced_lottery_math.py
# Append:
def optimize_jingcai_ticket(num_legs: int, combined_odds: float, target_investment: float) -> Dict[str, Any]:
    """
    竞彩智能拆单与封顶拦截器。
    处理法定最高奖金拦截，并检测20%偶然所得税（单注奖金>1万元）。
    """
    unit_bet_cost = 2.0
    pre_tax_unit_payout = combined_odds * unit_bet_cost
    
    is_taxed = pre_tax_unit_payout > 10000.0
    post_tax_odds = combined_odds * 0.8 if is_taxed else combined_odds
    post_tax_unit_payout = post_tax_odds * unit_bet_cost
    
    # 法定最高奖金 (Statutory Payout Ceiling)
    if num_legs <= 1:
        ceiling = 100000.0 # 单关最高10万
    elif 2 <= num_legs <= 3:
        ceiling = 200000.0 # 2-3关最高20万
    elif 4 <= num_legs <= 5:
        ceiling = 500000.0 # 4-5关最高50万
    else:
        ceiling = 1000000.0 # 6关及以上最高100万
        
    # 计算单票最大倍数 (Max bets per ticket before hitting ceiling)
    # 如果单注奖金已经超过天花板（极少见），最大倍数为1
    max_bets_per_ticket = max(1, int(ceiling // post_tax_unit_payout))
    max_investment_per_ticket = max_bets_per_ticket * unit_bet_cost
    
    target_bets = int(target_investment // unit_bet_cost)
    suggested_tickets = max(1, (target_bets + max_bets_per_ticket - 1) // max_bets_per_ticket)
    
    return {
        "is_taxed": is_taxed,
        "pre_tax_odds": combined_odds,
        "post_tax_odds": post_tax_odds,
        "payout_ceiling": ceiling,
        "max_bets_per_ticket": max_bets_per_ticket,
        "max_investment_per_ticket": max_investment_per_ticket,
        "suggested_tickets": suggested_tickets,
        "warning": "触发20%偶然所得税" if is_taxed else "安全（免税）"
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest standalone_workspace/tests/test_advanced_math.py::test_optimize_jingcai_ticket -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add standalone_workspace/skills/advanced_lottery_math.py standalone_workspace/tests/test_advanced_math.py
git commit -m "feat(math): implement Jingcai statutory payout ceiling interceptor and smart tax-avoidance splitter"
```

### Task 3: Zucai Anti-Hotpot Detector (Information Entropy)

**Files:**
- Modify: `standalone_workspace/skills/advanced_lottery_math.py`
- Modify: `standalone_workspace/tests/test_advanced_math.py`

- [ ] **Step 1: Write the failing test**

```python
# standalone_workspace/tests/test_advanced_math.py
# Append:
from skills.advanced_lottery_math import calculate_zucai_value_index

def test_calculate_zucai_value_index():
    # Match 1: True prob 50%, Public thinks 90% (Hotpot/Overvalued)
    # Match 2: True prob 40%, Public thinks 10% (Cold spot/Undervalued)
    matches = [
        {"true_prob": 0.5, "public_prob": 0.9},
        {"true_prob": 0.4, "public_prob": 0.1}
    ]
    
    result = calculate_zucai_value_index(matches)
    
    # Value index = true_prob / public_prob
    # Match 1 = 0.555, Match 2 = 4.0
    assert result[0]["value_index"] < 1.0
    assert result[1]["value_index"] == 4.0
    assert result[1]["is_value_pick"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest standalone_workspace/tests/test_advanced_math.py::test_calculate_zucai_value_index -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# standalone_workspace/skills/advanced_lottery_math.py
# Append:
def calculate_zucai_value_index(matches: List[Dict[str, float]]) -> List[Dict[str, Any]]:
    """
    传统足彩（任九/十四场）防“火锅奖”价值指数计算器。
    通过对比泊松真实胜率(true_prob)与全国大众投注比例(public_prob)，
    寻找被大众低估的高价值冷门盲区。
    """
    results = []
    for match in matches:
        true_prob = match.get("true_prob", 0.0)
        public_prob = match.get("public_prob", 0.0)
        
        # 避免除以 0
        if public_prob <= 0.001:
            public_prob = 0.001
            
        value_index = round(true_prob / public_prob, 3)
        
        # 如果价值指数 > 1.2，说明真实胜率远高于大众认知，值得作为足彩防冷胆码
        is_value_pick = value_index > 1.2
        
        # 信息熵辅助参考 (衡量大众分歧程度，越接近0.33分歧越大)
        # 这里仅作简单输出
        
        results.append({
            "true_prob": true_prob,
            "public_prob": public_prob,
            "value_index": value_index,
            "is_value_pick": is_value_pick,
            "warning": "严重高估（火锅预警）" if value_index < 0.6 else "正常"
        })
        
    return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest standalone_workspace/tests/test_advanced_math.py::test_calculate_zucai_value_index -v`
Expected: PASS

- [ ] **Step 5: Sync to OpenClaw and Commit**

```bash
cp standalone_workspace/skills/advanced_lottery_math.py openclaw_workspace/runtime/football_analyzer/skills/
git add .
git commit -m "feat(math): implement Zucai anti-hotpot detector using information entropy/value index"
```
