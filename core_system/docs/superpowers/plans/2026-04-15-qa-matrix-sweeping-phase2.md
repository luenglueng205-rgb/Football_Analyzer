# AI Native Digital Betting Syndicate - QA Matrix Sweeping Plan (Phase 2: Selection & Parlay)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate the second batch of 29 blind spots in the Self-Proving QA Engine's coverage matrix. This phase focuses on writing comprehensive `@matrix_cover` tests for all missing play types in the `SELECTION` and `PARLAY` stages.

**Architecture:** 
1. **Selection Coverage:** Create tests for the remaining 14 play types in `SmartBetSelector`, ensuring Jingcai uses standard EV, Beidan applies a 65% deduction, and Zucai uses Probability Edge.
2. **Parlay Coverage:** Create tests for the remaining 15 play types in `ParlayRulesEngine` and `LotteryRouter`, ensuring correct leg limits (e.g., Jingcai max 8, Beidan max 15) and Zucai combinatorics.

**Tech Stack:** Python 3.10+, `pytest`, `qa_engine.coverage_matrix.matrix_cover`

---

### Task 1: Complete SELECTION Stage Coverage (Jingcai)

**Files:**
- Modify: `standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py`

- [ ] **Step 1: Write Jingcai Selection Tests**

```python
# Append to standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py

@matrix_cover(play_type="JINGCAI_WDL", stage="SELECTION")
def test_jingcai_wdl_selection():
    selector = SmartBetSelector(min_ev_threshold=1.05)
    data = [{"match_id": "M1", "lottery_type": "JINGCAI", "markets": {"WDL": {"3": {"prob": 0.6, "odds": 2.0}}}}]
    res = selector.extract_value_bets(data)
    assert len(res) == 1
    assert res[0]["ev"] == 1.2

@matrix_cover(play_type="JINGCAI_HANDICAP_WDL", stage="SELECTION")
def test_jingcai_handicap_selection():
    selector = SmartBetSelector(min_ev_threshold=1.05)
    data = [{"match_id": "M1", "lottery_type": "JINGCAI", "markets": {"HANDICAP_WDL": {"3": {"prob": 0.5, "odds": 2.5}}}}]
    res = selector.extract_value_bets(data)
    assert len(res) == 1
    assert res[0]["ev"] == 1.25

@matrix_cover(play_type="JINGCAI_CS", stage="SELECTION")
def test_jingcai_cs_selection():
    selector = SmartBetSelector(min_ev_threshold=1.05)
    data = [{"match_id": "M1", "lottery_type": "JINGCAI", "markets": {"CS": {"1-0": {"prob": 0.15, "odds": 8.0}}}}]
    res = selector.extract_value_bets(data)
    assert len(res) == 1
    assert res[0]["ev"] == 1.2

@matrix_cover(play_type="JINGCAI_GOALS", stage="SELECTION")
def test_jingcai_goals_selection():
    selector = SmartBetSelector(min_ev_threshold=1.05)
    data = [{"match_id": "M1", "lottery_type": "JINGCAI", "markets": {"GOALS": {"3": {"prob": 0.3, "odds": 4.0}}}}]
    res = selector.extract_value_bets(data)
    assert len(res) == 1
    assert res[0]["ev"] == 1.2

@matrix_cover(play_type="JINGCAI_HTFT", stage="SELECTION")
def test_jingcai_htft_selection():
    selector = SmartBetSelector(min_ev_threshold=1.05)
    data = [{"match_id": "M1", "lottery_type": "JINGCAI", "markets": {"HTFT": {"3-3": {"prob": 0.4, "odds": 3.0}}}}]
    res = selector.extract_value_bets(data)
    assert len(res) == 1
    assert res[0]["ev"] == 1.2

@matrix_cover(play_type="JINGCAI_MIXED_PARLAY", stage="SELECTION")
def test_jingcai_mixed_selection():
    selector = SmartBetSelector(min_ev_threshold=1.05)
    # Testing that multiple markets in one match are extracted
    data = [{"match_id": "M1", "lottery_type": "JINGCAI", "markets": {
        "WDL": {"3": {"prob": 0.6, "odds": 2.0}},
        "GOALS": {"2": {"prob": 0.3, "odds": 4.0}}
    }}]
    res = selector.extract_value_bets(data)
    assert len(res) == 2
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `pytest standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py -v -k "test_jingcai_"`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py
git commit -m "test: add full JINGCAI selection coverage to QA matrix"
```

