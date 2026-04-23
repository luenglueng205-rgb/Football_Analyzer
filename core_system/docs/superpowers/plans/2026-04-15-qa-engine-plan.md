# AI Native Digital Betting Syndicate - Self-Proving QA Engine Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a "Self-Proving QA Engine" that programmatically enforces a 16x6 coverage matrix (16 play types × 6 lifecycle stages), validates against an Official Rulebook and a Strategy Rulebook, and automatically blocks deployment if coverage is < 100% or any rule is violated.

**Architecture:** 
1. **Rulebooks as Code:** Define `lottery_official_rulebook.md` and `strategy_rulebook.md` as the absolute sources of truth.
2. **Coverage Matrix Engine:** A framework to track and assert that all 96 intersections (16 play types × 6 stages: Analysis, Selection, Betting, Parlay, Live-check, Settlement) are implemented and tested.
3. **CI/CD Gatekeeper:** A daily script (`qa_deployment_gatekeeper.py`) that runs the matrix, generates a Markdown report, and exits with status 1 (blocking deployment) if any blind spots exist.

**Tech Stack:** Python 3.10+, `pytest`, custom decorators for matrix tracking, JSON/Markdown parsers.

---

### Task 1: Create the Strategy Rulebook (System Official Standard)

**Files:**
- Create: `standalone_workspace/docs/strategy_rulebook.md`

- [x] **Step 1: Create the Strategy Rulebook document**

```bash
mkdir -p standalone_workspace/docs
```

```markdown
# Strategy Rulebook (System Official Standard)

This document serves as the absolute source of truth for the system's internal betting strategies. The Self-Proving QA Engine will validate system outputs against these rules.

## 1. Selection Strategy (选场策略)
- **Jingcai (Fixed Odds):** A bet is selected ONLY IF `Expected Value (EV) >= 1.05`. EV is calculated as `Odds * Win Probability`.
- **Beidan (Dynamic Pool):** A bet is selected ONLY IF `EV >= 1.05`. EV MUST be calculated with the official 35% pool deduction: `(Odds * Win Probability) * 0.65`.
- **Zucai (No Odds Pool):** A bet is selected ONLY IF `Probability Edge >= 0.15`. Edge is calculated as `True Win Probability - Public Support Rate`.

## 2. Parlay Strategy (串关策略)
- **Jingcai:** Maximum legs allowed is 8. Decimal handicaps (e.g., 0.5) are strictly prohibited.
- **Beidan:** Maximum legs allowed is 15. SFGG (胜负过关) MUST use a 0.5 decimal handicap to eliminate draws.
- **Zucai:** Must be exactly 14 matches for 14-Match, and exactly 9 matches for Renjiu. Odds parameters MUST be ignored.
- **Payout Limits:** 2-3 legs <= 200,000 RMB; 4-5 legs <= 500,000 RMB; 6+ legs <= 1,000,000 RMB.

## 3. Live-check Strategy (临场/走地对冲策略)
- **Hedge Trigger:** A hedge is triggered ONLY IF the sum of implied probabilities (`sum(1/odds)`) of all remaining complementary markets is `< 1.0`, ensuring a guaranteed risk-free arbitrage.
- **Capital Distribution:** Hedge capital MUST be distributed proportionally to `Target Payout / Live Odds` to perfectly flatten the risk curve across all remaining outcomes.

## 4. Anomaly & Wind Control (风控策略)
- **CPU Protection:** Any combination request resulting in `> 50` total selections MUST be rejected to prevent combinatorics explosion.
- **Match Cancellation:** Any match marked as CANCELLED, POSTPONED, or W/O MUST be settled with odds of `1.0`.
```

- [x] **Step 2: Commit**

```bash
git add standalone_workspace/docs/strategy_rulebook.md
git commit -m "docs: establish Strategy Rulebook as the system's official strategy standard"
```

---

### Task 2: Build the Coverage Matrix Engine

**Files:**
- Create: `standalone_workspace/qa_engine/coverage_matrix.py`
- Create: `standalone_workspace/qa_engine/__init__.py`

- [ ] **Step 1: Create directories**

```bash
mkdir -p standalone_workspace/qa_engine
touch standalone_workspace/qa_engine/__init__.py
```

- [ ] **Step 2: Implement the Matrix Tracker**

