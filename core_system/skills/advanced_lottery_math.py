from typing import List, Dict, Any

def map_poisson_to_jingcai_scores(poisson_matrix: List[List[float]]) -> Dict[str, float]:
    """
    将 N x N 的泊松矩阵映射为竞彩官方的 31 个比分选项。
    包含长尾概率的折叠（胜其他、平其他、负其他）。
    """
    jingcai_scores = {
        "1:0": 0.0, "2:0": 0.0, "2:1": 0.0, "3:0": 0.0, "3:1": 0.0, "3:2": 0.0, "4:0": 0.0, "4:1": 0.0, "4:2": 0.0, "5:0": 0.0, "5:1": 0.0, "5:2": 0.0, "胜其他": 0.0,
        "0:0": 0.0, "1:1": 0.0, "2:2": 0.0, "3:3": 0.0, "平其他": 0.0,
        "0:1": 0.0, "0:2": 0.0, "1:2": 0.0, "0:3": 0.0, "1:3": 0.0, "2:3": 0.0, "0:4": 0.0, "1:4": 0.0, "2:4": 0.0, "0:5": 0.0, "1:5": 0.0, "2:5": 0.0, "负其他": 0.0
    }
    
    max_goals = len(poisson_matrix)
    for h in range(max_goals):
        for a in range(max_goals):
            prob = poisson_matrix[h][a]
            if prob == 0: continue
            
            score_str = f"{h}:{a}"
            if h > a:
                if score_str in jingcai_scores:
                    jingcai_scores[score_str] += prob
                else:
                    jingcai_scores["胜其他"] += prob
            elif h == a:
                if score_str in jingcai_scores:
                    jingcai_scores[score_str] += prob
                else:
                    jingcai_scores["平其他"] += prob
            else:
                if score_str in jingcai_scores:
                    jingcai_scores[score_str] += prob
                else:
                    jingcai_scores["负其他"] += prob
                    
    return jingcai_scores

def calculate_parlay_kelly(legs: List[Dict[str, float]], fraction: float = 0.25, lottery_type: str = "JINGCAI") -> Dict[str, float]:
    """
    计算 N 串 1 混合过关的期望值 (EV) 和凯利仓位。
    包含北单 (BEIDAN) 浮动奖金的全局抽水修正。
    legs 格式: [{"prob": 0.6, "odds": 1.8}, ...]
    """
    if not legs:
        return {"ev": 0.0, "kelly_fraction": 0.0}
        
    combined_prob = 1.0
    combined_odds = 1.0
    
    for leg in legs:
        combined_prob *= leg["prob"]
        combined_odds *= leg["odds"]
        
    if lottery_type.upper() == "BEIDAN":
        combined_odds = combined_odds * 0.65
        
    ev = (combined_prob * combined_odds) - 1.0
    
    if ev <= 0 or combined_odds <= 1.0:
        return {"ev": ev, "kelly_fraction": 0.0, "combined_odds": combined_odds, "combined_prob": combined_prob}
        
    b = combined_odds - 1.0 # Net odds
    p = combined_prob
    q = 1.0 - p
    
    full_kelly = (b * p - q) / b
    fractional_kelly = full_kelly * fraction
    
    # Cap at 10% for parlay safety
    fractional_kelly = min(max(fractional_kelly, 0.0), 0.10)
    
    return {
        "ev": ev,
        "kelly_fraction": full_kelly, # Return full, let caller scale
        "fractional_kelly": fractional_kelly,
        "combined_odds": combined_odds,
        "combined_prob": combined_prob
    }

def calculate_last_leg_hedge(original_bet: float, potential_payout: float, hedge_odds: Dict[str, float]) -> Dict[str, Any]:
    """
    计算竞彩串关“最后一关”的物理防守打水金额。
    目标是实现所有赛果的收益绝对均等（Arbitrage Lock）。
    
    :param original_bet: 原始投注本金 (如 100)
    :param potential_payout: 原始彩票的全红奖金 (如 1000)
    :param hedge_odds: 最后一关需要防守的其他选项赔率 (如 {"平": 3.0, "负": 4.0})
    """
    hedge_bets = {}
    total_hedge_cost = 0.0
    
    # 公式: 防守金额 = 预期总奖金 / 防守赔率
    for outcome, odds in hedge_odds.items():
        if odds <= 1.0:
            return {"error": "Invalid odds"}
        bet_amount = potential_payout / odds
        hedge_bets[outcome] = round(bet_amount, 2)
        total_hedge_cost += bet_amount
        
    total_investment = original_bet + total_hedge_cost
    guaranteed_profit = potential_payout - total_investment
    
    return {
        "hedge_bets": hedge_bets,
        "total_hedge_cost": round(total_hedge_cost, 2),
        "total_investment": round(total_investment, 2),
        "guaranteed_payout": potential_payout,
        "guaranteed_profit": round(guaranteed_profit, 2),
        "is_profitable": guaranteed_profit > 0
    }

