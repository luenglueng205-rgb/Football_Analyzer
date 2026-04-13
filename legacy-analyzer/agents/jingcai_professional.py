# -*- coding: utf-8 -*-
"""
竞彩足球专业分析模块 v3.0
功能：
1. 泊松进球预测模型（基于221,415条历史数据校准）
2. 盘口深度分析（让球胜平负/亚盘）
3. 比分矩阵预测
4. 半全场概率预测
5. 混合过关优化

v3.0 升级：集成历史数据库，利用完整历史数据进行分析
"""

import json
import os
import sys
import math
from typing import Dict, List, Optional, Tuple
from collections import Counter, defaultdict
import statistics

try:
    from scipy.stats import poisson, norm
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("Warning: scipy not available, using simplified Poisson model")

# 路径设置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BASE_DIR = os.path.dirname(PROJECT_ROOT)
DATA_DIR = os.path.join(BASE_DIR, 'data', 'chinese_mapped')
RULES_DIR = PROJECT_ROOT

# 尝试导入历史数据库
try:
    sys.path.insert(0, os.path.join(PROJECT_ROOT, 'data'))
    from historical_database import get_historical_database
    HISTORICAL_DB_AVAILABLE = True
except ImportError:
    HISTORICAL_DB_AVAILABLE = False
    get_historical_database = None


def load_data() -> Dict:
    """加载竞彩足球数据"""
    filepath = os.path.join(DATA_DIR, '竞彩足球_chinese_data.json')
    if not os.path.exists(filepath):
        return {"matches": [], "leagues": {}}
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_rules() -> Dict:
    """加载官方规则"""
    with open(os.path.join(RULES_DIR, 'official_rules.json'), 'r', encoding='utf-8') as f:
        return json.load(f)


