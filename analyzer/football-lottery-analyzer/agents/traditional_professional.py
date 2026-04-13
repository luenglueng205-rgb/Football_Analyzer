# -*- coding: utf-8 -*-
"""
传统足彩专业分析模块 v2.0
功能：
1. 14场胜负深度分析
2. 任选9场智能胆拖优化
3. 6场半全场预测
4. 4场进球预测
5. 奖池分析
"""

import json
import os
import sys
import math
from typing import Dict, List, Optional, Tuple
from collections import Counter, defaultdict
import statistics

try:
    from scipy.stats import poisson, entropy
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

# 路径设置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BASE_DIR = os.path.dirname(PROJECT_ROOT)
DATA_DIR = os.path.join(BASE_DIR, 'data', 'chinese_mapped')
RULES_DIR = PROJECT_ROOT


def load_data() -> Dict:
    """加载传统足彩数据"""
    filepath = os.path.join(DATA_DIR, '传统足彩_chinese_data.json')
    if not os.path.exists(filepath):
        return {"matches": [], "leagues": {}}
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_rules() -> Dict:
    """加载官方规则"""
    with open(os.path.join(RULES_DIR, 'official_rules.json'), 'r', encoding='utf-8') as f:
        return json.load(f)


class Traditional14Analyzer:
    """14场胜负深度分析"""
    
    def __init__(self, data: Dict):
        self.data = data
        self.matches = data.get("matches", [])
        self.league_stats = self._calculate_league_stats()
    
    def _calculate_league_stats(self) -> Dict:
        """计算各联赛统计"""
        league_stats = defaultdict(lambda: {
            "total": 0, "home": 0, "draw": 0, "away": 0,
            "cold_matches": 0, "hot_matches": 0
        })
        
        for m in self.matches:
            league = m.get("联赛代码", "unknown")
            result = m.get("比赛结果")
            
            league_stats[league]["total"] += 1
            if result == "H":
                league_stats[league]["home"] += 1
            elif result == "D":
                league_stats[league]["draw"] += 1
            elif result == "A":
                league_stats[league]["away"] += 1
        
        # 计算冷门率
        for league, stats in league_stats.items():
            if stats["total"] >= 50:
                stats["cold_rate"] = round(
                    (stats["draw"] + stats["away"]) / stats["total"] * 100, 1
                )
                stats["home_rate"] = round(stats["home"] / stats["total"] * 100, 1)
        
        return dict(league_stats)
    
    def analyze_current_round(self, matches: List[Dict]) -> Dict:
        """
        分析当前期次14场
        
        Args:
            matches: 当前期次的14场比赛
        """
        # 按联赛分组
        by_league = defaultdict(list)
        for m in matches:
            league = m.get("联赛代码", "unknown")
            by_league[league].append(m)
        
        league_analysis = {}
        for league, league_matches in by_league.items():
            stats = self.league_stats.get(league, {})
            avg_home_rate = stats.get("home_rate", 45)
            
            league_analysis[league] = {
                "match_count": len(league_matches),
                "historical_home_rate": avg_home_rate,
                "expected_upsets": round(len(league_matches) * (100 - avg_home_rate) / 100, 1),
                "stability_rating": self._rate_league_stability(avg_home_rate),
                "recommended_dan": avg_home_rate > 55
            }
        
        # 整体分析
        total_matches = len(matches)
        expected_dans = sum(1 for a in league_analysis.values() if a["recommended_dan"])
        
        return {
            "total_matches": total_matches,
            "by_league": league_analysis,
            "summary": {
                "expected_dans": expected_dans,
                "expected_tuos": total_matches - expected_dans,
                "difficulty": self._estimate_difficulty(total_matches, expected_dans),
                "strategy": self._generate_strategy(expected_dans)
            }
        }
    
    def _rate_league_stability(self, home_rate: float) -> str:
        """评级联赛稳定性"""
        if home_rate >= 60:
            return "非常稳定(适合做胆)"
        elif home_rate >= 50:
            return "较稳定"
        elif home_rate >= 40:
            return "中等"
        else:
            return "高冷门率(适合做拖)"
    
    def _estimate_difficulty(self, total: int, expected_dans: int) -> str:
        """估算难度"""
        dan_ratio = expected_dans / total if total > 0 else 0.5
        if dan_ratio >= 0.7:
            return "较易"
        elif dan_ratio >= 0.5:
            return "中等"
        else:
            return "困难"
    
    def _generate_strategy(self, expected_dans: int) -> Dict:
        """生成投注策略"""
        return {
            "recommended_dan_count": min(max(expected_dans - 1, 5), 9),
            "recommended_tuo_count": 14 - min(max(expected_dans - 1, 5), 9),
            "budget_allocation": {
                "dan_bets": "70%",
                "tuo_bets": "30%"
            }
        }
    
    def recommend_dantuo(
        self,
        matches: List[Dict],
        dan_indices: List[int],
        tuo_options: List[List[str]]
    ) -> Dict:
        """
        推荐胆拖方案
        
        Args:
            matches: 14场比赛
            dan_indices: 做胆的比赛索引
            tuo_options: 每场拖的选择 [["3","1"], ["3"], ...]
        """
        if len(dantuo) != len(tuo_options):
            return {"error": "选项数量不匹配"}
        
        dan_count = len(dan_indices)
        tuo_count = len(tuo_options)
        
        # 计算注数
        # 公式: C(dan_count, dan_count) * product(C(tuo_options[i], 1))
        # 即: 1 * product(len(tuo_options[i]))
        tuo_combinations = math.prod(len(opts) for opts in tuo_options)
        total_bets = tuo_combinations  # 胆全对，拖按选项组合
        
        # 复式成本
        single_bet_cost = 2  # 每注2元
        total_cost = total_bets * single_bet_cost
        
        # 容错分析
        fault_tolerance = self._analyze_fault_tolerance(dan_count, tuo_count)
        
        return {
            "dan_count": dan_count,
            "tuo_count": tuo_count,
            "tuo_options_per_match": [
                {"match": matches[i]["主队"] + " vs " + matches[i]["客队"], 
                 "options": opts}
                for i, opts in zip([j for j in range(14) if j not in dan_indices], tuo_options[:tuo_count])
            ],
            "total_bets": total_bets,
            "total_cost": total_cost,
            "fault_tolerance": fault_tolerance,
            "recommendations": self._generate_dantuo_recommendations(
                dan_count, tuo_count, total_bets, total_cost
            )
        }
    
    def _analyze_fault_tolerance(
        self,
        dan_count: int,
        tuo_count: int
    ) -> Dict:
        """分析容错能力"""
        # 如果胆错1场，需要所有拖都对
        # 如果拖错1场，需要对应胆对
        
        return {
            "dan_can_miss": 0,  # 胆不能错
            "tuo_can_miss": 1,  # 拖可错1场（如果有多个拖）
            "best_case": "全对",
            "acceptable_case": "胆全对+拖错1场",
            "worst_case": "胆错1场"
        }
    
    def _generate_dantuo_recommendations(
        self,
        dan_count: int,
        tuo_count: int,
        total_bets: int,
        total_cost: float
    ) -> List[Dict]:
        """生成胆拖建议"""
        recommendations = []
        
        # 根据胆数建议
        if dan_count >= 8:
            recommendations.append({
                "type": "高胆方案",
                "description": f"{dan_count}个胆 + {tuo_count}个拖",
                "pros": "成本低",
                "cons": "风险高(胆错全输)",
                "cost_range": f"{total_cost}元" if total_cost < 10000 else f"{total_cost/10000:.1f}万"
            })
        elif dan_count >= 6:
            recommendations.append({
                "type": "平衡方案",
                "description": f"{dan_count}个胆 + {tuo_count}个拖",
                "pros": "平衡风险与成本",
                "cons": "需要准确判断",
                "cost_range": f"{total_cost}元" if total_cost < 10000 else f"{total_cost/10000:.1f}万"
            })
        else:
            recommendations.append({
                "type": "保守方案",
                "description": f"{dan_count}个胆 + {tuo_count}个拖",
                "pros": "容错能力强",
                "cons": "成本较高",
                "cost_range": f"{total_cost}元" if total_cost < 10000 else f"{total_cost/10000:.1f}万"
            })
        
        return recommendations


