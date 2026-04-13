#!/usr/bin/env python3
"""
策略回测Skill - 增强版
功能：
1. 回测各种投注策略的历史表现
2. 计算ROI和胜率
3. 评估策略风险
4. 串关策略回测
5. 时间序列回测（训练集/测试集）
"""

import json
import os
import sys
from typing import Dict, List, Callable, Optional, Tuple
from collections import defaultdict
from itertools import combinations
import math

# 路径设置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BASE_DIR = os.path.dirname(PROJECT_ROOT)
DATA_DIR = os.path.join(BASE_DIR, 'data', 'chinese_mapped')


def load_data(lottery_type: str = "竞彩足球") -> Dict:
    """加载数据"""
    filepath = os.path.join(DATA_DIR, f'{lottery_type}_chinese_data.json')
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_match_result(match: Dict) -> str:
    """获取比赛结果"""
    try:
        home = int(match.get('主队进球', 0))
        away = int(match.get('客队进球', 0))
        if home > away:
            return 'H'
        elif home == away:
            return 'D'
        else:
            return 'A'
    except:
        return 'U'


def split_train_test(matches: List[Dict], test_ratio: float = 0.2) -> Tuple[List[Dict], List[Dict]]:
    """
    按时间分割训练集和测试集
    
    Args:
        matches: 比赛列表（按时间排序）
        test_ratio: 测试集比例
    
    Returns:
        (训练集, 测试集)
    """
    n = len(matches)
    split_idx = int(n * (1 - test_ratio))
    return matches[:split_idx], matches[split_idx:]


# ============================================================
# 核心回测函数
# ============================================================

def backtest_strategy(
    matches: List[Dict],
    strategy_func: Callable,
    stake_per_bet: float = 100,
    min_odds: float = 1.0
) -> Dict:
    """
    回测策略
    
    Args:
        matches: 比赛列表
        strategy_func: 策略函数
        stake_per_bet: 每注投注金额
        min_odds: 最小赔率
    
    Returns:
        回测结果
    """
    total_bets = 0
    total_stake = 0
    total_wins = 0
    total_profit = 0
    win_streak = 0
    lose_streak = 0
    max_win_streak = 0
    max_lose_streak = 0
    max_drawdown = 0
    current_balance = 0
    peak_balance = 0
    
    for match in matches:
        decision = strategy_func(match)
        
        if decision.get("bet"):
            odds = decision.get("odds", 1)
            if odds < min_odds:
                continue
                
            total_bets += 1
            stake = decision.get("stake", stake_per_bet)
            total_stake += stake
            
            # 检查是否中奖
            if decision.get("result_check"):
                result_check = decision["result_check"]
            else:
                option = decision.get("option", "H")
                result_check = "H" if option == "主胜" else ("D" if option == "平局" else "A")
            
            actual_result = get_match_result(match)
            
            if actual_result == result_check:
                # 中奖
                win = (odds - 1) * stake
                total_profit += win
                current_balance += win
                total_wins += 1
                win_streak += 1
                lose_streak = 0
            else:
                # 未中奖
                total_profit -= stake
                current_balance -= stake
                win_streak = 0
                lose_streak += 1
            
            max_win_streak = max(max_win_streak, win_streak)
            max_lose_streak = max(max_lose_streak, lose_streak)
            
            # 计算最大回撤
            peak_balance = max(peak_balance, current_balance)
            drawdown = peak_balance - current_balance
            max_drawdown = max(max_drawdown, drawdown)
    
    win_rate = (total_wins / total_bets * 100) if total_bets > 0 else 0
    roi = (total_profit / total_stake * 100) if total_stake > 0 else 0
    
    return {
        "total_bets": total_bets,
        "total_stake": total_stake,
        "total_wins": total_wins,
        "total_losses": total_bets - total_wins,
        "win_rate": round(win_rate, 2),
        "total_profit": round(total_profit, 2),
        "roi": round(roi, 2),
        "avg_profit_per_bet": round(total_profit / total_bets, 2) if total_bets > 0 else 0,
        "max_win_streak": max_win_streak,
        "max_lose_streak": max_lose_streak,
        "max_drawdown": round(max_drawdown, 2),
        "sharpe_ratio": round(calculate_sharpe_ratio(matches, strategy_func), 2)
    }