class PoissonGoalPredictor:
    """
    泊松进球预测模型 v3.0
    
    v3.0 升级:
    - 优先使用历史数据库 (221,415条数据) 校准联赛参数
    - 备用本地竞彩数据进行补充
    - 支持球队实力评估
    """
    
    def __init__(self, data: Dict, use_historical: bool = True):
        self.data = data
        self.matches = data.get("matches", [])
        self.league_avg_goals = {}
        self.home_advantage = {}
        self.historical_db = None
        
        # 尝试加载历史数据库
        if use_historical and HISTORICAL_DB_AVAILABLE and get_historical_database:
            try:
                self.historical_db = get_historical_database(lazy_load=True)
                print(f"✅ 泊松预测器已连接历史数据库 (221,415条数据)")
            except Exception as e:
                print(f"⚠️ 历史数据库加载失败: {e}, 使用本地数据")
        
        self._calculate_parameters()
    
    def _calculate_parameters(self):
        """计算各联赛参数 - 优先使用历史数据"""
        
        # 第一优先级：从历史数据库获取
        if self.historical_db:
            try:
                raw_stats = self.historical_db._league_stats
                if raw_stats:
                    for league, stats in raw_stats.items():
                        self.league_avg_goals[league] = {
                            "home": stats.get("avg_home_goals", 1.5),
                            "away": stats.get("avg_away_goals", 1.2),
                            "total": stats.get("avg_total_goals", 2.7)
                        }
                        home_rate = stats.get("home_win_rate", 0.44)
                        away_rate = stats.get("away_win_rate", 0.30)
                        self.home_advantage[league] = home_rate / away_rate if away_rate > 0 else 1.2
                    print(f"✅ 已从历史数据库加载 {len(self.league_avg_goals)} 个联赛参数")
                    return
            except Exception as e:
                print(f"⚠️ 历史数据库读取失败: {e}")
        
        # 第二优先级：使用本地竞彩数据
        league_stats = defaultdict(lambda: {"home_goals": [], "away_goals": [], "total_goals": []})
        
        for m in self.matches:
            home = m.get("主队进球")
            away = m.get("客队进球")
            league = m.get("联赛代码", "unknown")
            
            if home is not None and away is not None:
                league_stats[league]["home_goals"].append(home)
                league_stats[league]["away_goals"].append(away)
                league_stats[league]["total_goals"].append(home + away)
        
        for league, stats in league_stats.items():
            if len(stats["total_goals"]) >= 50:
                self.league_avg_goals[league] = {
                    "home": statistics.mean(stats["home_goals"]) if stats["home_goals"] else 1.5,
                    "away": statistics.mean(stats["away_goals"]) if stats["away_goals"] else 1.2,
                    "total": statistics.mean(stats["total_goals"]) if stats["total_goals"] else 2.7
                }
                # 计算主场优势
                self.home_advantage[league] = (
                    statistics.mean(stats["home_goals"]) / statistics.mean(stats["away_goals"])
                    if stats["away_goals"] and statistics.mean(stats["away_goals"]) > 0 else 1.2
                )
        
        print(f"✅ 已从本地数据加载 {len(self.league_avg_goals)} 个联赛参数")
    
    def predict_single_match(
        self,
        home_team: str,
        away_team: str,
        league: str = "unknown",
        home_strength: float = 1.0,
        away_strength: float = 1.0
    ) -> Dict:
        """
        预测单场比赛进球
        
        Args:
            home_team: 主队名称
            away_team: 客队名称
            league: 联赛代码
            home_strength: 主队实力调整 (0.5-1.5)
            away_strength: 客队实力调整 (0.5-1.5)
        """
        # 获取联赛平均参数
        league_params = self.league_avg_goals.get(league, {
            "home": 1.5, "away": 1.2, "total": 2.7
        })
        
        # 调整后的预期进球
        expected_home_goals = league_params["home"] * home_strength
        expected_away_goals = league_params["away"] * away_strength
        
        # 泊松分布计算
        total_goals_probs = self._calculate_total_goals_poisson(
            expected_home_goals, expected_away_goals
        )
        
        score_probs = self._calculate_score_matrix(
            expected_home_goals, expected_away_goals, max_goals=5
        )
        
        return {
            "match": f"{home_team} vs {away_team}",
            "league": league,
            "expected_goals": {
                "home": round(expected_home_goals, 2),
                "away": round(expected_away_goals, 2),
                "total": round(expected_home_goals + expected_away_goals, 2)
            },
            "total_goals_distribution": total_goals_probs,
            "score_matrix": score_probs,
            "most_likely_scores": self._get_top_scores(score_probs, top_n=5),
            "recommended_bets": self._generate_bet_recommendations(
                total_goals_probs, score_probs
            )
        }
    
    def _calculate_total_goals_poisson(
        self,
        expected_home: float,
        expected_away: float,
        max_goals: int = 7
    ) -> Dict:
        """计算总进球数的泊松概率"""
        if not SCIPY_AVAILABLE:
            # 简化版泊松计算
            expected_total = expected_home + expected_away
            probs = {}
            for goals in range(max_goals + 1):
                probs[str(goals)] = round(
                    (expected_total ** goals * math.exp(-expected_total)) / math.factorial(goals) * 100, 2
                )
            # 7+球
            probs["7+"] = round(100 - sum(float(v) for v in probs.values()), 2)
            return probs
        
        # scipy版本
        expected_total = expected_home + expected_away
        probs = {}
        for goals in range(max_goals + 1):
            probs[str(goals)] = round(poisson.pmf(goals, expected_total) * 100, 2)
        
        # 7+球
        probs["7+"] = round((1 - poisson.cdf(max_goals - 1, expected_total)) * 100, 2)
        return probs
    
    def _calculate_score_matrix(
        self,
        expected_home: float,
        expected_away: float,
        max_goals: int = 5
    ) -> Dict:
        """计算比分概率矩阵"""
        if not SCIPY_AVAILABLE:
            # 简化版
            scores = {}
            for h in range(max_goals + 1):
                for a in range(max_goals + 1):
                    p_home = (expected_home ** h * math.exp(-expected_home)) / math.factorial(h)
                    p_away = (expected_away ** a * math.exp(-expected_away)) / math.factorial(a)
                    scores[f"{h}:{a}"] = round(p_home * p_away * 100, 2)
            return scores
        
        # scipy版本
        scores = {}
        for h in range(max_goals + 1):
            for a in range(max_goals + 1):
                p = poisson.pmf(h, expected_home) * poisson.pmf(a, expected_away)
                scores[f"{h}:{a}"] = round(p * 100, 2)
        return scores
    
    def _get_top_scores(self, score_probs: Dict, top_n: int = 5) -> List[Dict]:
        """获取概率最高的比分"""
        sorted_scores = sorted(
            score_probs.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]
        
        return [
            {"score": score, "probability": prob, "odds_recommendation": self._score_to_odds(score)}
            for score, prob in sorted_scores
        ]
    
    def _score_to_odds(self, score: str) -> str:
        """比分转赔率建议"""
        # 基于历史平均赔率
        score_odds_map = {
            "1:0": "7.0", "2:0": "10.0", "2:1": "9.0",
            "1:1": "6.0", "0:0": "5.0",
            "0:1": "8.0", "0:2": "12.0", "1:2": "10.0",
            "3:0": "18.0", "3:1": "15.0", "1:3": "20.0"
        }
        return score_odds_map.get(score, "根据实际赔率")
    
    def _generate_bet_recommendations(
        self,
        total_goals: Dict,
        score_probs: Dict
    ) -> Dict:
        """生成投注建议"""
        # 总进球推荐
        top_total = max(total_goals.items(), key=lambda x: float(x[1]))
        
        # 比分推荐
        top_scores = self._get_top_scores(score_probs, top_n=3)
        
        return {
            "total_goals": {
                "recommended": top_total[0],
                "probability": top_total[1],
                "confidence": "高" if float(top_total[1]) > 20 else "中"
            },
            "score_predictions": top_scores,
            "strategy": "泊松模型仅供参考，需结合球队状态、阵容等因素"
        }


