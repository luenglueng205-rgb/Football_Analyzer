# AI Native Digital Betting Syndicate - QA Matrix Sweeping Plan (Phase 1: Settlement & Betting)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate the first batch of 91 blind spots in the Self-Proving QA Engine's coverage matrix. This phase focuses on writing comprehensive `@matrix_cover` tests for all 16 play types in the `SETTLEMENT` and `BETTING` stages.

**Architecture:** 
1. **Settlement Coverage:** Create tests for the remaining 14 play types to ensure `determine_all_play_types_results` correctly maps 90-min scores to official outcomes.
2. **Betting Coverage:** Create tests for all 16 play types to ensure `LotteryRouter` correctly routes, validates, and rejects malformed tickets according to the Official Rulebook.

**Tech Stack:** Python 3.10+, `pytest`, `qa_engine.coverage_matrix.matrix_cover`

---

### Task 1: Complete SETTLEMENT Stage Coverage (Jingcai)

**Files:**
- Modify: `standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py`

- [ ] **Step 1: Write Jingcai Settlement Tests**

```python
# Append to standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py

@matrix_cover(play_type="JINGCAI_HANDICAP_WDL", stage="SETTLEMENT")
def test_jingcai_handicap_settlement():
    engine = SettlementEngine()
    res = engine.determine_all_play_types_results("1-2", handicaps={"JINGCAI_HANDICAP": 1})
    assert res["JINGCAI_HANDICAP_WDL"] == "1" # 1+1 = 2, Draw

@matrix_cover(play_type="JINGCAI_CS", stage="SETTLEMENT")
def test_jingcai_cs_settlement():
    engine = SettlementEngine()
    res = engine.determine_all_play_types_results("3-1")
    assert res["CS"] == "3-1"

@matrix_cover(play_type="JINGCAI_GOALS", stage="SETTLEMENT")
def test_jingcai_goals_settlement():
    engine = SettlementEngine()
    res = engine.determine_all_play_types_results("2-2")
    assert res["GOALS"] == "4"

@matrix_cover(play_type="JINGCAI_HTFT", stage="SETTLEMENT")
def test_jingcai_htft_settlement():
    engine = SettlementEngine()
    res = engine.determine_all_play_types_results("2-1", ht_score="0-1")
    assert res["HTFT"] == "0-3" # HT Away(0), FT Home(3)

@matrix_cover(play_type="JINGCAI_MIXED_PARLAY", stage="SETTLEMENT")
def test_jingcai_mixed_settlement():
    engine = SettlementEngine()
    # Mixed parlay relies on the underlying results being present
    res = engine.determine_all_play_types_results("1-0", ht_score="0-0", handicaps={"JINGCAI_HANDICAP": -1})
    assert res["WDL"] == "3"
    assert res["JINGCAI_HANDICAP_WDL"] == "1"
    assert res["HTFT"] == "1-3"
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `pytest standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py -v -k "test_jingcai_"`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py
git commit -m "test: add full JINGCAI settlement coverage to QA matrix"
```

---

### Task 2: Complete SETTLEMENT Stage Coverage (Beidan & Zucai)

**Files:**
- Modify: `standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py`

- [ ] **Step 1: Write Beidan and Zucai Settlement Tests**

