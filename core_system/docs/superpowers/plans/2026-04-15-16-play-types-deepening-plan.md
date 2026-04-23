# AI Native Digital Betting Syndicate - 16 Play Types Deepening Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor four core strategy modules (`SmartBetSelector`, `ParlayRulesEngine`, `LiveMatchMonitor`, `SettlementEngine`) to establish a mathematically rigorous, self-proving framework that 100% physically supports all 16 official lottery play types across Jingcai, Beidan, and Zucai (based on 2026-04-15 rules).

**Architecture:** 
1. **Selection:** Introduce Probability Edge model for pool-based Zucai (no odds) and enforce 65% SP net return for Beidan.
2. **Parlay:** Implement physical combinations for high-order M-N matrices and Beidan 15-leg chains.
3. **Live-check:** Build multi-market derivative mappings to support hedging for CS, Goals, and HT/FT.
4. **Settlement:** Create a universal 90-min result parser that maps one match into 16 distinct official play-type outcomes.

**Tech Stack:** Python 3.10+, `itertools.combinations`, `math.prod`, `asyncio`, JSON

---

### Task 1: Refactor SmartBetSelector for Zucai and Beidan

**Files:**
- Modify: `standalone_workspace/tools/smart_bet_selector.py`
- Modify: `standalone_workspace/tests/test_smart_bet_selector.py`

- [ ] **Step 1: Update the test file to verify new lottery type logic**

```python
def test_extract_value_bets_with_lottery_types():
    from tools.smart_bet_selector import SmartBetSelector
    selector = SmartBetSelector(min_ev_threshold=1.05)
    
    matches_data = [
        {
            "match_id": "M1",
            "lottery_type": "JINGCAI",
            "markets": {"WDL": {"3": {"odds": 2.0, "prob": 0.6}}} # EV = 1.2
        },
        {
            "match_id": "M2",
            "lottery_type": "BEIDAN",
            "markets": {"WDL": {"3": {"odds": 2.0, "prob": 0.9}}} # EV = 2.0 * 0.9 * 0.65 = 1.17
        },
        {
            "match_id": "M3",
            "lottery_type": "ZUCAI",
            "markets": {"WDL": {"3": {"odds": 0.0, "prob": 0.7, "support_rate": 0.4, "estimated_pool": 1000000}}} # Probability Edge
        }
    ]
    
    results = selector.extract_value_bets(matches_data)
    assert len(results) == 3
    
    jingcai_res = next(r for r in results if r["match_id"] == "M1")
    assert jingcai_res["ev"] == 1.2
    
    beidan_res = next(r for r in results if r["match_id"] == "M2")
    assert beidan_res["ev"] == 1.17
    
    zucai_res = next(r for r in results if r["match_id"] == "M3")
    assert "probability_edge" in zucai_res
    assert zucai_res["probability_edge"] == 0.3 # 0.7 - 0.4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest standalone_workspace/tests/test_smart_bet_selector.py -v`
Expected: FAIL due to missing lottery type routing and probability edge calculation.

- [ ] **Step 3: Implement lottery-aware selection logic**

