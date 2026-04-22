import pytest
import sys
from pathlib import Path

# Add standalone_workspace to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from skills.trap_identifier import identify_low_odds_trap
from skills.latency_arbitrage import detect_latency_arbitrage
from skills.betfair_anomaly import detect_betfair_anomaly

def test_detect_betfair_anomaly():
    # Betfair market: Home odds 2.0 (Implied prob 50%).
    # But matched volume on Home is 85% of total market volume.
    # Money is pouring into Home, but odds aren't dropping -> Smart Money is Laying (Selling) Home.
    
    result = detect_betfair_anomaly(odds=2.0, volume_percentage=0.85)
    
    assert result["is_anomaly"] is True
    assert "大热必死" in result["analysis"] or "主力派发" in result["analysis"]
    assert result["suggested_action"] == "FADE" # 反向操作

def test_detect_latency_arbitrage():
    # Pinnacle odds for Home: 2.10 (Fair prob ~ 47.6%)
    # Jingcai odds for Home: 2.30
    # Normally Jingcai is lower than Pinnacle due to high vig. 
    # If Jingcai > Pinnacle, it means Jingcai hasn't reacted to a market crash yet.
    
    result = detect_latency_arbitrage(jingcai_odds=2.30, pinnacle_odds=2.10)
    
    assert result["is_arbitrage"] is True
    assert result["ev"] > 0
    assert "时差套利" in result["alert"]
    
    # Normal situation: Pinnacle 1.80, Jingcai 1.60
    result_normal = detect_latency_arbitrage(jingcai_odds=1.60, pinnacle_odds=1.80)
    assert result_normal["is_arbitrage"] is False

def test_identify_low_odds_trap():
    # Jingcai offers 1.25 for Home Win. Implied prob (with 11% vig) = 0.89 / 1.25 = 71.2%
    # But our Poisson engine says the true prob is only 55.0%
    result = identify_low_odds_trap(jingcai_odds=1.25, true_prob=0.55)
    
    assert result["is_trap"] is True
    assert "蚊子肉陷阱" in result["warning"]
    
    # Safe bet: Jingcai 1.80 (Implied = 0.89/1.8 = 49.4%). True prob = 50.0%
    result_safe = identify_low_odds_trap(jingcai_odds=1.80, true_prob=0.50)
    assert result_safe["is_trap"] is False