class RX9Optimizer:
    """任选9场智能优化器 (已接入 LotteryMathEngine)"""
    
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
    
    def optimize_rx9(
        self,
        matches_14: List[Dict],
        budget: float,
        confidence_levels: List[float] = None
    ) -> Dict:
        """
        优化任选9场方案 (已接入底层数学引擎计算奖池)
        
        Args:
            matches_14: 14场比赛
            budget: 预算
            confidence_levels: 每场比赛的信心指数 [0-1]
        """
        n = len(matches_14)
        if n != 14:
            return {"error": "需要14场比赛"}
        
        # 默认信心指数（全部1.0）
        if confidence_levels is None:
            confidence_levels = [1.0] * 14
        
        # 按信心指数排序
        sorted_indices = sorted(range(14), key=lambda i: confidence_levels[i], reverse=True)
        
        # 选择最有信心的9场
        selected_indices = sorted_indices[:9]
        
        # 我们基于预算动态分配胆拖
        # 基础公式: bets = C(胆, 胆) * C(拖, 选出来的拖数) * (每个拖的选项数 ^ 选出来的拖数)
        # 任九需要命中9场。如果设了 D 个胆，T 个拖 (D+T>=9)。
        # 用户买的是：从 T 个拖里选 (9-D) 个，所以注数是 C(T, 9-D) * (2^(9-D)) (假设双选)
        
        # 简易策略生成：
        dan_count = 6
        tuo_count = 3  # 6胆3拖
        
        recommended_dan_indices = selected_indices[:dan_count]
        tuo_indices = selected_indices[dan_count:dan_count+tuo_count]
        
        # 建议每拖选2个结果
        options_per_tuo = 2
        # 计算注数: C(3, 3) * 2^3 = 8
        total_bets = math.comb(tuo_count, 9 - dan_count) * (options_per_tuo ** (9 - dan_count))
        total_cost = total_bets * 2
        
        # 结合引擎获取奖池估算
        prize_estimation = {}
        if self.math_engine:
            # 假设奖池 1000 万
            pool = self.math_engine.calculate_traditional(10000000, "RX9")
            if "error" not in pool:
                prize_estimation = pool
        
        return {
            "selected_matches": [
                {
                    "index": i,
                    "match": f"{matches_14[i].get('主队', 'T{}'.format(i+1))} vs {matches_14[i].get('客队', '')}",
                    "confidence": confidence_levels[i],
                    "is_dan": i in recommended_dan_indices
                }
                for i in selected_indices
            ],
            "dan_tuo_plan": {
                "dan_count": dan_count,
                "dan_indices": recommended_dan_indices,
                "tuo_count": tuo_count,
                "tuo_indices": tuo_indices,
                "tuo_options_per_match": options_per_tuo
            },
            "cost_analysis": {
                "total_bets": total_bets,
                "total_cost": total_cost,
                "budget": budget,
                "within_budget": total_cost <= budget
            },
            "prize_estimation": prize_estimation,
            "recommendations": self._generate_rx9_recommendations(
                dan_count, tuo_count, total_bets, total_cost, budget
            )
        }
    
    def _generate_rx9_recommendations(
        self,
        dan_count: int,
        tuo_count: int,
        total_bets: int,
        total_cost: float,
        budget: float
    ) -> List[Dict]:
        """生成任选9场建议"""
        recommendations = []
        
        if total_cost > budget:
            recommendations.append({
                "issue": "成本超出预算",
                "solution": "减少拖的选项数或减少胆数",
                "suggested_options": 1
            })
        
        if dan_count < 5:
            recommendations.append({
                "issue": "胆数偏少",
                "solution": "增加有把握的胆",
                "pros": "成本低",
                "cons": "风险高"
            })
        elif dan_count > 8:
            recommendations.append({
                "issue": "胆数偏多",
                "solution": "减少胆数，增加拖",
                "pros": "风险低",
                "cons": "成本高"
            })
        
        recommendations.append({
            "strategy": "平衡方案",
            "dan_range": "6-7个",
            "tuo_strategy": "每拖选2个结果",
            "optimal_cost_range": "100-500元"
        })
        
        return recommendations
    
    def recommend_combinations(self, matches: List[Dict]) -> List[Dict]:
        """
        推荐任选9场组合
        
        Args:
            matches: 选定的9场比赛
        """
        if len(matches) != 9:
            return {"error": "需要9场比赛"}
        
        combinations = []
        
        # 全包9场单式
        combinations.append({
            "type": "单式全包",
            "bets": 9,
            "cost": 18,
            "description": "每场只选1个结果",
            "risk": "极高"
        })
        
        # 6胆3拖
        combinations.append({
            "type": "6胆3拖",
            "bets": 2 ** 3,  # 每拖2个选项
            "cost": 2 ** 3 * 2,
            "description": "6个稳胆 + 3个双选拖",
            "risk": "中"
        })
        
        # 7胆2拖
        combinations.append({
            "type": "7胆2拖",
            "bets": 2 ** 2,
            "cost": 2 ** 2 * 2,
            "description": "7个稳胆 + 2个双选拖",
            "risk": "低"
        })
        
        # 5胆4拖
        combinations.append({
            "type": "5胆4拖",
            "bets": 2 ** 4,
            "cost": 2 ** 4 * 2,
            "description": "5个稳胆 + 4个双选拖",
            "risk": "中低"
        })
        
        return {
            "total_matches": 9,
            "combinations": combinations,
            "recommended": combinations[2]  # 7胆2拖推荐
        }