```python
# Append to standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py

@matrix_cover(play_type="BEIDAN_WDL", stage="SETTLEMENT")
def test_beidan_wdl_settlement():
    engine = SettlementEngine()
    res = engine.determine_all_play_types_results("0-0")
    assert res["WDL"] == "1"

@matrix_cover(play_type="BEIDAN_SFGG", stage="SETTLEMENT")
def test_beidan_sfgg_settlement():
    engine = SettlementEngine()
    res = engine.determine_all_play_types_results("1-1", handicaps={"BEIDAN_HANDICAP": 0.5})
    assert res["BEIDAN_HANDICAP_WDL"] == "3" # 1.5 > 1 -> Home Win

@matrix_cover(play_type="BEIDAN_GOALS", stage="SETTLEMENT")
def test_beidan_goals_settlement():
    engine = SettlementEngine()
    res = engine.determine_all_play_types_results("4-4")
    assert res["GOALS"] == "7" # Capped at 7

@matrix_cover(play_type="BEIDAN_HTFT", stage="SETTLEMENT")
def test_beidan_htft_settlement():
    engine = SettlementEngine()
    res = engine.determine_all_play_types_results("0-0", ht_score="0-0")
    assert res["HTFT"] == "1-1"

@matrix_cover(play_type="BEIDAN_CS", stage="SETTLEMENT")
def test_beidan_cs_settlement():
    engine = SettlementEngine()
    res = engine.determine_all_play_types_results("0-2")
    assert res["CS"] == "0-2"

@matrix_cover(play_type="ZUCAI_14_MATCH", stage="SETTLEMENT")
def test_zucai_14_settlement():
    engine = SettlementEngine()
    res = engine.determine_all_play_types_results("3-0")
    assert res["WDL"] == "3"

@matrix_cover(play_type="ZUCAI_RENJIU", stage="SETTLEMENT")
def test_zucai_renjiu_settlement():
    engine = SettlementEngine()
    res = engine.determine_all_play_types_results("1-1")
    assert res["WDL"] == "1"

@matrix_cover(play_type="ZUCAI_6_HTFT", stage="SETTLEMENT")
def test_zucai_6_htft_settlement():
    engine = SettlementEngine()
    res = engine.determine_all_play_types_results("2-0", ht_score="1-0")
    assert res["HTFT"] == "3-3"

@matrix_cover(play_type="ZUCAI_4_GOALS", stage="SETTLEMENT")
def test_zucai_4_goals_settlement():
    engine = SettlementEngine()
    res = engine.determine_all_play_types_results("2-1")
    assert res["GOALS"] == "3"
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `pytest standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py
git commit -m "test: add full BEIDAN and ZUCAI settlement coverage to QA matrix"
```

---

### Task 3: Complete BETTING Stage Coverage (Jingcai & Beidan Validation)

**Files:**
- Modify: `standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py`

- [x] **Step 1: Write Jingcai & Beidan Betting Route Tests**

```python
# Append to standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py
from tools.lottery_router import LotteryRouter
import pytest

@matrix_cover(play_type="JINGCAI_WDL", stage="BETTING")
def test_jingcai_wdl_betting():
    router = LotteryRouter()
    ticket = {"play_type": "WDL", "legs": [{"match_id": "M1", "odds": 2.0}]}
    res = router.route_and_validate("JINGCAI", ticket)
    assert res["status"] == "VALIDATED"

@matrix_cover(play_type="JINGCAI_HANDICAP_WDL", stage="BETTING")
def test_jingcai_handicap_betting():
    router = LotteryRouter()
    # Jingcai must reject decimal handicaps
    ticket = {"play_type": "HANDICAP_WDL", "legs": [{"match_id": "M1", "handicap": 0.5, "odds": 2.0}]}
    with pytest.raises(ValueError, match="必须是整数"):
        router.route_and_validate("JINGCAI", ticket)

@matrix_cover(play_type="JINGCAI_CS", stage="BETTING")
def test_jingcai_cs_betting():
    router = LotteryRouter()
    ticket = {"play_type": "CS", "legs": [{"match_id": "M1", "odds": 7.0}]}
    res = router.route_and_validate("JINGCAI", ticket)
    assert res["status"] == "VALIDATED"

@matrix_cover(play_type="JINGCAI_GOALS", stage="BETTING")
def test_jingcai_goals_betting():
    router = LotteryRouter()
    ticket = {"play_type": "GOALS", "legs": [{"match_id": "M1", "odds": 3.0}]}
    res = router.route_and_validate("JINGCAI", ticket)
    assert res["status"] == "VALIDATED"

@matrix_cover(play_type="JINGCAI_HTFT", stage="BETTING")
def test_jingcai_htft_betting():
    router = LotteryRouter()
    ticket = {"play_type": "HTFT", "legs": [{"match_id": "M1", "odds": 4.0}]}
    res = router.route_and_validate("JINGCAI", ticket)
    assert res["status"] == "VALIDATED"

@matrix_cover(play_type="JINGCAI_MIXED_PARLAY", stage="BETTING")
def test_jingcai_mixed_betting():
    router = LotteryRouter()
    ticket = {"play_type": "MIXED_PARLAY", "legs": [{"match_id": "M1", "play_type": "WDL", "odds": 2.0}, {"match_id": "M2", "play_type": "CS", "odds": 7.0}]}
    res = router.route_and_validate("JINGCAI", ticket)
    assert res["status"] == "VALIDATED"

@matrix_cover(play_type="BEIDAN_WDL", stage="BETTING")
def test_beidan_wdl_betting():
    router = LotteryRouter()
    ticket = {"play_type": "WDL", "legs": [{"match_id": "M1"}]}
    res = router.route_and_validate("BEIDAN", ticket)
    assert res["status"] == "VALIDATED"

