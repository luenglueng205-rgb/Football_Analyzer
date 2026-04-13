#!/usr/bin/env python3
"""
赔率分析Skill - 增强版
功能：
1. 计算理论概率和期望值
2. 多维度价值投注策略
3. 庄家抽水分析
4. 赔率异常检测
5. 联赛价值排名
"""

import json
import os
import sys
from typing import Dict, List, Optional, Tuple
from collections import Counter, defaultdict

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
    """获取比赛结果 (H=主胜, D=平, A=客胜)"""
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
        return 'U'  # Unknown


def calculate_theoretical_probability(odds: float) -> float:
    """从赔率计算理论概率"""
    if odds <= 0:
        return 0
    return (1 / odds) * 100


def calculate_bookmaker_margin(home_odds: float, draw_odds: float, away_odds: float) -> float:
    """计算庄家抽水率"""
    if not all([home_odds, draw_odds, away_odds]):
        return 0
    margin = (1/home_odds + 1/draw_odds + 1/away_odds - 1) * 100
    return margin


def calculate_expected_value(odds: float, actual_probability: float) -> float:
    """计算期望值"""
    theoretical_prob = calculate_theoretical_probability(odds)
    return actual_probability - theoretical_prob


# ============================================================
# 价值投注分析 - 增强版
# ============================================================

def analyze_value_bets_by_odds_range(matches: List[Dict], threshold: float = 2.0) -> List[Dict]:
    """
    按赔率区间分析价值投注
    
    Args:
        matches: 比赛列表
        threshold: 价值阈值(%)
    
    Returns:
        价值投注分析列表
    """
    valid = [m for m in matches if m.get('主队赔率') and m.get('平局赔率') and m.get('客队赔率')]
    
    # 赔率分组
    odds_ranges = [
        (1.1, 1.3, "超低赔"),
        (1.3, 1.5, "低赔"),
        (1.5, 1.8, "中低赔"),
        (1.8, 2.2, "中赔"),
        (2.2, 2.8, "中高赔"),
        (2.8, 3.5, "高赔"),
        (3.5, 5.0, "高回报"),
        (5.0, 10.0, "超高回报")
    ]
    
    results = []
    for low, high, name in odds_ranges:
        range_matches = [m for m in valid if low <= m.get('主队赔率', 0) < high]
        if len(range_matches) < 10:
            continue
        
        # 统计各结果数量
        home_wins = sum(1 for m in range_matches if get_match_result(m) == 'H')
        draws = sum(1 for m in range_matches if get_match_result(m) == 'D')
        away_wins = sum(1 for m in range_matches if get_match_result(m) == 'A')
        
        home_rate = home_wins / len(range_matches) * 100
        draw_rate = draws / len(range_matches) * 100
        away_rate = away_wins / len(range_matches) * 100
        
        # 理论概率
        avg_home_odds = sum(m['主队赔率'] for m in range_matches) / len(range_matches)
        avg_draw_odds = sum(m['平局赔率'] for m in range_matches) / len(range_matches)
        avg_away_odds = sum(m['客队赔率'] for m in range_matches) / len(range_matches)
        
        theoretical_home = calculate_theoretical_probability(avg_home_odds)
        theoretical_draw = calculate_theoretical_probability(avg_draw_odds)
        theoretical_away = calculate_theoretical_probability(avg_away_odds)
        
        results.append({
            "range": f"{low}-{high}",
            "name": name,
            "match_count": len(range_matches),
            "home_win_rate": round(home_rate, 2),
            "draw_rate": round(draw_rate, 2),
            "away_win_rate": round(away_rate, 2),
            "theoretical_home": round(theoretical_home, 2),
            "theoretical_draw": round(theoretical_draw, 2),
            "theoretical_away": round(theoretical_away, 2),
            "home_value": round(home_rate - theoretical_home, 2),
            "draw_value": round(draw_rate - theoretical_draw, 2),
            "away_value": round(away_rate - theoretical_away, 2),
            "best_bet": max([('主胜', home_rate, theoretical_home, home_rate - theoretical_home),
                           ('平局', draw_rate, theoretical_draw, draw_rate - theoretical_draw),
                           ('客胜', away_rate, theoretical_away, away_rate - theoretical_away)],
                          key=lambda x: x[3]),
            "is_value": max(home_rate - theoretical_home, draw_rate - theoretical_draw, away_rate - theoretical_away) > threshold
        })
    
    return results