class SixBQCPredictor:
    """6场半全场预测器"""
    
    def __init__(self, data: Dict):
        self.data = data
        self.matches = data.get("matches", [])
    
    def predict_6bqc(
        self,
        matches: List[Dict],
        expected_results: List[Dict] = None
    ) -> Dict:
        """
        预测6场半全场
        
        Args:
            matches: 6场比赛
            expected_results: 每场比赛的预期结果 [{half: "3/1/0", full: "3/1/0"}]
        """
        if len(matches) != 6:
            return {"error": "需要6场比赛"}
        
        # 如果没有提供预期结果，生成基于统计的预测
        if expected_results is None:
            expected_results = self._generate_default_predictions(matches)
        
        # 计算每场的半全场概率
        predictions = []
        total_accuracy_difficulty = 1.0
        
        for i, (m, exp) in enumerate(zip(matches, expected_results)):
            half_prob = self._estimate_half_probability(exp["half"])
            full_prob = self._estimate_full_probability(exp["full"])
            combined_prob = half_prob * full_prob / 100
            
            predictions.append({
                "match_index": i + 1,
                "match": f"{m.get('主队', 'T{}'.format(i+1))} vs {m.get('客队', '')}",
                "predicted_bqc": exp.get("bqc", "未知"),
                "half_probability": half_prob,
                "full_probability": full_prob,
                "combined_probability": round(combined_prob, 2),
                "difficulty": "高" if combined_prob < 15 else "中" if combined_prob < 25 else "低"
            })
            
            total_accuracy_difficulty *= combined_prob / 100
        
        # 全部正确的难度
        all_correct_prob = total_accuracy_difficulty * 100
        
        return {
            "predictions": predictions,
            "overall_difficulty": {
                "probability": round(all_correct_prob, 6),
                "rating": "极高" if all_correct_prob < 0.01 else "很高" if all_correct_prob < 0.1 else "高",
                "note": "6场半全场需猜中12个结果，难度极大"
            },
            "recommended_strategy": self._generate_bqc_strategy(predictions)
        }
    
    def _generate_default_predictions(self, matches: List[Dict]) -> List[Dict]:
        """生成默认预测（基于主场优势）"""
        predictions = []
        for m in matches:
            # 假设半场和全场主队都领先
            predictions.append({
                "half": "3",  # 半场主队领先
                "full": "3",  # 全场主队赢
                "bqc": "3-3"
            })
        return predictions
    
    def _estimate_half_probability(self, half_result: str) -> float:
        """估算半场结果概率"""
        prob_map = {
            "3": 35.0,  # 半场主队领先约35%
            "1": 30.0,  # 半场平局约30%
            "0": 35.0   # 半场客队领先约35%
        }
        return prob_map.get(half_result, 33.3)
    
    def _estimate_full_probability(self, full_result: str) -> float:
        """估算全场结果概率"""
        prob_map = {
            "3": 45.0,  # 全场主队赢约45%
            "1": 27.0,  # 全场平局约27%
            "0": 28.0   # 全场客队赢约28%
        }
        return prob_map.get(full_result, 33.3)
    
    def _generate_bqc_strategy(self, predictions: List[Dict]) -> Dict:
        """生成半全场策略"""
        # 按概率排序
        sorted_preds = sorted(predictions, key=lambda x: x["combined_probability"], reverse=True)
        
        return {
            "highest_probability": sorted_preds[:3],
            "lowest_probability": sorted_preds[-3:],
            "recommended_bets": [
                p["predicted_bqc"] for p in sorted_preds[:4] if p["combined_probability"] > 20
            ],
            "avoid_bets": [
                p["predicted_bqc"] for p in sorted_preds[-2:] if p["combined_probability"] < 10
            ],
            "tips": [
                "优先选择强队主场做胆",
                "避免预测半场逆转",
                "组合使用: 胜胜、平平、负负"
            ]
        }