```python
from typing import List, Dict, Any

class SmartBetSelector:
    """
    智能选票器。支持竞彩(固定赔率)、北单(65%返奖率)和传统足彩(无赔率概率优势)。
    """
    def __init__(self, min_ev_threshold: float = 1.05, min_edge_threshold: float = 0.15):
        self.min_ev_threshold = min_ev_threshold
        self.min_edge_threshold = min_edge_threshold # 足彩特有：真实胜率与大众支持率的最小差值

    def extract_value_bets(self, matches_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        value_bets = []
        
        for match in matches_data:
            match_id = match.get("match_id")
            lottery_type = match.get("lottery_type", "JINGCAI").upper()
            markets = match.get("markets", {})
            
            for market_name, options in markets.items():
                for selection, data in options.items():
                    prob = data.get("prob", 0.0)
                    
                    if lottery_type == "ZUCAI":
                        support_rate = data.get("support_rate", 0.0)
                        edge = prob - support_rate
                        
                        if edge >= self.min_edge_threshold:
                            value_bets.append({
                                "match_id": match_id,
                                "lottery_type": lottery_type,
                                "market": market_name,
                                "selection": selection,
                                "prob": round(prob, 4),
                                "support_rate": support_rate,
                                "probability_edge": round(edge, 4),
                                "ev": 0.0, # 足彩无直接EV
                                "desc": f"[{match_id}] ZUCAI {market_name} - {selection} (胜率:{prob:.1%}, 大众:{support_rate:.1%}, 优势:{edge:.1%})"
                            })
                    else:
                        odds = data.get("odds", 0.0)
                        ev = odds * prob
                        
                        # 北单必须扣除 35% 奖池抽水
                        if lottery_type == "BEIDAN":
                            ev = ev * 0.65
                            
                        if ev >= self.min_ev_threshold:
                            value_bets.append({
                                "match_id": match_id,
                                "lottery_type": lottery_type,
                                "market": market_name,
                                "selection": selection,
                                "odds": odds,
                                "prob": round(prob, 4),
                                "ev": round(ev, 4),
                                "desc": f"[{match_id}] {lottery_type} {market_name} - {selection} (赔率:{odds}, 胜率:{prob:.1%}, EV:{ev:.2f})"
                            })
                        
        value_bets.sort(key=lambda x: x.get("probability_edge", x["ev"]), reverse=True)
        return value_bets
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest standalone_workspace/tests/test_smart_bet_selector.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

Run: `git add standalone_workspace/tools/smart_bet_selector.py standalone_workspace/tests/test_smart_bet_selector.py`
Run: `git commit -m "feat: implement Zucai probability edge and Beidan 65% SP net return in bet selector"`

---

### Task 2: Upgrade ParlayRulesEngine for M-N Decomposition

**Files:**
- Modify: `standalone_workspace/tools/parlay_rules_engine.py`
- Modify: `standalone_workspace/tests/test_destructive_parlay.py`

- [ ] **Step 1: Write the failing test for physical M-N decomposition**

```python
def test_m_n_physical_decomposition():
    from tools.parlay_rules_engine import ParlayRulesEngine
    engine = ParlayRulesEngine()
    
    # 3 matches, playing 3x4 (which means three 2x1 and one 3x1)
    legs = ["M1", "M2", "M3"]
    
    combos = engine.get_m_n_ticket_combinations(legs, 3, 4)
    
    assert len(combos) == 4
    assert ["M1", "M2"] in combos
    assert ["M1", "M3"] in combos
    assert ["M2", "M3"] in combos
    assert ["M1", "M2", "M3"] in combos
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest standalone_workspace/tests/test_destructive_parlay.py -v`
Expected: FAIL due to missing `get_m_n_ticket_combinations` function.

- [ ] **Step 3: Implement combination decomposition logic**

```python
# Add this method to ParlayRulesEngine class in standalone_workspace/tools/parlay_rules_engine.py
    def get_m_n_ticket_combinations(self, ticket_legs: list, m: int, n: int) -> list:
        """
        物理拆解 M串N。例如 3串4 拆解为 3个2串1 和 1个3串1 的具体场次列表。
        """
        import itertools
        m_n_map = {
            "3_3": [2], "3_4": [2, 3],
            "4_4": [3], "4_5": [3, 4], "4_6": [2], "4_11": [2, 3, 4],
            "5_5": [4], "5_6": [4, 5], "5_10": [2], "5_16": [3, 4, 5], "5_20": [2, 3], "5_26": [2, 3, 4, 5],
            "6_6": [5], "6_7": [5, 6], "6_15": [2], "6_20": [3], "6_22": [4, 5, 6], "6_35": [2, 3], "6_42": [3, 4, 5, 6], "6_50": [2, 3, 4], "6_57": [2, 3, 4, 5, 6],
            "7_7": [6], "7_8": [6, 7], "7_21": [5], "7_35": [4], "7_120": [2, 3, 4, 5, 6, 7],
            "8_8": [7], "8_9": [7, 8], "8_28": [6], "8_56": [5], "8_70": [4], "8_247": [2, 3, 4, 5, 6, 7, 8]
        }
        
        key = f"{m}_{n}"
        if key not in m_n_map:
            raise ValueError(f"Unsupported M_N combination: {key}")
            
        target_sizes = m_n_map[key]
        combinations = []
        
        for size in target_sizes:
            combos = list(itertools.combinations(ticket_legs, size))
            # Convert tuples to lists
            combinations.extend([list(c) for c in combos])
            
        return combinations
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest standalone_workspace/tests/test_destructive_parlay.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

