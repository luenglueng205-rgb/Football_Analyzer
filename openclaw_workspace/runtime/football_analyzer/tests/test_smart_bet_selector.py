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