```python
# standalone_workspace/qa_engine/coverage_matrix.py
import json
import os
from pathlib import Path

# 16 Play Types
PLAY_TYPES = [
    "JINGCAI_WDL", "JINGCAI_HANDICAP_WDL", "JINGCAI_CS", "JINGCAI_GOALS", "JINGCAI_HTFT", "JINGCAI_MIXED_PARLAY",
    "BEIDAN_WDL", "BEIDAN_SFGG", "BEIDAN_UP_DOWN_ODD_EVEN", "BEIDAN_GOALS", "BEIDAN_HTFT", "BEIDAN_CS",
    "ZUCAI_14_MATCH", "ZUCAI_RENJIU", "ZUCAI_6_HTFT", "ZUCAI_4_GOALS"
]

# 6 Lifecycle Stages
STAGES = ["ANALYSIS", "SELECTION", "BETTING", "PARLAY", "LIVE_CHECK", "SETTLEMENT"]

class CoverageTracker:
    def __init__(self):
        self.matrix = {pt: {st: False for st in STAGES} for pt in PLAY_TYPES}
        
    def mark_covered(self, play_type: str, stage: str):
        if play_type in self.matrix and stage in self.matrix[play_type]:
            self.matrix[play_type][stage] = True
            
    def get_coverage_report(self) -> dict:
        total_nodes = len(PLAY_TYPES) * len(STAGES)
        covered_nodes = sum(sum(1 for st in self.matrix[pt].values() if st) for pt in PLAY_TYPES)
        
        missing = []
        for pt in PLAY_TYPES:
            for st in STAGES:
                if not self.matrix[pt][st]:
                    missing.append(f"{pt} -> {st}")
                    
        return {
            "total_nodes": total_nodes,
            "covered_nodes": covered_nodes,
            "coverage_percentage": round((covered_nodes / total_nodes) * 100, 2),
            "is_complete": covered_nodes == total_nodes,
            "missing_nodes": missing,
            "matrix_data": self.matrix
        }

# Global instance for tests to register coverage
_tracker = CoverageTracker()

def matrix_cover(play_type: str, stage: str):
    """
    Decorator for pytest functions to register that they test a specific matrix node.
    """
    def decorator(func):
        # Register immediately upon import/collection
        _tracker.mark_covered(play_type, stage)
        return func
    return decorator

def get_global_tracker():
    return _tracker
```

- [ ] **Step 3: Commit**

```bash
git add standalone_workspace/qa_engine/
git commit -m "test: build Coverage Matrix Engine to track 16x6 play type lifecycle coverage"
```

---

### Task 3: Implement Differential & Metamorphic Test Gates

**Files:**
- Create: `standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py`

- [x] **Step 1: Create test directory**

```bash
mkdir -p standalone_workspace/tests/qa_matrix_tests
touch standalone_workspace/tests/qa_matrix_tests/__init__.py
```

- [x] **Step 2: Write Metamorphic Tests mapping to the Matrix**

```python
# standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from qa_engine.coverage_matrix import matrix_cover
from tools.smart_bet_selector import SmartBetSelector
from tools.settlement_engine import SettlementEngine
from tools.parlay_rules_engine import ParlayRulesEngine

@matrix_cover(play_type="ZUCAI_RENJIU", stage="SELECTION")
def test_zucai_selection_edge():
    selector = SmartBetSelector(min_edge_threshold=0.15)
    data = [{"match_id": "M1", "lottery_type": "ZUCAI", "markets": {"WDL": {"3": {"prob": 0.6, "support_rate": 0.4}}}}]
    res = selector.extract_value_bets(data)
    assert len(res) == 1
    assert res[0]["probability_edge"] == 0.2

@matrix_cover(play_type="BEIDAN_WDL", stage="SELECTION")
def test_beidan_selection_65_percent_deduction():
    selector = SmartBetSelector(min_ev_threshold=1.0)
    # 2.0 odds * 0.8 prob = 1.6 EV. 1.6 * 0.65 = 1.04 EV
    data = [{"match_id": "M1", "lottery_type": "BEIDAN", "markets": {"WDL": {"3": {"prob": 0.8, "odds": 2.0}}}}]
    res = selector.extract_value_bets(data)
    assert len(res) == 1
    assert res[0]["ev"] == 1.04

@matrix_cover(play_type="JINGCAI_MIXED_PARLAY", stage="PARLAY")
def test_jingcai_m_n_decomposition():
    engine = ParlayRulesEngine()
    combos = engine.get_m_n_ticket_combinations(["M1", "M2", "M3", "M4"], 4, 11)
    assert len(combos) == 11 # 6x 2-leg, 4x 3-leg, 1x 4-leg

@matrix_cover(play_type="BEIDAN_UP_DOWN_ODD_EVEN", stage="SETTLEMENT")
def test_beidan_up_down_settlement():
    engine = SettlementEngine()
    res = engine.determine_all_play_types_results("2-1") # 3 goals -> UP, Odd
    assert res["UP_DOWN_ODD_EVEN"] == "UP_ODD"

@matrix_cover(play_type="JINGCAI_WDL", stage="SETTLEMENT")
def test_metamorphic_cancellation_invariance():
    engine = SettlementEngine()
    # A cancelled match must always return 1.0 regardless of input scores
    res1 = engine.determine_all_play_types_results("0-0", status="CANCELLED")
    res2 = engine.determine_all_play_types_results("9-9", status="POSTPONED")
    assert res1["odds_applied"] == 1.0 and res1["status"] == "VOID"
    assert res2["odds_applied"] == 1.0 and res2["status"] == "VOID"
```

