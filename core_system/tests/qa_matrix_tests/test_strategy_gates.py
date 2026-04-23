# standalone_workspace/tests/qa_matrix_tests/test_strategy_gates.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from qa_engine.coverage_matrix import matrix_cover
from tools.smart_bet_selector import SmartBetSelector
from tools.settlement_engine import SettlementEngine
from tools.parlay_rules_engine import ParlayRulesEngine
from tools.lottery_router import LotteryRouter
from tools.live_match_monitor import LiveMatchMonitor
from tools.monte_carlo_simulator import MatchTimelineSimulator
from tools.odds_analyzer import OddsAnalyzer
from tools.market_probability_engine import MarketProbabilityEngine
import pytest

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

@matrix_cover(play_type="JINGCAI_WDL", stage="BETTING")
def test_jingcai_wdl_betting():
    router = LotteryRouter()
    ticket = {"play_type": "WDL", "legs": [{"match_id": "M1", "odds": 2.0}]}
    res = router.route_and_validate("JINGCAI", ticket)
    assert res["status"] == "SUCCESS"

@matrix_cover(play_type="JINGCAI_HANDICAP_WDL", stage="BETTING")
def test_jingcai_handicap_betting():
    router = LotteryRouter()
    # Jingcai must reject decimal handicaps
    ticket = {"play_type": "HANDICAP_WDL", "legs": [{"match_id": "M1", "handicap": 0.5, "odds": 2.0}]}
    with pytest.raises(ValueError, match="小数让球"):
        router.route_and_validate("JINGCAI", ticket)

@matrix_cover(play_type="JINGCAI_CS", stage="BETTING")
def test_jingcai_cs_betting():
    router = LotteryRouter()
    ticket = {"play_type": "CS", "legs": [{"match_id": "M1", "odds": 7.0}]}
    res = router.route_and_validate("JINGCAI", ticket)
    assert res["status"] == "SUCCESS"

@matrix_cover(play_type="JINGCAI_GOALS", stage="BETTING")
def test_jingcai_goals_betting():
    router = LotteryRouter()
    ticket = {"play_type": "GOALS", "legs": [{"match_id": "M1", "odds": 3.0}]}
    res = router.route_and_validate("JINGCAI", ticket)
    assert res["status"] == "SUCCESS"

@matrix_cover(play_type="JINGCAI_HTFT", stage="BETTING")
def test_jingcai_htft_betting():
    router = LotteryRouter()
    ticket = {"play_type": "HTFT", "legs": [{"match_id": "M1", "odds": 4.0}]}
    res = router.route_and_validate("JINGCAI", ticket)
    assert res["status"] == "SUCCESS"

@matrix_cover(play_type="JINGCAI_MIXED_PARLAY", stage="BETTING")
def test_jingcai_mixed_betting():
    router = LotteryRouter()
    ticket = {"play_type": "MIXED_PARLAY", "legs": [{"match_id": "M1", "play_type": "WDL", "odds": 2.0}, {"match_id": "M2", "play_type": "CS", "odds": 7.0}]}
    res = router.route_and_validate("JINGCAI", ticket)
    assert res["status"] == "SUCCESS"

@matrix_cover(play_type="BEIDAN_WDL", stage="BETTING")
def test_beidan_wdl_betting():
    router = LotteryRouter()
    ticket = {"play_type": "WDL", "legs": [{"match_id": "M1"}]}
    res = router.route_and_validate("BEIDAN", ticket)
    assert res["status"] == "SUCCESS"

@matrix_cover(play_type="BEIDAN_SFGG", stage="BETTING")
def test_beidan_sfgg_betting():
    router = LotteryRouter()
    # Beidan SFGG must have decimal handicap
    ticket = {"play_type": "SFGG", "legs": [{"match_id": "M1", "handicap": 0.5}]}
    res = router.route_and_validate("BEIDAN", ticket)
    assert res["status"] == "SUCCESS"

