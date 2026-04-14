from math import exp
from typing import Dict

def _factorial(n: int) -> int:
    if n < 2: return 1
    r = 1
    for i in range(2, n + 1): r *= i
    return r

def _poisson_pmf(k: int, mu: float) -> float:
    if k < 0: return 0.0
    if mu <= 0: return 1.0 if k == 0 else 0.0
    return exp(-mu) * (mu ** k) / _factorial(k)

def calculate_poisson_probabilities(home_xg: float, away_xg: float) -> Dict[str, float]:
    """泊松分布计算真实胜平负概率"""
    max_goals = 10
    p_home = p_draw = p_away = 0.0
    
    for hg in range(max_goals + 1):
        ph = _poisson_pmf(hg, home_xg)
        for ag in range(max_goals + 1):
            pa = _poisson_pmf(ag, away_xg)
            joint = ph * pa
            if hg > ag:
                p_home += joint
            elif hg == ag:
                p_draw += joint
            else:
                p_away += joint
                
    return {"home_win": p_home, "draw": p_draw, "away_win": p_away}

def calculate_kelly_and_ev(odds: float, probability: float, lottery_type: str = "jingcai", kelly_fraction: float = 0.25) -> Dict[str, float]:
    """计算期望值(EV)与凯利仓位，严格隔离北单 0.65 机制"""
    if probability <= 0 or odds <= 1:
        return {"ev": 0.0, "kelly_stake_ratio": 0.0, "actual_odds": odds}
        
    actual_odds = odds * 0.65 if lottery_type == "beijing" else odds
    ev = (actual_odds * probability) - 1
    
    q = 1 - probability
    p = probability
    b = actual_odds - 1
    
    kelly = (b * p - q) / b if b > 0 else 0
    optimal_bet = min(kelly * kelly_fraction, 0.10) if kelly > 0 else 0.0
    
    return {
        "ev": ev,
        "kelly_stake_ratio": optimal_bet,
        "actual_odds": actual_odds
    }
