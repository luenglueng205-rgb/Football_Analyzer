import os
import json
from typing import List, Dict, Any, Tuple

class SmartMoneyTracker:
    """
    监控赔率时间序列的加速度，发现“断崖式”剧烈震荡拉响风控警报。
    """
    def __init__(self, default_drop_threshold: float = 0.25):
        # 赔率跌幅超过 default_drop_threshold 视为异常资金介入
        self.hyperparams_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs", "hyperparams.json")
        self.drop_threshold = self._load_dynamic_threshold(default_drop_threshold)

    def _load_dynamic_threshold(self, default_val):
        try:
            if os.path.exists(self.hyperparams_path):
                with open(self.hyperparams_path, "r", encoding="utf-8") as f:
                    params = json.load(f)
                    return params.get("smart_money_tracker", {}).get("drop_threshold", default_val)
        except Exception:
            pass
        return default_val

    def detect_anomaly(self, odds_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        if len(odds_history) < 2:
            return {"is_anomaly": False, "reason": "数据不足"}
            
        initial = odds_history[0]
        latest = odds_history[-1]
        
        home_drop = (initial["home"] - latest["home"]) / initial["home"]
        away_drop = (initial["away"] - latest["away"]) / initial["away"]
        draw_drop = (initial["draw"] - latest["draw"]) / initial["draw"]
        
        if home_drop > self.drop_threshold:
            return {"is_anomaly": True, "trigger_side": "home", "reason": f"主胜赔率暴跌 {home_drop*100:.1f}%，疑似聪明资金砸盘主队"}
            
        if away_drop > self.drop_threshold:
            return {"is_anomaly": True, "trigger_side": "away", "reason": f"客胜赔率暴跌 {away_drop*100:.1f}%，疑似聪明资金砸盘客队"}
            
        if draw_drop > self.drop_threshold:
            return {"is_anomaly": True, "trigger_side": "draw", "reason": f"平局赔率暴跌 {draw_drop*100:.1f}%，疑似默契球防范"}
            
        return {"is_anomaly": False, "reason": "赔率波动正常"}

    @staticmethod
    def remove_juice(home: float, draw: float, away: float) -> Tuple[float, float, float]:
        if home <= 0 or draw <= 0 or away <= 0:
            return 0.0, 0.0, 0.0
        implied_home = 1.0 / home
        implied_draw = 1.0 / draw
        implied_away = 1.0 / away
        total_implied = implied_home + implied_draw + implied_away
        return implied_home / total_implied, implied_draw / total_implied, implied_away / total_implied

    @staticmethod
    def detect_sharp_money(opening_odds: Dict[str, float], live_odds: Dict[str, float], threshold: float = 0.04) -> Dict[str, Any]:
        oh, od, oa = opening_odds.get("home", 0), opening_odds.get("draw", 0), opening_odds.get("away", 0)
        lh, ld, la = live_odds.get("home", 0), live_odds.get("draw", 0), live_odds.get("away", 0)

        if not all([oh, od, oa, lh, ld, la]):
            return {"has_sharp_money": False, "report": "赔率数据不全"}

        true_open_h, true_open_d, true_open_a = SmartMoneyTracker.remove_juice(float(oh), float(od), float(oa))
        true_live_h, true_live_d, true_live_a = SmartMoneyTracker.remove_juice(float(lh), float(ld), float(la))

        delta_h = true_live_h - true_open_h
        delta_d = true_live_d - true_open_d
        delta_a = true_live_a - true_open_a

        sharp_direction = None
        max_delta = 0.0

        if delta_h > threshold:
            sharp_direction, max_delta = "home", float(delta_h)
        elif delta_a > threshold:
            sharp_direction, max_delta = "away", float(delta_a)
        elif delta_d > threshold:
            sharp_direction, max_delta = "draw", float(delta_d)

        if sharp_direction:
            severity = "CRITICAL" if max_delta >= 0.07 else "WARNING"
            return {
                "has_sharp_money": True,
                "direction": sharp_direction,
                "delta_probability": max_delta,
                "severity": severity,
                "report": f"[{severity}] 聪明资金异动！{sharp_direction}方向真实胜率被资金砸高了 {max_delta*100:.1f}%！",
            }

        return {"has_sharp_money": False, "report": "盘口平稳，未检测到主力资金介入。"}
