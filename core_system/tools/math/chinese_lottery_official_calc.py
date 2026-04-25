import math
from itertools import combinations
import numpy as np

class ChineseLotteryOfficialCalculator:
    """
    2026 AI-Native: 中国体彩官方规则终极计算器 (The Official Rule Engine)
    这里封装了竞彩、北单、传统足彩最硬核的官方奖金计算、串关组合、抽水和封顶规则。
    AI 必须调用此工具，才能算出真实合法的奖金，而不是盲目相信数学期望。
    """

    # ==========================================
    # 1. 竞彩足球 (Jingcai) 官方规则
    # ==========================================
    @staticmethod
    def calculate_jingcai_mn_combinations(matches_count: int, pass_type: int) -> int:
        """
        竞彩 M串N 基础组合数计算 (例如 3串1, 4串11)
        pass_type: 几串几的后者，这里简化为基础的 N 串 1 (N-pass-1) 组合数
        真实体彩支持如 4串11 (包含 6个2关, 4个3关, 1个4关)，需在此基础扩展。
        这里提供最核心的 N 关组合数计算。
        """
        if pass_type > matches_count:
            return 0
        return math.comb(matches_count, pass_type)

    @staticmethod
    def calculate_jingcai_max_bonus(selected_odds: list, pass_type: int, bet_amount: float = 2.0) -> float:
        """
        竞彩最大理论奖金计算 (包含官方单注封顶规则)
        selected_odds: 选中的每场比赛的最大赔率列表 [1.85, 2.10, 3.50, ...]
        pass_type: N 串 1
        """
        if len(selected_odds) < pass_type:
            return 0.0
            
        # 1. 算出所有可能的 N 串 1 组合
        combos = list(combinations(selected_odds, pass_type))
        
        # 2. 官方硬性单注封顶风控
        # 2-3关: 20万; 4-5关: 50万; 6关及以上: 100万
        if pass_type <= 3: max_limit = 200_000.0
        elif pass_type <= 5: max_limit = 500_000.0
        else: max_limit = 1_000_000.0

        total_max_bonus = 0.0
        for combo in combos:
            # 基础奖金 = 2元 * 赔率连乘
            combo_bonus = bet_amount * np.prod(combo)
            # 应用国家单注封顶
            combo_bonus = min(combo_bonus, max_limit)
            # 应用国家个人所得税 (单注 >= 1万 扣 20%)
            if combo_bonus >= 10000.0:
                combo_bonus *= 0.80
                
            total_max_bonus += combo_bonus
            
        return round(total_max_bonus, 2)

    # ==========================================
    # 2. 北京单场 (Beidan) 官方规则
    # ==========================================
    @staticmethod
    def calculate_beidan_real_sp(estimated_sp_list: list) -> float:
        """
        北京单场真实 SP 奖金计算 (65% 强制抽水)
        北单的 65% 乘数在整个串关组合中【只乘一次】。
        """
        # 基础奖金 = 2元 * SP连乘 * 65%
        raw_bonus = 2.0 * np.prod(estimated_sp_list) * 0.65
        
        # 官方 2元保底机制
        real_bonus = max(raw_bonus, 2.0)
        
        # 依法扣税 (单注 >= 1万 扣 20%)
        if real_bonus >= 10000.0:
            real_bonus *= 0.80
            
        return round(real_bonus, 2)

    # ==========================================
    # 3. 传统足彩 14场 (Toto 14) 官方规则
    # ==========================================
    @staticmethod
    def estimate_toto14_prize(total_pool: float, rollover_pool: float, estimated_winners_1st: int, estimated_winners_2nd: int) -> dict:
        """
        传统足彩 14场 真实奖池分配预估
        一等奖 70%, 二等奖 30%。加上往期滚存 (全给一等奖)。单注封顶 500 万。
        """
        # 计算当期可分配总奖金 (扣除体彩中心发行费后，假设 total_pool 已是净奖池)
        prize_1st_total = (total_pool * 0.70) + rollover_pool
        prize_2nd_total = total_pool * 0.30
        
        # 估算单注奖金
        prize_1st_single = prize_1st_total / estimated_winners_1st if estimated_winners_1st > 0 else 0.0
        prize_2nd_single = prize_2nd_total / estimated_winners_2nd if estimated_winners_2nd > 0 else 0.0
        
        # 官方单注最高封顶 500 万
        prize_1st_single = min(prize_1st_single, 5_000_000.0)
        prize_2nd_single = min(prize_2nd_single, 5_000_000.0)
        
        # 依法扣税 (单注 >= 1万 扣 20%)
        if prize_1st_single >= 10000.0: prize_1st_single *= 0.80
        if prize_2nd_single >= 10000.0: prize_2nd_single *= 0.80
            
        return {
            "1st_prize_per_ticket": round(prize_1st_single, 2),
            "2nd_prize_per_ticket": round(prize_2nd_single, 2),
            "is_firepot": prize_1st_single < 1000.0 # 俗称火锅奖 (低于1000元)
        }

if __name__ == "__main__":
    print("==================================================")
    print("🇨🇳 [Official Rules] 中国体彩官方规则计算引擎自检...")
    print("==================================================")
    
    # 1. 竞彩 4串1 极端赔率测试 (测试单注封顶与扣税)
    # 假设买了 4 场高赔率爆冷 (平均赔率 25.0)
    odds_4c1 = [25.0, 25.0, 25.0, 25.0]
    max_bonus = ChineseLotteryOfficialCalculator.calculate_jingcai_max_bonus(odds_4c1, pass_type=4)
    print(f"   -> 🎫 [竞彩 4串1] 极端赔率理论奖金: {2.0 * (25**4):.2f}元 | 官方风控+税后真实奖金: {max_bonus}元")
    
    # 2. 北单 3串1 测试 (测试 65% 抽水与保底)
    # 假设买了 3 场超级大热 (SP极低 1.1)
    sp_3c1 = [1.1, 1.1, 1.1]
    beidan_bonus = ChineseLotteryOfficialCalculator.calculate_beidan_real_sp(sp_3c1)
    print(f"   -> 🎟️ [北单 3串1] 理论乘积: {2.0 * (1.1**3):.2f}元 | 官方65%抽水+保底后真实奖金: {beidan_bonus}元")
    
    # 3. 足彩 14场 测试 (测试火锅奖预警)
    # 假设奖池 3000 万，无滚存。如果全是正路，估计有 5 万人中一等奖
    toto_prize = ChineseLotteryOfficialCalculator.estimate_toto14_prize(30_000_000, 0, 50000, 200000)
    print(f"   -> 💣 [足彩14场] 预测一等奖单注: {toto_prize['1st_prize_per_ticket']}元 | 是否为火锅奖: {toto_prize['is_firepot']}")
