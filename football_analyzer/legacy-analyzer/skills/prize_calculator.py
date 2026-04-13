#!/usr/bin/env python3
"""
奖金计算Skill
功能：
1. 计算竞彩足球奖金
2. 计算北京单场SP值奖金
3. 计算传统足彩奖金
4. 计算M串N奖金
"""

import json
import os
from typing import Dict, List, Optional, Union
from itertools import combinations

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_official_rules() -> Dict:
    """加载官方规则"""
    with open(os.path.join(BASE_DIR, 'knowledge', 'official_rules.json'), 'r', encoding='utf-8') as f:
        return json.load(f)


def load_mxn_rules() -> Dict:
    """加载M串N规则"""
    with open(os.path.join(BASE_DIR, 'knowledge', 'mxn_combinations.json'), 'r', encoding='utf-8') as f:
        return json.load(f)


# ==================== 竞彩足球奖金计算 ====================

def calculate_jingcai_single(
    odds: float,
    stake: float = 2,
    multiplier: int = 1
) -> Dict:
    """
    计算竞彩足球单场奖金
    
    Args:
        odds: 固定赔率
        stake: 投注金额
        multiplier: 倍数
    
    Returns:
        奖金计算结果
    """
    bets = stake * multiplier
    prize = bets * odds
    
    return {
        "bet": bets,
        "odds": odds,
        "prize": prize,
        "profit": prize - bets
    }


def calculate_jingcai_parlay(
    matches: List[Dict],
    play_type: str = "胜平负",
    stake: float = 2,
    multiplier: int = 1
) -> Dict:
    """
    计算竞彩足球过关奖金
    
    Args:
        matches: 比赛列表，每个包含赔率信息
        play_type: 玩法类型
        stake: 投注金额
        multiplier: 倍数
    
    Returns:
        奖金计算结果
    """
    rules = load_official_rules()
    max_parlay = rules["竞彩足球"]["玩法"][play_type]["max_parlay"]
    
    if len(matches) > max_parlay:
        raise ValueError(f"{play_type}最多{ max_parlay}关")
    
    # 获取各场赔率
    odds_list = []
    for m in matches:
        if play_type == "胜平负":
            # 需要根据选择的选项获取赔率
            pass
        elif play_type == "比分":
            pass
        # 简化处理：使用主队赔率作为示例
    
    # 计算赔率乘积
    odds_product = 1
    for m in matches:
        if m.get("主队赔率"):
            odds_product *= m["主队赔率"]
    
    bets = stake * multiplier
    prize = bets * odds_product
    
    return {
        "bet": bets,
        "odds_product": odds_product,
        "prize": prize,
        "profit": prize - bets,
        "max_prize": rules["竞彩足球"]["奖金规则"]["prize_limits"].get(
            f"{len(matches)}关" if len(matches) <= 3 else "6关及以上",
            1000000
        )
    }


# ==================== 北京单场SP值计算 ====================

def calculate_beijing_sp_prize(
    bet_amount: float,
    sp_value: float,
    multiplier: int = 1
) -> Dict:
    """
    计算北京单场SP值奖金
    
    Args:
        bet_amount: 投注金额
        sp_value: SP值（赛后公布）
        multiplier: 倍数
    
    Returns:
        奖金计算结果
    """
    prize = bet_amount * sp_value * multiplier
    
    return {
        "bet": bet_amount * multiplier,
        "sp_value": sp_value,
        "prize": prize,
        "profit": prize - bet_amount * multiplier
    }


def calculate_beijing_parlay(
    matches: List[Dict],
    sp_values: List[float],
    bet_amount: float = 2
) -> Dict:
    """
    计算北京单场串关奖金
    
    Args:
        matches: 比赛列表
        sp_values: 各场SP值列表
        bet_amount: 投注金额
    
    Returns:
        奖金计算结果
    """
    if len(matches) != len(sp_values):
        raise ValueError("比赛数和SP值数不匹配")
    
    if len(matches) > 15:
        raise ValueError("北京单场最多15关")
    
    # 计算SP值乘积
    sp_product = 1
    for sp in sp_values:
        sp_product *= sp
    
    prize = bet_amount * sp_product
    
    return {
        "bet": bet_amount,
        "sp_product": sp_product,
        "prize": prize,
        "profit": prize - bet_amount
    }


