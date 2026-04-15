import logging

logger = logging.getLogger(__name__)

class ParlayRulesEngine:
    """
    官方规则守护者：严格校验竞彩与北京单场的 M串1、M串N 及自由过关组合数学规则。
    避免因玩法组合越界导致出票失败或计算错乱。
    """
    
    def __init__(self):
        # 竞彩官方最大串关场次限制
        self.JINGCAI_MAX_LEGS = {
            "WDL": 8,       # 胜平负
            "HANDICAP": 8,  # 让球胜平负
            "GOALS": 6,     # 总进球数
            "CS": 4,        # 比分
            "HTFT": 4       # 半全场
        }
        
        # 北京单场官方最大串关场次限制
        self.BEIDAN_MAX_LEGS = {
            "WDL": 15,      # 胜平负/上下单双
            "HANDICAP": 15, # 让球胜平负
            "GOALS": 15,    # 总进球数
            "HTFT": 15,     # 半全场
            "CS": 3         # 比分
        }
        
        # 竞彩 M串N 固定组合字典映射 (M_N: [包含的串数])
        # 例如: 3串4 包含 3个2串1 和 1个3串1
        self.JINGCAI_M_N_COMBOS = {
            "3_3": [2], "3_4": [2, 3],
            "4_4": [3], "4_5": [3, 4], "4_6": [2], "4_11": [2, 3, 4],
            "5_5": [4], "5_6": [4, 5], "5_10": [2], "5_16": [3, 4, 5], "5_20": [2, 3], "5_26": [2, 3, 4, 5],
            "6_6": [5], "6_7": [5, 6], "6_15": [2], "6_20": [3], "6_22": [4, 5, 6], "6_35": [2, 3], "6_42": [3, 4, 5, 6], "6_50": [2, 3, 4], "6_57": [2, 3, 4, 5, 6],
            "7_7": [6], "7_8": [6, 7], "7_21": [5], "7_35": [4], "7_120": [2, 3, 4, 5, 6, 7],
            "8_8": [7], "8_9": [7, 8], "8_28": [6], "8_56": [5], "8_70": [4], "8_247": [2, 3, 4, 5, 6, 7, 8], "8_255": [2, 3, 4, 5, 6, 7, 8]
        }

    def validate_ticket_legs(self, lottery_type: str, ticket_legs: list) -> dict:
        """
        校验当前票的场次数是否符合官方对应玩法的上限。
        """
        max_legs_dict = self.JINGCAI_MAX_LEGS if lottery_type == "竞彩足球" else self.BEIDAN_MAX_LEGS
        
        # 混合过关时，受限于票内最严格的玩法
        strictest_limit = 15 # 默认最高
        for leg in ticket_legs:
            play_type = leg.get("play_type", "WDL")
            limit = max_legs_dict.get(play_type, 4) # 未知玩法默认最严4串
            if limit < strictest_limit:
                strictest_limit = limit
                
        num_legs = len(ticket_legs)
        if num_legs > strictest_limit:
            msg = f"违规：{lottery_type} 包含 {ticket_legs[0].get('play_type')} 玩法时，最多允许 {strictest_limit} 串 1，当前票包含 {num_legs} 场。"
            logger.error(msg)
            return {"is_valid": False, "reason": msg, "max_allowed": strictest_limit}
            
        return {"is_valid": True, "reason": "合法"}

    def decompose_m_n(self, lottery_type: str, m: int, n: int) -> list:
        """
        将 M串N 拆解为底层的 M串1 组合列表。
        比如传入 竞彩足球 3串4，返回 [2, 3] (代表拆分为2串1和3串1)。
        """
        if lottery_type == "竞彩足球":
            combo_key = f"{m}_{n}"
            if combo_key not in self.JINGCAI_M_N_COMBOS:
                raise ValueError(f"竞彩足球不支持 {m}串{n} 的固定组合。")
            return self.JINGCAI_M_N_COMBOS[combo_key]
        elif lottery_type == "北京单场":
            # 北单的 M串N 其实是“模糊定胆”或自由过关，直接允许选 M 场过 N 关
            if n > m or m > 15:
                raise ValueError(f"北京单场不支持 {m}场过{n}关。")
            return [n] # 北单主要是 N串1 型
        else:
            raise ValueError(f"未知的彩票类型: {lottery_type}")

    def generate_free_parlay_combinations(self, match_selections: list, target_parlays: list) -> int:
        """
        计算自由过关（支持复式投注：即单场比赛双选/多选容错）的总注数。
        :param match_selections: 每场比赛选择的结果数列表。例如选3场，第一场双选，后两场单选，则为 [2, 1, 1]
        :param target_parlays: 目标过关数列表。例如打 2串1 和 3串1，则为 [2, 3]
        """
        import itertools
        import math
        
        total_tickets = 0
        num_matches = len(match_selections)
        
        for k in target_parlays:
            if k <= num_matches:
                # 遍历所有 k 场比赛的组合
                for combo in itertools.combinations(match_selections, k):
                    # 复式投注的注数 = 该组合中每场比赛选择数的乘积
                    tickets_for_combo = math.prod(combo)
                    total_tickets += tickets_for_combo
                    
        return total_tickets

    def calculate_chuantong_combinations(self, match_selections: list, play_type: str = "renjiu") -> int:
        """
        计算传统足彩（14场胜负彩、任选九场、6场半全场、4场进球彩）的复式注数。
        :param match_selections: 选定的场次结果数列表。例如任九选了10场，其中2场双选，8场单选，则传入 [2, 2, 1, 1, 1, 1, 1, 1, 1, 1]
        :param play_type: 玩法类型 ("14_match", "renjiu", "6_htft", "4_goals")
        :return: 满足官方规则的总注数
        """
        import itertools
        import math
        
        num_matches = len(match_selections)
        
        # 增加硬性风控拦截，防止被恶意传入组合爆炸参数导致 CPU 瘫痪
        if sum(match_selections) > 50:
             raise ValueError("⚠️ 物理风控拦截：单票总选择项超过 50 个，属于严重越界或组合爆炸攻击，已拒绝出票。")
             
        if play_type == "14_match":
            if num_matches != 14:
                raise ValueError("14场胜负彩必须且只能选择14场比赛")
            return math.prod(match_selections)
            
        elif play_type == "renjiu":
            if num_matches < 9 or num_matches > 14:
                raise ValueError("任选九场必须选择 9 至 14 场比赛")
            total_tickets = 0
            for combo in itertools.combinations(match_selections, 9):
                total_tickets += math.prod(combo)
            return total_tickets
            
        elif play_type == "6_htft":
            if num_matches != 6:
                raise ValueError("6场半全场必须选择6场比赛（共12个半全场结果）")
            return math.prod(match_selections)
            
        elif play_type == "4_goals":
            if num_matches != 4:
                raise ValueError("4场进球彩必须选择4场比赛（共8支球队结果）")
            return math.prod(match_selections)
            
        else:
            raise ValueError(f"未知的传统足彩玩法: {play_type}")

    def calculate_fuzzy_banker_combinations(self, banker_selections: list, tuo_selections: list, parlay_size: int, min_bankers: int = None) -> int:
        """
        计算竞彩/北单的“胆拖投注”及北单特有的“模糊定胆”组合数（完全支持单场双选/多选复式）。
        :param banker_selections: 胆码场次的选择数列表。如2个胆，第一个双选，第二个单选 -> [2, 1]
        :param tuo_selections: 拖码场次的选择数列表。如3个拖全单选 -> [1, 1, 1]
        :param parlay_size: 过关方式 (例如 4串1，P=4)
        :param min_bankers: 至少包含的胆码数量。如果是竞彩标准胆拖，该值等于胆码总数（必须全中）；如果是北单模糊定胆，该值可小于胆码总数。
        :return: 满足条件的总注数
        """
        import itertools
        import math
        
        num_bankers = len(banker_selections)
        num_tuo = len(tuo_selections)
        total_matches = num_bankers + num_tuo
        
        # 如果是竞彩标准胆拖，默认必须包含所有胆码
        if min_bankers is None:
            min_bankers = num_bankers
            
        if num_bankers > total_matches:
            raise ValueError("胆码数量不能超过总选取场次")
        if min_bankers > num_bankers:
            raise ValueError("最少命中胆码数不能超过设定的胆码总数")
        if parlay_size > total_matches:
            raise ValueError("过关场次不能大于总场次")
            
        total_tickets = 0
        
        # 遍历每注票中可能包含的胆码数量 k
        max_possible_bankers_in_ticket = min(num_bankers, parlay_size)
        for k in range(min_bankers, max_possible_bankers_in_ticket + 1):
            tuo_needed = parlay_size - k
            
            if 0 <= tuo_needed <= num_tuo:
                # 算出胆码中选 k 场的所有复式乘积之和
                banker_combinations_sum = 0
                for b_combo in itertools.combinations(banker_selections, k):
                    banker_combinations_sum += math.prod(b_combo)
                    
                # 算出拖码中选 tuo_needed 场的所有复式乘积之和
                tuo_combinations_sum = 0
                if tuo_needed == 0:
                    tuo_combinations_sum = 1
                else:
                    for t_combo in itertools.combinations(tuo_selections, tuo_needed):
                        tuo_combinations_sum += math.prod(t_combo)
                        
                # 组合注数 = 胆码复式总和 * 拖码复式总和
                total_tickets += banker_combinations_sum * tuo_combinations_sum
                
        return total_tickets