def optimize_jingcai_ticket(num_legs: int, combined_odds: float, target_investment: float) -> Dict[str, Any]:
    """
    竞彩智能拆单与封顶拦截器。
    处理法定最高奖金拦截，并检测20%偶然所得税（单注奖金>1万元）。
    """
    unit_bet_cost = 2.0
    pre_tax_unit_payout = combined_odds * unit_bet_cost
    
    is_taxed = pre_tax_unit_payout > 10000.0
    post_tax_odds = combined_odds * 0.8 if is_taxed else combined_odds
    post_tax_unit_payout = post_tax_odds * unit_bet_cost
    
    # 法定最高奖金 (Statutory Payout Ceiling)
    if num_legs <= 1:
        ceiling = 100000.0 # 单关最高10万
    elif 2 <= num_legs <= 3:
        ceiling = 200000.0 # 2-3关最高20万
    elif 4 <= num_legs <= 5:
        ceiling = 500000.0 # 4-5关最高50万
    else:
        ceiling = 1000000.0 # 6关及以上最高100万
        
    # 计算单票最大倍数 (Max bets per ticket before hitting ceiling)
    # 如果单注奖金已经超过天花板（极少见），最大倍数为1
    max_bets_per_ticket = max(1, int(ceiling // post_tax_unit_payout))
    max_investment_per_ticket = max_bets_per_ticket * unit_bet_cost
    
    target_bets = int(target_investment // unit_bet_cost)
    suggested_tickets = max(1, (target_bets + max_bets_per_ticket - 1) // max_bets_per_ticket)
    
    return {
        "is_taxed": is_taxed,
        "pre_tax_odds": combined_odds,
        "post_tax_odds": post_tax_odds,
        "payout_ceiling": ceiling,
        "max_bets_per_ticket": max_bets_per_ticket,
        "max_investment_per_ticket": max_investment_per_ticket,
        "suggested_tickets": suggested_tickets,
        "warning": "触发20%偶然所得税" if is_taxed else "安全（免税）"
    }

def calculate_zucai_value_index(matches: List[Dict[str, float]]) -> List[Dict[str, Any]]:
    """
    传统足彩（任九/十四场）防“火锅奖”价值指数计算器。
    通过对比泊松真实胜率(true_prob)与全国大众投注比例(public_prob)，
    寻找被大众低估的高价值冷门盲区。
    """
    results = []
    for match in matches:
        true_prob = match.get("true_prob", 0.0)
        public_prob = match.get("public_prob", 0.0)
        
        # 避免除以 0
        if public_prob <= 0.001:
            public_prob = 0.001
            
        value_index = round(true_prob / public_prob, 3)
        
        # 如果价值指数 > 1.2，说明真实胜率远高于大众认知，值得作为足彩防冷胆码
        is_value_pick = value_index > 1.2
        
        # 信息熵辅助参考 (衡量大众分歧程度，越接近0.33分歧越大)
        # 这里仅作简单输出
        
        results.append({
            "true_prob": true_prob,
            "public_prob": public_prob,
            "value_index": value_index,
            "is_value_pick": is_value_pick,
            "warning": "严重高估（火锅预警）" if value_index < 0.6 else "正常"
        })
        
    return results

def calculate_beidan_sxds_matrix(poisson_matrix: List[List[float]]) -> Dict[str, float]:
    """
    计算北京单场专属玩法：上下盘单双 (SXDS)。
    上盘: 总进球 >= 3; 下盘: 总进球 < 3
    单双: 总进球数的奇偶
    """
    sxds = {
        "上单": 0.0,
        "上双": 0.0,
        "下单": 0.0,
        "下双": 0.0
    }
    
    max_goals = len(poisson_matrix)
    for h in range(max_goals):
        for a in range(max_goals):
            prob = poisson_matrix[h][a]
            if prob == 0: continue
            
            total_goals = h + a
            is_over = total_goals >= 3
            is_even = total_goals % 2 == 0
            
            if is_over and not is_even:
                sxds["上单"] += prob
            elif is_over and is_even:
                sxds["上双"] += prob
            elif not is_over and not is_even:
                sxds["下单"] += prob
            elif not is_over and is_even:
                sxds["下双"] += prob
                
    # Normalize in case of rounding errors, though it should sum to 1.0 if matrix is full
    total = sum(sxds.values())
    if total > 0:
        for k in sxds:
            sxds[k] = round(sxds[k] / total, 4)
            
    return sxds
