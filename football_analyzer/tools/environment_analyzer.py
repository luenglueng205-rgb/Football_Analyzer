import json
import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UnstructuredFactorAnalyzer:
    """
    非结构化因素分析器。
    专门处理比赛当天天气、裁判执法尺度等定性数据。
    结合大模型的语义推理，将外部环境因素转化为定量的 xG (预期进球) 修正系数。
    """
    
    def __init__(self):
        # 模拟内置裁判数据库 (实战中应从数据库查询)
        self.referee_db = {
            "Anthony Taylor": {"foul_rate": "high", "penalty_rate": "low", "card_strictness": "high"},
            "Michael Oliver": {"foul_rate": "medium", "penalty_rate": "high", "card_strictness": "medium"},
            "Mike Dean": {"foul_rate": "high", "penalty_rate": "high", "card_strictness": "high"}
        }
        
    def _evaluate_weather_impact(self, weather_desc: str) -> Dict[str, float]:
        """简易启发式天气影响评估"""
        weather = weather_desc.lower()
        impact = {"xg_modifier": 1.0, "open_play_penalty": 0.0}
        
        if "rain" in weather or "heavy rain" in weather:
            impact["xg_modifier"] = 0.85 # 大雨削弱总进球期望 15%
            impact["open_play_penalty"] = 0.20 # 运动战进球受罚更严重
        elif "snow" in weather:
            impact["xg_modifier"] = 0.80 # 冰雪天气削弱总进球期望 20%
        elif "wind" in weather or "gale" in weather:
            impact["xg_modifier"] = 0.90 # 狂风影响长传和射门
            
        return impact
        
    def _evaluate_referee_impact(self, referee_name: str) -> Dict[str, float]:
        """裁判执法尺度评估"""
        ref_data = self.referee_db.get(referee_name, {"foul_rate": "medium", "penalty_rate": "medium"})
        impact = {"xg_modifier": 1.0, "card_expectation_modifier": 1.0}
        
        # 判点球概率高，提升总 xG 期望 (每个点球约合 0.76 xG)
        if ref_data["penalty_rate"] == "high":
            impact["xg_modifier"] += 0.08
            
        # 吹罚严厉 (犯规多)，比赛节奏破碎，降低运动战 xG，但提升得牌期望
        if ref_data["foul_rate"] == "high":
            impact["xg_modifier"] -= 0.05
            impact["card_expectation_modifier"] = 1.30
            
        return impact

    def analyze_match_environment(self, match_id: str, weather: str, referee: str) -> Dict[str, Any]:
        """
        核心方法：分析比赛环境对总进球 (xG) 和比赛走势的量化影响
        """
        weather_impact = self._evaluate_weather_impact(weather)
        ref_impact = self._evaluate_referee_impact(referee)
        
        # 综合 xG 修正系数
        total_xg_modifier = weather_impact["xg_modifier"] * ref_impact["xg_modifier"]
        
        # 格式化语义推理建议，供 LLM 参考
        semantic_reasoning = f"【环境分析结论】"
        if total_xg_modifier < 0.9:
            semantic_reasoning += f" 恶劣天气('{weather}')叠加裁判因素('{referee}')严重影响比赛流畅度，建议下调总进球期望，偏向小球。"
        elif total_xg_modifier > 1.05:
            semantic_reasoning += f" 裁判('{referee}')判罚点球概率极高，建议适当上调总进球期望，关注大球和半场进球。"
        else:
            semantic_reasoning += " 环境因素对比赛影响中性，可维持基础预测。"
            
        return {
            "match_id": match_id,
            "environment_factors": {
                "weather": weather,
                "referee": referee
            },
            "quantitative_adjustments": {
                "total_xg_modifier": round(total_xg_modifier, 3), # 传递给大模型用于修正泊松分布参数
                "card_expectation_modifier": ref_impact.get("card_expectation_modifier", 1.0)
            },
            "llm_semantic_reasoning": semantic_reasoning
        }

# --- 工具函数供 Agent 调用 ---
def get_match_environment_impact(match_id: str, weather_desc: str, referee_name: str) -> str:
    """
    供大语言模型(LLM)调用的工具函数。
    输入天气描述和主裁判名字，返回量化后的 xG 修正系数和语义推理。
    """
    logger.info(f"正在分析非结构化环境因素 (Weather: {weather_desc}, Referee: {referee_name})...")
    analyzer = UnstructuredFactorAnalyzer()
    result = analyzer.analyze_match_environment(match_id, weather_desc, referee_name)
    return json.dumps(result, ensure_ascii=False)

if __name__ == "__main__":
    import json
    # 测试极端环境
    print(get_match_environment_impact("ENG_PL_001", "Heavy rain and very windy", "Anthony Taylor"))