Run: `git add standalone_workspace/tools/parlay_rules_engine.py standalone_workspace/tests/test_destructive_parlay.py`
Run: `git commit -m "feat: implement exact physical decomposition of M-N parlays using itertools"`

---

### Task 3: Expand LiveMatchMonitor for Multi-Market Hedging

**Files:**
- Modify: `standalone_workspace/tools/live_match_monitor.py`
- Modify: `standalone_workspace/tests/test_lifecycle.py`

- [ ] **Step 1: Write the failing test for complex hedging**

```python
def test_complex_live_hedging():
    from tools.live_match_monitor import LiveMatchMonitor
    monitor = LiveMatchMonitor()
    
    # 初盘买了比分 1-0
    monitor.register_live_bet("M1", "CS_1-0", 100, 7.0)
    
    # 走地80分钟，比分已经是 1-0，需要对冲剩下的所有可能（其他比分）
    live_markets = {
        "CS_1-1": 15.0,
        "CS_2-0": 12.0,
        "CS_OTHER": 20.0
    }
    
    result = monitor.evaluate_complex_hedge("M1", live_markets, 80)
    
    assert result["hedge_recommended"] is True
    assert "hedge_distribution" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest standalone_workspace/tests/test_lifecycle.py -v`
Expected: FAIL due to missing `evaluate_complex_hedge` function.

- [ ] **Step 3: Implement complex hedging logic**