@matrix_cover(play_type="BEIDAN_UP_DOWN_ODD_EVEN", stage="BETTING")
def test_beidan_udoe_betting():
    router = LotteryRouter()
    ticket = {"play_type": "UP_DOWN_ODD_EVEN", "legs": [{"match_id": "M1"}]}
    res = router.route_and_validate("BEIDAN", ticket)
    assert res["status"] == "SUCCESS"

@matrix_cover(play_type="BEIDAN_GOALS", stage="BETTING")
def test_beidan_goals_betting():
    router = LotteryRouter()
    ticket = {"play_type": "GOALS", "legs": [{"match_id": "M1"}]}
    res = router.route_and_validate("BEIDAN", ticket)
    assert res["status"] == "SUCCESS"

@matrix_cover(play_type="BEIDAN_HTFT", stage="BETTING")
def test_beidan_htft_betting():
    router = LotteryRouter()
    ticket = {"play_type": "HTFT", "legs": [{"match_id": "M1"}]}
    res = router.route_and_validate("BEIDAN", ticket)
    assert res["status"] == "SUCCESS"

@matrix_cover(play_type="BEIDAN_CS", stage="BETTING")
def test_beidan_cs_betting():
    router = LotteryRouter()
    ticket = {"play_type": "CS", "legs": [{"match_id": "M1"}]}
    res = router.route_and_validate("BEIDAN", ticket)
    assert res["status"] == "SUCCESS"


@matrix_cover(play_type="ZUCAI_14_MATCH", stage="BETTING")
def test_zucai_14_betting():
    router = LotteryRouter()
    # 14 match must have exactly 14 legs
    legs = [{"match_id": f"M{i}"} for i in range(14)]
    ticket = {"play_type": "14_match", "legs": legs}
    res = router.route_and_validate("ZUCAI", ticket)
    assert res["status"] == "SUCCESS"

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

@matrix_cover(play_type="ZUCAI_RENJIU", stage="BETTING")
def test_zucai_renjiu_betting():
    router = LotteryRouter()
    # Renjiu must have exactly 9 legs
    legs = [{"match_id": f"M{i}"} for i in range(9)]
    ticket = {"play_type": "renjiu", "legs": legs}
    res = router.route_and_validate("ZUCAI", ticket)
    assert res["status"] == "SUCCESS"

@matrix_cover(play_type="ZUCAI_6_HTFT", stage="BETTING")
def test_zucai_6_htft_betting():
    router = LotteryRouter()
    legs = [{"match_id": f"M{i}"} for i in range(6)]
    ticket = {"play_type": "6_htft", "legs": legs}
    res = router.route_and_validate("ZUCAI", ticket)
    assert res["status"] == "SUCCESS"

@matrix_cover(play_type="ZUCAI_4_GOALS", stage="BETTING")
def test_zucai_4_goals_betting():
    router = LotteryRouter()
    legs = [{"match_id": f"M{i}"} for i in range(4)]
    ticket = {"play_type": "4_goals", "legs": legs}
    res = router.route_and_validate("ZUCAI", ticket)
    assert res["status"] == "SUCCESS"

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

@matrix_cover(play_type="JINGCAI_WDL", stage="PARLAY")
def test_jingcai_wdl_parlay():
    engine = ParlayRulesEngine()
    legs_ok = [{"match_id": f"M{i}", "play_type": "WDL"} for i in range(8)]
    legs_bad = [{"match_id": f"M{i}", "play_type": "WDL"} for i in range(9)]
    assert engine.validate_ticket_legs("竞彩足球", legs_ok)["is_valid"] is True
    assert engine.validate_ticket_legs("竞彩足球", legs_bad)["is_valid"] is False