@matrix_cover(play_type="BEIDAN_SFGG", stage="BETTING")
def test_beidan_sfgg_betting():
    router = LotteryRouter()
    # Beidan SFGG must have decimal handicap
    ticket = {"play_type": "SFGG", "legs": [{"match_id": "M1", "handicap": 0.5}]}
    res = router.route_and_validate("BEIDAN", ticket)
    assert res["status"] == "VALIDATED"

@matrix_cover(play_type="BEIDAN_UP_DOWN_ODD_EVEN", stage="BETTING")
def test_beidan_udoe_betting():
    router = LotteryRouter()
    ticket = {"play_type": "UP_DOWN_ODD_EVEN", "legs": [{"match_id": "M1"}]}
    res = router.route_and_validate("BEIDAN", ticket)
    assert res["status"] == "VALIDATED"

@matrix_cover(play_type="BEIDAN_GOALS", stage="BETTING")
def test_beidan_goals_betting():
    router = LotteryRouter()
    ticket = {"play_type": "GOALS", "legs": [{"match_id": "M1"}]}
    res = router.route_and_validate("BEIDAN", ticket)
    assert res["status"] == "VALIDATED"

@matrix_cover(play_type="BEIDAN_HTFT", stage="BETTING")
def test_beidan_htft_betting():
    router = LotteryRouter()
    ticket = {"play_type": "HTFT", "legs": [{"match_id": "M1"}]}
    res = router.route_and_validate("BEIDAN", ticket)
    assert res["status"] == "VALIDATED"

@matrix_cover(play_type="BEIDAN_CS", stage="BETTING")
def test_beidan_cs_betting():
    router = LotteryRouter()
    ticket = {"play_type": "CS", "legs": [{"match_id": "M1"}]}
    res = router.route_and_validate("BEIDAN", ticket)
    assert res["status"] == "VALIDATED"
```

- [x] **Step 2: Run tests to verify they pass**

Run: `pytest standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py -v`
Expected: PASS

- [x] **Step 3: Commit**

```bash
git add standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py
git commit -m "test: add full JINGCAI and BEIDAN betting validation coverage to QA matrix"
```

---

### Task 4: Complete BETTING Stage Coverage (Zucai Validation)

**Files:**
- Modify: `standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py`

- [ ] **Step 1: Write Zucai Betting Route Tests**

```python
# Append to standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py

@matrix_cover(play_type="ZUCAI_14_MATCH", stage="BETTING")
def test_zucai_14_betting():
    router = LotteryRouter()
    # 14 match must have exactly 14 legs
    legs = [{"match_id": f"M{i}"} for i in range(14)]
    ticket = {"play_type": "14_match", "legs": legs}
    res = router.route_and_validate("ZUCAI", ticket)
    assert res["status"] == "VALIDATED"

@matrix_cover(play_type="ZUCAI_RENJIU", stage="BETTING")
def test_zucai_renjiu_betting():
    router = LotteryRouter()
    # Renjiu must have exactly 9 legs
    legs = [{"match_id": f"M{i}"} for i in range(9)]
    ticket = {"play_type": "renjiu", "legs": legs}
    res = router.route_and_validate("ZUCAI", ticket)
    assert res["status"] == "VALIDATED"

@matrix_cover(play_type="ZUCAI_6_HTFT", stage="BETTING")
def test_zucai_6_htft_betting():
    router = LotteryRouter()
    legs = [{"match_id": f"M{i}"} for i in range(6)]
    ticket = {"play_type": "6_htft", "legs": legs}
    res = router.route_and_validate("ZUCAI", ticket)
    assert res["status"] == "VALIDATED"

@matrix_cover(play_type="ZUCAI_4_GOALS", stage="BETTING")
def test_zucai_4_goals_betting():
    router = LotteryRouter()
    legs = [{"match_id": f"M{i}"} for i in range(4)]
    ticket = {"play_type": "4_goals", "legs": legs}
    res = router.route_and_validate("ZUCAI", ticket)
    assert res["status"] == "VALIDATED"
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `pytest standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py -v`
Expected: PASS

- [ ] **Step 3: Check Gatekeeper Status**

Run: `python3 standalone_workspace/scripts/qa_deployment_gatekeeper.py`
Expected: Coverage should jump from 5.21% (5/96) to roughly 36.4% (35/96).

- [ ] **Step 4: Commit**

```bash
git add standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py
git commit -m "test: add full ZUCAI betting validation coverage to QA matrix"
```
