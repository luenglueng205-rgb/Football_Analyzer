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

def calculate_parlay_kelly(legs: List[Dict[str, float]], fraction: float = 0.25) -> Dict[str, float]:
    """
    计算 N 串 1 混合过关的期望值 (EV) 和凯利仓位。
    legs 格式: [{"prob": 0.6, "odds": 1.8}, ...]
    """
    if not legs:
        return {"ev": 0.0, "kelly_fraction": 0.0}
        
    combined_prob = 1.0
    combined_odds = 1.0
    
    for leg in legs:
        combined_prob *= leg["prob"]
        combined_odds *= leg["odds"]
        
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
