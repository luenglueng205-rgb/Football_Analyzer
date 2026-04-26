import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MatchTimelineSimulator:
    """
    轻量级蒙特卡洛时间轴比赛模拟器。
    专门用于预测竞彩/北京单场的“半全场”(HT/FT) 和“总进球”玩法。
    利用纯数学矩阵运算，在毫秒级模拟上万场比赛的时间切片。
    """
    
    def __init__(self, num_simulations: int = 10000):
        self.num_simulations = num_simulations
        
    def _determine_outcome(self, home_goals: np.ndarray, away_goals: np.ndarray) -> np.ndarray:
        """根据进球数判断赛果 H(胜) D(平) A(负)"""
        conditions = [home_goals > away_goals, home_goals == away_goals, home_goals < away_goals]
        choices = ['3', '1', '0']  # 3:胜, 1:平, 0:负 (符合中国体彩习惯)
        return np.select(conditions, choices, default='0')

    def simulate_ht_ft_probabilities(self, home_xg: float, away_xg: float) -> Dict[str, float]:
        """
        核心方法：模拟半全场概率
        :param home_xg: 主队全场预期进球
        :param away_xg: 客队全场预期进球
        :return: 9种半全场结果的概率字典 (如 '31': 0.15 表示半场胜全场平)
        """
        # 将 xG 均摊到 90 分钟 (极简泊松过程近似为伯努利试验)
        home_prob_per_min = home_xg / 90.0
        away_prob_per_min = away_xg / 90.0

        # 生成 0-1 之间的随机数矩阵 [模拟次数, 90分钟]
        home_events = np.random.rand(self.num_simulations, 90) < home_prob_per_min
        away_events = np.random.rand(self.num_simulations, 90) < away_prob_per_min

        # 提取半场 (0-45) 和全场 (0-90) 的进球数
        home_ht_goals = home_events[:, :45].sum(axis=1)
        away_ht_goals = away_events[:, :45].sum(axis=1)
        
        home_ft_goals = home_events.sum(axis=1)
        away_ft_goals = away_events.sum(axis=1)

        # 判断半场和全场赛果
        ht_outcomes = self._determine_outcome(home_ht_goals, away_ht_goals)
        ft_outcomes = self._determine_outcome(home_ft_goals, away_ft_goals)

        # 组合为半全场结果 (如 "33", "10")
        ht_ft_combined = np.char.add(ht_outcomes, ft_outcomes)

        # 统计概率
        unique, counts = np.unique(ht_ft_combined, return_counts=True)
        probabilities = {str(k): float(v / self.num_simulations) for k, v in zip(unique, counts)}
        
        # 补齐可能概率为0的选项
        all_ht_ft = ['33', '31', '30', '13', '11', '10', '03', '01', '00']
        for outcome in all_ht_ft:
            if outcome not in probabilities:
                probabilities[outcome] = 0.0
                
        return probabilities

class TimeSliceMonteCarlo:
    """
    将 90 分钟切片，进行蒙特卡洛微观模拟，彻底颠覆静态双泊松，精准预测半全场。
    """
    def __init__(self, time_slices: int = 90):
        self.time_slices = time_slices

    def simulate_match(self, home_xg: float, away_xg: float, simulations: int = 10000) -> Dict[str, Any]:
        # 每个时间片进球概率
        home_prob_per_slice = home_xg / self.time_slices
        away_prob_per_slice = away_xg / self.time_slices
        
        home_wins = 0
        draws = 0
        away_wins = 0
        
        # 统计半全场 (Half-Time / Full-Time)
        # H: Home, D: Draw, A: Away
        ht_ft_counts = {"HH": 0, "HD": 0, "HA": 0, "DH": 0, "DD": 0, "DA": 0, "AH": 0, "AD": 0, "AA": 0}
        
        # 批量模拟矩阵运算以提高速度
        home_goals_matrix = np.random.binomial(1, home_prob_per_slice, (simulations, self.time_slices))
        away_goals_matrix = np.random.binomial(1, away_prob_per_slice, (simulations, self.time_slices))
        
        # 半场进球汇总 (前 45 分钟)
        ht_home = np.sum(home_goals_matrix[:, :45], axis=1)
        ht_away = np.sum(away_goals_matrix[:, :45], axis=1)
        
        # 全场进球汇总
        ft_home = np.sum(home_goals_matrix, axis=1)
        ft_away = np.sum(away_goals_matrix, axis=1)
        
        for i in range(simulations):
            ht_h, ht_a = ht_home[i], ht_away[i]
            ft_h, ft_a = ft_home[i], ft_away[i]
            
            # 全场赛果
            if ft_h > ft_a:
                home_wins += 1
                ft_res = "H"
            elif ft_h == ft_a:
                draws += 1
                ft_res = "D"
            else:
                away_wins += 1
                ft_res = "A"
                
            # 半场赛果
            if ht_h > ht_a:
                ht_res = "H"
            elif ht_h == ht_a:
                ht_res = "D"
            else:
                ht_res = "A"
                
            ht_ft_counts[f"{ht_res}{ft_res}"] += 1
            
        return {
            "home_win_prob": round(home_wins / simulations, 4),
            "draw_prob": round(draws / simulations, 4),
            "away_win_prob": round(away_wins / simulations, 4),
            "half_full_time": {k: round(v / simulations, 4) for k, v in ht_ft_counts.items()}
        }

# --- 工具函数供 Agent 调用 ---
def run_monte_carlo_ht_ft(home_xg: float, away_xg: float) -> str:
    """
    供大语言模型(LLM)调用的工具函数。
    返回格式化的半全场概率 JSON 字符串。
    """
    logger.info(f"正在执行蒙特卡洛时间轴模拟 (Home xG: {home_xg}, Away xG: {away_xg})...")
    simulator = MatchTimelineSimulator(num_simulations=10000)
    probs = simulator.simulate_ht_ft_probabilities(home_xg, away_xg)
    
    # 按照体彩习惯排序并格式化
    sorted_probs = dict(sorted(probs.items(), key=lambda item: item[1], reverse=True))
    
    result = {
        "home_xg": home_xg,
        "away_xg": away_xg,
        "half_full_time_probabilities": sorted_probs,
        "most_likely_ht_ft": list(sorted_probs.keys())[0],
        "note": "3=胜, 1=平, 0=负。例如 '31' 代表半场胜全场平。"
    }
    return json.dumps(result, ensure_ascii=False)

if __name__ == "__main__":
    import json
    # 测试一场势均力敌的比赛
    print(run_monte_carlo_ht_ft(1.45, 1.20))