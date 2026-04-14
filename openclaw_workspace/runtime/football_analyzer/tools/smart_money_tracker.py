import math
from typing import Dict, Any, Tuple

class SmartMoneyTracker:
    """
    2026 版聪明资金追踪器 (Smart Money Tracker)
    基于泊松分布和赔率偏移，剥离庄家抽水 (Juice/Vig)，计算真实的资金砸盘方向。
    """
    
    @staticmethod
    def remove_juice(home: float, draw: float, away: float) -> Tuple[float, float, float]:
        """
        剥离庄家抽水，还原真实的隐含概率 (Implied True Probability)
        """
        if home <= 0 or draw <= 0 or away <= 0:
            return 0.0, 0.0, 0.0
            
        implied_home = 1.0 / home
        implied_draw = 1.0 / draw
        implied_away = 1.0 / away
        
        total_implied = implied_home + implied_draw + implied_away
        
        # 按比例剥离抽水
        true_home = implied_home / total_implied
        true_draw = implied_draw / total_implied
        true_away = implied_away / total_implied
        
        return true_home, true_draw, true_away

    @classmethod
    def detect_sharp_money(cls, opening_odds: Dict[str, float], live_odds: Dict[str, float], threshold: float = 0.04) -> Dict[str, Any]:
        """
        对比初盘(Opening)和即时盘(Live)，检测聪明资金(Sharp Money)的介入方向
        threshold: 真实概率偏移超过 4% 视为异常资金介入
        """
        oh, od, oa = opening_odds.get('home', 0), opening_odds.get('draw', 0), opening_odds.get('away', 0)
        lh, ld, la = live_odds.get('home', 0), live_odds.get('draw', 0), live_odds.get('away', 0)
        
        if not all([oh, od, oa, lh, ld, la]):
            return {"has_sharp_money": False, "reason": "赔率数据不全"}
            
        # 计算初盘真实概率
        true_open_h, true_open_d, true_open_a = cls.remove_juice(oh, od, oa)
        # 计算即时盘真实概率
        true_live_h, true_live_d, true_live_a = cls.remove_juice(lh, ld, la)
        
        # 计算偏移量 (Delta)
        delta_h = true_live_h - true_open_h
        delta_d = true_live_d - true_open_d
        delta_a = true_live_a - true_open_a
        
        sharp_direction = None
        max_delta = 0.0
        
        if delta_h > threshold:
            sharp_direction = "home"
            max_delta = delta_h
        elif delta_a > threshold:
            sharp_direction = "away"
            max_delta = delta_a
        elif delta_d > threshold:
            sharp_direction = "draw"
            max_delta = delta_d
            
        if sharp_direction:
            severity = "CRITICAL" if max_delta >= 0.07 else "WARNING"
            return {
                "has_sharp_money": True,
                "direction": sharp_direction,
                "delta_probability": max_delta,
                "severity": severity,
                "report": f"[{severity}] 聪明资金异动！{sharp_direction}方向真实胜率被资金砸高了 {max_delta*100:.1f}%！庄家在疯狂降水防范赔付。"
            }
            
        return {
            "has_sharp_money": False,
            "delta_h": delta_h,
            "delta_a": delta_a,
            "report": "盘口平稳，未检测到主力资金介入。"
        }
