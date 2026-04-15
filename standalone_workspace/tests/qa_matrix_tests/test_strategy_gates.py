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