def calculate_sharpe_ratio(matches: List[Dict], strategy_func: Callable, 
                           stake_per_bet: float = 100) -> float:
    """计算夏普比率"""
    returns = []
    
    for match in matches:
        decision = strategy_func(match)
        if decision.get("bet"):
            odds = decision.get("odds", 1)
            stake = decision.get("stake", stake_per_bet)
            
            actual_result = get_match_result(match)
            result_check = decision.get("result_check", "H")
            
            if actual_result == result_check:
                returns.append((odds - 1) * stake / stake)
            else:
                returns.append(-1.0)
    
    if len(returns) < 2:
        return 0
    
    mean_return = sum(returns) / len(returns)
    std_return = math.sqrt(sum((r - mean_return) ** 2 for r in returns) / len(returns))
    
    if std_return == 0:
        return 0
    
    return mean_return / std_return * math.sqrt(252)


# ============================================================
# 预设策略
# ============================================================

def strategy_favorite_only(match: Dict) -> Dict:
    """策略1：只押热门（赔率<1.5的主队）"""
    if match.get("主队赔率") and match["主队赔率"] < 1.5:
        return {"bet": True, "option": "H", "odds": match["主队赔率"], "stake": 100, "result_check": "H"}
    return {"bet": False}


def strategy_low_odds_home(match: Dict) -> Dict:
    """策略2：只押低赔主队（赔率<1.8）"""
    if match.get("主队赔率") and match["主队赔率"] < 1.8:
        return {"bet": True, "option": "H", "odds": match["主队赔率"], "stake": 100, "result_check": "H"}
    return {"bet": False}


def strategy_medium_odds_draw(match: Dict) -> Dict:
    """策略3：押中赔率平局（赔率3.0-3.5）"""
    if match.get("平局赔率") and 3.0 <= match["平局赔率"] < 3.5:
        return {"bet": True, "option": "D", "odds": match["平局赔率"], "stake": 100, "result_check": "D"}
    return {"bet": False}


def strategy_high_odds_away(match: Dict) -> Dict:
    """策略4：押高赔客队（赔率>4.0）"""
    if match.get("客队赔率") and match["客队赔率"] > 4.0:
        return {"bet": True, "option": "A", "odds": match["客队赔率"], "stake": 100, "result_check": "A"}
    return {"bet": False}


def strategy_value_bet_home(match: Dict) -> Dict:
    """策略5：价值投注-主胜（基于赔率区间统计）"""
    odds = match.get("主队赔率")
    if not odds or not match.get("平局赔率") or not match.get("客队赔率"):
        return {"bet": False}
    
    # 根据赔率区间判断是否存在价值
    if 1.3 <= odds < 1.5:
        # 超低赔：历史胜率约75%
        return {"bet": True, "option": "H", "odds": odds, "stake": 100, "result_check": "H"}
    elif 1.5 <= odds < 1.8:
        # 低赔：历史胜率约60%
        return {"bet": True, "option": "H", "odds": odds, "stake": 100, "result_check": "H"}
    
    return {"bet": False}


def strategy_parlay_2_low_odds(match: Dict, min_odds: float = 1.3, max_odds: float = 1.8) -> Dict:
    """策略6：2串1组合（用于串关回测）"""
    odds = match.get("主队赔率")
    if odds and min_odds <= odds < max_odds:
        return {"bet": True, "option": "H", "odds": odds, "stake": 100, "result_check": "H"}
    return {"bet": False}


# ============================================================
# 增强回测：时间序列验证
# ============================================================

def backtest_with_train_test(
    matches: List[Dict],
    strategy_func: Callable,
    test_ratio: float = 0.2
) -> Dict:
    """
    带训练/测试集分割的回测
    
    Args:
        matches: 比赛列表
        strategy_func: 策略函数
        test_ratio: 测试集比例
    
    Returns:
        包含训练集和测试集结果的字典
    """
    # 按时间排序（假设数据已按时间排序）
    sorted_matches = sorted(matches, key=lambda x: x.get('比赛日期', ''))
    
    train_set, test_set = split_train_test(sorted_matches, test_ratio)
    
    train_result = backtest_strategy(train_set, strategy_func)
    test_result = backtest_strategy(test_set, strategy_func)
    
    return {
        "train_set": {
            "match_count": len(train_set),
            "bet_count": train_result["total_bets"],
            "win_rate": train_result["win_rate"],
            "roi": train_result["roi"]
        },
        "test_set": {
            "match_count": len(test_set),
            "bet_count": test_result["total_bets"],
            "win_rate": test_result["win_rate"],
            "roi": test_result["roi"]
        },
        "consistency": abs(train_result["roi"] - test_result["roi"]) < 5,
        "train_result": train_result,
        "test_result": test_result
    }


