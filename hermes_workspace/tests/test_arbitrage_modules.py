import pytest
import sys
from pathlib import Path

# Add standalone_workspace to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hermes_workspace.tools.math.trap_identifier import identify_low_odds_trap
from hermes_workspace.tools.math.latency_arbitrage import detect_latency_arbitrage
from hermes_workspace.tools.math.betfair_anomaly import detect_betfair_anomaly
from hermes_workspace.tools.math.kelly_variance_analyzer import analyze_kelly_variance

def test_analyze_kelly_variance():
    # Scenario 1: High consensus (Low variance). All bookies agree Home is strong.
    # Odds: Bet365: 1.50, Pinnacle: 1.51, William Hill: 1.49, Macauslot: 1.50
    odds_consensus = [1.50, 1.51, 1.49, 1.50]
    result_consensus = analyze_kelly_variance(odds_consensus)
    
    assert "variance" in result_consensus
    assert result_consensus["variance"] < 0.005
    assert result_consensus["is_consensus"] is True
    
    # Scenario 2: High variance (Bookies are confused or someone knows something)
    # Odds: Bet365: 1.50, Pinnacle: 1.80, William Hill: 1.40, Macauslot: 1.90
    odds_chaos = [1.50, 1.80, 1.40, 1.90]
    result_chaos = analyze_kelly_variance(odds_chaos)
    
    assert result_chaos["variance"] > 0.01
    assert result_chaos["is_consensus"] is False
    assert "分歧极大" in result_chaos["analysis"]

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