@matrix_cover(play_type="JINGCAI_HANDICAP_WDL", stage="PARLAY")
def test_jingcai_handicap_parlay():
    engine = ParlayRulesEngine()
    legs_ok = [{"match_id": f"M{i}", "play_type": "HANDICAP"} for i in range(8)]
    legs_bad = [{"match_id": f"M{i}", "play_type": "HANDICAP"} for i in range(9)]
    assert engine.validate_ticket_legs("竞彩足球", legs_ok)["is_valid"] is True
    assert engine.validate_ticket_legs("竞彩足球", legs_bad)["is_valid"] is False

@matrix_cover(play_type="JINGCAI_GOALS", stage="PARLAY")
def test_jingcai_goals_parlay():
    engine = ParlayRulesEngine()
    legs_ok = [{"match_id": f"M{i}", "play_type": "GOALS"} for i in range(6)]
    legs_bad = [{"match_id": f"M{i}", "play_type": "GOALS"} for i in range(7)]
    assert engine.validate_ticket_legs("竞彩足球", legs_ok)["is_valid"] is True
    assert engine.validate_ticket_legs("竞彩足球", legs_bad)["is_valid"] is False

@matrix_cover(play_type="JINGCAI_CS", stage="PARLAY")
def test_jingcai_cs_parlay():
    engine = ParlayRulesEngine()
    legs_ok = [{"match_id": f"M{i}", "play_type": "CS"} for i in range(4)]
    legs_bad = [{"match_id": f"M{i}", "play_type": "CS"} for i in range(5)]
    assert engine.validate_ticket_legs("竞彩足球", legs_ok)["is_valid"] is True
    assert engine.validate_ticket_legs("竞彩足球", legs_bad)["is_valid"] is False

@matrix_cover(play_type="JINGCAI_HTFT", stage="PARLAY")
def test_jingcai_htft_parlay():
    engine = ParlayRulesEngine()
    legs_ok = [{"match_id": f"M{i}", "play_type": "HTFT"} for i in range(4)]
    legs_bad = [{"match_id": f"M{i}", "play_type": "HTFT"} for i in range(5)]
    assert engine.validate_ticket_legs("竞彩足球", legs_ok)["is_valid"] is True
    assert engine.validate_ticket_legs("竞彩足球", legs_bad)["is_valid"] is False

@matrix_cover(play_type="BEIDAN_WDL", stage="PARLAY")
def test_beidan_wdl_parlay():
    engine = ParlayRulesEngine()
    legs_ok = [{"match_id": f"M{i}", "play_type": "WDL"} for i in range(15)]
    legs_bad = [{"match_id": f"M{i}", "play_type": "WDL"} for i in range(16)]
    assert engine.validate_ticket_legs("北京单场", legs_ok)["is_valid"] is True
    assert engine.validate_ticket_legs("北京单场", legs_bad)["is_valid"] is False

@matrix_cover(play_type="BEIDAN_SFGG", stage="PARLAY")
def test_beidan_sfgg_parlay():
    engine = ParlayRulesEngine()
    legs_ok = [{"match_id": f"M{i}", "play_type": "HANDICAP"} for i in range(15)]
    legs_bad = [{"match_id": f"M{i}", "play_type": "HANDICAP"} for i in range(16)]
    assert engine.validate_ticket_legs("北京单场", legs_ok)["is_valid"] is True
    assert engine.validate_ticket_legs("北京单场", legs_bad)["is_valid"] is False

@matrix_cover(play_type="BEIDAN_UP_DOWN_ODD_EVEN", stage="PARLAY")
def test_beidan_udoe_parlay():
    engine = ParlayRulesEngine()
    legs_ok = [{"match_id": f"M{i}", "play_type": "WDL"} for i in range(15)]
    assert engine.validate_ticket_legs("北京单场", legs_ok)["is_valid"] is True

@matrix_cover(play_type="BEIDAN_GOALS", stage="PARLAY")
def test_beidan_goals_parlay():
    engine = ParlayRulesEngine()
    legs_ok = [{"match_id": f"M{i}", "play_type": "GOALS"} for i in range(15)]
    assert engine.validate_ticket_legs("北京单场", legs_ok)["is_valid"] is True

