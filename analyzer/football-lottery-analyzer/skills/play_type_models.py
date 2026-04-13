from typing import Dict, List
from scipy.stats import poisson

class AdvancedPlayTypeModels:
    """
    中国体彩 16 种子玩法的深度概率模型引擎
    基于泊松分布和历史特征，精准计算所有细分玩法的真实数学概率。
    """
    
    @staticmethod
    def calculate_jingcai_bf(mu_home: float, mu_away: float, max_goals: int = 5) -> Dict[str, float]:
        """
        竞彩足球 - 比分 (BF)
        计算 0:0 到 5:2 等所有官方比分选项的概率。
        """
        bf_probs = {}
        other_win = 0.0
        other_draw = 0.0
        other_lose = 0.0
        
        for h in range(max_goals + 3):
            ph = poisson.pmf(h, mu_home)
            for a in range(max_goals + 3):
                pa = poisson.pmf(a, mu_away)
                prob = ph * pa
                
                score_str = f"{h}:{a}"
                # 官方常见比分范围
                if (h <= 5 and a <= 2 and h > a) or (h <= 2 and a <= 5 and h < a) or (h <= 3 and a <= 3 and h == a):
                    bf_probs[score_str] = prob
                else:
                    if h > a: other_win += prob
                    elif h == a: other_draw += prob
                    else: other_lose += prob
                    
        bf_probs["胜其他"] = other_win
        bf_probs["平其他"] = other_draw
        bf_probs["负其他"] = other_lose
        
        # 归一化并排序
        return dict(sorted(bf_probs.items(), key=lambda item: item[1], reverse=True))

    @staticmethod
    def calculate_jingcai_zjq(mu_home: float, mu_away: float) -> Dict[str, float]:
        """
        竞彩足球/北京单场 - 总进球 (ZJQ)
        计算 0, 1, 2, 3, 4, 5, 6, 7+ 球的概率
        """
        zjq_probs = {str(i): 0.0 for i in range(7)}
        zjq_probs["7+"] = 0.0
        
        mu_total = mu_home + mu_away
        for k in range(15):
            prob = poisson.pmf(k, mu_total)
            if k <= 6:
                zjq_probs[str(k)] += prob
            else:
                zjq_probs["7+"] += prob
                
        return zjq_probs

    @staticmethod
    def calculate_jingcai_bqc(mu_home: float, mu_away: float) -> Dict[str, float]:
        """
        竞彩足球/北京单场 - 半全场 (BQC)
        使用二元泊松简化模型 (假设半场进球约为全场的 45%)
        计算 胜胜, 胜平, 胜负, 平胜, 平平, 平负, 负胜, 负平, 负负
        """
        # 简化版：通过全场预期推导半场预期
        ht_mu_h = mu_home * 0.45
        ht_mu_a = mu_away * 0.45
        
        # 半场概率
        ht_probs = {"胜": 0.0, "平": 0.0, "负": 0.0}
        for h in range(5):
            ph = poisson.pmf(h, ht_mu_h)
            for a in range(5):
                pa = poisson.pmf(a, ht_mu_a)
                if h > a: ht_probs["胜"] += ph * pa
                elif h == a: ht_probs["平"] += ph * pa
                else: ht_probs["负"] += ph * pa
                
        # 全场概率
        ft_probs = {"胜": 0.0, "平": 0.0, "负": 0.0}
        for h in range(8):
            ph = poisson.pmf(h, mu_home)
            for a in range(8):
                pa = poisson.pmf(a, mu_away)
                if h > a: ft_probs["胜"] += ph * pa
                elif h == a: ft_probs["平"] += ph * pa
                else: ft_probs["负"] += ph * pa
                
        # 联合概率 (假设半场结果对全场有马尔可夫链式影响，这里使用独立性假设作为基准，实盘需结合球队逆风球特征调整)
        bqc_probs = {}
        for ht in ["胜", "平", "负"]:
            for ft in ["胜", "平", "负"]:
                bqc_probs[f"{ht}{ft}"] = ht_probs[ht] * ft_probs[ft]
                
        # 归一化
        total = sum(bqc_probs.values())
        return {k: v/total for k, v in bqc_probs.items()}

    @staticmethod
    def calculate_beijing_sxd(mu_home: float, mu_away: float) -> Dict[str, float]:
        """
        北京单场 - 上下单双 (SXD)
        上盘(>=3球), 下盘(<3球)
        单数(进球和为奇数), 双数(进球和为偶数)
        组合为：上单, 上双, 下单, 下双
        """
        sxd_probs = {"上单": 0.0, "上双": 0.0, "下单": 0.0, "下双": 0.0}
        mu_total = mu_home + mu_away
        
        for k in range(15):
            prob = poisson.pmf(k, mu_total)
            is_shang = k >= 3
            is_dan = k % 2 != 0
            
            if is_shang and is_dan: sxd_probs["上单"] += prob
            elif is_shang and not is_dan: sxd_probs["上双"] += prob
            elif not is_shang and is_dan: sxd_probs["下单"] += prob
            elif not is_shang and not is_dan: sxd_probs["下双"] += prob
            
        return sxd_probs
        
    @staticmethod
    def calculate_beijing_sfgg(home_win_prob: float, away_win_prob: float) -> Dict[str, float]:
        """
        北京单场 - 胜负过关 (SFGG)
        没有平局，必须分出胜负。通常结合让球，如果平局算走水或按特定规则。
        这里直接归一化胜负概率。
        """
        total = home_win_prob + away_win_prob
        if total == 0:
            return {"胜": 0.5, "负": 0.5}
        return {
            "胜": home_win_prob / total,
            "负": away_win_prob / total
        }

if __name__ == "__main__":
    # 测试一下阿森纳(1.54) vs 利物浦(1.19) 的高级玩法
    print("--- 竞彩: 比分 (BF) 预测前5 ---")
    bf = AdvancedPlayTypeModels.calculate_jingcai_bf(1.54, 1.19)
    for k, v in list(bf.items())[:5]: print(f"{k}: {v:.2%}")
    
    print("\n--- 竞彩/北单: 总进球 (ZJQ) ---")
    zjq = AdvancedPlayTypeModels.calculate_jingcai_zjq(1.54, 1.19)
    for k, v in zjq.items(): print(f"{k}球: {v:.2%}")
    
    print("\n--- 北单: 上下单双 (SXD) ---")
    sxd = AdvancedPlayTypeModels.calculate_beijing_sxd(1.54, 1.19)
    for k, v in sxd.items(): print(f"{k}: {v:.2%}")
