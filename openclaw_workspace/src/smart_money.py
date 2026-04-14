import json
import math
from typing import Dict, Tuple

def remove_juice(home: float, draw: float, away: float) -> Tuple[float, float, float]:
    """剥离庄家抽水，还原真实的隐含概率"""
    if home <= 0 or draw <= 0 or away <= 0:
        return 0.0, 0.0, 0.0
    implied_home = 1.0 / home
    implied_draw = 1.0 / draw
    implied_away = 1.0 / away
    total_implied = implied_home + implied_draw + implied_away
    return implied_home / total_implied, implied_draw / total_implied, implied_away / total_implied

def detect_sharp_money(opening_odds: Dict[str, float], live_odds: Dict[str, float], threshold: float = 0.04) -> Dict[str, str]:
    """对比初盘和即时盘，检测聪明资金的砸盘方向"""
    oh, od, oa = opening_odds.get('home', 0), opening_odds.get('draw', 0), opening_odds.get('away', 0)
    lh, ld, la = live_odds.get('home', 0), live_odds.get('draw', 0), live_odds.get('away', 0)
    
    if not all([oh, od, oa, lh, ld, la]):
        return {"has_sharp_money": False, "report": "赔率数据不全"}
        
    true_open_h, true_open_d, true_open_a = remove_juice(oh, od, oa)
    true_live_h, true_live_d, true_live_a = remove_juice(lh, ld, la)
    
    delta_h = true_live_h - true_open_h
    delta_d = true_live_d - true_open_d
    delta_a = true_live_a - true_open_a
    
    sharp_direction = None
    max_delta = 0.0
    
    if delta_h > threshold:
        sharp_direction, max_delta = "home", delta_h
    elif delta_a > threshold:
        sharp_direction, max_delta = "away", delta_a
    elif delta_d > threshold:
        sharp_direction, max_delta = "draw", delta_d
        
    if sharp_direction:
        severity = "CRITICAL" if max_delta >= 0.07 else "WARNING"
        return {
            "has_sharp_money": True,
            "direction": sharp_direction,
            "delta_probability": max_delta,
            "severity": severity,
            "report": f"[{severity}] 聪明资金异动！{sharp_direction}方向真实胜率被资金砸高了 {max_delta*100:.1f}%！"
        }
    return {"has_sharp_money": False, "report": "盘口平稳，未检测到主力资金介入。"}
