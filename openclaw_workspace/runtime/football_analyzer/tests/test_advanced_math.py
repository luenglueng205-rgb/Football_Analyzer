import pytest
import sys
from pathlib import Path

# Add standalone_workspace to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from skills.advanced_lottery_math import map_poisson_to_jingcai_scores, calculate_parlay_kelly, calculate_last_leg_hedge, optimize_jingcai_ticket, calculate_zucai_value_index

def test_optimize_jingcai_ticket():
    # 4-leg parlay, combined odds 6000.0, target investment 10,000 RMB (5000 bets)
    # Since odds > 5000, 1 bet (2 RMB) pays > 10,000 RMB -> TAXED 20%
    result = optimize_jingcai_ticket(num_legs=4, combined_odds=6000.0, target_investment=10000)
    
    # Statutory max payout for 4 legs is 500,000 RMB per ticket.
    # 1 bet pays 12,000 RMB (pre-tax). Post-tax is 9,600 RMB.
    assert result["is_taxed"] is True
    assert result["post_tax_odds"] == 4800.0 # 6000 * 0.8
    # Max bets per ticket to hit 500k ceiling with post-tax payout of 9.6k:
    # 500,000 / 9600 = 52.08 -> 52 bets per ticket (104 RMB per ticket)
    assert result["max_bets_per_ticket"] == 52
    assert result["suggested_tickets"] > 1

def test_calculate_zucai_value_index():
    # Match 1: True prob 50%, Public thinks 90% (Hotpot/Overvalued)
    # Match 2: True prob 40%, Public thinks 10% (Cold spot/Undervalued)
    matches = [
        {"true_prob": 0.5, "public_prob": 0.9},
        {"true_prob": 0.4, "public_prob": 0.1}
    ]
    
    result = calculate_zucai_value_index(matches)
    
    # Value index = true_prob / public_prob
    # Match 1 = 0.555, Match 2 = 4.0
    assert result[0]["value_index"] < 1.0
    assert result[1]["value_index"] == 4.0
    assert result[1]["is_value_pick"] is True

def test_map_poisson_to_jingcai_scores():
    matrix = [[0.01 for _ in range(10)] for _ in range(10)]
    matrix[5][0] = 0.05
    matrix[4][3] = 0.05
    result = map_poisson_to_jingcai_scores(matrix)
    assert "胜其他" in result
    assert "平其他" in result
    assert "负其他" in result
    assert result["1:0"] == 0.01
    assert result["胜其他"] >= 0.10 

def test_calculate_parlay_kelly():
    legs = [{"prob": 0.6, "odds": 1.8}, {"prob": 0.5, "odds": 2.1}]
    result = calculate_parlay_kelly(legs)
    assert "ev" in result
    assert "kelly_fraction" in result
    assert abs(result["ev"] - 0.134) < 0.001
    assert abs(result["kelly_fraction"] - 0.048) < 0.005

def test_calculate_last_leg_hedge():
    result = calculate_last_leg_hedge(
        original_bet=100,
        potential_payout=1000,
        hedge_odds={"Draw": 3.0, "Away": 4.0}
    )
    assert "hedge_bets" in result
    assert abs(result["hedge_bets"]["Draw"] - 333.33) < 0.1
    assert abs(result["hedge_bets"]["Away"] - 250.0) < 0.1
    assert abs(result["guaranteed_profit"] - 316.67) < 0.1

def test_beidan_parlay_kelly_bug_fix():
    # 3-leg parlay, odds = 2.0 each
    legs = [{"prob": 0.5, "odds": 2.0}, {"prob": 0.5, "odds": 2.0}, {"prob": 0.5, "odds": 2.0}]
    
    # Jingcai mode (default)
    result_jc = calculate_parlay_kelly(legs)
    assert result_jc["combined_odds"] == 8.0
    
    # Beidan mode
    result_bd = calculate_parlay_kelly(legs, lottery_type="BEIDAN")
    # Expected combined odds: (2.0 * 2.0 * 2.0) * 0.65 = 5.2
    assert result_bd["combined_odds"] == 5.2
