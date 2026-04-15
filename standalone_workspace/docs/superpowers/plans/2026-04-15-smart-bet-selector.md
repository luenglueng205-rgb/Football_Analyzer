# 智能选票与价值投注推演引擎 (Smart Bet Selector) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补齐最后一块拼图。创建一个专门负责“打票决策”的模块。它不仅能计算所有玩法的理论概率，还能基于 Kelly 准则过滤掉负 EV (低赔率) 的垃圾玩法，并在合法的范围内（考虑同场互斥）智能拼装出当天 ROI 最高的串关组合。

**Architecture:**
- **`SmartBetSelector` 类**：接收多场比赛的 `all_markets` 数据。遍历竞彩、北单、传足的每一种玩法，计算 `EV = Prob * Odds`。
- **玩法隔离与推荐**：识别哪些比赛适合打胜平负，哪些因为进球数集中更适合打“总进球”，哪些因为让球赔率失衡适合打“北单让球”。
- **串关组装**：调用 `ParlayFilterMatrix`，将过滤出的正 EV 选项组合成最高回报的合法串关。

**Tech Stack:** Python 3.10+, `itertools`

---

### Task 1: 创建智能选票决策器 (Smart Bet Selector)

**Files:**
- Create: `standalone_workspace/tools/smart_bet_selector.py`
- Create: `standalone_workspace/tests/test_smart_bet_selector.py`

- [ ] **Step 1: Write the failing test**

```python
# standalone_workspace/tests/test_smart_bet_selector.py
import pytest
from tools.smart_bet_selector import SmartBetSelector

def test_select_best_value_bets():
    selector = SmartBetSelector()
    
    # 模拟两场比赛的全景玩法赔率和概率
    # 比赛1: 强弱悬殊，胜平负无价值，但让球和平局有极高价值
    match_1 = {
        "match_id": "M1",
        "home_team": "Man City",
        "markets": {
            "1x2": {"home": {"odds": 1.10, "prob": 0.85}, "draw": {"odds": 9.0, "prob": 0.10}}, # EV: home=0.935 (无价值), draw=0.9
            "handicap_-2": {"home": {"odds": 2.5, "prob": 0.45}} # EV = 1.125 (有价值)
        }
    }
    
    # 比赛2: 势均力敌，总进球小球有价值
    match_2 = {
        "match_id": "M2",
        "home_team": "Chelsea",
        "markets": {
            "1x2": {"home": {"odds": 2.5, "prob": 0.35}}, # EV = 0.875
            "total": {"under_2.5": {"odds": 1.9, "prob": 0.60}} # EV = 1.14 (有价值)
        }
    }
    
    recommendations = selector.extract_value_bets([match_1, match_2])
    
    # 期望系统能抛弃 M1 的胜平负，准确抓取 M1 的让球和 M2 的小球
    assert len(recommendations) == 2
    assert recommendations[0]["market"] == "handicap_-2"
    assert recommendations[1]["selection"] == "under_2.5"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest standalone_workspace/tests/test_smart_bet_selector.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Write minimal implementation**

```python
# standalone_workspace/tools/smart_bet_selector.py
from typing import List, Dict, Any

class SmartBetSelector:
    """
    智能选票器。负责遍历所有玩法，砍掉低赔陷阱，只保留期望值 (EV) > 1 的价值投注。
    """
    def __init__(self, min_ev_threshold: float = 1.05):
        # 设定最低期望值门槛，1.05 表示每投注 100 元，理论预期回报 105 元
        self.min_ev_threshold = min_ev_threshold

    def extract_value_bets(self, matches_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        value_bets = []
        
        for match in matches_data:
            match_id = match.get("match_id")
            markets = match.get("markets", {})
            
            # 遍历该场比赛的所有玩法和选项
            for market_name, options in markets.items():
                for selection, data in options.items():
                    odds = data.get("odds", 0.0)
                    prob = data.get("prob", 0.0)
                    
                    ev = odds * prob
                    
                    if ev >= self.min_ev_threshold:
                        value_bets.append({
                            "match_id": match_id,
                            "market": market_name,
                            "selection": selection,
                            "odds": odds,
                            "prob": round(prob, 4),
                            "ev": round(ev, 4),
                            "desc": f"[{match_id}] {market_name} - {selection} (赔率:{odds}, 胜率:{prob:.1%}, EV:{ev:.2f})"
                        })
                        
        # 按照 EV 从高到低排序，优先推荐最有价值的单子
        value_bets.sort(key=lambda x: x["ev"], reverse=True)
        return value_bets
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest standalone_workspace/tests/test_smart_bet_selector.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add standalone_workspace/tests/test_smart_bet_selector.py standalone_workspace/tools/smart_bet_selector.py
git commit -m "feat: implement SmartBetSelector to strictly filter negative EV traps and extract value bets"
```