def analyze_value_bets_by_league(matches: List[Dict], min_matches: int = 50) -> List[Dict]:
    """
    按联赛分析价值投注
    
    Args:
        matches: 比赛列表
        min_matches: 最小比赛数
    
    Returns:
        联赛价值分析列表
    """
    leagues = defaultdict(list)
    for match in matches:
        if match.get('主队赔率') and match.get('平局赔率') and match.get('客队赔率'):
            leagues[match.get('联赛代码', 'UNKNOWN')].append(match)
    
    results = []
    for league_code, league_matches in leagues.items():
        if len(league_matches) < min_matches:
            continue
        
        # 总体统计
        home_wins = sum(1 for m in league_matches if get_match_result(m) == 'H')
        draws = sum(1 for m in league_matches if get_match_result(m) == 'D')
        total = len(league_matches)
        
        home_rate = home_wins / total * 100
        draw_rate = draws / total * 100
        away_rate = 100 - home_rate - draw_rate
        
        # 平均赔率
        avg_home = sum(m['主队赔率'] for m in league_matches) / total
        avg_draw = sum(m['平局赔率'] for m in league_matches) / total
        avg_away = sum(m['客队赔率'] for m in league_matches) / total
        
        # 理论概率
        theoretical_home = calculate_theoretical_probability(avg_home)
        theoretical_draw = calculate_theoretical_probability(avg_draw)
        theoretical_away = calculate_theoretical_probability(avg_away)
        
        # 平均抽水
        margins = [calculate_bookmaker_margin(m['主队赔率'], m['平局赔率'], m['客队赔率']) 
                   for m in league_matches]
        avg_margin = sum(margins) / len(margins)
        
        # 计算价值
        home_value = home_rate - theoretical_home
        draw_value = draw_rate - theoretical_draw
        away_value = away_rate - theoretical_away
        
        results.append({
            "league_code": league_code,
            "league_name": league_matches[0].get('联赛中文名', league_code),
            "match_count": total,
            "home_win_rate": round(home_rate, 2),
            "draw_rate": round(draw_rate, 2),
            "away_win_rate": round(away_rate, 2),
            "avg_odds": {
                "home": round(avg_home, 2),
                "draw": round(avg_draw, 2),
                "away": round(avg_away, 2)
            },
            "avg_margin": round(avg_margin, 2),
            "home_value": round(home_value, 2),
            "draw_value": round(draw_value, 2),
            "away_value": round(away_value, 2),
            "overall_value": round(max(home_value, draw_value, away_value), 2),
            "recommendation": get_recommendation(home_value, draw_value, away_value)
        })
    
    # 按整体价值排序
    results.sort(key=lambda x: -x['overall_value'])
    return results


def get_recommendation(home_value: float, draw_value: float, away_value: float) -> Dict:
    """根据价值生成推荐"""
    max_value = max(home_value, draw_value, away_value)
    
    if max_value < 0:
        return {"type": "avoid", "reason": "所有选项都低于理论值", "bet": None}
    elif max_value < 2:
        return {"type": "neutral", "reason": "价值不明显", "bet": None}
    elif max_value < 5:
        return {"type": "slight_value", "reason": "存在轻微价值", 
                "bet": ['主胜' if home_value == max_value else '平局' if draw_value == max_value else '客胜'][0]}
    else:
        return {"type": "value_bet", "reason": "显著价值投注机会", 
                "bet": ['主胜' if home_value == max_value else '平局' if draw_value == max_value else '客胜'][0]}


def find_best_value_combinations(matches: List[Dict], min_value: float = 3.0, 
                                  min_odds: float = 1.3, max_odds: float = 3.5) -> List[Dict]:
    """
    找出最佳价值投注组合（用于串关）
    
    Args:
        matches: 比赛列表
        min_value: 最小价值阈值(%)
        min_odds: 最小赔率
        max_odds: 最大赔率
    
    Returns:
        价值投注列表
    """
    valid = [m for m in matches if m.get('主队赔率') and m.get('平局赔率') and m.get('客队赔率')]
    
    # 按联赛分组统计真实胜率
    league_stats = defaultdict(lambda: {"home": [], "draw": [], "away": []})
    for match in valid:
        league = match.get('联赛代码', 'UNKNOWN')
        league_stats[league]["home"].append(match)
        league_stats[league]["draw"].append(match)
        league_stats[league]["away"].append(match)
    
    # 计算每个联赛各选项的真实胜率
    for league in league_stats:
        stats = league_stats[league]
        for option in ["home", "draw", "away"]:
            odds_key = "主队赔率" if option == "home" else ("平局赔率" if option == "draw" else "客队赔率")
            option_matches = [m for m in stats[option] if min_odds <= m.get(odds_key, 0) <= max_odds]
            
            if len(option_matches) >= 20:
                wins = sum(1 for m in option_matches if get_match_result(m) == ('H' if option == 'home' else ('D' if option == 'draw' else 'A')))
                actual_prob = wins / len(option_matches) * 100
                
                avg_odds = sum(m[odds_key] for m in option_matches) / len(option_matches)
                theoretical_prob = calculate_theoretical_probability(avg_odds)
                
                stats[option] = {
                    "match_count": len(option_matches),
                    "actual_prob": actual_prob,
                    "theoretical_prob": theoretical_prob,
                    "value": actual_prob - theoretical_prob
                }
            else:
                stats[option] = {"match_count": 0, "value": 0}
    
    # 找出高价值比赛
    value_matches = []
    for match in valid:
        league = match.get('联赛代码', 'UNKNOWN')
        league_data = league_stats.get(league, {})
        
        for option, odds_key, result_check in [
            ("home", "主队赔率", "H"),
            ("draw", "平局赔率", "D"),
            ("away", "客队赔率", "A")
        ]:
            odds = match.get(odds_key, 0)
            if not (min_odds <= odds <= max_odds):
                continue
            
            theoretical_prob = calculate_theoretical_probability(odds)
            league_stat = league_data.get(option, {})
            
            if league_stat.get("match_count", 0) >= 20:
                actual_prob = league_stat["actual_prob"]
                value = actual_prob - theoretical_prob
                
                if value >= min_value:
                    value_matches.append({
                        "match": f"{match.get('主队', '')} vs {match.get('客队', '')}",
                        "league": match.get('联赛中文名', league),
                        "bet": "主胜" if option == "home" else ("平局" if option == "draw" else "客胜"),
                        "odds": odds,
                        "theoretical_prob": round(theoretical_prob, 2),
                        "actual_prob": round(actual_prob, 2),
                        "value": round(value, 2)
                    })
    
    # 按价值排序
    value_matches.sort(key=lambda x: -x['value'])
    return value_matches


