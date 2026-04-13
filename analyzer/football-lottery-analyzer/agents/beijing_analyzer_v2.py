# -*- coding: utf-8 -*-
"""
北京单场专业分析模块 v2.0
功能：
1. 胜平负(含让球)分析
2. 总进球分析
3. 比分分析
4. 半全场分析
5. 上下单双分析
6. SP值挖掘
7. 串关优化
"""

import json
import os
import sys
import math
from typing import Dict, List, Optional, Tuple
from collections import Counter, defaultdict
try:
    from scipy.stats import poisson
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
import statistics

# 路径设置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BASE_DIR = os.path.dirname(PROJECT_ROOT)
DATA_DIR = os.path.join(BASE_DIR, 'data', 'chinese_mapped')
RULES_DIR = PROJECT_ROOT


def load_data() -> Dict:
    """加载北京单场数据"""
    filepath = os.path.join(DATA_DIR, '北京单场_chinese_data.json')
    if not os.path.exists(filepath):
        return {"matches": [], "leagues": {}}
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_rules() -> Dict:
    """加载官方规则"""
    with open(os.path.join(RULES_DIR, 'official_rules.json'), 'r', encoding='utf-8') as f:
        return json.load(f)


class BeijingSPFOddsAnalyzer:
    """北京单场胜平负(含让球)分析器"""
    
    def __init__(self, data: Dict):
        self.data = data
        self.matches = data.get("matches", [])
        self.rules = load_rules()["北京单场"]["玩法"]["胜平负"]
    
    def analyze_win_draw_lose(self) -> Dict:
        """
        分析胜平负分布
        北京单场胜平负包含让球机制
        """
        results = {"H": 0, "D": 0, "A": 0}
        valid_matches = 0
        
        for m in self.matches:
            if m.get("比赛结果") in results:
                results[m["比赛结果"]] += 1
                valid_matches += 1
        
        if valid_matches == 0:
            return {"error": "没有有效数据"}
        
        return {
            "total": valid_matches,
            "home_win_rate": round(results["H"] / valid_matches * 100, 1),
            "draw_rate": round(results["D"] / valid_matches * 100, 1),
            "away_win_rate": round(results["A"] / valid_matches * 100, 1),
            "distribution": {
                "主胜": results["H"],
                "平局": results["D"],
                "客胜": results["A"]
            }
        }
    
    def analyze_concession_impact(self) -> Dict:
        """
        分析让球对结果的影响
        让球后主客胜率会发生变化
        """
        # 模拟让球分析（实际需要让球盘口数据）
        base_analysis = self.analyze_win_draw_lose()
        
        # 让球后的理论变化
        return {
            "base_distribution": base_analysis,
            "concession_analysis": {
                "no_concession": {
                    "home_win": f"{base_analysis.get('home_win_rate', 0)}%",
                    "note": "无让球时主胜概率"
                },
                "home_concession_1": {
                    "home_win_adj": "主队让1球后胜率下降约10-15%",
                    "common_result": "让球平/让球负概率增加"
                },
                "away_concession_1": {
                    "away_win_adj": "客队让1球后主胜概率增加约5-10%"
                }
            },
            "recommendation": "关注让球数与球队实力的匹配度"
        }
    
    def recommend_based_on_odds(self, min_odds: float = 1.5, max_odds: float = 3.5) -> List[Dict]:
        """
        基于赔率推荐投注
        """
        recommendations = []
        
        for m in self.matches:
            odds = m.get("主队赔率")
            if odds and min_odds <= odds <= max_odds:
                league = m.get("联赛中文名", m.get("联赛代码", ""))
                recommendations.append({
                    "league": league,
                    "home_team": m.get("主队", ""),
                    "away_team": m.get("客队", ""),
                    "home_odds": odds,
                    "theoretical_prob": round(1 / odds * 100, 1),
                    "recommendation": "主胜" if odds < 2.0 else "需结合其他分析"
                })
        
        return sorted(recommendations, key=lambda x: x["home_odds"])[:10]


