import math
from typing import Dict, Any, List

class BayesianXGModel:
    """
    2026 版贝叶斯预期进球 (Bayesian xG) 模型
    不再单纯取历史平均进球，而是：
    1. 基于身价或历史档次给出先验 (Prior)
    2. 基于近期表现平滑后验 (Posterior)
    3. 基于伤停名单动态衰减 xG 贡献
    """
    
    @staticmethod
    def adjust_xg_for_injuries(base_xg: float, injuries: List[Dict]) -> float:
        """
        根据伤停名单衰减 xG
        伤停列表里如果包含 'Forward' 或 'Midfielder' 并且状态是 'Out'，则衰减进攻火力。
        """
        if not injuries:
            return base_xg
            
        decay = 0.0
        for injury in injuries:
            status = injury.get("status", "").lower()
            position = injury.get("position", "").lower()
            
            if status in ["out", "injured"]:
                if position == "forward":
                    decay += 0.15  # 主力前锋伤停，衰减 15% 进攻期望
                elif position == "midfielder":
                    decay += 0.08  # 主力中场伤停，衰减 8%
                    
        decay = min(decay, 0.40) # 最大衰减不超过 40%
        return base_xg * (1.0 - decay)
        
    @staticmethod
    def calculate_bayesian_xg(team_stats: Dict, league_avg: float, injuries: List[Dict] = None) -> float:
        """
        计算贝叶斯平滑后的 xG
        """
        sample_size = team_stats.get("sample_size", 0)
        recent_avg = team_stats.get("avg_home_goals", team_stats.get("avg_away_goals", league_avg))
        
        # 贝叶斯平滑：样本越小，越向联赛平均回归
        # 假设 10 场是一个稳定的先验权重节点
        prior_weight = 10.0 / (10.0 + sample_size)
        posterior_weight = 1.0 - prior_weight
        
        bayesian_xg = (league_avg * prior_weight) + (recent_avg * posterior_weight)
        
        # 伤停衰减
        final_xg = BayesianXGModel.adjust_xg_for_injuries(bayesian_xg, injuries)
        
        return max(0.1, final_xg) # 保证至少有 0.1 的 xG 防止数学异常