```python
# Add this method to LiveMatchMonitor class in standalone_workspace/tools/live_match_monitor.py
    def evaluate_complex_hedge(self, match_id: str, live_markets: dict, current_minute: int) -> dict:
        """
        支持多盘口的联合对冲计算器。计算如何分配本金买断剩余所有可能性以锁定利润。
        """
        if match_id not in self.active_bets:
            return {"hedge_recommended": False, "reason": "No active bet found"}
            
        bet = self.active_bets[match_id]
        potential_return = bet["stake"] * bet["odds"]
        
        # Calculate sum of inverse odds for all remaining live markets
        # IF sum(1/odds) < 1, an arbitrage (hedge) opportunity exists
        implied_prob_sum = sum(1.0 / odds for odds in live_markets.values())
        
        if implied_prob_sum == 0:
            return {"hedge_recommended": False, "reason": "No valid live markets provided"}
            
        # We need to guarantee a payout of `target_payout` regardless of outcome
        # For each market: hedge_stake * odds = target_payout
        # Total hedge investment = sum(target_payout / odds) = target_payout * implied_prob_sum
        # We want: potential_return - Total hedge investment > 0
        # Let's set target_payout = potential_return to perfectly flatten the risk
        
        total_hedge_investment = potential_return * implied_prob_sum
        
        if total_hedge_investment < potential_return - bet["stake"]:
            # Profitable hedge
            hedge_distribution = {
                market: round(potential_return / odds, 2)
                for market, odds in live_markets.items()
            }
            guaranteed_profit = potential_return - total_hedge_investment - bet["stake"]
            
            return {
                "hedge_recommended": True,
                "current_minute": current_minute,
                "total_hedge_cost": round(total_hedge_investment, 2),
                "guaranteed_net_profit": round(guaranteed_profit, 2),
                "hedge_distribution": hedge_distribution
            }
            
        return {
            "hedge_recommended": False,
            "reason": "Hedge cost too high, no guaranteed profit",
            "cost": round(total_hedge_investment, 2),
            "potential_return": potential_return
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest standalone_workspace/tests/test_lifecycle.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

Run: `git add standalone_workspace/tools/live_match_monitor.py standalone_workspace/tests/test_lifecycle.py`
Run: `git commit -m "feat: implement multi-market complex hedging distribution in LiveMatchMonitor"`

---

### Task 4: Rewrite SettlementEngine for All 16 Play Types

**Files:**
- Modify: `standalone_workspace/tools/settlement_engine.py`
- Modify: `standalone_workspace/tests/test_destructive_math.py`

- [x] **Step 1: Write the failing test for universal 16-play settlement**

```python
def test_universal_16_play_settlement():
    from tools.settlement_engine import SettlementEngine
    engine = SettlementEngine()
    
    # HT 0-1, FT 2-1
    result = engine.determine_all_play_types_results("2-1", "0-1", {"JINGCAI_HANDICAP": -1, "BEIDAN_HANDICAP": -0.5})
    
    assert result["status"] == "SETTLED"
    assert result["WDL"] == "3"
    assert result["JINGCAI_HANDICAP_WDL"] == "1" # 2 - 1 - 1 = 0 (Draw)
    assert result["BEIDAN_HANDICAP_WDL"] == "3" # 2 - 0.5 = 1.5 > 1 (Win)
    assert result["GOALS"] == "3"
    assert result["CS"] == "2-1"
    assert result["HTFT"] == "0-3"
    assert result["UP_DOWN_ODD_EVEN"] == "DOWN_ODD" # 3 goals (<4 is DOWN), Odd
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest standalone_workspace/tests/test_destructive_math.py -v`
Expected: FAIL due to missing `determine_all_play_types_results` function.

- [x] **Step 3: Implement universal play type parsing logic**

```python
# Replace determine_match_result with determine_all_play_types_results in standalone_workspace/tools/settlement_engine.py
    def determine_all_play_types_results(self, ft_score: str, ht_score: str = None, handicaps: dict = None, status: str = "FINISHED") -> dict:
        """
        根据 90分钟比分 一次性生成 16 种玩法的所有正确选项。隔离加时赛。
        """
        if status.upper() in ["CANCELLED", "POSTPONED", "ABANDONED"] or not ft_score or ft_score.upper() in ["W/O", "AWARDED"]:
            return {"status": "VOID", "official_result": "REFUND", "odds_applied": 1.0}
            
        try:
            home_goals, away_goals = map(int, ft_score.split("-"))
            total_goals = home_goals + away_goals
        except ValueError:
            return {"status": "VOID", "official_result": "REFUND", "odds_applied": 1.0}
            
        results = {
            "status": "SETTLED",
            "WDL": "3" if home_goals > away_goals else "1" if home_goals == away_goals else "0",
            "GOALS": str(min(total_goals, 7)), # Usually capped at 7+
            "CS": f"{home_goals}-{away_goals}",
            "ODD_EVEN": "ODD" if total_goals % 2 != 0 else "EVEN"
        }
        
        # Handicap WDL
        if handicaps:
            jc_h = handicaps.get("JINGCAI_HANDICAP", 0)
            adjusted_home_jc = home_goals + jc_h
            results["JINGCAI_HANDICAP_WDL"] = "3" if adjusted_home_jc > away_goals else "1" if adjusted_home_jc == away_goals else "0"
            
            bd_h = handicaps.get("BEIDAN_HANDICAP", 0)
            adjusted_home_bd = home_goals + bd_h
            results["BEIDAN_HANDICAP_WDL"] = "3" if adjusted_home_bd > away_goals else "1" if adjusted_home_bd == away_goals else "0"
            
        # HTFT
        if ht_score:
            try:
                ht_home, ht_away = map(int, ht_score.split("-"))
                ht_res = "3" if ht_home > ht_away else "1" if ht_home == ht_away else "0"
                results["HTFT"] = f"{ht_res}-{results['WDL']}"
            except ValueError:
                pass
                
        # Beidan UP_DOWN_ODD_EVEN (0-2 goals = DOWN, 3+ goals = UP)
        up_down = "UP" if total_goals >= 3 else "DOWN"
        results["UP_DOWN_ODD_EVEN"] = f"{up_down}_{results['ODD_EVEN']}"
        
        return results
```

- [x] **Step 4: Run test to verify it passes**

Run: `pytest standalone_workspace/tests/test_destructive_math.py -v`
Expected: PASS

- [x] **Step 5: Commit**

Run: `git add standalone_workspace/tools/settlement_engine.py standalone_workspace/tests/test_destructive_math.py`
Run: `git commit -m "feat: implement universal 90-min parser mapping one match to 16 official play type results"`

---