- [x] **Step 3: Run test to verify passes**

Run: `pytest standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py -v`
Expected: PASS

- [x] **Step 4: Commit**

```bash
git add standalone_workspace/tests/qa_matrix_tests/
git commit -m "test: implement metamorphic and strategy rulebook test gates mapped to coverage matrix"
```

---

### Task 4: Create the CI/CD Deployment Gatekeeper

**Files:**
- Create: `standalone_workspace/scripts/qa_deployment_gatekeeper.py`

- [ ] **Step 1: Write the Gatekeeper script**

```python
# standalone_workspace/scripts/qa_deployment_gatekeeper.py
import sys
import os
import pytest
import json
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from qa_engine.coverage_matrix import get_global_tracker

def run_gatekeeper():
    print("\n" + "="*70)
    print("🛡️  STARTING SELF-PROVING QA ENGINE GATEKEEPER 🛡️")
    print("="*70)
    
    # 1. Run all QA Matrix tests to populate the tracker
    print("\n[1/3] Running Strategy & Official Rulebook Test Suite...")
    test_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../tests/qa_matrix_tests'))
    
    # Run pytest programmatically
    exit_code = pytest.main([test_dir, "-q", "--disable-warnings"])
    
    if exit_code != 0:
        print("\n❌ GATEKEEPER BLOCKED: Tests failed. Code violates Strategy or Official Rulebooks.")
        sys.exit(1)
        
    # 2. Check the 16x6 Coverage Matrix
    print("\n[2/3] Analyzing 16x6 Play Type Lifecycle Coverage Matrix...")
    tracker = get_global_tracker()
    report = tracker.get_coverage_report()
    
    print(f"Coverage: {report['coverage_percentage']}% ({report['covered_nodes']}/{report['total_nodes']} nodes)")
    
    # 3. Generate Report
    print("\n[3/3] Generating Deployment Report...")
    report_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../tests/qa_reports'))
    os.makedirs(report_dir, exist_ok=True)
    
    report_path = os.path.join(report_dir, f"qa_matrix_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=4)
        
    print(f"Report saved to: {report_path}")
    
    if not report["is_complete"]:
        print("\n❌ GATEKEEPER BLOCKED: Coverage < 100%. The following nodes are missing implementation/tests:")
        for missing in report["missing_nodes"]:
            print(f"  - {missing}")
        print("\nYou MUST implement and test these blind spots before deployment is allowed.")
        sys.exit(1)
        
    print("\n✅ GATEKEEPER PASSED: 100% Coverage & Rulebook Alignment Verified. Deployment Allowed.")
    sys.exit(0)

if __name__ == "__main__":
    run_gatekeeper()
```

- [ ] **Step 2: Run the Gatekeeper**

Run: `python3 standalone_workspace/scripts/qa_deployment_gatekeeper.py`
Expected: Should run the tests, print the coverage (which will be `< 100%` because we haven't written tests for all 96 nodes yet), print the missing nodes, and exit with status 1.

- [ ] **Step 3: Commit**

```bash
git add standalone_workspace/scripts/qa_deployment_gatekeeper.py
git commit -m "build: create daily CI/CD deployment gatekeeper to block if matrix coverage < 100%"
```
