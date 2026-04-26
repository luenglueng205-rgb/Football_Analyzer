import pytest
from tools.smart_money_tracker import SmartMoneyTracker

def test_detect_anomaly():
    tracker = SmartMoneyTracker()
    
    # 模拟初赔到即时赔的剧烈震荡 (客胜从 6.0 暴跌至 3.5)
    odds_history = [
        {"timestamp": "10:00", "home": 1.5, "draw": 4.0, "away": 6.0},
        {"timestamp": "11:00", "home": 1.8, "draw": 3.8, "away": 4.5},
        {"timestamp": "12:00", "home": 2.1, "draw": 3.5, "away": 3.5}
    ]
    
    alert = tracker.detect_anomaly(odds_history)
    
    assert alert["is_anomaly"] is True
    assert alert["trigger_side"] == "away"
    assert "暴跌" in alert["reason"]
