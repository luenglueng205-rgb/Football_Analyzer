import json
import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BayesianUpdater:
    """
    贝叶斯先验与动态更新引擎 (Bayesian Hierarchical Modeler)。
    专门处理赛季初、换帅或缺乏历史数据时的“冷启动”预测。
    结合先验知识（如球队身价、主教练等级）和少量近期比赛数据，计算出更准确的贝叶斯 xG。
    """
    
    def __init__(self):
        # 基础身价转化为先验 xG 的映射常数 (例如英超: 曼城第一档，升班马第四档)
        self.value_tier_to_prior_xg = {
            1: 2.2,  # 顶级豪门
            2: 1.6,  # 强队
            3: 1.2,  # 中游球队
            4: 0.9   # 保级队/升班马
        }

    def calculate_bayesian_xg(self, team_value_tier: int, recent_xg_avg: float, matches_played: int, is_new_manager: bool = False, manager_elo_boost: float = 0.0) -> Dict[str, Any]:
        """
        核心方法：计算贝叶斯更新后的 xG
        :param team_value_tier: 球队身价档次 (1-4，1为最高)
        :param recent_xg_avg: 球队近期的场均实际 xG
        :param matches_played: 近期样本比赛场数 (决定后验权重)
        :param is_new_manager: 是否刚刚换帅
        :param manager_elo_boost: 新帅带来的战术红利加成 (如名帅接手 +0.2)
        """
        # 1. 获取先验 xG (Prior xG)
        prior_xg = self.value_tier_to_prior_xg.get(team_value_tier, 1.2)
        
        if is_new_manager:
            prior_xg += manager_elo_boost
            
        # 2. 计算贝叶斯权重 (样本越多，越相信近期实际数据；样本越少，越相信身价先验)
        # 假设 10 场比赛为完全置信阈值
        confidence_in_recent = min(matches_played / 10.0, 0.9)
        confidence_in_prior = 1.0 - confidence_in_recent
        
        # 3. 贝叶斯后验更新 (Posterior Update)
        posterior_xg = (prior_xg * confidence_in_prior) + (recent_xg_avg * confidence_in_recent)
        
        semantic_reasoning = f"【贝叶斯推断】"
        if matches_played < 5:
            semantic_reasoning += f" 样本量仅 {matches_played} 场极小。系统强依赖身价先验({prior_xg})，贝叶斯修正后预期进球从近期表象的 {recent_xg_avg} 调整为 {round(posterior_xg, 2)}。"
        elif is_new_manager:
            semantic_reasoning += f" 发生换帅事件，注入新帅红利({manager_elo_boost})。历史数据失效，贝叶斯重置 xG 为 {round(posterior_xg, 2)}。"
        else:
            semantic_reasoning += f" 样本量充足，近期数据置信度达 {round(confidence_in_recent*100)}%，贝叶斯后验 xG 为 {round(posterior_xg, 2)}。"

        return {
            "prior_xg": round(prior_xg, 3),
            "recent_xg_avg": round(recent_xg_avg, 3),
            "posterior_xg": round(posterior_xg, 3),
            "confidence_weight": round(confidence_in_recent, 3),
            "llm_semantic_reasoning": semantic_reasoning
        }

def get_bayesian_xg_prior(team_value_tier: int, recent_xg_avg: float, matches_played: int, is_new_manager: bool, manager_elo_boost: float) -> str:
    logger.info("执行贝叶斯先验推断 (Bayesian Update)...")
    updater = BayesianUpdater()
    res = updater.calculate_bayesian_xg(team_value_tier, recent_xg_avg, matches_played, is_new_manager, manager_elo_boost)
    return json.dumps(res, ensure_ascii=False)

if __name__ == "__main__":
    # 测试：一支豪门球队(1档)开局3场表现极差(场均xG仅0.8)，且刚换名帅(加成0.3)
    print(get_bayesian_xg_prior(1, 0.8, 3, True, 0.3))