# ==================== 传统足彩奖金计算 ====================

def calculate_traditional_prize(
    total_sales: float,
    prize_pool_balance: float = 0,
    winner_count: int = 1,
    prize_level: str = "一等奖"
) -> Dict:
    """
    计算传统足彩奖金
    
    Args:
        total_sales: 当期销售额
        prize_pool_balance: 奖池余额
        winner_count: 中奖注数
        prize_level: 奖级
    
    Returns:
        奖金计算结果
    """
    # 奖金总额 = 销售额的64%
    prize_total = total_sales * 0.64 + prize_pool_balance
    
    # 一等奖：奖金总额的70%
    # 二等奖：奖金总额的30%
    if prize_level == "一等奖":
        prize_per_bet = (prize_total * 0.70) / winner_count
    else:
        prize_per_bet = (prize_total * 0.30) / winner_count
    
    # 封顶500万
    cap = 5000000
    actual_prize = min(prize_per_bet, cap)
    
    return {
        "prize_total": prize_total,
        "prize_per_bet_before_cap": prize_per_bet,
        "prize_per_bet": actual_prize,
        "cap": cap,
        "is_capped": prize_per_bet > cap,
        "winner_count": winner_count,
        "prize_level": prize_level
    }


def calculate_dantuo_bet(
    dan_count: int,
    dan_options: int,
    tuo_count: int,
    tuo_options: List[int]
) -> Dict:
    """
    计算胆拖投注注数
    
    Args:
        dan_count: 胆的数量
        dan_options: 每个胆的选项数（通常为1）
        tuo_count: 拖的数量
        tuo_options: 每个拖的选项数列表
    
    Returns:
        投注计算结果
    """
    # 胆的组合数（固定为1，因为胆只选1个）
    dan_combinations = dan_count * dan_options  # 通常 = dan_count
    
    # 拖的组合数 = 各拖选项数乘积
    tuo_combinations = 1
    for opts in tuo_options:
        tuo_combinations *= opts
    
    total_bets = dan_combinations * tuo_combinations
    total_cost = total_bets * 2  # 每注2元
    
    return {
        "dan_count": dan_count,
        "dan_combinations": dan_combinations,
        "tuo_count": tuo_count,
        "tuo_combinations": tuo_combinations,
        "total_bets": total_bets,
        "total_cost": total_cost
    }


# ==================== M串N奖金计算 ====================

def calculate_mxn_bet(
    m: int,
    n_type: str,
    stake: float = 2,
    multiplier: int = 1
) -> Dict:
    """
    计算M串N投注金额
    
    Args:
        m: 选择比赛场数
        n_type: 组合类型（如"4串11"）
        stake: 单注金额
        multiplier: 倍数
    
    Returns:
        投注计算结果
    """
    rules = load_mxn_rules()
    
    m_str = str(m)
    combos = rules["北京单场"]["combinations"].get(m_str, {})
    
    if n_type not in combos:
        raise ValueError(f"不支持的组合类型: {m}串{n_type}")
    
    total_bets = combos[n_type]["total"]
    total_cost = total_bets * stake * multiplier
    
    # 分解组合
    breakdown = {k: v for k, v in combos[n_type].items() if k != "total"}
    
    return {
        "m": m,
        "n_type": n_type,
        "total_bets": total_bets,
        "breakdown": breakdown,
        "stake_per_bet": stake,
        "multiplier": multiplier,
        "total_cost": total_cost
    }