---

### Task 2: Complete SELECTION Stage Coverage (Beidan & Zucai)

**Files:**
- Modify: `standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py`

- [ ] **Step 1: Write Beidan and Zucai Selection Tests**

```python
# Append to standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py

@matrix_cover(play_type="BEIDAN_SFGG", stage="SELECTION")
def test_beidan_sfgg_selection():
    selector = SmartBetSelector(min_ev_threshold=1.0)
    data = [{"match_id": "M1", "lottery_type": "BEIDAN", "markets": {"SFGG": {"3": {"prob": 0.8, "odds": 2.0}}}}]
    res = selector.extract_value_bets(data)
    assert len(res) == 1
    assert res[0]["ev"] == 1.04 # 1.6 * 0.65

@matrix_cover(play_type="BEIDAN_UP_DOWN_ODD_EVEN", stage="SELECTION")
def test_beidan_udoe_selection():
    selector = SmartBetSelector(min_ev_threshold=1.0)
    data = [{"match_id": "M1", "lottery_type": "BEIDAN", "markets": {"UP_DOWN_ODD_EVEN": {"UP_ODD": {"prob": 0.5, "odds": 3.5}}}}]
    res = selector.extract_value_bets(data)
    assert len(res) == 1
    assert res[0]["ev"] == 1.1375 # 1.75 * 0.65

@matrix_cover(play_type="BEIDAN_GOALS", stage="SELECTION")
def test_beidan_goals_selection():
    selector = SmartBetSelector(min_ev_threshold=1.0)
    data = [{"match_id": "M1", "lottery_type": "BEIDAN", "markets": {"GOALS": {"3": {"prob": 0.3, "odds": 6.0}}}}]
    res = selector.extract_value_bets(data)
    assert len(res) == 1
    assert res[0]["ev"] == 1.17 # 1.8 * 0.65

@matrix_cover(play_type="BEIDAN_HTFT", stage="SELECTION")
def test_beidan_htft_selection():
    selector = SmartBetSelector(min_ev_threshold=1.0)
    data = [{"match_id": "M1", "lottery_type": "BEIDAN", "markets": {"HTFT": {"3-3": {"prob": 0.4, "odds": 4.0}}}}]
    res = selector.extract_value_bets(data)
    assert len(res) == 1
    assert res[0]["ev"] == 1.04 # 1.6 * 0.65

@matrix_cover(play_type="BEIDAN_CS", stage="SELECTION")
def test_beidan_cs_selection():
    selector = SmartBetSelector(min_ev_threshold=1.0)
    data = [{"match_id": "M1", "lottery_type": "BEIDAN", "markets": {"CS": {"1-0": {"prob": 0.15, "odds": 12.0}}}}]
    res = selector.extract_value_bets(data)
    assert len(res) == 1
    assert res[0]["ev"] == 1.17 # 1.8 * 0.65

@matrix_cover(play_type="ZUCAI_14_MATCH", stage="SELECTION")
def test_zucai_14_selection():
    selector = SmartBetSelector(min_edge_threshold=0.15)
    data = [{"match_id": "M1", "lottery_type": "ZUCAI", "markets": {"14_MATCH": {"3": {"prob": 0.6, "support_rate": 0.4}}}}]
    res = selector.extract_value_bets(data)
    assert len(res) == 1
    assert res[0]["probability_edge"] == 0.2

@matrix_cover(play_type="ZUCAI_6_HTFT", stage="SELECTION")
def test_zucai_6_htft_selection():
    selector = SmartBetSelector(min_edge_threshold=0.15)
    data = [{"match_id": "M1", "lottery_type": "ZUCAI", "markets": {"6_HTFT": {"3-3": {"prob": 0.4, "support_rate": 0.2}}}}]
    res = selector.extract_value_bets(data)
    assert len(res) == 1
    assert res[0]["probability_edge"] == 0.2

@matrix_cover(play_type="ZUCAI_4_GOALS", stage="SELECTION")
def test_zucai_4_goals_selection():
    selector = SmartBetSelector(min_edge_threshold=0.15)
    data = [{"match_id": "M1", "lottery_type": "ZUCAI", "markets": {"4_GOALS": {"3": {"prob": 0.3, "support_rate": 0.1}}}}]
    res = selector.extract_value_bets(data)
    assert len(res) == 1
    assert res[0]["probability_edge"] == 0.2
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `pytest standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py
git commit -m "test: add full BEIDAN and ZUCAI selection coverage to QA matrix"
```

---

### Task 3: Complete PARLAY Stage Coverage (Jingcai)

**Files:**
- Modify: `standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py`

- [ ] **Step 1: Write Jingcai Parlay Limit Tests**

```python
# Append to standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py

