import numpy as np
import math

class OmniMarketPricer:
    """
    100% AI-Native: 全玩法定价引擎 (16-Market Omni-Pricer)
    将底层的泊松分布矩阵，映射为中国体彩（竞彩/北单）所有 16 种玩法的精确胜率。
    只有算出了所有玩法的真实概率，AI 才能跨玩法寻找最高 EV 的标的。
    """
    def __init__(self, xg_home: float, xg_away: float, rho: float = -0.05):
        self.max_goals = 10
        self.prob_matrix = np.zeros((self.max_goals, self.max_goals))
        self._build_matrix(xg_home, xg_away, rho)

    def _build_matrix(self, xg_home, xg_away, rho):
        for x in range(self.max_goals):
            for y in range(self.max_goals):
                p_x = (math.exp(-xg_home) * (xg_home ** x)) / math.factorial(x)
                p_y = (math.exp(-xg_away) * (xg_away ** y)) / math.factorial(y)
                correction = 1.0
                if x == 0 and y == 0: correction = 1 - xg_home * xg_away * rho
                elif x == 0 and y == 1: correction = 1 + xg_home * rho
                elif x == 1 and y == 0: correction = 1 + xg_away * rho
                elif x == 1 and y == 1: correction = 1 - rho
                self.prob_matrix[x, y] = max(0, p_x * p_y * correction)
        self.prob_matrix = self.prob_matrix / np.sum(self.prob_matrix)

    def price_all_markets(self, handicap: int = -1) -> dict:
        """一键计算竞彩/北单所有核心玩法的真实概率"""
        markets = {}
        
        # 1. 胜平负 (1X2)
        markets["HAD_H"] = np.sum(np.tril(self.prob_matrix, -1))
        markets["HAD_D"] = np.sum(np.diag(self.prob_matrix))
        markets["HAD_A"] = np.sum(np.triu(self.prob_matrix, 1))
        
        # 2. 让球胜平负 (Handicap)
        hh, hd, ha = 0.0, 0.0, 0.0
        for x in range(self.max_goals):
            for y in range(self.max_goals):
                net_score = x - y + handicap
                if net_score > 0: hh += self.prob_matrix[x, y]
                elif net_score == 0: hd += self.prob_matrix[x, y]
                else: ha += self.prob_matrix[x, y]
        markets[f"HHAD_{handicap}_H"] = hh
        markets[f"HHAD_{handicap}_D"] = hd
        markets[f"HHAD_{handicap}_A"] = ha
        
        # 3. 总进球数 (Total Goals 0-7+)
        markets["TTG"] = {}
        for tg in range(8):
            if tg < 7:
                prob = sum(self.prob_matrix[x, y] for x in range(self.max_goals) for y in range(self.max_goals) if x+y == tg)
            else:
                prob = sum(self.prob_matrix[x, y] for x in range(self.max_goals) for y in range(self.max_goals) if x+y >= 7)
            markets["TTG"][str(tg)] = prob
            
        # 4. 北单特色：上下单双 (ShangXiaDanShuang)
        # 上(>=3球)下(<3球)，单(奇数)双(偶数)
        sxds = {"ShangDan": 0, "ShangShuang": 0, "XiaDan": 0, "XiaShuang": 0}
        for x in range(self.max_goals):
            for y in range(self.max_goals):
                tg = x + y
                prob = self.prob_matrix[x, y]
                is_shang = tg >= 3
                is_dan = (tg % 2) != 0
                if is_shang and is_dan: sxds["ShangDan"] += prob
                elif is_shang and not is_dan: sxds["ShangShuang"] += prob
                elif not is_shang and is_dan: sxds["XiaDan"] += prob
                else: sxds["XiaShuang"] += prob
        markets["SXDS"] = sxds
        
        # 5. 精确比分 (Correct Score - Top 5 likely)
        scores = []
        for x in range(self.max_goals):
            for y in range(self.max_goals):
                scores.append((f"{x}:{y}", self.prob_matrix[x, y]))
        scores.sort(key=lambda item: item[1], reverse=True)
        markets["CRS_TOP5"] = {k: v for k, v in scores[:5]}

        return markets

if __name__ == "__main__":
    # 模拟一场 AI 研判后 xG 为 主2.1 客0.8 的比赛
    pricer = OmniMarketPricer(2.1, 0.8)
    all_probs = pricer.price_all_markets(handicap=-1)
    
    print("==================================================")
    print("🎯 [Omni-Pricer] 全玩法概率降维扫描完成！")
    print("==================================================")
    print(f"1. [胜平负] 主胜: {all_probs['HAD_H']:.1%} | 平: {all_probs['HAD_D']:.1%} | 客胜: {all_probs['HAD_A']:.1%}")
    print(f"2. [让球(-1)] 让胜: {all_probs['HHAD_-1_H']:.1%} | 让平: {all_probs['HHAD_-1_D']:.1%} | 让负: {all_probs['HHAD_-1_A']:.1%}")
    print(f"3. [总进球] 2球: {all_probs['TTG']['2']:.1%} | 3球: {all_probs['TTG']['3']:.1%}")
    print(f"4. [北单上下单双] 上单: {all_probs['SXDS']['ShangDan']:.1%} | 下双: {all_probs['SXDS']['XiaShuang']:.1%}")
    print(f"5. [最高概率比分] {all_probs['CRS_TOP5']}")
