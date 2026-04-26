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
        # 1. 破坏性测试修复：防范负数 xG 导致的 NaN 崩溃
        if home_xg < 0 or away_xg < 0:
            raise ValueError("xG (预期进球) 必须大于等于 0")
            
        # 2. 破坏性测试修复：当遇到极大 xG 时，动态扩展泊松矩阵，防止截断导致概率丢失
        # 正常比赛 7 个球够了，如果是 20.0 xG，矩阵需要扩大到至少 45 才能收敛
        dynamic_max_goals = max(self.max_goals, int(max(home_xg, away_xg) * 2 + 5))
        
        # 构建泊松概率矩阵
        matrix = [[0.0 for _ in range(dynamic_max_goals)] for _ in range(dynamic_max_goals)]
        for h in range(dynamic_max_goals):
            for a in range(dynamic_max_goals):
                matrix[h][a] = poisson.pmf(h, home_xg) * poisson.pmf(a, away_xg)
        
        # 1. 胜平负 (W/D/L)
        w, d, l = 0.0, 0.0, 0.0
        # 2. 让球胜平负 (Handicap W/D/L)
        hw, hd, hl = 0.0, 0.0, 0.0
        # 3. 总进球 (Total Goals 0-7+)
        total_goals = {str(i): 0.0 for i in range(8)}
        total_goals["7+"] = 0.0
        # 4. 上下单双 (BD: Over/Under Odd/Even) - 假设 3 球为上盘界限
        shang_dan, shang_shuang, xia_dan, xia_shuang = 0.0, 0.0, 0.0, 0.0
        
        for h in range(dynamic_max_goals):
            for a in range(dynamic_max_goals):
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

        # 5. 精确的半全场预估 (Half-Time/Full-Time)
        # 足球中半场进球数约占全场的 45%，下半场约占 55%
        ht_home_xg, ht_away_xg = home_xg * 0.45, away_xg * 0.45
        sh_home_xg, sh_away_xg = home_xg * 0.55, away_xg * 0.55
        
        # 预先计算泊松概率，提升速度
        ht_dynamic_max_goals = max(self.max_goals, int(max(ht_home_xg, ht_away_xg) * 2 + 5))
        sh_dynamic_max_goals = max(self.max_goals, int(max(sh_home_xg, sh_away_xg) * 2 + 5))
        
        ht_probs_home = [poisson.pmf(i, ht_home_xg) for i in range(ht_dynamic_max_goals)]
        ht_probs_away = [poisson.pmf(i, ht_away_xg) for i in range(ht_dynamic_max_goals)]
        sh_probs_home = [poisson.pmf(i, sh_home_xg) for i in range(sh_dynamic_max_goals)]
        sh_probs_away = [poisson.pmf(i, sh_away_xg) for i in range(sh_dynamic_max_goals)]
        
        htft = {
            "胜胜": 0.0, "胜平": 0.0, "胜负": 0.0,
            "平胜": 0.0, "平平": 0.0, "平负": 0.0,
            "负胜": 0.0, "负平": 0.0, "负负": 0.0,
        }
        
        # 四重循环，精确计算半全场的联合分布
        for h1 in range(ht_dynamic_max_goals):
            for a1 in range(ht_dynamic_max_goals):
                p_ht = ht_probs_home[h1] * ht_probs_away[a1]
                if p_ht < 1e-6: continue
                
                ht_res = "胜" if h1 > a1 else "平" if h1 == a1 else "负"
                
                for h2 in range(sh_dynamic_max_goals):
                    for a2 in range(sh_dynamic_max_goals):
                        p_sh = sh_probs_home[h2] * sh_probs_away[a2]
                        ft_h = h1 + h2
                        ft_a = a1 + a2
                        ft_res = "胜" if ft_h > ft_a else "平" if ft_h == ft_a else "负"
                        
                        htft[f"{ht_res}{ft_res}"] += p_ht * p_sh
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