def calculate_mxn_prize(
    mxn_info: Dict,
    correct_count: int,
    odds_list: List[float],
    stake: float = 2
) -> Dict:
    """
    计算M串N中奖奖金
    
    Args:
        mxn_info: M串N投注信息
        correct_count: 正确场数
        odds_list: 各场赔率列表
        stake: 单注金额
    
    Returns:
        中奖计算结果
    """
    breakdown = mxn_info["breakdown"]
    total_prize = 0
    winning_combos = []
    
    # 遍历所有可能的组合
    for combo_type, count in breakdown.items():
        k = int(combo_type.replace("串1", ""))
        
        if k <= correct_count:
            # 这个组合类型有可能中奖
            # 计算赔率乘积（简化处理）
            if k <= len(odds_list):
                # 取前k个赔率计算
                sample_odds = odds_list[:k]
                avg_odds = sum(sample_odds) / len(sample_odds)
                combo_prize = avg_odds * stake
                
                # 中奖注数 = C(correct_count, k)
                if correct_count >= k:
                    import math
                    win_bets = math.comb(correct_count, k)
                    combo_total = combo_prize * win_bets * count
                    
                    total_prize += combo_total
                    winning_combos.append({
                        "type": combo_type,
                        "possible_bets": win_bets,
                        "prize_per_bet": combo_prize,
                        "total": combo_total
                    })
    
    return {
        "correct_count": correct_count,
        "total_prize": total_prize,
        "winning_combos": winning_combos,
        "profit": total_prize - mxn_info["total_cost"]
    }


# ==================== 智能推荐 ====================

def recommend_bet_by_odds(
    odds: float,
    budget: float = 100,
    lottery_type: str = "竞彩足球"
) -> Dict:
    """
    根据赔率和预算推荐投注方式
    
    Args:
        odds: 赔率
        budget: 预算
        lottery_type: 彩票类型
    
    Returns:
        推荐结果
    """
    if lottery_type == "竞彩足球":
        # 计算单关
        max_bet = min(budget, 10000)
        single_prize = calculate_jingcai_single(odds, max_bet, 1)
        
        # 2串1方案
        parlay2_prize = None
        parlay3_prize = None
        
        if budget >= 4:
            parlay2_prize = {
                "bet": 4,
                "potential_prize": 4 * (odds ** 2),
                "roi": ((4 * (odds ** 2)) - 4) / 4 * 100
            }
        
        if budget >= 8:
            parlay3_prize = {
                "bet": 8,
                "potential_prize": 8 * (odds ** 3),
                "roi": ((8 * (odds ** 3)) - 8) / 8 * 100
            }
        
        return {
            "odds": odds,
            "budget": budget,
            "single": single_prize,
            "parlay2": parlay2_prize,
            "parlay3": parlay3_prize
        }
    
    return {}


def main():
    """测试函数"""
    print("=" * 60)
    print("奖金计算Skill - 测试")
    print("=" * 60)
    
    # 测试竞彩足球单场
    print("\n【竞彩足球单场奖金计算】")
    result = calculate_jingcai_single(1.85, 100, 1)
    print(f"  赔率1.85, 投注100元")
    print(f"  中奖奖金: {result['prize']:.2f}元")
    print(f"  盈利: {result['profit']:.2f}元")
    
    # 测试M串N
    print("\n【M串N投注计算】")
    mxn = calculate_mxn_bet(4, "4串11", 2, 1)
    print(f"  4串11: {mxn['total_bets']}注, 金额{mxn['total_cost']}元")
    print(f"  分解: {mxn['breakdown']}")
    
    # 测试胆拖
    print("\n【胆拖投注计算】")
    dantuo = calculate_dantuo_bet(
        dan_count=10,
        dan_options=1,
        tuo_count=4,
        tuo_options=[2, 2, 2, 2]
    )
    print(f"  10个胆 + 4个拖(每个2选)")
    print(f"  总注数: {dantuo['total_bets']}")
    print(f"  总成本: {dantuo['total_cost']}元")
    
    # 测试传统足彩
    print("\n【传统足彩奖金计算】")
    prize = calculate_traditional_prize(
        total_sales=50000000,  # 5000万销售额
        prize_pool_balance=10000000,  # 1000万奖池
        winner_count=5
    )
    print(f"  销售额5000万 + 奖池1000万")
    print(f"  奖金总额: {prize['prize_total']/10000:.0f}万")
    print(f"  每注奖金: {prize['prize_per_bet']/10000:.1f}万")


if __name__ == "__main__":
    main()