@matrix_cover(play_type="JINGCAI_WDL", stage="PARLAY")
def test_jingcai_wdl_parlay():
    engine = ParlayRulesEngine()
    # Max 8 legs for WDL
    assert engine.validate_ticket_legs("JINGCAI", "WDL", 8) is True
    assert engine.validate_ticket_legs("JINGCAI", "WDL", 9) is False

@matrix_cover(play_type="JINGCAI_HANDICAP_WDL", stage="PARLAY")
def test_jingcai_handicap_parlay():
    engine = ParlayRulesEngine()
    assert engine.validate_ticket_legs("JINGCAI", "HANDICAP_WDL", 8) is True
    assert engine.validate_ticket_legs("JINGCAI", "HANDICAP_WDL", 9) is False

@matrix_cover(play_type="JINGCAI_CS", stage="PARLAY")
def test_jingcai_cs_parlay():
    engine = ParlayRulesEngine()
    # Max 4 legs for CS
    assert engine.validate_ticket_legs("JINGCAI", "CS", 4) is True
    assert engine.validate_ticket_legs("JINGCAI", "CS", 5) is False

@matrix_cover(play_type="JINGCAI_GOALS", stage="PARLAY")
def test_jingcai_goals_parlay():
    engine = ParlayRulesEngine()
    # Max 6 legs for GOALS
    assert engine.validate_ticket_legs("JINGCAI", "GOALS", 6) is True
    assert engine.validate_ticket_legs("JINGCAI", "GOALS", 7) is False

@matrix_cover(play_type="JINGCAI_HTFT", stage="PARLAY")
def test_jingcai_htft_parlay():
    engine = ParlayRulesEngine()
    # Max 4 legs for HTFT
    assert engine.validate_ticket_legs("JINGCAI", "HTFT", 4) is True
    assert engine.validate_ticket_legs("JINGCAI", "HTFT", 5) is False
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `pytest standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py
git commit -m "test: add full JINGCAI parlay coverage to QA matrix"
```

---

### Task 4: Complete PARLAY Stage Coverage (Beidan & Zucai)

**Files:**
- Modify: `standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py`

- [x] **Step 1: Write Beidan & Zucai Parlay Limit Tests**

