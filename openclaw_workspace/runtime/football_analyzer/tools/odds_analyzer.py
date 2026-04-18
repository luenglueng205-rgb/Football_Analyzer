#!/usr/bin/env python3
"""
赔率分析工具 - OpenClaw规范版本
Odds Analyzer Tool - 增强版：集成221,415条历史数据
"""

import os
import logging
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

try:
    from tools.historical_database import get_historical_database
    HISTORICAL_DB_AVAILABLE = True
except Exception:
    HISTORICAL_DB_AVAILABLE = False
    get_historical_database = None


class OddsAnalyzer:
    """
    赔率分析工具 - 增强版
    
    功能：
    1. 计算理论概率
    2. 分析庄家抽水
    3. 检测赔率异常
    4. 识别价值投注
    5. 历史数据校准（基于221,415条比赛）
    """
    
    def __init__(self, use_historical: bool = True):
        self.analysis_cache = {}
        
        # 初始化历史数据库
        self.historical_db = None
        if use_historical and HISTORICAL_DB_AVAILABLE and get_historical_database:
            try:
                self.historical_db = get_historical_database(lazy_load=True)
                print(f"✅ OddsAnalyzer 已连接历史数据库 (221,415条数据)")
            except Exception as e:
                logger.warning(f"历史数据库加载失败: {e}")
    
    def analyze(self, odds: Dict[str, float], league: str = None, 
                calibrate: bool = True) -> Dict:
        """
        分析赔率（增强版：支持历史数据校准）
        
        Args:
            odds: 赔率字典 {"home": 1.85, "draw": 3.40, "away": 4.20}
            league: 联赛代码 (如 'E0', 'D1')
            calibrate: 是否使用历史数据进行校准
            
        Returns:
            分析结果字典
        """
        home_odds = odds.get('home', 0)
        draw_odds = odds.get('draw', 0)
        away_odds = odds.get('away', 0)
        
        # 计算隐含概率
        implied_prob = self._calculate_implied_probabilities(home_odds, draw_odds, away_odds)
        
        # 使用历史数据校准
        calibrated_prob = implied_prob
        calibration_info = None
        if calibrate and self.historical_db and league:
            calibrated_prob, calibration_info = self._calibrate_with_historical(
                implied_prob, league
            )
        
        # 计算庄家抽水
        juice = self._calculate_juice(home_odds, draw_odds, away_odds)
        
        # 公平赔率（使用校准后的概率）
        fair_odds = self._calculate_fair_odds(calibrated_prob)
        
        # 价值分析
        value_analysis = self._analyze_value(odds, calibrated_prob, fair_odds)
        
        # 获取联赛统计
        league_stats = None
        if self.historical_db and league:
            try:
                stats = self.historical_db.get_league_stats(league)
                if stats and stats.get("sample_size", 0) > 0:
                    league_stats = {
                        "avg_goals": stats.get("avg_total_goals", 2.7),
                        "over_2_5_rate": stats.get("over_2_5_rate", 0.52),
                        "btts_rate": stats.get("btts_yes_rate", 0.47),
                        "draw_rate": stats.get("draw_rate", 0.26),
                        "sample_size": stats.get("sample_size", 0)
                    }
            except:
                pass
        
        return {
            "input_odds": odds,
            "implied_probabilities": calibrated_prob,
            "fair_odds": fair_odds,
            "juice": juice,
            "value_analysis": value_analysis,
            "league_stats": league_stats,
            "calibration_info": calibration_info,
            "recommendation": self._generate_recommendation(value_analysis, league_stats)
        }
    
    def _calibrate_with_historical(self, implied_prob: Dict, league: str) -> Tuple[Dict, Dict]:
        """
        使用历史数据校准概率
        
        基于该联赛的历史胜平负比例，对赔率隐含概率进行校准
        """
        try:
            league_stats = self.historical_db.get_league_stats(league)
            sample_size = league_stats.get("sample_size", 0)
            
            if sample_size < 100:
                return implied_prob, {"calibrated": False, "reason": "样本不足"}
            
            hist_home = league_stats.get("home_win_rate", 0.44)
            hist_draw = league_stats.get("draw_rate", 0.26)
            hist_away = league_stats.get("away_win_rate", 0.30)
            
            # 计算隐含概率的历史比例
            raw_total = sum(implied_prob.values()) if sum(implied_prob.values()) > 0 else 1
            raw_home = implied_prob.get("home", 0) / raw_total
            raw_draw = implied_prob.get("draw", 0) / raw_total
            raw_away = implied_prob.get("away", 0) / raw_total
            
            # 加权平均（历史权重可调）
            hist_weight = 0.25  # 25%历史权重
            
            calibrated = {
                "home": raw_home * (1 - hist_weight) + hist_home * hist_weight,
                "draw": raw_draw * (1 - hist_weight) + hist_draw * hist_weight,
                "away": raw_away * (1 - hist_weight) + hist_away * hist_weight
            }
            
            # 归一化
            total = sum(calibrated.values())
            if total > 0:
                calibrated = {k: v / total for k, v in calibrated.items()}
            
            return calibrated, {
                "calibrated": True,
                "league": league,
                "sample_size": sample_size,
                "historical_weight": hist_weight,
                "hist_distribution": {"home": hist_home, "draw": hist_draw, "away": hist_away}
            }
        except Exception as e:
            logger.warning(f"校准失败: {e}")
            return implied_prob, {"calibrated": False, "reason": str(e)}
    
    def _calculate_implied_probabilities(
        self, home: float, draw: float, away: float
    ) -> Dict[str, float]:
        """计算隐含概率"""
        total = (1/home + 1/draw + 1/away) if home > 0 and draw > 0 and away > 0 else 0
        
        if total == 0:
            return {"home": 0, "draw": 0, "away": 0}
        
        return {
            "home": (1/home) / total,
            "draw": (1/draw) / total,
            "away": (1/away) / total
        }
    
    def _calculate_juice(self, home: float, draw: float, away: float) -> float:
        """计算庄家抽水"""
        total_implied = (1/home + 1/draw + 1/away) if home > 0 and draw > 0 and away > 0 else 0
        
        if total_implied == 0:
            return 0
        
        return (1 - 1/total_implied) * 100
    
    def _calculate_fair_odds(self, probabilities: Dict[str, float]) -> Dict[str, float]:
        """计算公平赔率"""
        return {
            "home": 1 / probabilities.get("home", 0.33) if probabilities.get("home", 0) > 0 else 0,
            "draw": 1 / probabilities.get("draw", 0.33) if probabilities.get("draw", 0) > 0 else 0,
            "away": 1 / probabilities.get("away", 0.33) if probabilities.get("away", 0) > 0 else 0
        }
    
    def _analyze_value(
        self,
        odds: Dict[str, float],
        implied: Dict[str, float],
        fair: Dict[str, float]
    ) -> Dict[str, Dict]:
        """分析价值"""
        value_results = {}
        
        for outcome in ['home', 'draw', 'away']:
            bookmaker_odds = odds.get(outcome, 0)
            implied_prob = implied.get(outcome, 0)
            fair_odds = fair.get(outcome, 0)
            
            if bookmaker_odds > 0 and implied_prob > 0:
                # 计算期望值
                expected_value = (bookmaker_odds * implied_prob) - 1
                
                # 计算价值百分比
                value_percent = ((bookmaker_odds / fair_odds) - 1) * 100 if fair_odds > 0 else 0
                
                value_results[outcome] = {
                    "bookmaker_odds": bookmaker_odds,
                    "implied_probability": implied_prob,
                    "fair_odds": fair_odds,
                    "expected_value": expected_value,
                    "value_percent": value_percent,
                    "has_value": value_percent > 5  # 超过5%视为有价值
                }
        
        return value_results
    
    def _generate_recommendation(self, value_analysis: Dict, 
                                   league_stats: Dict = None) -> Dict:
        """
        生成推荐（增强版：结合联赛历史特征）
        """
        valuable_outcomes = [
            outcome for outcome, data in value_analysis.items()
            if data.get('has_value', False)
        ]
        
        # 增强推荐信息
        additional_tips = []
        if league_stats:
            # 大小球建议
            if league_stats.get("over_2_5_rate", 0.52) > 0.55:
                additional_tips.append(f"历史大球率{league_stats['over_2_5_rate']:.1%}，推荐大球")
            elif league_stats.get("over_2_5_rate", 0.52) < 0.45:
                additional_tips.append(f"历史小球率{1-league_stats['over_2_5_rate']:.1%}，推荐小球")
            
            # 双方进球建议
            if league_stats.get("btts_rate", 0.47) > 0.50:
                additional_tips.append(f"历史双方进球率{league_stats['btts_rate']:.1%}")
            
            # 平局可能性
            if league_stats.get("draw_rate", 0.26) > 0.28:
                additional_tips.append(f"历史平局率{league_stats['draw_rate']:.1%}，注意平局选项")
        
        if valuable_outcomes:
            # 选择价值最大的
            best = max(
                valuable_outcomes,
                key=lambda x: value_analysis[x].get('value_percent', 0)
            )
            
            confidence = min(value_analysis[best].get('value_percent', 0) / 20, 0.9)
            if league_stats:
                confidence = min(confidence + 0.05, 0.92)  # 有历史数据时提升置信度
            
            return {
                "action": "bet",
                "outcomes": valuable_outcomes,
                "primary": best,
                "confidence": confidence,
                "additional_tips": additional_tips
            }
        else:
            return {
                "action": "skip",
                "reason": "No value bets found",
                "confidence": 0.5,
                "additional_tips": additional_tips
            }
    
    def compare_bookmakers(
        self,
        odds1: Dict[str, float],
        odds2: Dict[str, float]
    ) -> Dict:
        """比较两个庄家的赔率"""
        analysis1 = self.analyze(odds1)
        analysis2 = self.analyze(odds2)
        
        best_odds = {}
        for outcome in ['home', 'draw', 'away']:
            if odds1.get(outcome, 0) >= odds2.get(outcome, 0):
                best_odds[outcome] = {"odds": odds1.get(outcome), "bookmaker": 1}
            else:
                best_odds[outcome] = {"odds": odds2.get(outcome), "bookmaker": 2}
        
        return {
            "bookmaker1": odds1,
            "bookmaker2": odds2,
            "best_odds": best_odds,
            "arb_opportunity": self._check_arbitrage(odds1, odds2)
        }
    
    def _check_arbitrage(
        self,
        odds1: Dict[str, float],
        odds2: Dict[str, float]
    ) -> Optional[Dict]:
        """检查套利机会"""
        all_odds = [odds1, odds2]
        
        # 简化检查
        max_home = max(o.get('home', 0) for o in all_odds)
        max_draw = max(o.get('draw', 0) for o in all_odds)
        max_away = max(o.get('away', 0) for o in all_odds)
        
        implied_total = 1/max_home + 1/max_draw + 1/max_away if max_home > 0 and max_draw > 0 and max_away > 0 else 0
        
        if implied_total < 1:
            profit = (1 - implied_total) * 100
            return {
                "exists": True,
                "profit_percent": profit,
                "max_home": max_home,
                "max_draw": max_draw,
                "max_away": max_away
            }
        
        return {"exists": False}