@matrix_cover(play_type="BEIDAN_HTFT", stage="PARLAY")
def test_beidan_htft_parlay():
    engine = ParlayRulesEngine()
    legs_ok = [{"match_id": f"M{i}", "play_type": "HTFT"} for i in range(15)]
    assert engine.validate_ticket_legs("北京单场", legs_ok)["is_valid"] is True

@matrix_cover(play_type="BEIDAN_CS", stage="PARLAY")
def test_beidan_cs_parlay():
    engine = ParlayRulesEngine()
    legs_ok = [{"match_id": f"M{i}", "play_type": "CS"} for i in range(3)]
    legs_bad = [{"match_id": f"M{i}", "play_type": "CS"} for i in range(4)]
    assert engine.validate_ticket_legs("北京单场", legs_ok)["is_valid"] is True
    assert engine.validate_ticket_legs("北京单场", legs_bad)["is_valid"] is False

@matrix_cover(play_type="ZUCAI_14_MATCH", stage="PARLAY")
def test_zucai_14_parlay():
    engine = ParlayRulesEngine()
    selections = [1] * 14
    assert engine.calculate_chuantong_combinations(selections, "14_match") == 1
    selections = [1] * 13 + [2]
    assert engine.calculate_chuantong_combinations(selections, "14_match") == 2
    with pytest.raises(ValueError, match="必须且只能选择14场"):
        engine.calculate_chuantong_combinations([1] * 13, "14_match")

@matrix_cover(play_type="ZUCAI_RENJIU", stage="PARLAY")
def test_zucai_renjiu_parlay():
    engine = ParlayRulesEngine()
    assert engine.calculate_chuantong_combinations([1] * 9, "renjiu") == 1
    assert engine.calculate_chuantong_combinations([1] * 10, "renjiu") == 10

@matrix_cover(play_type="ZUCAI_6_HTFT", stage="PARLAY")
def test_zucai_6_htft_parlay():
    engine = ParlayRulesEngine()
    assert engine.calculate_chuantong_combinations([1] * 6, "6_htft") == 1
    with pytest.raises(ValueError, match="必须选择6场比赛"):
        engine.calculate_chuantong_combinations([1] * 5, "6_htft")

@matrix_cover(play_type="ZUCAI_4_GOALS", stage="PARLAY")
def test_zucai_4_goals_parlay():
    engine = ParlayRulesEngine()
    assert engine.calculate_chuantong_combinations([1] * 4, "4_goals") == 1
    with pytest.raises(ValueError, match="必须选择4场比赛"):
        engine.calculate_chuantong_combinations([1] * 3, "4_goals")


@matrix_cover(play_type="JINGCAI_WDL", stage="ANALYSIS")
def test_analysis_jingcai_wdl():
    analyzer = OddsAnalyzer(use_historical=False)
    res = analyzer.analyze({"home": 2.0, "draw": 3.2, "away": 3.8}, calibrate=False)
    p = res["implied_probabilities"]
    assert abs(sum(p.values()) - 1.0) < 1e-6


@matrix_cover(play_type="JINGCAI_HANDICAP_WDL", stage="ANALYSIS")
def test_analysis_jingcai_handicap_wdl():
    eng = MarketProbabilityEngine()
    p = eng.handicap_wdl_from_xg(home_xg=1.4, away_xg=1.0, handicap=-1.0)
    assert abs(sum(p.values()) - 1.0) < 1e-6


@matrix_cover(play_type="JINGCAI_CS", stage="ANALYSIS")
def test_analysis_jingcai_cs():
    eng = MarketProbabilityEngine()
    top = eng.cs_topk(home_xg=1.2, away_xg=0.9, k=10)
    assert abs(sum(top.values()) - 1.0) < 1e-6


@matrix_cover(play_type="JINGCAI_GOALS", stage="ANALYSIS")
def test_analysis_jingcai_goals():
    eng = MarketProbabilityEngine()
    dist = eng.goals_distribution(home_xg=1.2, away_xg=1.0)
    assert abs(sum(dist.values()) - 1.0) < 1e-6
    assert "7+" in dist


