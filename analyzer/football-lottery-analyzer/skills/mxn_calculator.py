#!/usr/bin/env python3
"""
M串N计算工具 - Skill
功能：
1. 计算M串N完整组合
2. 计算投注金额
3. 计算奖金
4. 计算容错范围
5. 智能推荐M串N组合
"""

import json
import os
from itertools import combinations
from typing import Dict, List, Tuple, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_mxn_rules() -> Dict:
    """加载M串N组合规则"""
    with open(os.path.join(BASE_DIR, 'knowledge', 'mxn_combinations.json'), 'r', encoding='utf-8') as f:
        return json.load(f)


def load_official_rules() -> Dict:
    """加载官方规则"""
    with open(os.path.join(BASE_DIR, 'knowledge', 'official_rules.json'), 'r', encoding='utf-8') as f:
        return json.load(f)


def calculate_combinations(m: int, n_type: str = "full") -> Dict:
    """
    计算M串N的组合数
    
    Args:
        m: 选择比赛场数
        n_type: 组合类型
            - "1": 只有M串1
            - "4": M串4 (含2串1和3串1)
            - "11": M串11 (含2串1,3串1,4串1)
            - "full": 完整组合
            - "min_error": 最小容错组合
            - "max_error": 最大容错组合
    
    Returns:
        包含组合信息的字典
    """
    rules = load_mxn_rules()
    
    if m > 15 or m < 2:
        raise ValueError("M值必须在2-15之间")
    
    m_str = str(m)
    combos = rules["北京单场"]["combinations"].get(m_str, {})
    
    if n_type == "full":
        # 最完整的组合
        for key, value in combos.items():
            if "2串1" in value and "3串1" in value and f"{m}串1" in value:
                return {
                    "m": m,
                    "n_type": key,
                    "total_bets": value["total"],
                    "breakdown": value,
                    "max_error": m - min([int(k.replace("串1", "")) for k in value.keys()])
                }
    elif n_type == "1":
        # 只有M串1
        return {
            "m": m,
            "n_type": f"{m}串1",
            "total_bets": 1,
            "breakdown": {f"{m}串1": 1},
            "max_error": 0
        }
    elif n_type == "min_error":
        # 最小容错（只有2串1）
        for key, value in combos.items():
            if list(value.keys()) == ["total", "2串1"]:
                return {
                    "m": m,
                    "n_type": key,
                    "total_bets": value["total"],
                    "breakdown": value,
                    "max_error": m - 2
                }
    elif n_type == "max_error":
        # 最大容错（完整组合）
        return calculate_combinations(m, "full")
    else:
        # 指定具体类型
        key = f"{m}串{n_type}"
        if key in combos:
            value = combos[key]
            return {
                "m": m,
                "n_type": key,
                "total_bets": value["total"],
                "breakdown": value,
                "max_error": m - min([int(k.replace("串1", "")) for k in value.keys() if k != "total"])
            }
    
    return None


def list_all_mxn_options(m: int, lottery_type: str = "北京单场") -> List[Dict]:
    """
    列出所有可用的M串N选项
    
    Args:
        m: 选择比赛场数
        lottery_type: 彩票类型 ("竞彩足球" 或 "北京单场")
    
    Returns:
        所有可用组合的列表
    """
    rules = load_mxn_rules()
    
    m_str = str(m)
    combos = rules[lottery_type]["combinations"].get(m_str, {})
    
    result = []
    for key, value in combos.items():
        result.append({
            "name": key,
            "total_bets": value["total"],
            "breakdown": {k: v for k, v in value.items() if k != "total"},
            "max_error": m - min([int(k.replace("串1", "")) for k in value.keys() if k != "total"]),
            "cost_2yuan": value["total"] * 2
        })
    
    # 按总注数排序
    result.sort(key=lambda x: x["total_bets"])
    return result


def calculate_bet_amount(total_bets: int, unit_price: int = 2, multiplier: int = 1) -> int:
    """
    计算投注金额
    
    Args:
        total_bets: 总注数
        unit_price: 单注价格(默认2元)
        multiplier: 倍数(默认1倍)
    
    Returns:
        总投注金额
    """
    return total_bets * unit_price * multiplier


def calculate_parlay_odds(matches: List[Dict], lottery_type: str = "竞彩足球") -> Dict:
    """
    计算串关的赔率
    
    Args:
        matches: 比赛列表，每个包含odds字段
        lottery_type: 彩票类型
    
    Returns:
        各关次的理论赔率
    """
    if not matches:
        return {}
    
    odds_list = [m.get("odds", 1.0) for m in matches]
    
    result = {}
    for k in range(2, len(odds_list) + 1):
        # C(len, k) 组合数
        combo_odds = []
        for combo in combinations(odds_list, k):
            combo_odds.append(combo)
        result[f"{k}串1"] = combo_odds
    
    return result


def recommend_mxn(m: int, budget: float, lottery_type: str = "竞彩足球") -> List[Dict]:
    """
    根据预算推荐M串N组合
    
    Args:
        m: 选择比赛场数
        budget: 预算金额
        lottery_type: 彩票类型
    
    Returns:
        推荐组合列表
    """
    options = list_all_mxn_options(m, lottery_type)
    
    # 计算每种组合的成本和性价比
    recommendations = []
    for opt in options:
        cost = opt["cost_2yuan"]
        if cost <= budget:
            # 计算性价比（容错能力/成本）
            efficiency = opt["max_error"] / (cost / 2) if cost > 0 else 0
            recommendations.append({
                **opt,
                "cost": cost,
                "efficiency": round(efficiency, 4),
                "value_score": opt["max_error"] * 10 + efficiency * 100
            })
    
    # 按价值排序
    recommendations.sort(key=lambda x: -x["value_score"])
    
    return recommendations[:5]  # 返回前5个推荐


def get_play_type_limits(lottery_type: str, play_type: str) -> Dict:
    """
    获取玩法的串关限制
    
    Args:
        lottery_type: 彩票类型
        play_type: 玩法类型
    
    Returns:
        玩法限制信息
    """
    rules = load_mxn_rules()
    return rules[lottery_type]["play_type_limits"].get(play_type, {})


def main():
    """主函数 - 测试用"""
    print("=" * 60)
    print("M串N计算工具 - 测试")
    print("=" * 60)
    
    # 测试：列出5串的所有选项
    print("\n【5串所有可用组合】")
    options = list_all_mxn_options(5, "竞彩足球")
    for opt in options:
        print(f"  {opt['name']}: {opt['total_bets']}注, 容错{opt['max_error']}场, 金额{opt['cost_2yuan']}元")
    
    print("\n【根据预算推荐】(预算100元)")
    recs = recommend_mxn(5, 100, "竞彩足球")
    for i, rec in enumerate(recs, 1):
        print(f"  推荐{i}: {rec['name']} - {rec['cost']}元, 容错{rec['max_error']}场")
    
    print("\n【根据预算推荐】(预算500元, 8串)")
    recs = recommend_mxn(8, 500, "北京单场")
    for i, rec in enumerate(recs, 1):
        print(f"  推荐{i}: {rec['name']} - {rec['cost']}元, 容错{rec['max_error']}场")
    
    print("\n【玩法限制查询】")
    print(f"  竞彩足球-比分: {get_play_type_limits('竞彩足球', '比分')}")
    print(f"  北京单场-胜平负: {get_play_type_limits('北京单场', '胜平负')}")


if __name__ == "__main__":
    main()