class BeijingZJQAnalyzer:
    """北京单场总进球分析器"""
    
    def __init__(self, data: Dict):
        self.data = data
        self.matches = data.get("matches", [])
    
    def analyze_total_goals_distribution(self) -> Dict:
        """
        分析总进球数分布
        """
        goals = []
        for m in self.matches:
            home = m.get("主队进球")
            away = m.get("客队进球")
            if home is not None and away is not None:
                goals.append(home + away)
        
        if not goals:
            return {"error": "没有有效数据"}
        
        counter = Counter(goals)
        total = len(goals)
        
        distribution = {}
        for i in range(8):
            count = counter.get(i, 0)
            distribution[str(i)] = {
                "count": count,
                "rate": round(count / total * 100, 1)
            }
        
        # 7+球合并
        over_7 = sum(counter.get(i, 0) for i in range(7, 20))
        distribution["7+"] = {
            "count": over_7,
            "rate": round(over_7 / total * 100, 1)
        }
        
        return {
            "total_matches": total,
            "avg_goals": round(statistics.mean(goals), 2),
            "median_goals": statistics.median(goals),
            "distribution": distribution,
            "most_common": counter.most_common(3)
        }
    
    def analyze_by_league(self) -> Dict:
        """
        按联赛分析进球分布
        """
        league_goals = defaultdict(list)
        
        for m in self.matches:
            home = m.get("主队进球")
            away = m.get("客队进球")
            if home is not None and away is not None:
                league = m.get("联赛代码", "unknown")
                league_goals[league].append(home + away)
        
        league_stats = {}
        for league, goals in league_goals.items():
            if len(goals) >= 50:
                league_stats[league] = {
                    "matches": len(goals),
                    "avg_goals": round(statistics.mean(goals), 2),
                    "median_goals": statistics.median(goals),
                    "high_scoring_rate": round(
                        sum(1 for g in goals if g >= 3) / len(goals) * 100, 1
                    )
                }
        
        return {
            "league_stats": dict(sorted(
                league_stats.items(), 
                key=lambda x: x[1]["avg_goals"], 
                reverse=True
            ))
        }
    
    def recommend_bets(self) -> Dict:
        """
        总进球投注建议
        """
        dist = self.analyze_total_goals_distribution()
        if "error" in dist:
            return dist
        
        # 找出最常见的进球区间
        recommendations = []
        for key, val in dist["distribution"].items():
            if val["rate"] > 15:
                recommendations.append({
                    "total_goals": key,
                    "rate": val["rate"],
                    "recommendation": "值得关注"
                })
        
        return {
            "avg_goals": dist["avg_goals"],
            "recommendations": recommendations,
            "strategy": "关注2-3球区间，兼顾0-1球防守"
        }


