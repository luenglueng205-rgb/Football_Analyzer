import pytest
import sys
from pathlib import Path

# Add standalone_workspace to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from skills.advanced_lottery_math import map_poisson_to_jingcai_scores, calculate_parlay_kelly, calculate_last_leg_hedge

def test_calculate_last_leg_hedge():
    # We have a 4-leg parlay ticket. 3 legs have won.
    # Original bet: 100 RMB. Potential payout: 1000 RMB.
    # Last leg is Team A vs Team B. Our parlay needs Team A to Win.
    # Current odds for Draw: 3.0, Away Win: 4.0
    
    result = calculate_last_leg_hedge(
        original_bet=100,
        potential_payout=1000,
        hedge_odds={"Draw": 3.0, "Away": 4.0}
    )
    
    # To guarantee equal profit across all outcomes:
    # Let x = bet on Draw, y = bet on Away
    # If Home wins: Profit = 1000 - 100 - x - y
    # If Draw wins: Profit = 3.0*x - 100 - x - y = 2.0*x - 100 - y
    # If Away wins: Profit = 4.0*y - 100 - x - y = 3.0*y - 100 - x
    # Equating them:
    # 1000 - x - y = 3.0x - x - y => 1000 = 3.0x => x = 333.33
    # 1000 - x - y = 4.0y - x - y => 1000 = 4.0y => y = 250
    # Total investment = 100 + 333.33 + 250 = 683.33
    # Guaranteed return = 1000. Profit = 316.67
    
    assert "hedge_bets" in result
    assert abs(result["hedge_bets"]["Draw"] - 333.33) < 0.1
    assert abs(result["hedge_bets"]["Away"] - 250.0) < 0.1
    assert abs(result["guaranteed_profit"] - 316.67) < 0.1

def test_calculate_parlay_kelly():
    # 2-leg parlay: 
    # Leg 1: Prob 60%, Odds 1.8
    # Leg 2: Prob 50%, Odds 2.1
    legs = [{"prob": 0.6, "odds": 1.8}, {"prob": 0.5, "odds": 2.1}]
    
    result = calculate_parlay_kelly(legs)
    
    # Combined Prob = 0.3
    # Combined Odds = 3.78
    # EV = 0.3 * 3.78 - 1 = 1.134 - 1 = 0.134
    # Kelly = (p*b - q) / b where b = 2.78, p = 0.3, q = 0.7
    # Kelly = (0.3*2.78 - 0.7) / 2.78 = (0.834 - 0.7) / 2.78 = 0.134 / 2.78 = ~0.048
    
    assert "ev" in result
    assert "kelly_fraction" in result
    assert abs(result["ev"] - 0.134) < 0.001
    assert abs(result["kelly_fraction"] - 0.048) < 0.005

def test_map_poisson_to_jingcai_scores():
    # Mock a 10x10 poisson matrix where probabilities are just dummy values
    matrix = [[0.01 for _ in range(10)] for _ in range(10)]
    # Make 5-0 (home win other) have a specific value
    matrix[5][0] = 0.05
    # Make 4-3 (home win other) have a specific value
    matrix[4][3] = 0.05
    
    result = map_poisson_to_jingcai_scores(matrix)
    
    assert "胜其他" in result
    assert "平其他" in result
    assert "负其他" in result
    assert result["1:0"] == 0.01
    assert result["胜其他"] >= 0.10 # 5-0 and 4-3 plus others