def backtest_all_strategies(lottery_type: str = "竞彩足球") -> List[Dict]:
    """
    回测所有预设策略
    
    Args:
        lottery_type: 彩票类型
    
    Returns:
        所有策略的回测结果
    """
    data = load_data(lottery_type)
    matches = data["matches"]
    
    strategies = [
        ("只押热门(赔率<1.5)", strategy_favorite_only),
        ("只押低赔主队(赔率<1.8)", strategy_low_odds_home),
        ("押中赔率平局(3.0-3.5)", strategy_medium_odds_draw),
        ("押高赔客队(赔率>4.0)", strategy_high_odds_away),
        ("价值投注-主胜", strategy_value_bet_home),
    ]
    
    results = []
    for name, func in strategies:
        result = backtest_strategy(matches, func)
        result["strategy_name"] = name
        results.append(result)
    
    # 按ROI排序
    results.sort(key=lambda x: -x["roi"])
    return results


# ============================================================
# 串关策略回测
# ============================================================

def backtest_parlay_strategy(
    matches: List[Dict],
    parlay_size: int = 2,
    min_odds: float = 1.3,
    max_odds: float = 1.8,
    stake_per_combo: float = 100
) -> Dict:
    """
    回测串关策略
    
    Args:
        matches: 比赛列表
        parlay_size: 串关场数
        min_odds: 最小赔率
        max_odds: 最大赔率
        stake_per_combo: 每注组合投注金额
    
    Returns:
        串关回测结果
    """
    # 筛选符合条件的比赛
    valid_matches = [
        m for m in matches
        if m.get("主队赔率") and min_odds <= m["主队赔率"] < max_odds
    ]
    
    total_combos = 0
    total_stake = 0
    total_wins = 0
    total_profit = 0
    combo_list = []
    
    # 生成所有可能的串关组合
    for combo in combinations(valid_matches, parlay_size):
        total_combos += 1
        stake = stake_per_combo
        total_stake += stake
        
        # 检查是否全中
        all_wins = all(get_match_result(m) == 'H' for m in combo)
        
        if all_wins:
            # 计算赔率乘积
            odds_product = 1
            for m in combo:
                odds_product *= m["主队赔率"]
            
            win = (odds_product - 1) * stake
            total_profit += win
            total_wins += 1
            
            combo_list.append({
                "match": [f"{m.get('主队', '')} vs {m.get('客队', '')}" for m in combo],
                "odds": odds_product,
                "result": "WIN",
                "profit": win
            })
        else:
            total_profit -= stake
            combo_list.append({
                "match": [f"{m.get('主队', '')} vs {m.get('客队', '')}" for m in combo],
                "odds": 1,
                "result": "LOSE",
                "profit": -stake
            })
    
    # 限制显示数量
    if len(combo_list) > 10000:
        combo_list = combo_list[:10000]
    
    return {
        "parlay_size": parlay_size,
        "min_odds": min_odds,
        "max_odds": max_odds,
        "total_combinations": total_combos,
        "total_stake": total_stake,
        "total_wins": total_wins,
        "total_losses": total_combos - total_wins,
        "win_rate": round((total_wins / total_combos * 100), 4) if total_combos > 0 else 0,
        "total_profit": round(total_profit, 2),
        "roi": round((total_profit / total_stake * 100), 2) if total_stake > 0 else 0,
        "avg_odds": round(sum(c["odds"] for c in combo_list) / len(combo_list), 2) if combo_list else 0
    }


def optimize_parlay_params(matches: List[Dict], max_parlay: int = 4) -> List[Dict]:
    """
    优化串关参数
    
    Args:
        matches: 比赛列表
        max_parlay: 最大串关数
    
    Returns:
        最优参数组合
    """
    results = []
    
    for size in range(2, max_parlay + 1):
        for min_o in [1.2, 1.3, 1.4, 1.5]:
            for max_o in [1.5, 1.6, 1.8, 2.0, 2.2]:
                if min_o >= max_o:
                    continue
                    
                result = backtest_parlay_strategy(
                    matches, 
                    parlay_size=size,
                    min_odds=min_o,
                    max_odds=max_o
                )
                
                if result["total_combinations"] > 0:
                    results.append({
                        "parlay_size": size,
                        "min_odds": min_o,
                        "max_odds": max_o,
                        "win_rate": result["win_rate"],
                        "roi": result["roi"],
                        "total_bets": result["total_combinations"]
                    })
    
    # 按ROI排序
    results.sort(key=lambda x: -x["roi"])
    return results


# ============================================================
# 联赛特定策略回测
# ============================================================

def backtest_by_league(matches: List[Dict], strategy_func: Callable) -> List[Dict]:
    """
    按联赛回测策略
    
    Args:
        matches: 比赛列表
        strategy_func: 策略函数
    
    Returns:
        各联赛回测结果
    """
    leagues = defaultdict(list)
    for match in matches:
        league = match.get('联赛代码', 'UNKNOWN')
        leagues[league].append(match)
    
    results = []
    for league, league_matches in leagues.items():
        if len(league_matches) < 50:
            continue
        
        result = backtest_strategy(league_matches, strategy_func)
        result["league_code"] = league
        result["league_name"] = league_matches[0].get('联赛中文名', league)
        result["match_count"] = len(league_matches)
        
        results.append(result)
    
    results.sort(key=lambda x: -x["roi"])
    return results