@matrix_cover(play_type="JINGCAI_HTFT", stage="ANALYSIS")
def test_analysis_jingcai_htft():
    sim = MatchTimelineSimulator(num_simulations=2000)
    probs = sim.simulate_ht_ft_probabilities(home_xg=1.4, away_xg=1.0)
    assert len(probs) == 9
    assert abs(sum(probs.values()) - 1.0) < 0.05


@matrix_cover(play_type="JINGCAI_MIXED_PARLAY", stage="ANALYSIS")
def test_analysis_jingcai_mixed():
    eng = MarketProbabilityEngine()
    wdl = eng.wdl_from_xg(home_xg=1.4, away_xg=1.0)
    assert abs(sum(wdl.values()) - 1.0) < 1e-6
    sim = MatchTimelineSimulator(num_simulations=2000)
    probs = sim.simulate_ht_ft_probabilities(home_xg=1.4, away_xg=1.0)
    assert "33" in probs and "11" in probs and "00" in probs


@matrix_cover(play_type="BEIDAN_WDL", stage="ANALYSIS")
def test_analysis_beidan_wdl():
    eng = MarketProbabilityEngine()
    wdl = eng.wdl_from_xg(home_xg=1.2, away_xg=1.2)
    assert abs(sum(wdl.values()) - 1.0) < 1e-6


@matrix_cover(play_type="BEIDAN_SFGG", stage="ANALYSIS")
def test_analysis_beidan_sfgg():
    eng = MarketProbabilityEngine()
    p = eng.handicap_wdl_from_xg(home_xg=1.2, away_xg=1.2, handicap=0.5)
    assert abs(sum(p.values()) - 1.0) < 1e-6


@matrix_cover(play_type="BEIDAN_UP_DOWN_ODD_EVEN", stage="ANALYSIS")
def test_analysis_beidan_up_down_odd_even():
    eng = MarketProbabilityEngine()
    dist = eng.goals_distribution(home_xg=1.2, away_xg=1.0)
    up_prob = sum(v for k, v in dist.items() if k != "7+" and int(k) >= 3) + dist.get("7+", 0.0)
    assert 0.0 <= up_prob <= 1.0


@matrix_cover(play_type="BEIDAN_GOALS", stage="ANALYSIS")
def test_analysis_beidan_goals():
    eng = MarketProbabilityEngine()
    dist = eng.goals_distribution(home_xg=1.1, away_xg=0.9)
    assert abs(sum(dist.values()) - 1.0) < 1e-6


@matrix_cover(play_type="BEIDAN_HTFT", stage="ANALYSIS")
def test_analysis_beidan_htft():
    sim = MatchTimelineSimulator(num_simulations=2000)
    probs = sim.simulate_ht_ft_probabilities(home_xg=1.1, away_xg=0.9)
    assert len(probs) == 9


@matrix_cover(play_type="BEIDAN_CS", stage="ANALYSIS")
def test_analysis_beidan_cs():
    eng = MarketProbabilityEngine()
    top = eng.cs_topk(home_xg=1.1, away_xg=0.9, k=10)
    assert abs(sum(top.values()) - 1.0) < 1e-6


@matrix_cover(play_type="ZUCAI_14_MATCH", stage="ANALYSIS")
def test_analysis_zucai_14():
    eng = MarketProbabilityEngine()
    wdl = eng.wdl_from_xg(home_xg=1.3, away_xg=1.0)
    assert abs(sum(wdl.values()) - 1.0) < 1e-6


@matrix_cover(play_type="ZUCAI_RENJIU", stage="ANALYSIS")
def test_analysis_zucai_renjiu():
    eng = MarketProbabilityEngine()
    wdl = eng.wdl_from_xg(home_xg=1.0, away_xg=1.0)
    assert abs(sum(wdl.values()) - 1.0) < 1e-6


