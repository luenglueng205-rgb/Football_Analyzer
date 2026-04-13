import json
import logging
import math
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SmartMoneyTracker:
    """
    聪明资金 (Smart Money) 追踪器。
    通过对比初盘和即时盘，剥离博彩公司的抽水 (Margin/Vig)，
    计算真实的隐含概率偏移 (Line Movement)。
    当偏移量超过设定阈值时，触发聪明资金警报。
    """
    
    def __init__(self, alert_threshold: float = 0.04):
        self.alert_threshold = alert_threshold # 默认概率偏移超过 4% 视为聪明资金介入
        
    def _calculate_true_probabilities(self, odds: Dict[str, float]) -> Dict[str, float]:
        """剥离抽水，计算真实的隐含概率"""
        # 计算隐含概率的初始值 (倒数)
        implied = {k: 1.0 / v for k, v in odds.items() if v > 0}
        # 计算博彩公司的利润率 (Overround)
        margin = sum(implied.values())
        # 归一化，得到真实概率
        return {k: v / margin for k, v in implied.items()}

    def track_odds_movement(self, match_id: str, opening_odds: Dict[str, float], current_odds: Dict[str, float]) -> Dict[str, Any]:
        """
        核心方法：追踪赔率异动，识别聪明资金
        :param opening_odds: 初盘赔率 {"home": 2.1, "draw": 3.4, "away": 3.5}
        :param current_odds: 即时赔率 {"home": 1.8, "draw": 3.6, "away": 4.2}
        """
        try:
            # 兼容大模型或外部API传错类型，强转为浮点数
            opening_odds = {k: float(v) for k, v in opening_odds.items() if float(v) > 0 and not math.isnan(float(v))}
            current_odds = {k: float(v) for k, v in current_odds.items() if float(v) > 0 and not math.isnan(float(v))}
            
            # 确保传入的不是全部被过滤掉的空字典
            if not opening_odds or not current_odds:
                raise ValueError("赔率字典在清洗后为空，可能传入了全为 NaN 或负数的无效数据")
                
            open_probs = self._calculate_true_probabilities(opening_odds)
            curr_probs = self._calculate_true_probabilities(current_odds)
        except (ZeroDivisionError, ValueError, TypeError) as e:
            return {"error": f"赔率格式异常或存在非正数/无效赔率，无法计算隐含概率: {e}"}

        alerts = []
        market_summary = {}

        for outcome in ['home', 'draw', 'away']:
            if outcome not in open_probs or outcome not in curr_probs:
                continue
                
            prob_shift = curr_probs[outcome] - open_probs[outcome]
            market_summary[outcome] = {
                "opening_prob": round(open_probs[outcome], 4),
                "current_prob": round(curr_probs[outcome], 4),
                "shift": round(prob_shift, 4)
            }
            
            # 如果某一方的真实胜率暴涨超过阈值，拉响聪明资金警报
            if prob_shift >= self.alert_threshold:
                alerts.append({
                    "direction": outcome,
                    "shift_percentage": f"{round(prob_shift * 100, 2)}%",
                    "alert_level": "CRITICAL" if prob_shift >= 0.07 else "HIGH",
                    "signal": f"检测到 {outcome.upper()} 方向有大量聪明资金(Sharp Money)介入，真实概率暴涨 {round(prob_shift * 100, 2)}%"
                })
                
        # 构造给 LLM 的语义总结
        semantic_reasoning = "【资金面分析】"
        if not alerts:
            semantic_reasoning += " 盘口稳定，未检测到明显的聪明资金异常介入，散户资金分布均衡。"
        else:
            semantic_reasoning += " ⚠️ 警告：检测到严重盘口异动！" + "；".join([a["signal"] for a in alerts]) + "。建议风控师(RiskManager)重点关注该方向，或直接作为博冷/防冷依据。"

        return {
            "match_id": match_id,
            "market_movement": market_summary,
            "smart_money_alerts": alerts,
            "is_volatile_market": len(alerts) > 0,
            "llm_semantic_reasoning": semantic_reasoning
        }

# --- 工具函数供 Agent 调用 ---
def check_smart_money_alerts(match_id: str, opening_odds: Dict[str, float], current_odds: Dict[str, float]) -> str:
    """
    供大语言模型(LLM)调用的工具函数。
    输入初盘和即时盘，返回聪明资金的监控报告。
    """
    logger.info(f"正在追踪比赛 {match_id} 的聪明资金动向...")
    tracker = SmartMoneyTracker()
    result = tracker.track_odds_movement(match_id, opening_odds, current_odds)
    return json.dumps(result, ensure_ascii=False)

if __name__ == "__main__":
    # 测试：主胜赔率从 2.1 暴跌到 1.85 (典型的聪明资金买入主队)
    open_o = {"home": 2.10, "draw": 3.40, "away": 3.50}
    curr_o = {"home": 1.85, "draw": 3.60, "away": 4.20}
    print(check_smart_money_alerts("ENG_PL_001", open_o, curr_o))