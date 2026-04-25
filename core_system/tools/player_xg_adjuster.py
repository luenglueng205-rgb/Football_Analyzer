from typing import List, Dict, Any

class PlayerXgAdjuster:
    """
    量化核心球员伤停对球队整体预期进球 (xG) 的微观衰减。
    """
    def __init__(self):
        # 定义不同角色的基础衰减系数上限
        self.role_impact_caps = {
            "striker": 0.20,      # 主力前锋伤停最多影响 20% 进球
            "playmaker": 0.15,    # 核心前腰最多影响 15% 进球
            "winger": 0.10,       # 边锋最多影响 10%
            "defender": -0.15,    # 后卫伤停主要增加失球(此处暂作为对方xG加成，本类聚焦本队xG衰减，故这里用负值表示防守端影响)
            "goalkeeper": -0.20
        }

    def calculate_adjusted_xg(self, base_xg: float, injuries: List[Dict[str, Any]]) -> float:
        """
        计算衰减后的 xG。
        injuries 格式: [{"name": "KDB", "role": "playmaker", "importance": 0.9}]
        """
        total_decay_penalty = 0.0
        
        for player in injuries:
            role = player.get("role", "striker")
            importance = player.get("importance", 0.5) # 0.0 到 1.0，1.0为绝对核心
            
            cap = self.role_impact_caps.get(role, 0.05)
            if cap > 0: # 只计算对进球有直接正面贡献的角色的衰减
                penalty = cap * importance
                total_decay_penalty += penalty
                
        # 限制总衰减不超过 35%
        total_decay_penalty = min(total_decay_penalty, 0.35)
        
        adjusted_xg = base_xg * (1.0 - total_decay_penalty)
        return round(max(0.1, adjusted_xg), 2)

# 别名：测试文件使用 PlayerImpactAdjuster 名称
PlayerImpactAdjuster = PlayerXgAdjuster