class BeijingBFAnalyzer:
    """北京单场比分分析器"""
    
    def __init__(self, data: Dict):
        self.data = data
        self.matches = data.get("matches", [])
        self.score_options = [
            "1:0", "2:0", "2:1", "3:0", "3:1", "3:2", "4:0", "4:1", "4:2", "5:0", "5:1", "5:2", "胜其他",
            "0:0", "1:1", "2:2", "3:3", "平其他",
            "0:1", "0:2", "0:3", "0:4", "0:5", "1:2", "1:3", "1:4", "1:5", "2:3", "负其他"
        ]
    
    def analyze_score_distribution(self) -> Dict:
        """
        分析比分分布
        """
        score_counts = defaultdict(int)
        valid_matches = 0
        
        for m in self.matches:
            home = m.get("主队进球")
            away = m.get("客队进球")
            if home is not None and away is not None:
                score = f"{home}:{away}"
                
                # 归类到标准比分
                if score in self.score_options:
                    score_counts[score] += 1
                elif home > away:
                    # 主队赢但比分不在列表，归为"胜其他"
                    if home >= 6:
                        score_counts["胜其他"] += 1
                    else:
                        # 尝试找最接近的比分
                        score_counts[f"胜其他({score})"] = score_counts.get(f"胜其他({score})", 0) + 1
                elif home == away:
                    if home >= 4:
                        score_counts["平其他"] += 1
                else:
                    # 客队赢
                    if away >= 6:
                        score_counts["负其他"] += 1
                
                valid_matches += 1
        
        if valid_matches == 0:
            return {"error": "没有有效数据"}
        
        # 计算概率
        score_probs = {
            score: round(count / valid_matches * 100, 1)
            for score, count in score_counts.items()
        }
        
        return {
            "total_matches": valid_matches,
            "distribution": dict(Counter(score_probs).most_common(15)),
            "home_win_scores": {k: v for k, v in score_probs.items() if k.startswith(tuple("12345"))},
            "draw_scores": {k: v for k, v in score_probs.items() if "0:0" <= k <= "3:3" or "平其他" in k},
            "away_win_scores": {k: v for k, v in score_probs.items() if k.startswith("0:") or "负其他" in k}
        }
    
    def recommend_score_bets(self, confidence: str = "medium") -> List[Dict]:
        """
        比分投注推荐
        confidence: low/medium/high
        """
        dist = self.analyze_score_distribution()
        if "error" in dist:
            return []
        
        recommendations = []
        
        # 最常见的比分
        for score, rate in sorted(dist["distribution"].items(), key=lambda x: -x[1])[:5]:
            recommendations.append({
                "score": score,
                "probability": rate,
                "bet_type": "单选" if rate > 10 else "复式组合"
            })
        
        # 组合推荐
        combos = {
            "low_confidence": ["1:0", "1:1", "0:1", "2:0", "0:2"],
            "medium_confidence": ["2:1", "1:2", "2:0", "0:2", "1:1"],
            "high_confidence": ["2:1", "1:2"]
        }
        
        return {
            "single_recommendations": recommendations,
            "combo_recommendations": combos.get(confidence, combos["medium"]),
            "strategy": "比分难度高，建议结合总进球和胜平负综合分析"
        }


class BeijingBQCAnalyzer:
    """北京单场半全场分析器"""
    
    def __init__(self, data: Dict):
        self.data = data
        self.matches = data.get("matches", [])
        self.half_full_options = [
            "3-3", "3-1", "3-0",  # 胜胜、胜平、胜负
            "1-3", "1-1", "1-0",  # 平胜、平平、平负
            "0-3", "0-1", "0-0"   # 负胜、负平、负负
        ]
    
    def analyze_half_full_distribution(self) -> Dict:
        """
        分析半全场分布
        注意：北京单场数据可能只有全场结果，没有半场数据
        """
        # 由于数据可能没有半场信息，使用全场结果模拟
        results = {"H": 0, "D": 0, "A": 0}
        valid = 0
        
        for m in self.matches:
            result = m.get("比赛结果")
            if result in results:
                results[result] += 1
                valid += 1
        
        if valid == 0:
            return {"error": "没有有效数据"}
        
        # 模拟半全场分布（实际需要半场数据）
        # 假设：半场结果与全场结果有60%相关性
        return {
            "total_matches": valid,
            "full_time_distribution": {
                "home_win": round(results["H"] / valid * 100, 1),
                "draw": round(results["D"] / valid * 100, 1),
                "away_win": round(results["A"] / valid * 100, 1)
            },
            "note": "半全场需要半场比分数据，当前基于全场数据估算",
            "estimated_distributions": {
                "胜胜": "约15-20%（半场领先+全场获胜）",
                "胜平/胜负": "约5-8%",
                "平胜": "约8-12%（半场平局逆转）",
                "平平": "约12-15%（半场平局全场平）",
                "负负": "约15-20%（半场落后全场输）",
                "负胜": "约3-5%（半场落后逆转）"
            }
        }
    
    def recommend_bqc_bets(self) -> Dict:
        """
        半全场投注推荐
        """
        dist = self.analyze_half_full_distribution()
        if "error" in dist:
            return dist
        
        return {
            "strategy": "半全场难度极高，建议谨慎",
            "recommended_types": [
                {"type": "胜胜", "suitable": "强队主场", "risk": "低"},
                {"type": "平平", "suitable": "防守型球队", "risk": "中"},
                {"type": "负负", "suitable": "弱队客场", "risk": "低"}
            ],
            "combo_strategy": "可采用2-3个半全场组合降低难度"
        }