@matrix_cover(play_type="ZUCAI_6_HTFT", stage="ANALYSIS")
def test_analysis_zucai_6_htft():
    sim = MatchTimelineSimulator(num_simulations=2000)
    probs = sim.simulate_ht_ft_probabilities(home_xg=1.3, away_xg=1.0)
    assert len(probs) == 9


@matrix_cover(play_type="ZUCAI_4_GOALS", stage="ANALYSIS")
def test_analysis_zucai_4_goals():
    eng = MarketProbabilityEngine()
    dist = eng.goals_distribution(home_xg=1.3, away_xg=1.0)
    assert abs(sum(dist.values()) - 1.0) < 1e-6


@matrix_cover(play_type="JINGCAI_WDL", stage="LIVE_CHECK")
def test_live_check_jingcai_wdl():
    monitor = LiveMatchMonitor()
    monitor.register_live_bet("M1", "WDL_3", 100, 2.0)
    res = monitor.evaluate_hedge_opportunity("M1", "1-0", 5.0, 80)
    assert res["recommended_action"] == "HEDGE_NOW"


@matrix_cover(play_type="JINGCAI_HANDICAP_WDL", stage="LIVE_CHECK")
def test_live_check_jingcai_handicap_wdl():
    monitor = LiveMatchMonitor()
    monitor.register_live_bet("M1", "HANDICAP_WDL_3", 100, 2.2)
    res = monitor.evaluate_hedge_opportunity("M1", "1-0", 5.5, 80)
    assert res["recommended_action"] == "HEDGE_NOW"


@matrix_cover(play_type="JINGCAI_GOALS", stage="LIVE_CHECK")
def test_live_check_jingcai_goals():
    monitor = LiveMatchMonitor()
    monitor.register_live_bet("M1", "GOALS_3", 100, 5.0)
    res = monitor.evaluate_complex_hedge("M1", {"GOALS_OTHER": 20.0, "GOALS_3": 25.0}, 80)
    assert res["hedge_recommended"] is True


@matrix_cover(play_type="JINGCAI_CS", stage="LIVE_CHECK")
def test_live_check_jingcai_cs():
    monitor = LiveMatchMonitor()
    monitor.register_live_bet("M1", "CS_1-0", 100, 7.0)
    res = monitor.evaluate_complex_hedge("M1", {"CS_1-1": 15.0, "CS_2-0": 12.0, "CS_OTHER": 20.0}, 80)
    assert res["hedge_recommended"] is True


@matrix_cover(play_type="JINGCAI_HTFT", stage="LIVE_CHECK")
def test_live_check_jingcai_htft():
    monitor = LiveMatchMonitor()
    monitor.register_live_bet("M1", "HTFT_3-3", 100, 6.0)
    res = monitor.evaluate_complex_hedge("M1", {"HTFT_OTHER": 30.0, "HTFT_3-3": 35.0}, 70)
    assert res["hedge_recommended"] is True


@matrix_cover(play_type="JINGCAI_MIXED_PARLAY", stage="LIVE_CHECK")
def test_live_check_jingcai_mixed():
    monitor = LiveMatchMonitor()
    monitor.register_live_bet("M1", "MIXED", 100, 8.0)
    res = monitor.evaluate_complex_hedge("M1", {"ALT1": 25.0, "ALT2": 30.0}, 80)
    assert res["hedge_recommended"] is True


@matrix_cover(play_type="BEIDAN_WDL", stage="LIVE_CHECK")
def test_live_check_beidan_wdl():
    monitor = LiveMatchMonitor()
    monitor.register_live_bet("M1", "WDL_3", 100, 2.0)
    res = monitor.evaluate_hedge_opportunity("M1", "0-0", 5.0, 80)
    assert res["recommended_action"] == "HEDGE_NOW"