# ============================================================
# 赔率异常检测
# ============================================================

def detect_odds_anomaly(match: Dict, historical_matches: List[Dict], 
                         odds_threshold: float = 0.15) -> Dict:
    """
    检测赔率异常
    
    Args:
        match: 待检测比赛
        historical_matches: 历史比赛数据
        odds_threshold: 赔率偏离阈值(默认15%)
    
    Returns:
        异常检测结果
    """
    league = match.get('联赛代码')
    league_matches = [m for m in historical_matches 
                      if m.get('联赛代码') == league 
                      and m.get('主队赔率') and m.get('平局赔率') and m.get('客队赔率')]
    
    if len(league_matches) < 20:
        return {"status": "insufficient_data", "message": "历史数据不足"}
    
    # 计算联赛平均赔率
    avg_home = sum(m['主队赔率'] for m in league_matches) / len(league_matches)
    avg_draw = sum(m['平局赔率'] for m in league_matches) / len(league_matches)
    avg_away = sum(m['客队赔率'] for m in league_matches) / len(league_matches)
    
    anomalies = []
    warnings = []
    
    # 检查主队赔率
    current_home = match.get('主队赔率', 0)
    if current_home:
        deviation = (current_home - avg_home) / avg_home
        if abs(deviation) > odds_threshold:
            anomalies.append({
                "type": "home_odds",
                "current": current_home,
                "league_avg": round(avg_home, 2),
                "deviation": round(deviation * 100, 2),
                "direction": "偏高(主队被低估)" if deviation > 0 else "偏低(主队被高估)"
            })
    
    # 检查客队赔率
    current_away = match.get('客队赔率', 0)
    if current_away:
        deviation = (current_away - avg_away) / avg_away
        if abs(deviation) > odds_threshold:
            anomalies.append({
                "type": "away_odds",
                "current": current_away,
                "league_avg": round(avg_away, 2),
                "deviation": round(deviation * 100, 2),
                "direction": "偏高(客队被低估)" if deviation > 0 else "偏低(客队被高估)"
            })
    
    # 计算价值机会
    if current_home and current_away:
        theoretical_home = calculate_theoretical_probability(current_home)
        theoretical_away = calculate_theoretical_probability(current_away)
        
        # 统计该赔率范围的真实胜率
        similar_home = [m for m in league_matches 
                       if abs(m['主队赔率'] - current_home) / current_home < 0.1]
        if len(similar_home) >= 10:
            actual_home_rate = sum(1 for m in similar_home if get_match_result(m) == 'H') / len(similar_home) * 100
            home_value = actual_home_rate - theoretical_home
            
            if home_value > 3:
                warnings.append({
                    "type": "value_opportunity",
                    "bet": "主胜",
                    "odds": current_home,
                    "theoretical_prob": round(theoretical_home, 2),
                    "actual_prob": round(actual_home_rate, 2),
                    "value": round(home_value, 2)
                })
    
    return {
        "status": "complete",
        "has_anomaly": len(anomalies) > 0,
        "anomalies": anomalies,
        "warnings": warnings,
        "league_avg_odds": {
            "home": round(avg_home, 2),
            "draw": round(avg_draw, 2),
            "away": round(avg_away, 2)
        }
    }


# ============================================================
# 导出函数
# ============================================================

