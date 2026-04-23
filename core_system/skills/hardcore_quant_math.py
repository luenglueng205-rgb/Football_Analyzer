import math
import numpy as np

class HardcoreQuantMath:
    """
    2026 AI-Native: 瘦四肢，硬骨头 (Hard Bones)
    这里没有任何业务胶水代码，只有最纯粹的体育博彩数学定理。
    这些函数将作为 Tools 供大模型 (LLM) 自主调用，确保其在产生幻觉时仍能守住数学底线。
    """

    @staticmethod
    def pinnacle_devig(home_odds: float, draw_odds: float, away_odds: float) -> dict:
        """
        [专业级] 平博去水 (Pinnacle De-vigging) - 比例法 (Proportional Method)
        博彩公司的赔率包含了抽水 (Vig/Margin)。直接用 1/赔率 算出的胜率是错误的（总和会大于 100%）。
        该函数剥离庄家利润，还原真实的隐含胜率 (True Implied Probability)。
        """
        implied_home = 1 / home_odds
        implied_draw = 1 / draw_odds
        implied_away = 1 / away_odds
        
        margin = implied_home + implied_draw + implied_away
        
        true_home = implied_home / margin
        true_draw = implied_draw / margin
        true_away = implied_away / margin
        
        return {
            "true_home_prob": round(true_home, 4),
            "true_draw_prob": round(true_draw, 4),
            "true_away_prob": round(true_away, 4),
            "bookmaker_margin": round(margin - 1.0, 4)
        }

    @staticmethod
    def bivariate_poisson_match_simulation(xg_home: float, xg_away: float, rho: float = -0.05) -> dict:
        """
        [专业级] 双变量泊松分布 (Bivariate Poisson) 比赛推演
        输入主客队的预期进球数 (xG)，输出胜平负的确切概率。
        引入 rho 参数处理足球比赛中进球数的负相关性 (例如主队进球多时客队进球通常少)。
        """
        max_goals = 10
        prob_matrix = np.zeros((max_goals, max_goals))
        
        for x in range(max_goals):
            for y in range(max_goals):
                # 独立泊松概率
                p_x = (math.exp(-xg_home) * (xg_home ** x)) / math.factorial(x)
                p_y = (math.exp(-xg_away) * (xg_away ** y)) / math.factorial(y)
                
                # Dixon-Coles 修正因子 (处理 0-0, 1-0, 0-1, 1-1 的低分微调)
                correction = 1.0
                if x == 0 and y == 0:
                    correction = 1 - xg_home * xg_away * rho
                elif x == 0 and y == 1:
                    correction = 1 + xg_home * rho
                elif x == 1 and y == 0:
                    correction = 1 + xg_away * rho
                elif x == 1 and y == 1:
                    correction = 1 - rho
                    
                prob_matrix[x, y] = max(0, p_x * p_y * correction)

        # 归一化矩阵
        prob_matrix = prob_matrix / np.sum(prob_matrix)
        
        # 统计胜平负
        home_win = np.sum(np.tril(prob_matrix, -1))
        draw = np.sum(np.diag(prob_matrix))
        away_win = np.sum(np.triu(prob_matrix, 1))
        
        return {
            "home_win_prob": round(float(home_win), 4),
            "draw_prob": round(float(draw), 4),
            "away_win_prob": round(float(away_win), 4)
        }

    @staticmethod
    def fractional_kelly_criterion(prob: float, decimal_odds: float, fraction: float = 0.25) -> float:
        """
        [专业级] 分数凯利准则 (Fractional Kelly)
        计算最优下注比例。为了防爆仓，专业机构通常只下注全凯利的 1/4 (Quarter Kelly)。
        """
        b = decimal_odds - 1.0
        q = 1.0 - prob
        
        full_kelly = (b * prob - q) / b
        
        if full_kelly <= 0:
            return 0.0
            
        safe_kelly = full_kelly * fraction
        return round(safe_kelly, 4)

if __name__ == "__main__":
    print("==================================================")
    print("🧮 [Hardcore Math] 极简专业数学工具库自检...")
    print("==================================================")
    
    # 1. 平博去水测试
    devig = HardcoreQuantMath.pinnacle_devig(1.95, 3.60, 4.00)
    print(f"   -> 💧 [De-vigging] 平博赔率 1.95/3.60/4.00 去水后真实主胜率: {devig['true_home_prob']:.2%}")
    
    # 2. 泊松推演测试 (假设 AI 分析后给出 xG: 主队 1.8, 客队 1.1)
    poisson = HardcoreQuantMath.bivariate_poisson_match_simulation(1.8, 1.1)
    print(f"   -> ⚽ [Poisson] 预期进球 (1.8 vs 1.1) 推演胜率: 主 {poisson['home_win_prob']:.2%} | 平 {poisson['draw_prob']:.2%} | 客 {poisson['away_win_prob']:.2%}")
    
    # 3. 凯利仓位测试
    kelly = HardcoreQuantMath.fractional_kelly_criterion(0.55, 2.00, fraction=0.25)
    print(f"   -> 💰 [Kelly] 55%胜率买2.00赔率，1/4凯利建议仓位: {kelly:.2%}")