class HandicapAnalyzer:
    """盘口深度分析器（让球胜平负/亚盘）"""
    
    def __init__(self, data: Dict):
        self.data = data
        self.matches = data.get("matches", [])
    
    def analyze_concession(
        self,
        home_team: str,
        away_team: str,
        concession: int,
        home_odds: float,
        draw_odds: float,
        away_odds: float
    ) -> Dict:
        """
        分析让球盘口
        
        Args:
            home_team: 主队
            away_team: 客队
            concession: 让球数（正数为主队让球，负数为客队让球）
            home_odds/draw_odds/away_odds: 让球后的赔率
        """
        # 理论概率计算
        total_margin = 1.0 / home_odds + 1.0 / draw_odds + 1.0 / away_odds
        fair_home_prob = (1.0 / home_odds) / total_margin * 100
        fair_draw_prob = (1.0 / draw_odds) / total_margin * 100
        fair_away_prob = (1.0 / away_odds) / total_margin * 100
        
        # 盘口分析
        analysis = {
            "concession": f"{'+' if concession > 0 else ''}{concession}",
            "market_margins": {
                "home": round(fair_home_prob, 1),
                "draw": round(fair_draw_prob, 1),
                "away": round(fair_away_prob, 1)
            },
            "odds": {
                "home": home_odds,
                "draw": draw_odds,
                "away": away_odds
            }
        }
        
        # 让球影响分析
        if concession > 0:
            # 主队让球
            analysis["concession_impact"] = {
                "direction": "主队让球",
                "adjustment": f"主队需要赢{concession + 1}球才能赢盘",
                "fair_probability": {
                    "home_win_conceded": self._estimate_conceded_prob(
                        fair_home_prob, concession
                    ),
                    "draw_conceded": self._estimate_conceded_draw(
                        fair_home_prob, fair_draw_prob, concession
                    ),
                    "away_cover": round(100 - analysis["market_margins"]["home"], 1)
                },
                "recommendation": self._generate_concession_recommendation(
                    concession, home_odds, away_odds
                )
            }
        else:
            # 客队让球（等于主队受让）
            abs_concession = abs(concession)
            analysis["concession_impact"] = {
                "direction": "客队让球(主队受让)",
                "adjustment": f"客队需要赢{abs_concession + 1}球才能赢盘",
                "recommendation": self._generate_underdog_recommendation(
                    abs_concession, home_odds, away_odds
                )
            }
        
        return analysis
    
    def _estimate_conceded_prob(self, original_prob: float, concession: int) -> Dict:
        """估算让球后的概率变化"""
        # 每让1球，主队赢的概率下降约15-20%
        reduction = min(concession * 0.15, 0.4)
        return {
            "original": round(original_prob, 1),
            "adjusted": round(original_prob * (1 - reduction), 1),
            "note": f"让{concession}球后主胜概率下降约{reduction*100:.0f}%"
        }
    
    def _estimate_conceded_draw(self, home: float, draw: float, concession: int) -> Dict:
        """估算让球后的平局概率"""
        # 让球后平局概率通常上升
        increase = concession * 0.05
        return {
            "original": round(draw, 1),
            "adjusted": round(min(draw + increase, 40), 1),
            "note": "让球后平局概率通常上升"
        }
    
    def _generate_concession_recommendation(
        self,
        concession: int,
        home_odds: float,
        away_odds: float
    ) -> Dict:
        """生成让球投注建议"""
        recommendations = []
        
        if concession == 1:
            if home_odds < 1.5:
                recommendations.append({
                    "bet": "让球主胜",
                    "odds": home_odds,
                    "reason": "强队让1球赔率仍偏低，有价值",
                    "risk": "低"
                })
            elif home_odds > 2.0:
                recommendations.append({
                    "bet": "让球平",
                    "odds": home_odds,
                    "reason": "让1球后平局概率增加",
                    "risk": "中"
                })
        elif concession >= 2:
            recommendations.append({
                "bet": "让球平/让球主负",
                "strategy": "双选容错",
                "reason": f"让{concession}球风险较大，建议容错",
                "risk": "中"
            })
        
        return {"options": recommendations}
    
    def _generate_underdog_recommendation(
        self,
        concession: int,
        home_odds: float,
        away_odds: float
    ) -> Dict:
        """生成受让投注建议"""
        return {
            "options": [
                {
                    "bet": "主队受让胜",
                    "odds": home_odds,
                    "reason": "弱队获得让球优势",
                    "suitable": "主队防守反击型"
                }
            ]
        }
    
    def analyze_water_changes(self, historical_odds: List[float]) -> Dict:
        """
        分析水位变化（亚盘）
        """
        if len(historical_odds) < 2:
            return {"error": "数据不足"}
        
        changes = []
        for i in range(1, len(historical_odds)):
            change = historical_odds[i] - historical_odds[i-1]
            changes.append({
                "from": historical_odds[i-1],
                "to": historical_odds[i],
                "change": round(change, 2),
                "direction": "升" if change > 0 else "降"
            })
        
        # 分析趋势
        avg_change = statistics.mean([c["change"] for c in changes])
        
        return {
            "total_changes": len(changes),
            "average_change": round(avg_change, 3),
            "trend": "升水" if avg_change > 0.02 else "降水" if avg_change < -0.02 else "平稳",
            "interpretation": self._interpret_water_trend(avg_change)
        }
    
    def _interpret_water_trend(self, avg_change: float) -> str:
        """解读水位趋势"""
        if avg_change > 0.05:
            return "明显升水，大资金流向主队，需谨慎"
        elif avg_change > 0.02:
            return "轻微升水，主队热度增加"
        elif avg_change < -0.05:
            return "明显降水，大资金看低主队"
        elif avg_change < -0.02:
            return "轻微降水，主队热度降低"
        else:
            return "水位稳定，市场无明显倾向"


