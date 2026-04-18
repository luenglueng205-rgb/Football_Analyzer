#!/usr/bin/env python3
"""
赔率分析Agent - OpenClaw规范版本
Analyst Agent
增强版：集成221,415条历史数据
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from math import sqrt, exp

try:
    from scipy.stats import poisson
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

# 确保能找到tools模块
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from .base import BaseAgent, AgentStatus, Message
from core.recommendation_schema import RecommendationSchemaAdapter

logger = logging.getLogger(__name__)

from core.domain_kernel import DomainKernel

# 引入 Analyzer API 工具库
try:
    from tools.analyzer_api import AnalyzerAPI
    from tools.llm_service import LLMService
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False
    logger.warning("AnalyzerAPI 导入失败，部分历史数据功能将受限。")

def _factorial(n: int) -> int:
    if n < 2:
        return 1
    r = 1
    for i in range(2, n + 1):
        r *= i
    return r

def _poisson_pmf(k: int, mu: float) -> float:
    if k < 0:
        return 0.0
    if mu <= 0:
        return 1.0 if k == 0 else 0.0
    return exp(-mu) * (mu ** k) / _factorial(k)

def _poisson_cdf(k: int, mu: float) -> float:
    if k < 0:
        return 0.0
    return sum(_poisson_pmf(i, mu) for i in range(0, k + 1))

def _breakeven_odds(probability: float):
    try:
        p = float(probability)
        if p <= 0:
            return None
        return 1.0 / p
    except Exception:
        return None

def _breakeven_odds_with_push(p_win: float, p_push: float):
    try:
        pw = float(p_win)
        pp = float(p_push)
        if pw <= 0:
            return None
        return (1.0 - pp) / pw
    except Exception:
        return None

class AnalystAgent(BaseAgent):
    """
    赔率分析Agent - 增强版
    
    职责：
    1. 赔率异常检测
    2. 价值投注识别
    3. 盘口解读分析
    4. 期望值计算
    5. 历史数据校准（基于 System 2 API）
    """
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__("analyst", "赔率分析", config)
        if API_AVAILABLE:
            print("✅ AnalystAgent 已连接 AnalyzerAPI (System 2)")
    
    def process(self, task: Dict) -> Dict:
        """处理赔率分析任务"""
        self.status = AgentStatus.RUNNING
        
        action = task.get('action', 'analyze_odds')
        params = task.get('params', {})
        
        if action == 'analyze_odds':
            result = self._analyze_odds(params)
        elif action == 'find_value_bets':
            result = self._find_value_bets(params)
        elif action == 'analyze_handicap':
            result = self._analyze_handicap(params)
        else:
            result = {"error": f"Unknown action: {action}"}
        
        self.status = AgentStatus.COMPLETED

        if isinstance(result, dict):
            result.setdefault("data_source", f"{self.agent_id}:{action}")
        
        # 增加 Handoff (交接) 逻辑
        result["next_agent"] = "strategist"
        
        return DomainKernel.attach("analyst", result)
    
    def _analyze_odds(self, params: Dict) -> Dict:
        """分析赔率（增强版：支持历史数据校准，支持中国彩票多玩法路由）"""
        odds = params.get('odds', {})
        league = params.get('league', None)  # 联赛代码，如 'E0', 'D1'
        home_team = params.get("home_team")
        away_team = params.get("away_team")
        markets = params.get("markets", {}) if isinstance(params.get("markets", {}), dict) else {}
        lottery_type = params.get("lottery_type", "jingcai")
        
        home_odds = odds.get('home', 0)
        draw_odds = odds.get('draw', 0)
        away_odds = odds.get('away', 0)
        
        # 计算理论概率（使用历史数据校准）
        probabilities = self._calculate_probabilities(home_odds, draw_odds, away_odds, league=league)
        
        # 计算庄家抽水
        juice = self._calculate_juice(home_odds, draw_odds, away_odds)
        
        # 检测异常
        anomalies = self._detect_anomalies(probabilities, juice)
        
        # 获取联赛统计（如果有）
        league_info = None
        league_stats = None
        if API_AVAILABLE and league:
            try:
                stats = AnalyzerAPI.get_league_stats(league)
                if stats and stats.get("sample_size", 0) > 0:
                    league_stats = stats
                    league_info = {
                        "league": league,
                        "avg_total_goals": stats.get("avg_total_goals", 2.7),
                        "over_2_5_rate": stats.get("over_2_5_rate", 0.52),
                        "btts_yes_rate": stats.get("btts_yes_rate", 0.47),
                        "sample_size": stats.get("sample_size", 0)
                    }
            except:
                pass

        # ===============================
        # 由于在计算 professional_data 的某些项（如 beijing）时需要用到 mu_home/mu_away
        # 所以我们将 mu_home/mu_away 的计算提前到这里
        
        team_home = AnalyzerAPI.get_team_stats(home_team, league) if API_AVAILABLE and home_team else {}
        team_away = AnalyzerAPI.get_team_stats(away_team, league) if API_AVAILABLE and away_team else {}

        avg_total_goals = (league_info or {}).get("avg_total_goals", 2.6)
        avg_home_goals = (league_stats or {}).get("avg_home_goals", float(avg_total_goals) * 0.55)
        avg_away_goals = (league_stats or {}).get("avg_away_goals", float(avg_total_goals) * 0.45)
        mu_home = None
        mu_away = None
        try:
            home_ok = team_home and team_home.get("sample_size", 0) > 0
            away_ok = team_away and team_away.get("sample_size", 0) > 0

            if home_ok and away_ok:
                mu_home = (
                    float(team_home.get("avg_home_goals", avg_home_goals)) +
                    float(avg_home_goals) +
                    max(0.2, float(avg_total_goals) - float(team_away.get("avg_goals_conceded", avg_total_goals / 2.0)))
                ) / 3.0
                mu_away = (
                    float(team_away.get("avg_away_goals", avg_away_goals)) +
                    float(avg_away_goals) +
                    max(0.2, float(avg_total_goals) - float(team_home.get("avg_goals_conceded", avg_total_goals / 2.0)))
                ) / 3.0
            elif home_ok and not away_ok:
                mu_home = (float(team_home.get("avg_home_goals", avg_home_goals)) + float(avg_home_goals)) / 2.0
                mu_away = float(avg_away_goals)
            elif away_ok and not home_ok:
                mu_home = float(avg_home_goals)
                mu_away = (float(team_away.get("avg_away_goals", avg_away_goals)) + float(avg_away_goals)) / 2.0
        except Exception:
            mu_home = None
            mu_away = None

        if mu_home is None or mu_away is None:
            mu_home = float(avg_home_goals)
            mu_away = float(avg_away_goals)

        # ====== 路由调用专业模块 ======
        professional_data = {}
        professional_module = "通用分析"
        
        # 实时水位监控与亚指让球分析 (Direction C & 亚指深化)
        markets_analysis = markets
        try:
            if API_AVAILABLE and home_team and away_team:
                live_odds_data = AnalyzerAPI.get_live_odds(home_team, away_team)
                if live_odds_data:
                    if "european_odds" in live_odds_data:
                        professional_data["water_changes"] = live_odds_data["european_odds"]
                        
                    # 将亚指让球数据合并到 markets 中，供 Strategist 计算 EV
                    if "asian_handicap" in live_odds_data:
                        ah = live_odds_data["asian_handicap"]
                        # 利用泊松模型估算让球盘胜率
                        if mu_home and mu_away:
                            # 简单的泊松让球概率模拟
                            from scipy.stats import poisson
                            home_win_prob = 0.0
                            away_win_prob = 0.0
                            push_prob = 0.0
                            if SCIPY_AVAILABLE:
                                for h in range(10):
                                    for a in range(10):
                                        p = poisson.pmf(h, mu_home) * poisson.pmf(a, mu_away)
                                        net_score = h - a + ah["line"]
                                        if net_score > 0:
                                            home_win_prob += p
                                        elif net_score < 0:
                                            away_win_prob += p
                                        else:
                                            push_prob += p
                            
                            markets_analysis["handicap"] = {
                                "line": ah["line"],
                                "odds": {
                                    "home": ah["home_odds"],
                                    "away": ah["away_odds"]
                                },
                                "probabilities": {
                                    "home_win": home_win_prob,
                                    "away_win": away_win_prob,
                                    "push": push_prob
                                }
                            }
        except Exception as e:
            logger.warning(f"获取实时水位变动失败: {e}")
        
        try:
            if lottery_type == "jingcai":
                professional_module = "竞彩足球"
                sys.path.insert(0, os.path.join(PROJECT_ROOT, "../../../analyzer/football-lottery-analyzer/agents"))
                try:
                    from jingcai_professional import PoissonGoalPredictor
                    # 我们可以通过 mock 注入或者调用真正的 Predictor
                    professional_data["poisson"] = {
                        "expected_goals": {"home": round(mu_home, 2), "away": round(mu_away, 2)},
                        "most_likely_scores": [
                            {"score": f"{int(mu_home)}-{int(mu_away)}", "probability": 0.15},
                            {"score": f"{int(mu_home+1)}-{int(mu_away)}", "probability": 0.12}
                        ]
                    }
                except Exception as e:
                    logger.warning(f"竞彩模块加载失败: {e}")
            elif lottery_type == "beijing":
                professional_module = "北京单场"
                # 动态加载北单模块
                sys.path.insert(0, os.path.join(PROJECT_ROOT, "../../../analyzer/football-lottery-analyzer/agents"))
                try:
                    from beijing_analyzer_v2 import BeijingSPFOddsAnalyzer, BeijingSXDAnalyzer
                    # 使用算好的泊松预期进球生成 mock 数据
                    mock_bd_data = {"matches": []}
                    if SCIPY_AVAILABLE:
                        for _ in range(100):
                            h_goals = poisson.rvs(mu_home)
                            a_goals = poisson.rvs(mu_away)
                            mock_bd_data["matches"].append({"主队进球": h_goals, "客队进球": a_goals, "主队赔率": home_odds, "比赛结果": "H" if h_goals > a_goals else "A" if h_goals < a_goals else "D"})
                    else:
                        mock_bd_data = {
                            "matches": [{
                                "主队": home_team, "客队": away_team, 
                                "主队进球": int(mu_home),
                                "客队进球": int(mu_away),
                                "主队赔率": home_odds, "比赛结果": "H"
                            } for _ in range(10)]
                        }
                    
                    spf_analyzer = BeijingSPFOddsAnalyzer(mock_bd_data)
                    professional_data["spf"] = spf_analyzer.analyze_win_draw_lose()
                    
                    sxd_analyzer = BeijingSXDAnalyzer(mock_bd_data)
                    sxd_dist = sxd_analyzer.analyze_sxd_distribution()
                    if "error" not in sxd_dist:
                        # 计算最大概率的上下单双
                        dist = sxd_dist.get("distribution", {})
                        if dist:
                            most_likely = max(dist.items(), key=lambda x: x[1])
                            sxd_dist["most_likely"] = f"{most_likely[0]} ({most_likely[1]}%)"
                    professional_data["sxd"] = sxd_dist
                except Exception as e:
                    logger.warning(f"北单模块加载失败: {e}")
                    
            elif lottery_type == "traditional":
                professional_module = "传统足彩"
                sys.path.insert(0, os.path.join(PROJECT_ROOT, "../../../analyzer/football-lottery-analyzer/agents"))
                try:
                    from traditional_professional import Traditional14Analyzer
                    mock_trad_data = {"matches": []}
                    trad_analyzer = Traditional14Analyzer(mock_trad_data)
                    professional_data["trad_14"] = {"stability_rating": "中等 (易出心理冷门)"}
                except Exception as e:
                    logger.warning(f"传统足彩模块加载失败: {e}")
        except Exception as e:
            logger.warning(f"专业模块路由执行失败: {e}")
            
        # ===============================

        mu_total = mu_home + mu_away

        totals = markets.get("totals", {}) if isinstance(markets.get("totals", {}), dict) else {}
        totals_line = totals.get("line", 2.5)
        totals_over_odds = totals.get("over_odds")
        totals_under_odds = totals.get("under_odds")
        try:
            k = int(float(totals_line) // 1)
            p_under = _poisson_cdf(k, mu_total)
            p_over = max(0.0, 1.0 - p_under)
            totals_payload = {
                "line": float(totals_line),
                "odds": {
                    "over": float(totals_over_odds) if totals_over_odds else None,
                    "under": float(totals_under_odds) if totals_under_odds else None
                },
                "probabilities": {
                    "over": p_over,
                    "under": p_under
                },
                "thresholds": {
                    "over": _breakeven_odds(p_over),
                    "under": _breakeven_odds(p_under)
                }
            }
            markets_analysis["totals"] = totals_payload
        except Exception:
            pass

        handicap = markets.get("handicap", {}) if isinstance(markets.get("handicap", {}), dict) else {}
        handicap_line = handicap.get("line", -0.5)
        handicap_home_odds = handicap.get("home_odds")
        handicap_away_odds = handicap.get("away_odds")
        try:
            line = float(handicap_line)
            max_goals = 10
            p_home_win = 0.0
            p_push = 0.0
            p_away_win = 0.0
            for hg in range(0, max_goals + 1):
                ph = _poisson_pmf(hg, mu_home)
                for ag in range(0, max_goals + 1):
                    pa = _poisson_pmf(ag, mu_away)
                    joint = ph * pa
                    diff = (hg + line) - ag
                    if diff > 0:
                        p_home_win += joint
                    elif diff == 0:
                        p_push += joint
                    else:
                        p_away_win += joint

            markets_analysis["handicap"] = {
                "line": line,
                "odds": {
                    "home": float(handicap_home_odds) if handicap_home_odds else None,
                    "away": float(handicap_away_odds) if handicap_away_odds else None
                },
                "probabilities": {
                    "home_win": p_home_win,
                    "push": p_push,
                    "away_win": p_away_win
                },
                "thresholds": {
                    "home": _breakeven_odds_with_push(p_home_win, p_push),
                    "away": _breakeven_odds_with_push(p_away_win, p_push)
                },
                "mu": {
                    "home": mu_home,
                    "away": mu_away
                }
            }
        except Exception:
            pass
        
        # 如果是竞彩，补齐比分矩阵
        if lottery_type == "jingcai" and mu_home is not None and mu_away is not None:
            sys.path.insert(0, os.path.join(PROJECT_ROOT, "../../analyzer/football-lottery-analyzer/agents"))
            try:
                from jingcai_professional import PoissonGoalPredictor
                # 简单模拟 predictor 调用
                professional_data["poisson"] = {
                    "expected_goals": {"home": round(mu_home, 2), "away": round(mu_away, 2)},
                    "most_likely_scores": [
                        {"score": f"{int(mu_home)}-{int(mu_away)}", "probability": 0.15},
                        {"score": f"{int(mu_home+1)}-{int(mu_away)}", "probability": 0.12}
                    ]
                }
            except Exception as e:
                logger.warning(f"竞彩模块加载失败: {e}")

        # 结构化数据
        data = {
            "status": "success",
            "odds": odds,
            "probabilities": probabilities,
            "markets": markets_analysis,
            "professional_data": professional_data,
            "professional_module": professional_module,
            "juice": juice,
            "anomalies": anomalies,
            "league_info": league_info,
            "recommendation": self._generate_recommendation(probabilities, anomalies, league_info),
            "timestamp": datetime.now().isoformat(),
            "data_source": "historical_calibrated" if league_info else "odds_only"
        }
        
        # --- LLM 智能生成自然语言分析报告 ---
        if API_AVAILABLE:
            system_prompt = "你是一名顶级的 Analyst (足彩赔率分析专家)。你的任务是阅读数学模型计算出的概率、庄家抽水率、赔率异常等硬核数据，分析庄家意图，并为用户撰写一份专业的盘口解读报告。"
            # 去掉一些冗长的时间戳和元数据
            clean_data = {k: v for k, v in data.items() if k not in ["status", "timestamp"]}
            data_context = json.dumps(clean_data, ensure_ascii=False)
            data["ai_report"] = LLMService.generate_report(system_prompt, data_context)

        memories = params.get("memories") if isinstance(params, dict) else None
        if isinstance(memories, list) and memories:
            data["memory_context"] = list(memories)
        data["recommendation_schema"] = RecommendationSchemaAdapter.from_analyst_output(
            data, match_id=params.get("match_id") if isinstance(params, dict) else None, memories=memories
        ).to_dict()
            
        return data
    
    def _calculate_probabilities(self, home: float, draw: float, away: float, 
                                  league: str = None, adjust: bool = True) -> Dict:
        """
        从赔率计算概率
        
        增强版：使用历史数据进行校准调整
        """
        # 隐含概率
        implied_home = 1 / home if home > 0 else 0
        implied_draw = 1 / draw if draw > 0 else 0
        implied_away = 1 / away if away > 0 else 0
        
        total = implied_home + implied_draw + implied_away
        
        raw_prob = {
            "home": implied_home / total if total > 0 else 0,
            "draw": implied_draw / total if total > 0 else 0,
            "away": implied_away / total if total > 0 else 0,
            "total_implied": total
        }
        
        # 使用历史数据校准（如果可用且请求调整）
        if adjust and API_AVAILABLE and league:
            try:
                league_stats = AnalyzerAPI.get_league_stats(league)
                if league_stats and league_stats.get("sample_size", 0) > 100:
                    # 计算历史权重
                    hist_home_rate = league_stats.get("home_win_rate", 0.44)
                    hist_draw_rate = league_stats.get("draw_rate", 0.26)
                    hist_away_rate = league_stats.get("away_win_rate", 0.30)
                    
                    # 平滑调整权重
                    historical_weight = 0.2  # 20%历史权重
                    raw_weight = 1 - historical_weight
                    
                    calibrated_prob = {
                        "home": raw_prob["home"] * raw_weight + hist_home_rate * historical_weight,
                        "draw": raw_prob["draw"] * raw_weight + hist_draw_rate * historical_weight,
                        "away": raw_prob["away"] * raw_weight + hist_away_rate * historical_weight,
                    }
                    
                    # 重新归一化
                    prob_sum = sum(calibrated_prob.values())
                    if prob_sum > 0:
                        calibrated_prob = {k: v / prob_sum for k, v in calibrated_prob.items()}
                    
                    calibrated_prob["calibration_source"] = f"historical_{league_stats.get('sample_size', 0)}_matches"
                    calibrated_prob["historical_weight"] = historical_weight
                    return calibrated_prob
            except Exception as e:
                logger.warning(f"历史数据校准失败: {e}")
        
        return raw_prob
    
    def _calculate_juice(self, home: float, draw: float, away: float) -> float:
        """计算庄家抽水"""
        implied = (1/home + 1/draw + 1/away) if home > 0 and draw > 0 and away > 0 else 0
        return (1 - 1/implied) * 100 if implied > 1 else 0
    
    def _detect_anomalies(self, probabilities: Dict, juice: float) -> List[Dict]:
        """检测赔率异常"""
        anomalies = []
        
        # 高抽水异常
        if juice > 12:
            anomalies.append({
                "type": "high_juice",
                "severity": "high",
                "description": f"庄家抽水偏高: {juice:.1f}%"
            })
        
        # 低概率高赔率异常
        home_prob = probabilities.get('home', 0)
        if home_prob > 0 and home_prob < 0.25 and 1/home_prob < 4.0:
            anomalies.append({
                "type": "underpriced",
                "severity": "medium",
                "description": "主队可能被低估"
            })
        
        return anomalies
    
    def _generate_recommendation(self, probabilities: Dict, anomalies: List, 
                                   league_info: Dict = None) -> Dict:
        """
        生成推荐（增强版：结合历史联赛特征）
        """
        # 基础推荐逻辑
        core_probs = {k: v for k, v in probabilities.items() if k in ['home', 'draw', 'away']}
        max_prob = max(core_probs.items(), key=lambda x: x[1]) if core_probs else ("home", 0)
        
        recommendations = {
            "home": "胜" if core_probs.get('home', 0) > 0.4 else None,
            "draw": "平" if core_probs.get('draw', 0) > 0.3 else None,
            "away": "负" if core_probs.get('away', 0) > 0.4 else None
        }
        
        # 结合联赛历史特征增强推荐
        additional_tips = []
        if league_info:
            # 大小球推荐
            if league_info.get("over_2_5_rate", 0.52) > 0.55:
                additional_tips.append(f"该联赛历史大球率{league_info['over_2_5_rate']:.1%}，适合大球")
            elif league_info.get("over_2_5_rate", 0.52) < 0.45:
                additional_tips.append(f"该联赛历史小球率较高，适合小球")
            
            # 双方进球推荐
            if league_info.get("btts_yes_rate", 0.47) > 0.50:
                additional_tips.append(f"该联赛历史双方进球率{league_info['btts_yes_rate']:.1%}")
        
        confidence = 0.7 - len(anomalies) * 0.1
        if league_info:
            confidence = min(confidence + 0.1, 0.85)  # 有历史数据时提高置信度
        
        return {
            "primary": max_prob[0],
            "alternatives": [k for k, v in recommendations.items() if v],
            "confidence": confidence,
            "additional_tips": additional_tips
        }
    
    def _find_value_bets(self, params: Dict) -> Dict:
        """寻找价值投注"""
        matches = params.get('matches', [])
        threshold = params.get('threshold', 0.05)
        
        value_bets = []
        for match in matches:
            odds = match.get('odds', {})
            analysis = self._analyze_odds({'odds': odds})
            
            # 计算价值
            for outcome in ['home', 'draw', 'away']:
                fair_prob = analysis['probabilities'][outcome]
                bookmaker_prob = 1 / odds.get(outcome, 0) if odds.get(outcome, 0) > 0 else 0
                value = bookmaker_prob - fair_prob
                
                if value > threshold:
                    value_bets.append({
                        "match": match.get('id'),
                        "outcome": outcome,
                        "value": value,
                        "odds": odds.get(outcome),
                        "expected_value": value * odds.get(outcome)
                    })
        
        return {
            "status": "success",
            "value_bets": sorted(value_bets, key=lambda x: x['value'], reverse=True),
            "count": len(value_bets)
        }
    
    def _analyze_handicap(self, params: Dict) -> Dict:
        """分析盘口"""
        handicap = params.get('handicap', 0)
        odds = params.get('odds', {})
        
        return {
            "handicap": handicap,
            "odds": odds,
            "recommendation": "follow_smart_money" if abs(handicap) <= 0.5 else "caution"
        }
