import json
import logging
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PlayerImpactAdjuster:
    """
    球员级 xG 价值调整器。
    专门处理伤病/停赛对球队进攻火力的精确衰减。
    利用球员的 xG90 (每90分钟预期进球) 和 xA90 (预期助攻) 进行量化扣除。
    """
    
    def __init__(self):
        pass

    def _calc_offensive_contribution(self, players: List[Dict[str, float]]) -> float:
        """
        计算进攻火力贡献 (考虑进球和助攻转化)
        进球 xG 权重 1.0，助攻 xA 权重 0.5 (避免重复计算前锋的吃饼xG)
        """
        return sum((p.get('xg90', 0.0) * 1.0 + p.get('xa90', 0.0) * 0.5) * p.get('minutes_share', 1.0) for p in players)

    def calculate_xg_adjustment(self, team_base_xg: float, missing_players: List[Dict[str, Any]], replacement_players: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        核心方法：动态计算缺阵核心带来的火力下降，并更新基础预期进球
        :param team_base_xg: 球队基于历史数据的初始预期进球(xG)
        :param missing_players: 缺阵的核心球员列表，包含 xg90 和 xa90，如 [{"name": "德布劳内", "xg90": 0.25, "xa90": 0.40}]
        :param replacement_players: 顶替出场的替补球员列表，如果为空，则假定替补火力极弱
        """
        if replacement_players is None:
            replacement_players = []

        lost_xg = self._calc_offensive_contribution(missing_players)
        gained_xg = self._calc_offensive_contribution(replacement_players)
        net_xg_delta = gained_xg - lost_xg  # 通常为负数，代表实力下降
        
        # 调整预期进球，设定下限 0.1 避免计算出负数进球
        adjusted_xg = max(0.1, team_base_xg + net_xg_delta)
        
        # 格式化语义推理，供 LLM 参考
        missing_names = ", ".join([p.get('name', 'Unknown') for p in missing_players])
        semantic_reasoning = f"【伤停影响量化】核心球员({missing_names})缺阵，导致球队每场损失 {round(abs(net_xg_delta), 2)} 个预期进球(xG)。"
        if abs(net_xg_delta) > 0.3:
            semantic_reasoning += " ⚠️ 火力衰减严重！请使用调整后的 xG 重新计算泊松分布，大概率下调该队的胜率和总进球。"
        else:
            semantic_reasoning += " 影响在可控范围内，板凳深度足以弥补部分火力。"

        return {
            "original_xg": round(team_base_xg, 3),
            "adjusted_xg": round(adjusted_xg, 3),
            "net_xg_delta": round(net_xg_delta, 3),
            "missing_players_impact": missing_players,
            "llm_semantic_reasoning": semantic_reasoning
        }

# --- 工具函数供 Agent 调用 ---
def adjust_team_xg_by_players(team_base_xg: float, missing_players: List[Dict[str, Any]]) -> str:
    """
    供大语言模型(LLM)调用的工具函数。
    输入基础 xG 和缺阵球员的 xG90/xA90 数据，返回调整后的新预期进球。
    """
    logger.info(f"正在计算球员伤停对预期进球的精确衰减 (Base xG: {team_base_xg})...")
    adjuster = PlayerImpactAdjuster()
    result = adjuster.calculate_xg_adjustment(team_base_xg, missing_players)
    return json.dumps(result, ensure_ascii=False)

if __name__ == "__main__":
    import json
    # 测试：曼城 (初始 xG 2.4)，德布劳内缺阵 (xg90=0.25, xa90=0.40)
    missing = [{"name": "De Bruyne", "xg90": 0.25, "xa90": 0.40, "minutes_share": 1.0}]
    print(adjust_team_xg_by_players(2.40, missing))