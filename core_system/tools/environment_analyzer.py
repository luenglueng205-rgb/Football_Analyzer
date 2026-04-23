from typing import Dict, Any, Tuple

class EnvironmentAnalyzer:
    """
    量化天气、场地、主裁判尺度等非结构化因素对比赛的干扰。
    """
    def __init__(self):
        self.weather_impacts = {
            "heavy_rain": -0.15, # 大雨导致双方进攻效率下降 15%
            "snow": -0.20,       # 积雪导致下降 20%
            "extreme_heat": -0.10,
            "clear": 0.0
        }

    def calculate_impact(self, home_xg: float, away_xg: float, weather: Dict[str, Any], referee: Dict[str, Any]) -> Tuple[float, float]:
        condition = weather.get("condition", "clear")
        weather_modifier = self.weather_impacts.get(condition, 0.0)
        
        # 裁判严格度：掏牌多通常破坏比赛流畅性，微降 xG；但点球判罚严可能增加特定队 xG。此处简化为整体流畅性衰减。
        referee_modifier = 0.0
        if referee.get("strictness") == "high":
            referee_modifier = -0.05
            
        total_modifier = weather_modifier + referee_modifier
        
        # 限制最大干扰幅度
        total_modifier = max(-0.30, min(0.30, total_modifier))
        
        adj_home_xg = home_xg * (1 + total_modifier)
        adj_away_xg = away_xg * (1 + total_modifier)
        
        return round(max(0.1, adj_home_xg), 2), round(max(0.1, adj_away_xg), 2)