class FourJQCPredictor:
    """4场进球预测器"""
    
    def __init__(self, data: Dict):
        self.data = data
        self.matches = data.get("matches", [])
        self.goal_stats = self._calculate_goal_stats()
    
    def _calculate_goal_stats(self) -> Dict:
        """计算进球统计"""
        home_goals = []
        away_goals = []
        
        for m in self.matches:
            home = m.get("主队进球")
            away = m.get("客队进球")
            if home is not None:
                home_goals.append(home)
            if away is not None:
                away_goals.append(away)
        
        return {
            "home": Counter(home_goals) if home_goals else Counter({1: 1}),
            "away": Counter(away_goals) if away_goals else Counter({1: 1}),
            "home_avg": statistics.mean(home_goals) if home_goals else 1.4,
            "away_avg": statistics.mean(away_goals) if away_goals else 1.1
        }
    
    def predict_4jqc(
        self,
        matches: List[Dict],
        home_strengths: List[float] = None,
        away_strengths: List[float] = None
    ) -> Dict:
        """
        预测4场进球
        
        Args:
            matches: 4场比赛
            home_strengths: 主队进攻强度调整
            away_strengths: 客队进攻强度调整
        """
        if len(matches) != 4:
            return {"error": "需要4场比赛"}
        
        # 默认强度
        if home_strengths is None:
            home_strengths = [1.0] * 4
        if away_strengths is None:
            away_strengths = [1.0] * 4
        
        predictions = []
        
        for i, (m, hs, as_) in enumerate(zip(matches, home_strengths, away_strengths)):
            expected_home = self.goal_stats["home_avg"] * hs
            expected_away = self.goal_stats["away_avg"] * as_
            
            # 计算各进球数概率
            home_probs = self._calculate_goal_probs(expected_home, is_home=True)
            away_probs = self._calculate_goal_probs(expected_away, is_home=False)
            
            predictions.append({
                "match_index": i + 1,
                "match": f"{m.get('主队', 'T{}'.format(i+1))} vs {m.get('客队', '')}",
                "expected_goals": {
                    "home": round(expected_home, 2),
                    "away": round(expected_away, 2)
                },
                "home_goal_probs": home_probs,
                "away_goal_probs": away_probs,
                "recommended": {
                    "home": self._get_recommended_goal(home_probs),
                    "away": self._get_recommended_goal(away_probs)
                }
            })
        
        # 整体分析
        all_correct_prob = 1.0
        for p in predictions:
            all_correct_prob *= p["recommended"]["probability"] / 100
        
        return {
            "predictions": predictions,
            "overall_difficulty": {
                "probability": round(all_correct_prob * 100, 6),
                "rating": "极高" if all_correct_prob < 0.001 else "很高",
                "note": "4场进球需猜中8个进球数，难度极大"
            },
            "recommended_strategy": self._generate_jqc_strategy(predictions)
        }
    
    def _calculate_goal_probs(self, expected: float, is_home: bool) -> Dict:
        """计算进球数概率"""
        probs = {}
        
        if not SCIPY_AVAILABLE:
            for goals in range(8):
                p = (expected ** goals * math.exp(-expected)) / math.factorial(goals)
                probs[str(goals)] = round(p * 100, 1)
        else:
            for goals in range(8):
                probs[str(goals)] = round(poisson.pmf(goals, expected) * 100, 1)
        
        return probs
    
    def _get_recommended_goal(self, probs: Dict) -> Dict:
        """获取推荐进球数"""
        sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)
        top = sorted_probs[0]
        return {
            "goal": top[0],
            "probability": top[1]
        }
    
    def _generate_jqc_strategy(self, predictions: List[Dict]) -> Dict:
        """生成进球彩策略"""
        # 按难度排序
        sorted_preds = sorted(
            predictions,
            key=lambda x: x["recommended"]["probability"],
            reverse=True
        )
        
        return {
            "most_confident": sorted_preds[:2],
            "least_confident": sorted_preds[-2:],
            "recommended_bets": self._generate_multi_bets(sorted_preds),
            "tips": [
                "主场球队优先选1-2球",
                "客场球队优先选0-1球",
                "高比分联赛可考虑3-4球",
                "7+球极小概率，建议不选"
            ]
        }
    
    def _generate_multi_bets(self, predictions: List[Dict]) -> List[Dict]:
        """生成复式投注建议"""
        bets = []
        
        for p in predictions:
            prob = p["recommended"]["probability"]
            
            if prob >= 30:
                # 高概率：单选
                bets.append({
                    "match": p["match"],
                    "recommendation": p["recommended"]["goal"],
                    "type": "单选",
                    "confidence": "高"
                })
            elif prob >= 20:
                # 中等概率：双选
                second_prob = sorted(
                    p["home_goal_probs"].items() if "home_goal_probs" in p else p["away_goal_probs"].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[1]
                bets.append({
                    "match": p["match"],
                    "recommendation": [p["recommended"]["goal"], second_prob[0]],
                    "type": "双选",
                    "confidence": "中"
                })
            else:
                # 低概率：三选
                top3 = [x[0] for x in sorted(
                    p["home_goal_probs"].items() if "home_goal_probs" in p else p["away_goal_probs"].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:3]]
                bets.append({
                    "match": p["match"],
                    "recommendation": top3,
                    "type": "三选",
                    "confidence": "低"
                })
        
        return bets


class PrizePoolAnalyzer:
    """奖池分析器"""
    
    def __init__(self):
        self.pool_rate = 0.64  # 64%返奖率
        self.max_prize = 5000000  # 500万封顶
    
    def estimate_prize(
        self,
        total_sales: float,
        winner_count: int = 1,
        pool_balance: float = 0
    ) -> Dict:
        """
        估算奖金
        
        Args:
            total_sales: 当期销售额
            winner_count: 中奖注数
            pool_balance: 奖池余额
        """
        # 可分配奖金
        distributable = total_sales * self.pool_rate + pool_balance
        
        # 每注奖金
        per_bet_prize = distributable / winner_count if winner_count > 0 else 0
        
        # 封顶处理
        actual_prize = min(per_bet_prize, self.max_prize)
        
        return {
            "total_sales": total_sales,
            "distributable_prize": round(distributable, 2),
            "estimated_winners": winner_count,
            "per_bet_prize_before_cap": round(per_bet_prize, 2),
            "per_bet_prize_after_cap": round(actual_prize, 2),
            "cap_applied": actual_prize < per_bet_prize,
            "pool_balance": pool_balance
        }
    
    def analyze_rollover(self, last_period_prize: float, last_period_winners: int) -> Dict:
        """
        分析滚存
        
        Args:
            last_period_prize: 上期一等奖金额
            last_period_winners: 上期一等奖中奖注数
        """
        rollover_amount = last_period_prize * last_period_winners
        
        return {
            "last_period_first_prize": last_period_prize,
            "last_period_winners": last_period_winners,
            "rollover_amount": rollover_amount,
            "rollover_risk": "高" if rollover_amount > 10000000 else "中" if rollover_amount > 5000000 else "低",
            "recommendation": "一等奖滚存期间可适当增加投入"
        }


def main():
    """测试所有分析器"""
    data = load_data()
    
    print("=" * 60)
    print("传统足彩专业分析模块 v2.0")
    print("=" * 60)
    
    # 14场分析
    print("\n【14场深度分析】")
    analyzer14 = Traditional14Analyzer(data)
    print(f"联赛数量: {len(analyzer14.league_stats)}")
    
    # 任选9优化
    print("\n【任选9优化】")
    rx9 = RX9Optimizer(data)
    test_matches = [{"主队": f"H{i}", "客队": f"A{i}"} for i in range(14)]
    test_confidence = [0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 0.55, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
    rx9_result = rx9.optimize_rx9(test_matches, 500, test_confidence)
    print(f"推荐胆数: {rx9_result['dan_tuo_plan']['dan_count']}")
    print(f"推荐拖数: {rx9_result['dan_tuo_plan']['tuo_count']}")
    print(f"预计成本: {rx9_result['cost_analysis']['total_cost']}元")
    
    # 6场半全场
    print("\n【6场半全场预测】")
    bqc = SixBQCPredictor(data)
    test_6matches = [{"主队": f"H{i}", "客队": f"A{i}"} for i in range(6)]
    bqc_result = bqc.predict_6bqc(test_6matches)
    print(f"整体难度: {bqc_result['overall_difficulty']['rating']}")
    
    # 4场进球
    print("\n【4场进球预测】")
    jqc = FourJQCPredictor(data)
    test_4matches = [{"主队": f"H{i}", "客队": f"A{i}"} for i in range(4)]
    jqc_result = jqc.predict_4jqc(test_4matches)
    print(f"整体难度: {jqc_result['overall_difficulty']['rating']}")
    
    # 奖池分析
    print("\n【奖池分析】")
    pool = PrizePoolAnalyzer()
    prize = pool.estimate_prize(100000000, 1, 50000000)
    print(f"预计一等奖: {prize['per_bet_prize_after_cap']}元")


if __name__ == "__main__":
    main()
