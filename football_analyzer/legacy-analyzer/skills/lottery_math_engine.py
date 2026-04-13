import itertools
from decimal import Decimal, ROUND_HALF_EVEN
from typing import List, Dict, Tuple, Union

class LotteryMathEngine:
    """
    中国体育彩票量化计算引擎 (核心组合数学与奖金计算)
    支持：竞彩足球、北京单场、传统足彩、以及未来的数字彩票预留。
    """
    
    @staticmethod
    def jingcai_round(odds_list: List[float]) -> float:
        """
        竞彩特有的修约规则 (逢分进角/四舍五入 - 本质为银行家舍入法保留两位小数)
        单注奖金 = 2 * 赔率乘积，然后保留两位小数。
        注意：为避免浮点数精度丢失，整个乘法过程必须使用 Decimal
        """
        prod = Decimal('1.0')
        for o in odds_list:
            prod *= Decimal(str(o))
            
        prize = Decimal('2.0') * prod
        rounded = prize.quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN)
        return float(rounded)
        
    @staticmethod
    def apply_tax(prize: float) -> float:
        """
        计算个人所得税。单注中奖金额超过10000元，缴纳20%个税。
        """
        if prize > 10000:
            return prize * 0.8
        return prize
        
    @staticmethod
    def get_jingcai_max_limit(num_matches: int) -> float:
        """获取竞彩最高限额"""
        if num_matches <= 1:
            return 100000.0
        elif num_matches <= 3:
            return 200000.0
        elif num_matches <= 5:
            return 500000.0
        else:
            return 1000000.0

    @staticmethod
    def get_mxn_combinations(m: int, n: int) -> List[int]:
        """
        解析 M串N 的具体组合。例如 4串11 包含 2串1, 3串1, 4串1。
        返回需要组合的长度列表，例如 [2, 3, 4]
        """
        # 常见竞彩M串N映射字典
        mxn_map = {
            (3, 3): [2], (3, 4): [2, 3],
            (4, 4): [3], (4, 5): [3, 4], (4, 6): [2], (4, 11): [2, 3, 4],
            (5, 5): [4], (5, 6): [4, 5], (5, 10): [2], (5, 16): [3, 4, 5], (5, 20): [2, 3], (5, 26): [2, 3, 4, 5],
            (6, 6): [5], (6, 7): [5, 6], (6, 15): [2], (6, 20): [3], (6, 22): [4, 5, 6], (6, 35): [2, 3], (6, 42): [3, 4, 5, 6], (6, 50): [2, 3, 4], (6, 57): [2, 3, 4, 5, 6],
            (7, 7): [6], (7, 8): [6, 7], (7, 21): [5], (7, 35): [4], (7, 120): [2, 3, 4, 5, 6, 7],
            (8, 8): [7], (8, 9): [7, 8], (8, 28): [6], (8, 56): [5], (8, 70): [4], (8, 247): [2, 3, 4, 5, 6, 7, 8]
        }
        if n == 1:
            return [m]
        return mxn_map.get((m, n), [m])

    @classmethod
    def calculate_jingcai_mxn(cls, matches: List[Dict], m: int, n: int, multiple: int = 1) -> Dict:
        """
        计算竞彩M串N的奖金区间（最低保本奖金，最高理论奖金）
        matches: [{"odds": [1.5, 3.2], "play_type": "SPF"}, {"odds": [2.0], "play_type": "BF"}, ...]
        这里假设传入的是每个比赛选中的赔率列表。为了计算极值，我们会遍历所有可能的全对/错一场组合。
        """
        if len(matches) != m:
            return {"error": f"传入的比赛场数 {len(matches)} 与 M串N 的 M={m} 不符"}
            
        # 校验混合过关木桶效应
        max_allowed_legs = 8
        for match in matches:
            pt = match.get("play_type", "SPF")
            if pt in ["BF", "BQC"]:
                max_allowed_legs = min(max_allowed_legs, 4) # 比分/半全场最高4关
            elif pt == "ZJQ":
                max_allowed_legs = min(max_allowed_legs, 6) # 总进球最高6关
        
        if m > max_allowed_legs:
            return {"error": f"触发混合过关木桶效应，包含 {pt} 玩法，最高只能串 {max_allowed_legs} 关"}

        c_lengths = cls.get_mxn_combinations(m, n)
        
        # 展开每场比赛的选择，计算理论最高奖金 (全对，且都打出最高赔率)
        # 和最低中奖奖金 (刚好命中能中奖的最少场次，且打出最低赔率)
        max_odds_per_match = [max(match["odds"]) for match in matches]
        min_odds_per_match = [min(match["odds"]) for match in matches]
        
        def _calc_total_prize(odds_list: List[float], lengths: List[int]) -> float:
            total = 0.0
            for length in lengths:
                for combo in itertools.combinations(odds_list, length):
                    # 单注奖金计算 (内置了正确的 Decimal 和四舍五入)
                    single_prize = cls.jingcai_round(list(combo))
                    # 最低2元
                    single_prize = max(2.0, single_prize)
                    # 封顶
                    single_prize = min(single_prize, cls.get_jingcai_max_limit(length))
                    # 税
                    single_prize = cls.apply_tax(single_prize)
                    total += single_prize
            return total * multiple

        max_prize = _calc_total_prize(max_odds_per_match, c_lengths)
        
        # 计算最低奖金：只需命中 c_lengths 中最小的那个长度
        min_hit_length = min(c_lengths)
        # 找出 min_odds_per_match 中最小的 min_hit_length 个赔率
        lowest_hit_odds = sorted(min_odds_per_match)[:min_hit_length]
        min_prize = _calc_total_prize(lowest_hit_odds, [min_hit_length])
        
        # 计算总注数
        total_bets = 0
        for length in c_lengths:
            # 注数 = 各场选项数的组合
            for combo in itertools.combinations([len(match["odds"]) for match in matches], length):
                prod = 1
                for c in combo:
                    prod *= c
                total_bets += prod
                
        return {
            "m": m,
            "n": n,
            "total_bets": total_bets,
            "total_cost": total_bets * 2 * multiple,
            "min_prize": round(min_prize, 2),
            "max_prize": round(max_prize, 2)
        }

    @classmethod
    def calculate_beijing_single(cls, matches: List[Dict], m: int, n: int, multiple: int = 1) -> Dict:
        """
        北京单场奖金计算。
        北单单注奖金 = 2 * 65% * SP值乘积
        北单允许最高15关。
        """
        if m > 15:
            return {"error": "北京单场最高支持15关"}
            
        c_lengths = cls.get_mxn_combinations(m, n)
        max_sp_per_match = [max(match["odds"]) for match in matches]
        
        def _calc_total_prize(sp_list: List[float], lengths: List[int]) -> float:
            total = 0.0
            for length in lengths:
                for combo in itertools.combinations(sp_list, length):
                    # 北单计算公式: SP连乘 * 2 * 65%
                    prod = Decimal('1.0')
                    for o in combo:
                        prod *= Decimal(str(o))
                    prize = Decimal('2.0') * prod * Decimal('0.65')
                    single_prize = float(prize.quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN))
                    single_prize = cls.apply_tax(single_prize)
                    total += single_prize
            return total * multiple
            
        max_prize = _calc_total_prize(max_sp_per_match, c_lengths)
        
        min_hit_length = min(c_lengths)
        min_sp_per_match = [min(match["odds"]) for match in matches]
        lowest_hit_sp = sorted(min_sp_per_match)[:min_hit_length]
        min_prize = _calc_total_prize(lowest_hit_sp, [min_hit_length])
        
        total_bets = 0
        for length in c_lengths:
            for combo in itertools.combinations([len(match["odds"]) for match in matches], length):
                prod = 1
                for c in combo:
                    prod *= c
                total_bets += prod
                
        return {
            "m": m,
            "n": n,
            "total_bets": total_bets,
            "total_cost": total_bets * 2 * multiple,
            "min_prize": round(min_prize, 2),
            "max_prize": round(max_prize, 2)
        }

    @classmethod
    def calculate_traditional(cls, pool_size: float, play_type: str) -> Dict:
        """
        传统足彩奖池分配机制
        14C: 一等奖70%，二等奖30%
        RX9, 6BQC, 4JQC: 一等奖100%
        """
        if play_type == "14C":
            return {
                "1st_prize_pool": pool_size * 0.70,
                "2nd_prize_pool": pool_size * 0.30
            }
        elif play_type in ["RX9", "6BQC", "4JQC"]:
            return {
                "1st_prize_pool": pool_size * 1.0,
                "2nd_prize_pool": 0.0
            }
        return {"error": "未知的传统足彩玩法"}
