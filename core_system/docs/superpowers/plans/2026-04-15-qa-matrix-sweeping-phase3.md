# AI Native Digital Betting Syndicate - QA Matrix Sweeping Plan (Phase 3: Analysis & Live-Check)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the final 32 blind spots in the Self-Proving QA Engine by covering the remaining two empty stages: `ANALYSIS` and `LIVE_CHECK` for all 16 play types.

**Architecture:**
1. **Analysis Engine:** Add a lightweight, deterministic `MarketProbabilityEngine` (pure math, no external API) that maps `(home_xg, away_xg, odds, handicap)` into market probabilities for WDL, Handicap WDL, Goals, CS, HTFT.
2. **Matrix Tests:** Add `@matrix_cover` tests for all 16 play types across `ANALYSIS` and `LIVE_CHECK`.
3. **Gatekeeper Confirmation:** Run `qa_deployment_gatekeeper.py` and confirm it blocks unless coverage is 100%, then reaches 100% once Phase 3 tests are added.

**Tech Stack:** Python 3.10+, `math`, `pytest`, existing `MatchTimelineSimulator`, existing `OddsAnalyzer`, existing `LiveMatchMonitor`.

---

### Task 1: Create MarketProbabilityEngine (pure math analysis core)

**Files:**
- Create: `standalone_workspace/tools/market_probability_engine.py`
- Test: `standalone_workspace/tests/test_market_probability_engine.py`

- [ ] **Step 1: Write failing tests**

```python
def test_market_probability_engine_goals_distribution_sums_to_one():
    from tools.market_probability_engine import MarketProbabilityEngine
    eng = MarketProbabilityEngine(max_goals=7)
    dist = eng.goals_distribution(home_xg=1.2, away_xg=0.8)
    assert abs(sum(dist.values()) - 1.0) < 1e-6
    assert "7+" in dist
```

- [ ] **Step 2: Implement minimal engine**

```python
from dataclasses import dataclass
import math
from typing import Dict, Tuple

@dataclass(frozen=True)
class MarketProbabilityEngine:
    max_goals: int = 7
    max_score: int = 6

    def _poisson_pmf(self, k: int, mu: float) -> float:
        if k < 0:
            return 0.0
        if mu <= 0:
            return 1.0 if k == 0 else 0.0
        return math.exp(-mu) * (mu ** k) / math.factorial(k)

    def wdl_from_xg(self, home_xg: float, away_xg: float) -> Dict[str, float]:
        p_home = 0.0
        p_draw = 0.0
        p_away = 0.0
        for h in range(0, self.max_score + 1):
            ph = self._poisson_pmf(h, home_xg)
            for a in range(0, self.max_score + 1):
                pa = self._poisson_pmf(a, away_xg)
                p = ph * pa
                if h > a:
                    p_home += p
                elif h == a:
                    p_draw += p
                else:
                    p_away += p
        s = p_home + p_draw + p_away
        if s <= 0:
            return {"3": 0.0, "1": 0.0, "0": 0.0}
        return {"3": p_home / s, "1": p_draw / s, "0": p_away / s}

    def handicap_wdl_from_xg(self, home_xg: float, away_xg: float, handicap: float) -> Dict[str, float]:
        p_home = 0.0
        p_draw = 0.0
        p_away = 0.0
        for h in range(0, self.max_score + 1):
            ph = self._poisson_pmf(h, home_xg)
            for a in range(0, self.max_score + 1):
                pa = self._poisson_pmf(a, away_xg)
                p = ph * pa
                diff = (h + handicap) - a
                if diff > 0:
                    p_home += p
                elif diff == 0:
                    p_draw += p
                else:
                    p_away += p
        s = p_home + p_draw + p_away
        if s <= 0:
            return {"3": 0.0, "1": 0.0, "0": 0.0}
        return {"3": p_home / s, "1": p_draw / s, "0": p_away / s}

    def goals_distribution(self, home_xg: float, away_xg: float) -> Dict[str, float]:
        mu = max(0.0, home_xg + away_xg)
        dist: Dict[str, float] = {}
        p_tail = 0.0
        for g in range(0, self.max_goals + 1):
            p = self._poisson_pmf(g, mu)
            dist[str(g)] = p
        for g in range(self.max_goals + 1, self.max_goals + 10):
            p_tail += self._poisson_pmf(g, mu)
        dist["7+"] = dist.pop(str(self.max_goals)) + p_tail
        s = sum(dist.values())
        if s <= 0:
            return {k: 0.0 for k in dist}
        return {k: v / s for k, v in dist.items()}

    def cs_topk(self, home_xg: float, away_xg: float, k: int = 10) -> Dict[str, float]:
        pairs = []
        for h in range(0, self.max_score + 1):
            ph = self._poisson_pmf(h, home_xg)
            for a in range(0, self.max_score + 1):
                pa = self._poisson_pmf(a, away_xg)
                pairs.append((f"{h}-{a}", ph * pa))
        pairs.sort(key=lambda x: x[1], reverse=True)
        top = dict(pairs[:k])
        s = sum(top.values())
        if s <= 0:
            return {k: 0.0 for k in top}
        return {k: v / s for k, v in top.items()}
```

- [ ] **Step 3: Run tests**

Run: `python3 -m pytest standalone_workspace/tests/test_market_probability_engine.py -v`
Expected: PASS

---

### Task 2: Add ANALYSIS stage matrix tests for all 16 play types

**Files:**
- Modify: `standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py`

- [ ] **Step 1: Add tests**

Add one test per play type, each calling either:
- `OddsAnalyzer.analyze` (for WDL odds analysis)
- `MatchTimelineSimulator.simulate_ht_ft_probabilities` (for HTFT analysis)
- `MarketProbabilityEngine` (for Handicap WDL, Goals, CS)

- [ ] **Step 2: Run tests**

Run: `python3 -m pytest standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py -v`
Expected: PASS

---

### Task 3: Add LIVE_CHECK stage matrix tests for all 16 play types

**Files:**
- Modify: `standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py`

- [ ] **Step 1: Add tests**

Add one test per play type, each using `LiveMatchMonitor`:
- WDL/Handicap WDL: `evaluate_hedge_opportunity`
- Goals/CS/HTFT/Mixed: `evaluate_complex_hedge`
- Zucai play types: at minimum verify hedge calculator returns structured output (even if “no hedge recommended”)

- [ ] **Step 2: Run tests**

Run: `python3 -m pytest standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py -v`
Expected: PASS

---

### Task 4: Confirm Gatekeeper reaches 100% coverage

**Files:**
- None

- [ ] **Step 1: Run gatekeeper**

Run: `python3 standalone_workspace/scripts/qa_deployment_gatekeeper.py`
Expected:
- Coverage: `100.0% (96/96 nodes)`
- Gatekeeper PASSED

