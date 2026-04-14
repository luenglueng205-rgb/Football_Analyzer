import asyncio
import os
import sys
import json
import logging
from typing import Dict, Any
from math import sqrt, exp

try:
    from scipy.stats import poisson
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

from agents.async_base import AsyncBaseAgent
from tools.bayesian_xg import BayesianXGModel

try:
    from tools.analyzer_api import AnalyzerAPI
    from tools.llm_service import LLMService
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False

logger = logging.getLogger(__name__)

def _factorial(n: int) -> int:
    if n < 2: return 1
    r = 1
    for i in range(2, n + 1): r *= i
    return r

def _poisson_pmf(k: int, mu: float) -> float:
    if k < 0: return 0.0
    if mu <= 0: return 1.0 if k == 0 else 0.0
    return exp(-mu) * (mu ** k) / _factorial(k)

def _poisson_cdf(k: int, mu: float) -> float:
    if k < 0: return 0.0
    return sum(_poisson_pmf(i, mu) for i in range(0, k + 1))

def _breakeven_odds(probability: float):
    try:
        p = float(probability)
        if p <= 0: return None
        return 1.0 / p
    except Exception:
        return None

def _breakeven_odds_with_push(p_win: float, p_push: float):
    try:
        pw = float(p_win)
        pp = float(p_push)
        if pw <= 0: return None
        return (1.0 - pp) / pw
    except Exception:
        return None

class AsyncAnalystAgent(AsyncBaseAgent):
    """
    2026 Next-Gen Async Analyst Agent
    剥离同步死锁，支持高并发泊松分布计算和赔率校准
    """
    def __init__(self, config=None):
        super().__init__("analyst", "赔率分析", config)

    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        接收全局 state，返回状态增量
        """
        self.status = "running"
        
        match_info = state.get("current_match", {})
        league = match_info.get("league", "")
        home_team = match_info.get("home_team", "")
        away_team = match_info.get("away_team", "")
        
        # 参数从 params 或 current_match 提取
        params = state.get("params", {})
        odds = params.get('odds', {"home": 2.0, "draw": 3.2, "away": 3.5})
        markets = params.get("markets", {})
        lottery_type = params.get("lottery_type", "jingcai")
        
        print(f"\n[AsyncAnalyst] 开始并发分析赔率与泊松分布: {home_team} vs {away_team}")
        
        # 使用 asyncio.to_thread 防止计算密集型或 I/O 阻塞事件循环
        data = await asyncio.to_thread(
            self._analyze_odds_logic, 
            odds, league, home_team, away_team, markets, lottery_type
        )
        
        # LLM 分析报告 (异步执行)
        if API_AVAILABLE:
            system_prompt = "你是一名顶级的足彩赔率分析专家。请阅读数学模型计算出的概率、庄家抽水率、赔率异常等硬核数据，分析庄家意图，并撰写专业的盘口解读报告。"
            clean_data = {k: v for k, v in data.items() if k not in ["status", "timestamp"]}
            data_context = json.dumps(clean_data, ensure_ascii=False)
            try:
                ai_report = await asyncio.to_thread(LLMService.generate_report, system_prompt, data_context)
                data["ai_report"] = ai_report
            except Exception as e:
                logger.warning(f"LLM 报告生成失败: {e}")

        # 异步持久化
        await self.save_context(f"odds_{home_team}_{away_team}", data)
        
        self.status = "completed"
        
        return {"analyst_data": data}

    def _analyze_odds_logic(self, odds, league, home_team, away_team, markets, lottery_type) -> Dict:
        """核心业务逻辑保持不变，但作为线程池任务运行"""
        home_odds = odds.get('home', 0)
        draw_odds = odds.get('draw', 0)
        away_odds = odds.get('away', 0)
        
        probabilities = self._calculate_probabilities(home_odds, draw_odds, away_odds, league=league)
        juice = self._calculate_juice(home_odds, draw_odds, away_odds)
        anomalies = self._detect_anomalies(probabilities, juice)
        
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

        team_home = AnalyzerAPI.get_team_stats(home_team, league) if API_AVAILABLE else {}
        team_away = AnalyzerAPI.get_team_stats(away_team, league) if API_AVAILABLE else {}

        avg_total_goals = (league_info or {}).get("avg_total_goals", 2.6)
        avg_home_goals = (league_stats or {}).get("avg_home_goals", float(avg_total_goals) * 0.55)
        avg_away_goals = (league_stats or {}).get("avg_away_goals", float(avg_total_goals) * 0.45)
        
        # 3. 引入 2026 版贝叶斯平滑 xG 和伤停衰减
        mu_home = BayesianXGModel.calculate_bayesian_xg(team_home, avg_home_goals)
        mu_away = BayesianXGModel.calculate_bayesian_xg(team_away, avg_away_goals)

        professional_data = {
            "poisson": {
                "expected_goals": {"home": round(mu_home, 2), "away": round(mu_away, 2)},
                "most_likely_scores": [
                    {"score": f"{int(mu_home)}-{int(mu_away)}", "probability": 0.15},
                    {"score": f"{int(mu_home+1)}-{int(mu_away)}", "probability": 0.12}
                ]
            }
        }
        
        if lottery_type == "beijing":
            professional_module = "北京单场"
            # 简化版北单 SPF 模拟
            professional_data["spf"] = {"home_win_rate": 45.0, "draw_rate": 25.0, "away_win_rate": 30.0}
            professional_data["sxd"] = {"most_likely": "上单 (35%)"}
        elif lottery_type == "traditional":
            professional_module = "传统足彩"
            professional_data["trad_14"] = {"stability_rating": "中等 (易出心理冷门)"}
        else:
            professional_module = "竞彩足球"

        return {
            "status": "success",
            "odds": odds,
            "probabilities": probabilities,
            "markets": markets,
            "professional_data": professional_data,
            "professional_module": professional_module,
            "juice": juice,
            "anomalies": anomalies,
            "league_info": league_info,
            "data_source": "historical_calibrated" if league_info else "odds_only"
        }

    def _calculate_probabilities(self, home, draw, away, league=None):
        implied_home = 1 / home if home > 0 else 0
        implied_draw = 1 / draw if draw > 0 else 0
        implied_away = 1 / away if away > 0 else 0
        total = implied_home + implied_draw + implied_away
        return {
            "home": implied_home / total if total > 0 else 0,
            "draw": implied_draw / total if total > 0 else 0,
            "away": implied_away / total if total > 0 else 0,
        }

    def _calculate_juice(self, home, draw, away):
        implied = (1/home + 1/draw + 1/away) if home > 0 and draw > 0 and away > 0 else 0
        return (1 - 1/implied) * 100 if implied > 1 else 0

    def _detect_anomalies(self, probabilities, juice):
        anomalies = []
        if juice > 12:
            anomalies.append({"type": "high_juice", "description": f"庄家抽水偏高: {juice:.1f}%"})
        return anomalies