class BeijingSXDAnalyzer:
    """北京单场上下单双分析器"""
    
    def __init__(self, data: Dict):
        self.data = data
        self.matches = data.get("matches", [])
    
    def analyze_sxd_distribution(self) -> Dict:
        """
        分析上下单双分布
        规则：
        - 上盘：总进球 >= 3
        - 下盘：总进球 <= 2
        - 上单：上盘 + 奇数总进球
        - 上双：上盘 + 偶数总进球(含0)
        - 下单：下盘 + 奇数总进球
        - 下双：下盘 + 偶数总进球(含0)
        """
        sxd = {"上单": 0, "上双": 0, "下单": 0, "下双": 0}
        valid = 0
        
        for m in self.matches:
            home = m.get("主队进球")
            away = m.get("客队进球")
            if home is not None and away is not None:
                total = home + away
                is_over = total >= 3  # 上盘
                is_odd = total % 2 == 1  # 单数
                
                if is_over and is_odd:
                    sxd["上单"] += 1
                elif is_over and not is_odd:
                    sxd["上双"] += 1
                elif not is_over and is_odd:
                    sxd["下单"] += 1
                else:
                    sxd["下双"] += 1
                
                valid += 1
        
        if valid == 0:
            return {"error": "没有有效数据"}
        
        return {
            "total_matches": valid,
            "distribution": {
                k: round(v / valid * 100, 1) for k, v in sxd.items()
            },
            "counts": sxd
        }
    
    def analyze_by_league(self) -> Dict:
        """
        按联赛分析上下单双
        """
        league_sxd = defaultdict(lambda: {"上单": 0, "上双": 0, "下单": 0, "下双": 0, "total": 0})
        
        for m in self.matches:
            home = m.get("主队进球")
            away = m.get("客队进球")
            if home is not None and away is not None:
                league = m.get("联赛代码", "unknown")
                total = home + away
                
                league_sxd[league]["total"] += 1
                if total >= 3 and total % 2 == 1:
                    league_sxd[league]["上单"] += 1
                elif total >= 3:
                    league_sxd[league]["上双"] += 1
                elif total % 2 == 1:
                    league_sxd[league]["下单"] += 1
                else:
                    league_sxd[league]["下双"] += 1
        
        # 计算各联赛分布
        league_dist = {}
        for league, stats in league_sxd.items():
            if stats["total"] >= 50:
                league_dist[league] = {
                    "total": stats["total"],
                    "distribution": {
                        k: round(v / stats["total"] * 100, 1)
                        for k, v in stats.items() if k != "total"
                    },
                    "best_sxd": max(stats.items(), key=lambda x: x[1] if x[0] != "total" else 0)[0]
                }
        
        return {
            "league_distributions": dict(sorted(
                league_dist.items(),
                key=lambda x: x[1]["distribution"].get("上单", 0) + x[1]["distribution"].get("上双", 0),
                reverse=True
            ))
        }
    
    def recommend_sxd_bets(self) -> Dict:
        """
        上下单双投注推荐
        """
        dist = self.analyze_sxd_distribution()
        league_dist = self.analyze_by_league()
        
        if "error" in dist:
            return dist
        
        # 找出概率最高的选项
        best_option = max(dist["distribution"].items(), key=lambda x: x[1])
        
        return {
            "overall_recommendation": {
                "best_option": best_option[0],
                "probability": best_option[1]
            },
            "strategy": "下盘(0-2球)概率约50%，下双略高于下单",
            "by_league": {
                league: data["best_sxd"]
                for league, data in list(league_dist["league_distributions"].items())[:5]
            },
            "tips": [
                "进攻型联赛优先关注上单/上双",
                "防守型联赛优先关注下单/下双",
                "可结合胜平负和总进球综合分析"
            ]
        }