class ParlayOptimizer:
    """竞彩足球串关优化器 (已接入 LotteryMathEngine)"""
    
    def __init__(self, data: Dict):
        self.data = data
        self.matches = data.get("matches", [])
        
        # 尝试引入重构后的 LotteryMathEngine
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

    def _get_prize_estimation(self, matches: List[Dict], m: int, n: int) -> Dict:
        """调用引擎获取极值奖金和真实成本"""
        if not self.math_engine:
            return {}
        
        # 将传入的简单格式适配引擎需要的格式
        formatted_matches = []
        for match in matches:
            odds_val = match.get("odds", 2.0)
            if not isinstance(odds_val, list):
                odds_val = [odds_val]
            formatted_matches.append({
                "odds": odds_val,
                "play_type": match.get("play_type", "SPF")
            })
            
        return self.math_engine.calculate_jingcai_mxn(formatted_matches, m, n)
    
    def optimize_mxn(
        self,
        selected_matches: List[Dict],
        budget: float,
        risk_level: str = "medium"
    ) -> Dict:
        """
        优化M串N过关方案
        
        Args:
            selected_matches: 选定的比赛 [{match, odds, confidence, play_type}]
            budget: 预算金额
            risk_level: low/medium/high
        """
        n = len(selected_matches)
        if n < 2:
            return {"error": "串关至少需要2场"}
        
        # 检查是否包含特殊玩法导致木桶效应
        max_allowed = 8
        for m in selected_matches:
            pt = m.get("play_type", "SPF")
            if pt in ["BF", "BQC"]:
                max_allowed = min(max_allowed, 4)
            elif pt == "ZJQ":
                max_allowed = min(max_allowed, 6)
                
        if n > max_allowed:
            return {"error": f"混合过关限制：包含 {pt} 玩法，最高只能串 {max_allowed} 关"}
        
        # 根据风险等级选择方案
        strategies = {
            "low": self._low_risk_strategy,
            "medium": self._medium_risk_strategy,
            "high": self._high_risk_strategy
        }
        
        strategy_func = strategies.get(risk_level, self._medium_risk_strategy)
        return strategy_func(selected_matches, budget, n)
    
    def _build_option(self, matches, m: int, n_type: int, desc: str, risk: str, budget: float):
        """构建单个推荐选项，集成底层数学引擎"""
        est = self._get_prize_estimation(matches, m, n_type)
        
        # 如果引擎返回了 error，直接抛弃此方案
        if est.get("error"):
            return None
            
        bets = est.get("total_bets", 1)
        cost = est.get("total_cost", bets * 2)
        
        # 计算可以买多少倍
        multiple = max(1, int(budget // cost)) if cost > 0 else 1
        actual_cost = cost * multiple
        
        return {
            "type": f"{m}串{n_type}",
            "description": desc,
            "bets": bets,
            "multiple": multiple,
            "estimated_cost": actual_cost,
            "min_prize": round(est.get("min_prize", 0) * multiple, 2),
            "max_prize": round(est.get("max_prize", 0) * multiple, 2),
            "min_correct": min(self.math_engine.get_mxn_combinations(m, n_type)) if self.math_engine else m,
            "risk": risk
        }

    def _low_risk_strategy(self, matches: List[Dict], budget: float, n: int) -> Dict:
        """低风险策略：2串1容错"""
        options = []
        
        # 2串1 (从n场中挑2场) - 逻辑：在真实世界中，如果是n场比赛买2串1，即n串(n*(n-1)/2)
        # 但我们这里的m指的是场数，n_type是组合数。所以实际上是 n串(nC2) 这种非标准说法。
        # 官方标准的M串N是：例如 3串3(1个3串1), 3串4(3个2串1, 1个3串1)。
        
        # 假设用户选了n场，我们要推荐 n 场内的低风险 M串N
        
        # 方案1: n串(n_combo) 选低关数
        if n == 2:
            opt = self._build_option(matches, 2, 1, "2串1最低风险", "低", budget)
            if opt: options.append(opt)
        elif n == 3:
            opt = self._build_option(matches, 3, 3, "3串3容错(3个2串1)", "低", budget)
            if opt: options.append(opt)
            opt2 = self._build_option(matches, 3, 4, "3串4容错1场", "低-中", budget)
            if opt2: options.append(opt2)
        elif n >= 4:
            opt = self._build_option(matches, n, 6 if n==4 else 10 if n==5 else 15, f"{n}场挑2关容错", "低", budget)
            if opt: options.append(opt)
            
        return {
            "strategy": "低风险",
            "recommended": options[0] if options else None,
            "alternatives": options[1:],
            "tips": ["选择低赔稳胆组合", "避免串入高赔选项"]
        }
    
    def _medium_risk_strategy(self, matches: List[Dict], budget: float, n: int) -> Dict:
        """中等风险策略"""
        options = []
        if n == 3:
            opt = self._build_option(matches, 3, 1, "3串1全对", "中", budget)
            if opt: options.append(opt)
        elif n == 4:
            opt = self._build_option(matches, 4, 5, "4串5容错1场", "中", budget)
            if opt: options.append(opt)
            opt2 = self._build_option(matches, 4, 11, "4串11容错2场", "中-低", budget)
            if opt2: options.append(opt2)
        elif n == 5:
            opt = self._build_option(matches, 5, 16, "5串16容错2场", "中", budget)
            if opt: options.append(opt)
        elif n >= 6:
            opt = self._build_option(matches, n, 1, f"{n}串1全对", "中-高", budget)
            if opt: options.append(opt)
            
        return {
            "strategy": "中等风险",
            "recommended": options[0] if options else None,
            "alternatives": options[1:],
            "tips": ["选择赔率1.5-2.5的组合", "控制串关数在3-5关"]
        }
    
    def _high_risk_strategy(self, matches: List[Dict], budget: float, n: int) -> Dict:
        """高风险高回报策略"""
        options = []
        if n >= 4:
            opt = self._build_option(matches, n, 1, f"{n}串1博冷", "高", budget)
            if opt: options.append(opt)
        if n == 6:
            opt = self._build_option(matches, 6, 57, "6串57全包容错", "高", budget)
            if opt: options.append(opt)
            
        return {
            "strategy": "高风险",
            "recommended": options[0] if options else None,
            "alternatives": options[1:],
            "tips": ["适合以小博大", "必须包含至少一场高赔冷门"]
        }
    
    def optimize_mixed_bet(
        self,
        matches: List[Dict],
        play_types: List[str],
        budget: float
    ) -> Dict:
        """
        优化混合过关
        竞彩支持不同玩法混合串关
        """
        return {
            "play_types": play_types,
            "total_matches": len(matches),
            "allowed_combinations": [
                "胜平负 + 让球胜平负",
                "胜平负 + 总进球",
                "胜平负 + 比分",
                "胜平负 + 半全场",
                "总进球 + 比分",
                "比分 + 半全场",
                "多玩法混合"
            ],
            "tips": [
                "混合过关奖金更高",
                "建议玩法不超过3种",
                "优先组合互补性强的玩法"
            ]
        }


class HalfFullTimePredictor:
    """半全场预测模型"""
    
    def __init__(self, data: Dict):
        self.data = data
        self.matches = data.get("matches", [])
    
    def predict_half_full(
        self,
        home_team: str,
        away_team: str,
        expected_home_goals: float,
        expected_away_goals: float
    ) -> Dict:
        """
        预测半全场结果
        """
        # 估算半场进球（通常是全场的40-50%）
        half_home_factor = 0.45
        half_away_factor = 0.40
        
        half_home_goals = expected_home_goals * half_home_factor
        half_away_goals = expected_away_goals * half_away_factor
        
        # 半场结果概率
        half_options = [
            ("3", "主队半场领先"),
            ("1", "半场平局"),
            ("0", "客队半场领先")
        ]
        
        half_probs = {}
        if not SCIPY_AVAILABLE:
            for opt, name in half_options:
                if opt == "3":
                    prob = max(half_home_goals - half_away_goals, 0.1) * 30
                elif opt == "1":
                    prob = 1 - abs(half_home_goals - half_away_goals) * 20
                else:
                    prob = max(half_away_goals - half_home_goals, 0.1) * 30
                half_probs[opt] = round(min(max(prob, 10), 50), 1)
        else:
            # 更精确的泊松模型
            for h in range(4):
                for a in range(4):
                    half_prob = poisson.pmf(h, half_home_goals) * poisson.pmf(a, half_away_goals)
                    if h > a:
                        half_probs["3"] = half_probs.get("3", 0) + half_prob
                    elif h == a:
                        half_probs["1"] = half_probs.get("1", 0) + half_prob
                    else:
                        half_probs["0"] = half_probs.get("0", 0) + half_prob
            half_probs = {k: round(v * 100, 1) for k, v in half_probs.items()}
        
        # 全场结果（基于总进球预测）
        full_probs = self._predict_full_time_result(expected_home_goals, expected_away_goals)
        
        # 半全场组合
        bqc_probs = self._calculate_bqc_combinations(half_probs, full_probs)
        
        return {
            "match": f"{home_team} vs {away_team}",
            "half_time": {
                "expected_home_goals": round(half_home_goals, 2),
                "expected_away_goals": round(half_away_goals, 2),
                "probabilities": half_probs
            },
            "full_time": {
                "expected_goals": {
                    "home": expected_home_goals,
                    "away": expected_away_goals
                },
                "probabilities": full_probs
            },
            "bqc_probabilities": dict(sorted(
                bqc_probs.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]),
            "recommendations": self._generate_bqc_recommendations(bqc_probs)
        }
    
    def _predict_full_time_result(
        self,
        expected_home: float,
        expected_away: float
    ) -> Dict:
        """预测全场结果"""
        if not SCIPY_AVAILABLE:
            # 简化估算
            home_win_prob = max(expected_home - expected_away + 0.3, 0.1) * 35
            away_win_prob = max(expected_away - expected_home + 0.3, 0.1) * 35
            draw_prob = 100 - home_win_prob - away_win_prob
            
            return {
                "3": round(min(max(home_win_prob, 10), 60), 1),
                "1": round(min(max(draw_prob, 15), 45), 1),
                "0": round(min(max(away_win_prob, 10), 60), 1)
            }
        
        # 泊松模型
        results = {"3": 0, "1": 0, "0": 0}
        for h in range(6):
            for a in range(6):
                prob = poisson.pmf(h, expected_home) * poisson.pmf(a, expected_away)
                if h > a:
                    results["3"] += prob
                elif h == a:
                    results["1"] += prob
                else:
                    results["0"] += prob
        
        return {k: round(v * 100, 1) for k, v in results.items()}
    
    def _calculate_bqc_combinations(
        self,
        half_probs: Dict,
        full_probs: Dict
    ) -> Dict:
        """计算半全场组合概率"""
        bqc_options = {
            "3-3": ("3", "3"), "3-1": ("3", "1"), "3-0": ("3", "0"),
            "1-3": ("1", "3"), "1-1": ("1", "1"), "1-0": ("1", "0"),
            "0-3": ("0", "3"), "0-1": ("0", "1"), "0-0": ("0", "0")
        }
        
        bqc_probs = {}
        for bqc, (half, full) in bqc_options.items():
            half_prob = half_probs.get(half, 0)
            full_prob = full_probs.get(full, 0)
            # 假设半全场独立
            bqc_probs[bqc] = round(half_prob * full_prob / 100, 2)
        
        # 归一化
        total = sum(bqc_probs.values())
        if total > 0:
            bqc_probs = {k: round(v / total * 100, 1) for k, v in bqc_probs.items()}
        
        return bqc_probs
    
    def _generate_bqc_recommendations(self, bqc_probs: Dict) -> List[Dict]:
        """生成半全场投注建议"""
        recommendations = []
        
        for bqc, prob in list(bqc_probs.items())[:3]:
            name_map = {
                "3-3": "胜胜", "3-1": "胜平", "3-0": "胜负",
                "1-3": "平胜", "1-1": "平平", "1-0": "平负",
                "0-3": "负胜", "0-1": "负平", "0-0": "负负"
            }
            
            recommendations.append({
                "bqc": bqc,
                "name": name_map.get(bqc, bqc),
                "probability": prob,
                "suitable": self._get_bqc_suitable_scenario(bqc)
            })
        
        return recommendations
    
    def _get_bqc_suitable_scenario(self, bqc: str) -> str:
        """半全场适用场景"""
        scenarios = {
            "3-3": "强队主场，预计大胜",
            "3-1": "强队主场，可能小胜或被逼平",
            "3-0": "强队主场，大胜后被逆转",
            "1-3": "弱队逆转强队",
            "1-1": "势均力敌，双方保守",
            "1-0": "弱队先进球被逆转",
            "0-3": "客队大胜",
            "0-1": "客队小胜",
            "0-0": "闷平，防守大战"
        }
        return scenarios.get(bqc, "")


def main():
    """测试所有分析器"""
    data = load_data()
    
    print("=" * 60)
    print("竞彩足球专业分析模块 v2.0")
    print("=" * 60)
    
    # 泊松进球预测
    print("\n【泊松进球预测】")
    predictor = PoissonGoalPredictor(data)
    if data["matches"]:
        sample = data["matches"][0]
        result = predictor.predict_single_match(
            sample.get("主队", "主队"),
            sample.get("客队", "客队"),
            sample.get("联赛代码", "unknown"),
            home_strength=1.0,
            away_strength=1.0
        )
        print(f"预期进球: {result['expected_goals']}")
        print(f"最可能比分: {result['most_likely_scores'][:2]}")
    
    # 盘口分析
    print("\n【盘口深度分析】")
    handicap = HandicapAnalyzer(data)
    analysis = handicap.analyze_concession(
        "主队", "客队", 1, 1.8, 3.5, 4.0
    )
    print(f"让球: {analysis['concession']}")
    print(f"市场概率: {analysis['market_margins']}")
    
    # 串关优化
    print("\n【串关优化】")
    parlay = ParlayOptimizer(data)
    test_matches = [
        {"match": "A vs B", "odds": 1.8, "confidence": 0.8},
        {"match": "C vs D", "odds": 2.0, "confidence": 0.75},
        {"match": "E vs F", "odds": 1.6, "confidence": 0.85}
    ]
    result = parlay.optimize_mxn(test_matches, 100, "medium")
    print(f"推荐方案: {result.get('recommended', {})}")
    
    # 半全场预测
    print("\n【半全场预测】")
    bqc = HalfFullTimePredictor(data)
    bqc_result = bqc.predict_half_full("主队", "客队", 1.8, 1.2)
    print(f"半场预期: {bqc_result['half_time']['expected_home_goals']}-{bqc_result['half_time']['expected_away_goals']}")
    print(f"推荐: {bqc_result['recommendations'][:2]}")


if __name__ == "__main__":
    main()
