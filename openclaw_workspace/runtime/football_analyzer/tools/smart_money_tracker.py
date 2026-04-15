import os
import json
from typing import List, Dict, Any

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