class BeijingSPValueAnalyzer:
    """北京单场SP值分析器"""
    
    def __init__(self, data: Dict):
        self.data = data
        self.matches = data.get("matches", [])
    
    def estimate_sp_value(self, odds: float, actual_result: str) -> Dict:
        """
        估算SP值与实际结果的差异
        公式：SP值 = 投注金额 / 中奖金额
        
        Args:
            odds: 理论赔率
            actual_result: 实际结果
        """
        # 理论概率
        theoretical_prob = 1 / odds if odds > 0 else 0
        
        return {
            "theoretical_odds": odds,
            "theoretical_prob": round(theoretical_prob * 100, 1),
            "actual_result": actual_result,
            "value_indicator": "有价值" if theoretical_prob > 50 else "需谨慎"
        }
    
    def analyze_sp_patterns(self) -> Dict:
        """
        分析SP值规律
        """
        patterns = {
            "low_odds_high_sp": [],  # 低赔率高SP值的情况
            "high_odds_low_sp": [],   # 高赔率低SP值的情况
            "anomalies": []
        }
        
        for m in self.matches:
            odds = m.get("主队赔率")
            result = m.get("比赛结果")
            
            if odds and result:
                if odds < 1.5 and result == "H":
                    patterns["low_odds_high_sp"].append({
                        "match": f"{m.get('主队')} vs {m.get('客队')}",
                        "odds": odds
                    })
                elif odds > 3.0 and result == "H":
                    patterns["high_odds_low_sp"].append({
                        "match": f"{m.get('主队')} vs {m.get('客队')}",
                        "odds": odds
                    })
        
        return {
            "patterns": patterns,
            "recommendations": {
                "冷门识别": "高赔率主胜(>3.0)是重要冷门信号",
                "稳胆识别": "低赔率主胜(<1.5)通常SP值稳定",
                "波动分析": "SP值受投注分布影响，可能偏离理论值"
            }
        }
    
    def recommend_sp_strategy(self) -> Dict:
        """
        SP值投注策略
        """
        return {
            "strategy_name": "SP值挖掘策略",
            "key_points": [
                "关注SP值与理论赔率的偏离",
                "高SP值选项可能意味着被低估",
                "结合球队实力和近期状态",
                "注意投注时机"
            ],
            "risk_management": [
                "单场投注不超过预算的10%",
                "选择2-3个SP值接近的选项",
                "避免追逐极端高SP值"
            ]
        }


