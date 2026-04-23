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
    
    # 按照 EV 从高到低排序，EV: under_2.5=1.14, handicap_-2=1.125
    assert recommendations[0]["market"] == "total"
    assert recommendations[0]["selection"] == "under_2.5"
    assert recommendations[1]["market"] == "handicap_-2"
    assert recommendations[1]["selection"] == "home"

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