# ============================================================
# 报告生成
# ============================================================

def generate_backtest_report(lottery_type: str = "竞彩足球") -> str:
    """生成回测报告"""
    data = load_data(lottery_type)
    matches = data["matches"]
    
    report = []
    report.append("=" * 70)
    report.append(f"{lottery_type} 策略回测报告")
    report.append("=" * 70)
    
    # 1. 总体统计
    report.append(f"\n【数据概览】")
    report.append(f"  总比赛数: {len(matches):,}")
    valid = [m for m in matches if m.get('主队赔率')]
    report.append(f"  有效比赛数: {len(valid):,}")
    
    # 2. 策略回测结果
    report.append(f"\n【策略回测结果】")
    strategies = backtest_all_strategies(lottery_type)
    
    report.append(f"{'策略名称':<25} {'投注数':>8} {'胜率':>8} {'ROI':>10} {'最大连赢':>8} {'最大连输':>8}")
    report.append("-" * 75)
    
    for s in strategies:
        symbol = "✓" if s["roi"] > 0 else "✗"
        report.append(
            f"{s['strategy_name']:<25} {s['total_bets']:>8} "
            f"{s['win_rate']:>7.1f}% {s['roi']:>+9.1f}% "
            f"{s['max_win_streak']:>8} {s['max_lose_streak']:>8} {symbol}"
        )
    
    # 3. 串关回测
    report.append(f"\n【串关策略回测】")
    for size in [2, 3, 4]:
        result = backtest_parlay_strategy(matches, parlay_size=size)
        if result["total_combinations"] > 0:
            symbol = "✓" if result["roi"] > 0 else "✗"
            report.append(
                f"  {size}串1 (赔率1.3-1.8): "
                f"组合数{result['total_combinations']:,}, "
                f"胜率{result['win_rate']:.2f}%, "
                f"ROI{result['roi']:+.1f}% {symbol}"
            )
    
    # 4. 联赛分析
    report.append(f"\n【各联赛回测 (只押热门策略)】")
    league_results = backtest_by_league(matches, strategy_favorite_only)
    
    report.append(f"{'联赛':<20} {'投注数':>8} {'胜率':>8} {'ROI':>10} {'建议':>10}")
    report.append("-" * 60)
    
    for lr in league_results[:10]:
        rec = "推荐" if lr["roi"] > 0 else "谨慎"
        report.append(
            f"{lr['league_name']:<20} {lr['total_bets']:>8} "
            f"{lr['win_rate']:>7.1f}% {lr['roi']:>+9.1f}% {rec:>10}"
        )
    
    report.append("\n" + "=" * 70)
    
    return "\n".join(report)


# ============================================================
# 测试
# ============================================================

def main():
    """测试函数"""
    print("=" * 70)
    print("策略回测Skill - 增强版测试")
    print("=" * 70)
    
    # 加载数据
    data = load_data("竞彩足球")
    matches = data["matches"]
    print(f"\n总比赛数: {len(matches):,}")
    
    # 策略回测
    print("\n【策略回测结果】")
    strategies = backtest_all_strategies("竞彩足球")
    
    print(f"{'策略':<25} {'投注数':>8} {'胜率':>8} {'ROI':>10} {'建议':>8}")
    print("-" * 65)
    for s in strategies:
        symbol = "✓" if s["roi"] > 0 else "✗"
        print(f"{s['strategy_name']:<25} {s['total_bets']:>8} {s['win_rate']:>7.1f}% {s['roi']:>+9.1f}% {symbol:>8}")
    
    # 串关回测
    print("\n【串关策略回测】")
    for size in [2, 3]:
        result = backtest_parlay_strategy(matches, parlay_size=size)
        print(f"  {size}串1: 组合{result['total_combinations']:,}, 胜率{result['win_rate']:.4f}%, ROI{result['roi']:+.1f}%")
    
    # 训练/测试验证
    print("\n【时间序列验证】")
    validation = backtest_with_train_test(matches, strategy_favorite_only)
    print(f"  训练集ROI: {validation['train_result']['roi']:.1f}%")
    print(f"  测试集ROI: {validation['test_result']['roi']:.1f}%")
    print(f"  一致性: {'通过' if validation['consistency'] else '不通过'}")
    
    print("\n✓ 测试完成!")


if __name__ == "__main__":
    main()