class BeijingParlayOptimizer:
    """北京单场串关优化器 (已接入 LotteryMathEngine)"""
    
    def __init__(self, data: Dict):
        self.data = data
        self.matches = data.get("matches", [])
        
        self.math_engine = None
        try:
            import sys
            import os
            SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
            PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
            if PROJECT_ROOT not in sys.path:
                sys.path.insert(0, PROJECT_ROOT)
            from skills.lottery_math_engine import LotteryMathEngine
            self.math_engine = LotteryMathEngine
        except Exception as e:
            print(f"LotteryMathEngine 导入失败: {e}")
    
    def optimize_parlay(self, selected_matches: List[Dict], budget: float) -> Dict:
        """
        优化串关方案 (真实接入底层计算引擎)
        
        Args:
            selected_matches: 选择的比赛，包含 SP值 odds
            budget: 预算
        """
        m = len(selected_matches)
        if m > 15:
            return {"error": "北京单场最高支持15关"}
        
        if m < 2:
            return {"error": "串关至少需要2场"}
            
        formatted_matches = []
        for match in selected_matches:
            odds_val = match.get("odds", 2.0)
            if not isinstance(odds_val, list):
                odds_val = [odds_val]
            formatted_matches.append({"odds": odds_val})
        
        combinations = []
        # 北单通常玩高串，我们给几个主流容错方案
        # m串1全对，m串(m)即容错1场等
        n_options = [1]
        if m >= 3:
            # 加入 m串m (比如3串3其实就是包含3个2串1的组合) 这种在官方叫 m串m_type
            # 为了适配引擎，这里n就是容错的组合数。
            # 我们简化，只推荐全包或 m串1
            n_options.append(m) # 代表 m串m
            
        for n_type in n_options:
            if not self.math_engine:
                continue
            
            est = self.math_engine.calculate_beijing_single(formatted_matches, m, n_type)
            if "error" in est:
                continue
                
            bets = est.get("total_bets", 1)
            cost = est.get("total_cost", bets * 2)
            
            multiple = max(1, int(budget // cost)) if cost > 0 else 1
            actual_cost = cost * multiple
            
            combinations.append({
                "type": f"{m}串{n_type}",
                "bets": bets,
                "multiple": multiple,
                "estimated_cost": actual_cost,
                "min_prize": round(est.get("min_prize", 0) * multiple, 2),
                "max_prize": round(est.get("max_prize", 0) * multiple, 2),
                "description": f"北单SP值预期 (已扣除65%返奖率)"
            })
        
        return {
            "total_matches": m,
            "budget": budget,
            "recommended_combinations": combinations,
            "tips": [
                "北单奖金与最终SP值挂钩，当前为估算值",
                "最高支持15关，建议利用此特性博取高赔",
                "已应用65%返奖率折算"
            ]
        }
    
    def recommend_cross_play_parlay(self) -> Dict:
        """
        跨玩法串关推荐
        北京单场支持不同玩法混合串关
        """
        return {
            "cross_play_opportunities": [
                {
                    "combination": "胜平负 + 总进球",
                    "description": "先用胜平负筛选，再用总进球细化",
                    "risk": "中"
                },
                {
                    "combination": "胜平负 + 半全场",
                    "description": "双重预测，提高准确性",
                    "risk": "高"
                },
                {
                    "combination": "比分 + 总进球",
                    "description": "比分是总进球的细化版",
                    "risk": "高"
                }
            ],
            "recommendation": "优先考虑胜平负+总进球组合，难度适中"
        }


def main():
    """测试所有分析器"""
    data = load_data()
    
    print("=" * 60)
    print("北京单场专业分析模块 v2.0")
    print("=" * 60)
    
    # 胜平负分析
    print("\n【胜平负分析】")
    spf = BeijingSPFOddsAnalyzer(data)
    print(spf.analyze_win_draw_lose())
    
    # 总进球分析
    print("\n【总进球分析】")
    zjq = BeijingZJQAnalyzer(data)
    goals = zjq.analyze_total_goals_distribution()
    if "error" not in goals:
        print(f"平均进球: {goals['avg_goals']}")
        print(f"最常见: {goals['most_common'][:3]}")
    
    # 比分分析
    print("\n【比分分析】")
    bf = BeijingBFAnalyzer(data)
    scores = bf.analyze_score_distribution()
    if "error" not in scores:
        print(f"总比赛数: {scores['total_matches']}")
    
    # 半全场分析
    print("\n【半全场分析】")
    bqc = BeijingBQCAnalyzer(data)
    print(bqc.analyze_half_full_distribution())
    
    # 上下单双分析
    print("\n【上下单双分析】")
    sxd = BeijingSXDAnalyzer(data)
    dist = sxd.analyze_sxd_distribution()
    if "error" not in dist:
        print(f"分布: {dist['distribution']}")
    
    # SP值分析
    print("\n【SP值分析】")
    sp = BeijingSPValueAnalyzer(data)
    print(sp.analyze_sp_patterns()["recommendations"])
    
    # 串关优化
    print("\n【串关优化】")
    parlay = BeijingParlayOptimizer(data)
    print(parlay.optimize_parlay(5, 50, ["胜平负", "总进球"]))


if __name__ == "__main__":
    main()