```python
# Append to standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py

@matrix_cover(play_type="BEIDAN_WDL", stage="PARLAY")
def test_beidan_wdl_parlay():
    engine = ParlayRulesEngine()
    # Max 15 legs for Beidan WDL
    assert engine.validate_ticket_legs("BEIDAN", "WDL", 15) is True
    assert engine.validate_ticket_legs("BEIDAN", "WDL", 16) is False

@matrix_cover(play_type="BEIDAN_SFGG", stage="PARLAY")
def test_beidan_sfgg_parlay():
    engine = ParlayRulesEngine()
    assert engine.validate_ticket_legs("BEIDAN", "SFGG", 15) is True
    assert engine.validate_ticket_legs("BEIDAN", "SFGG", 16) is False

@matrix_cover(play_type="BEIDAN_UP_DOWN_ODD_EVEN", stage="PARLAY")
def test_beidan_udoe_parlay():
    engine = ParlayRulesEngine()
    assert engine.validate_ticket_legs("BEIDAN", "UP_DOWN_ODD_EVEN", 15) is True

@matrix_cover(play_type="BEIDAN_GOALS", stage="PARLAY")
def test_beidan_goals_parlay():
    engine = ParlayRulesEngine()
    assert engine.validate_ticket_legs("BEIDAN", "GOALS", 15) is True

@matrix_cover(play_type="BEIDAN_HTFT", stage="PARLAY")
def test_beidan_htft_parlay():
    engine = ParlayRulesEngine()
    assert engine.validate_ticket_legs("BEIDAN", "HTFT", 15) is True

@matrix_cover(play_type="BEIDAN_CS", stage="PARLAY")
def test_beidan_cs_parlay():
    engine = ParlayRulesEngine()
    # Max 3 legs for Beidan CS
    assert engine.validate_ticket_legs("BEIDAN", "CS", 3) is True
    assert engine.validate_ticket_legs("BEIDAN", "CS", 4) is False

@matrix_cover(play_type="ZUCAI_14_MATCH", stage="PARLAY")
def test_zucai_14_parlay():
    engine = ParlayRulesEngine()
    # 14 match with 14 singles
    selections = [1] * 14
    assert engine.calculate_chuantong_combinations(selections, "14_match") == 1
    # 13 singles, 1 double
    selections = [1] * 13 + [2]
    assert engine.calculate_chuantong_combinations(selections, "14_match") == 2
    # Invalid length
    with pytest.raises(ValueError, match="必须是 14 场"):
        engine.calculate_chuantong_combinations([1]*13, "14_match")

@matrix_cover(play_type="ZUCAI_RENJIU", stage="PARLAY")
def test_zucai_renjiu_parlay():
    engine = ParlayRulesEngine()
    # 9 singles
    assert engine.calculate_chuantong_combinations([1]*9, "renjiu") == 1
    # 10 singles = C(10,9) = 10
    assert engine.calculate_chuantong_combinations([1]*10, "renjiu") == 10

@matrix_cover(play_type="ZUCAI_6_HTFT", stage="PARLAY")
def test_zucai_6_htft_parlay():
    engine = ParlayRulesEngine()
    assert engine.calculate_chuantong_combinations([1]*6, "6_htft") == 1
    with pytest.raises(ValueError, match="必须是 6 场"):
        engine.calculate_chuantong_combinations([1]*5, "6_htft")

@matrix_cover(play_type="ZUCAI_4_GOALS", stage="PARLAY")
def test_zucai_4_goals_parlay():
    engine = ParlayRulesEngine()
    assert engine.calculate_chuantong_combinations([1]*4, "4_goals") == 1
    with pytest.raises(ValueError, match="必须是 4 场"):
        engine.calculate_chuantong_combinations([1]*3, "4_goals")
```

- [x] **Step 2: Run tests to verify they pass**

Run: `pytest standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py -v`
Expected: PASS

- [x] **Step 3: Check Gatekeeper Status**

Run: `python3 standalone_workspace/scripts/qa_deployment_gatekeeper.py`
Expected: Coverage should jump from 36.4% (35/96) to roughly 66.6% (64/96).

- [x] **Step 4: Commit**

```bash
git add standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py
git commit -m "test: add full BEIDAN and ZUCAI parlay coverage to QA matrix"
```
