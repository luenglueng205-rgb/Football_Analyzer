import math
from scipy.stats import poisson
from typing import Dict, Any

class LotteryMathEngine:
    """
    全景概率引擎：输入主客队的预期进球数 (xG)，输出包含比分、让球、总进球、半全场等全玩法概率表。
    """
    def __init__(self, max_goals: int = 7):
        self.max_goals = max_goals

    def _build_score_matrix(self, home_xg: float, away_xg: float) -> list:
        matrix = [[0.0 for _ in range(self.max_goals)] for _ in range(self.max_goals)]
        for h in range(self.max_goals):
            for a in range(self.max_goals):
                matrix[h][a] = poisson.pmf(h, home_xg) * poisson.pmf(a, away_xg)
        return matrix

    def calculate_all_markets(self, home_xg: float, away_xg: float, handicap: float = -1.0) -> Dict[str, Any]:
        matrix = self._build_score_matrix(home_xg, away_xg)
        
        # 1. 胜平负 (W/D/L)
        w, d, l = 0.0, 0.0, 0.0
        # 2. 让球胜平负 (Handicap W/D/L)
        hw, hd, hl = 0.0, 0.0, 0.0
        # 3. 总进球 (Total Goals 0-7+)
        total_goals = {str(i): 0.0 for i in range(8)}
        total_goals["7+"] = 0.0
        # 4. 上下单双 (BD: Over/Under Odd/Even) - 假设 3 球为上盘界限
        shang_dan, shang_shuang, xia_dan, xia_shuang = 0.0, 0.0, 0.0, 0.0
        
        for h in range(self.max_goals):
            for a in range(self.max_goals):
                prob = matrix[h][a]
                
                # W/D/L
                if h > a: w += prob
                elif h == a: d += prob
                else: l += prob
                
                # Handicap (让球)
                adjusted_h = h + handicap
                if adjusted_h > a: hw += prob
                elif adjusted_h == a: hd += prob
                else: hl += prob
                
                # Total Goals
                tg = h + a
                if tg >= 7: total_goals["7+"] += prob
                else: total_goals[str(tg)] += prob
                
                # 上下单双 (北单玩法: 3球以上为上，偶数为双)
                is_shang = (tg >= 3)
                is_shuang = (tg % 2 == 0)
                if is_shang and not is_shuang: shang_dan += prob
                elif is_shang and is_shuang: shang_shuang += prob
                elif not is_shang and not is_shuang: xia_dan += prob
                elif not is_shang and is_shuang: xia_shuang += prob

        # 5. 简单的半全场预估 (Half-Time/Full-Time) - 简化逻辑：半场 xG 大致为全场一半
        ht_w, ht_d, ht_l = 0.0, 0.0, 0.0
        ht_matrix = self._build_score_matrix(home_xg * 0.45, away_xg * 0.45) # 假设半场进球偏少
        for hh in range(self.max_goals):
            for ha in range(self.max_goals):
                p = ht_matrix[hh][ha]
                if hh > ha: ht_w += p
                elif hh == ha: ht_d += p
                else: ht_l += p
                
        # 组装半全场 9 种结果的近似概率 (简单相乘近似，仅供 AI 参考)
        htft = {
            "胜胜": ht_w * w, "胜平": ht_w * d, "胜负": ht_w * l,
            "平胜": ht_d * w, "平平": ht_d * d, "平负": ht_d * l,
            "负胜": ht_l * w, "负平": ht_l * d, "负负": ht_l * l,
        }
        # 归一化 HTFT
        htft_sum = sum(htft.values())
        if htft_sum > 0:
            htft = {k: v / htft_sum for k, v in htft.items()}

        return {
            "match_prob": {"Win": round(float(w), 4), "Draw": round(float(d), 4), "Lose": round(float(l), 4)},
            "handicap_prob": {"Handicap_Win": round(float(hw), 4), "Handicap_Draw": round(float(hd), 4), "Handicap_Lose": round(float(hl), 4)},
            "total_goals": {k: round(float(v), 4) for k, v in total_goals.items()},
            "bd_up_down": {"上单": round(float(shang_dan), 4), "上双": round(float(shang_shuang), 4), "下单": round(float(xia_dan), 4), "下双": round(float(xia_shuang), 4)},
            "ht_ft_prob": {k: round(float(v), 4) for k, v in htft.items()}
        }
