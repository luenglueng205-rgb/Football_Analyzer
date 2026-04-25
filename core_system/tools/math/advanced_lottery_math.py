import math
import numpy as np

class AdvancedLotteryMath:
    @staticmethod
    def dixon_coles_poisson_adjustment(xg_home: float, xg_away: float, rho: float = -0.05, zero_inflation: float = 1.05) -> dict:
        """
        [实战强化] Dixon-Coles 双变量泊松分布 + 零膨胀修正
        修复了纯泊松模型严重低估 0-0 平局发生率的致命缺陷。
        zero_inflation: 对 0-0 结果的额外放大系数 (默认放大 5%)
        """
        max_goals = 10
        prob_matrix = np.zeros((max_goals, max_goals))
        
        for x in range(max_goals):
            for y in range(max_goals):
                p_x = (math.exp(-xg_home) * (xg_home ** x)) / math.factorial(x)
                p_y = (math.exp(-xg_away) * (xg_away ** y)) / math.factorial(y)
                
                correction = 1.0
                if x == 0 and y == 0:
                    # Dixon-Coles 修正 + 零膨胀修正
                    correction = (1 - xg_home * xg_away * rho) * zero_inflation
                elif x == 0 and y == 1:
                    correction = 1 + xg_home * rho
                elif x == 1 and y == 0:
                    correction = 1 + xg_away * rho
                elif x == 1 and y == 1:
                    correction = 1 - rho
                    
                prob_matrix[x, y] = max(0, p_x * p_y * correction)

        prob_matrix = prob_matrix / np.sum(prob_matrix)
        
        return {
            "home_win": round(float(np.sum(np.tril(prob_matrix, -1))), 4),
            "draw": round(float(np.sum(np.diag(prob_matrix))), 4),
            "away_win": round(float(np.sum(np.triu(prob_matrix, 1))), 4),
            "prob_0_0": round(float(prob_matrix[0, 0]), 4)
        }