@matrix_cover(play_type="BEIDAN_SFGG", stage="LIVE_CHECK")
def test_live_check_beidan_sfgg():
    monitor = LiveMatchMonitor()
    monitor.register_live_bet("M1", "SFGG_3", 100, 2.0)
    res = monitor.evaluate_hedge_opportunity("M1", "0-0", 5.0, 80)
    assert res["recommended_action"] == "HEDGE_NOW"


@matrix_cover(play_type="BEIDAN_UP_DOWN_ODD_EVEN", stage="LIVE_CHECK")
def test_live_check_beidan_udoe():
    monitor = LiveMatchMonitor()
    monitor.register_live_bet("M1", "UP_ODD", 100, 3.5)
    res = monitor.evaluate_complex_hedge("M1", {"DOWN_EVEN": 10.0, "DOWN_ODD": 12.0, "UP_EVEN": 11.0}, 80)
    assert res["hedge_recommended"] is True


@matrix_cover(play_type="BEIDAN_GOALS", stage="LIVE_CHECK")
def test_live_check_beidan_goals():
    monitor = LiveMatchMonitor()
    monitor.register_live_bet("M1", "GOALS_3", 100, 5.0)
    res = monitor.evaluate_complex_hedge("M1", {"GOALS_OTHER": 20.0, "GOALS_3": 25.0}, 80)
    assert res["hedge_recommended"] is True


@matrix_cover(play_type="BEIDAN_HTFT", stage="LIVE_CHECK")
def test_live_check_beidan_htft():
    monitor = LiveMatchMonitor()
    monitor.register_live_bet("M1", "HTFT_1-1", 100, 4.0)
    res = monitor.evaluate_complex_hedge("M1", {"HTFT_OTHER": 30.0, "HTFT_1-1": 35.0}, 70)
    assert res["hedge_recommended"] is True


@matrix_cover(play_type="BEIDAN_CS", stage="LIVE_CHECK")
def test_live_check_beidan_cs():
    monitor = LiveMatchMonitor()
    monitor.register_live_bet("M1", "CS_0-0", 100, 10.0)
    res = monitor.evaluate_complex_hedge("M1", {"CS_1-0": 12.0, "CS_0-1": 12.0, "CS_OTHER": 20.0}, 80)
    assert res["hedge_recommended"] is True


@matrix_cover(play_type="ZUCAI_14_MATCH", stage="LIVE_CHECK")
def test_live_check_zucai_14():
    monitor = LiveMatchMonitor()
    monitor.register_live_bet("M1", "WDL_3", 100, 2.0)
    res = monitor.evaluate_hedge_opportunity("M1", "1-0", 5.0, 80)
    assert res["recommended_action"] == "HEDGE_NOW"


@matrix_cover(play_type="ZUCAI_RENJIU", stage="LIVE_CHECK")
def test_live_check_zucai_renjiu():
    monitor = LiveMatchMonitor()
    monitor.register_live_bet("M1", "WDL_1", 100, 2.5)
    res = monitor.evaluate_hedge_opportunity("M1", "0-0", 6.0, 80)
    assert res["recommended_action"] == "HEDGE_NOW"


@matrix_cover(play_type="ZUCAI_6_HTFT", stage="LIVE_CHECK")
def test_live_check_zucai_6_htft():
    monitor = LiveMatchMonitor()
    monitor.register_live_bet("M1", "HTFT_3-3", 100, 6.0)
    res = monitor.evaluate_complex_hedge("M1", {"HTFT_OTHER": 30.0, "HTFT_3-3": 35.0}, 70)
    assert res["hedge_recommended"] is True


@matrix_cover(play_type="ZUCAI_4_GOALS", stage="LIVE_CHECK")
def test_live_check_zucai_4_goals():
    monitor = LiveMatchMonitor()
    monitor.register_live_bet("M1", "GOALS_3", 100, 5.0)
    res = monitor.evaluate_complex_hedge("M1", {"GOALS_OTHER": 20.0, "GOALS_3": 25.0}, 80)
    assert res["hedge_recommended"] is True
