import math
from typing import Dict, List

def adjust_xg_for_injuries(base_xg: float, injuries: List[Dict]) -> float:
    """根据伤停名单衰减 xG"""
    if not injuries:
        return base_xg
        
    decay = 0.0
    for injury in injuries:
        status = injury.get("status", "").lower()
        position = injury.get("position", "").lower()
        
        if status in ["out", "injured"]:
            if position == "forward":
                decay += 0.15
            elif position == "midfielder":
                decay += 0.08
                
    decay = min(decay, 0.40)
    return base_xg * (1.0 - decay)
    
def calculate_bayesian_xg(team_stats: Dict, league_avg: float, injuries: List[Dict] = None) -> float:
    """计算贝叶斯平滑后的 xG"""
    sample_size = team_stats.get("sample_size", 0)
    recent_avg = team_stats.get("avg_home_goals", team_stats.get("avg_away_goals", league_avg))
    
    prior_weight = 10.0 / (10.0 + sample_size)
    posterior_weight = 1.0 - prior_weight
    
    bayesian_xg = (league_avg * prior_weight) + (recent_avg * posterior_weight)
    final_xg = adjust_xg_for_injuries(bayesian_xg, injuries)
    
    return max(0.1, final_xg)