def analyze_value_bets(matches: List[Dict], threshold: float = 2.0) -> List[Dict]:
    """兼容旧接口"""
    return analyze_value_bets_by_odds_range(matches, threshold)


def analyze_league_odds(league_code: str, lottery_type: str = "竞彩足球") -> Dict:
    """兼容旧接口"""
    data = load_data(lottery_type)
    matches = [m for m in data['matches'] if m['联赛代码'] == league_code]
    valid = [m for m in matches if m.get('主队赔率') and m.get('平局赔率') and m.get('客队赔率')]
    
    if not valid:
        return {"error": "没有有效数据"}
    
    avg_home = sum(m['主队赔率'] for m in valid) / len(valid)
    avg_draw = sum(m['平局赔率'] for m in valid) / len(valid)
    avg_away = sum(m['客队赔率'] for m in valid) / len(valid)
    
    margins = [calculate_bookmaker_margin(m['主队赔率'], m['平局赔率'], m['客队赔率']) for m in valid]
    avg_margin = sum(margins) / len(margins)
    
    home_wins = sum(1 for m in valid if get_match_result(m) == 'H')
    draws = sum(1 for m in valid if get_match_result(m) == 'D')
    
    return {
        "league_code": league_code,
        "match_count": len(valid),
        "average_odds": {
            "home": round(avg_home, 2),
            "draw": round(avg_draw, 2),
            "away": round(avg_away, 2)
        },
        "average_margin": round(avg_margin, 2),
        "result_distribution": {
            "home_win": home_wins,
            "draw": draws,
            "away_win": len(valid) - home_wins - draws,
            "home_win_rate": round(home_wins / len(valid) * 100, 2),
            "draw_rate": round(draws / len(valid) * 100, 2),
            "away_win_rate": round((len(valid) - home_wins - draws) / len(valid) * 100, 2)
        }
    }


def find_best_value_leagues(lottery_type: str = "竞彩足球", top_n: int = 10) -> List[Dict]:
    """兼容旧接口"""
    data = load_data(lottery_type)
    league_analysis = analyze_value_bets_by_league(data["matches"])
    return [{
        "league_name": l["league_name"],
        "value": l["overall_value"],
        "match_count": l["match_count"],
        "home_win_rate": l["home_win_rate"],
        "avg_margin": l["avg_margin"],
        "recommendation": l["recommendation"]["type"]
    } for l in league_analysis[:top_n]]


# ============================================================
# 测试
# ============================================================

def main():
    """测试函数"""
    print("=" * 70)
    print("赔率分析Skill - 增强版测试")
    print("=" * 70)
    
    # 加载竞彩足球数据
    data = load_data("竞彩足球")
    matches = data["matches"]
    print(f"\n总比赛数: {len(matches):,}")
    
    # 1. 按赔率区间分析
    print("\n" + "=" * 70)
    print("【按赔率区间分析】")
    print("=" * 70)
    odds_analysis = analyze_value_bets_by_odds_range(matches)
    
    print(f"{'区间':<10} {'比赛数':>8} {'主胜率':>8} {'理论':>8} {'价值':>8} {'平局率':>8} {'客胜率':>8} {'建议':>12}")
    print("-" * 90)
    for vb in odds_analysis:
        best = vb["best_bet"]
        print(f"{vb['name']:<10} {vb['match_count']:>8} {vb['home_win_rate']:>7.1f}% {vb['theoretical_home']:>7.1f}% {vb['home_value']:>+7.1f}% {vb['draw_rate']:>7.1f}% {vb['away_win_rate']:>7.1f}% {best[0]:>12}")
    
    # 2. 联赛价值排名
    print("\n" + "=" * 70)
    print("【联赛价值排名TOP10】")
    print("=" * 70)
    league_analysis = analyze_value_bets_by_league(matches)
    
    print(f"{'联赛':<20} {'比赛数':>8} {'主胜率':>8} {'主队价值':>10} {'整体价值':>10} {'建议':>15}")
    print("-" * 85)
    for league in league_analysis[:10]:
        rec = league["recommendation"]["type"]
        print(f"{league['league_name']:<20} {league['match_count']:>8} {league['home_win_rate']:>7.1f}% {league['home_value']:>+9.1f}% {league['overall_value']:>+9.1f}% {rec:>15}")
    
    # 3. 最佳价值组合
    print("\n" + "=" * 70)
    print("【最佳价值投注组合TOP10】")
    print("=" * 70)
    value_combos = find_best_value_combinations(matches, min_value=3.0)
    
    for i, combo in enumerate(value_combos[:10], 1):
        print(f"{i:2}. {combo['league']:<15} {combo['match']:<30} {combo['bet']:<4} @ {combo['odds']:.2f} 价值:{combo['value']:+.1f}%")
    
    print("\n✓ 测试完成!")


if __name__ == "__main__":
    main()
