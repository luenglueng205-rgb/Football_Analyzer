import pytest
from tools.monte_carlo_simulator import TimeSliceMonteCarlo

def test_monte_carlo_simulation():
    simulator = TimeSliceMonteCarlo()
    
    # 主队 xG = 2.0, 客队 xG = 1.0
    result = simulator.simulate_match(home_xg=2.0, away_xg=1.0, simulations=1000)
    
    assert "home_win_prob" in result
    assert "draw_prob" in result
    assert "away_win_prob" in result
    assert "half_full_time" in result
    
    # 主队胜率应该大于客队
    assert result["home_win_prob"] > result["away_win_prob"]
    # 胜胜 (Home-Home) 的概率应该被计算出来
    assert "HH" in result["half_full_time"]
