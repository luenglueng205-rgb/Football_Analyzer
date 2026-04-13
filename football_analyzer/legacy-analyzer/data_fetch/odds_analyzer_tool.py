#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
足球彩票分析系统 - 赔率分析工具
独立的赔率分析和价值识别工具，不依赖爬虫
"""

import os
import sys
from typing import Dict, List, Optional, Tuple, Any

# 尝试导入数据获取模块
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from data_fetch.odds_scraper import OddsScraper
    HAS_SCRAPER = True
except ImportError:
    HAS_SCRAPER = False


class OddsAnalyzer:
    """
    赔率分析工具类
    
    功能：
    1. 赔率数据清洗和标准化
    2. 隐含概率计算
    3. 庄家抽水分析
    4. 价值投注识别
    5. 期望值计算
    """
    
    def __init__(self):
        self.scraper = OddsScraper() if HAS_SCRAPER else None
    
    def analyze_odds(self, odds: Dict[str, float]) -> Dict:
        """
        分析赔率
        
        Args:
            odds: 赔率字典 {"home": 1.85, "draw": 3.40, "away": 4.20}
            
        Returns:
            完整分析结果
        """
        home_odds = odds.get('home', odds.get('1', 0))
        draw_odds = odds.get('draw', odds.get('X', 0))
        away_odds = odds.get('away', odds.get('2', 0))
        
        # 计算隐含概率
        probabilities = self.calculate_implied_probability({
            'home': home_odds,
            'draw': draw_odds,
            'away': away_odds
        })
        
        # 计算庄家抽水
        juice_analysis = self.analyze_bookmaker_juice({
            'home': home_odds,
            'draw': draw_odds,
            'away': away_odds
        })
        
        # 识别价值投注
        value_analysis = self.identify_value_bets({
            'home': home_odds,
            'draw': draw_odds,
            'away': away_odds
        }, probabilities)
        
        # 计算公平赔率
        fair_odds = self.calculate_fair_odds(probabilities)
        
        return {
            'input_odds': {
                'home': home_odds,
                'draw': draw_odds,
                'away': away_odds
            },
            'probabilities': probabilities,
            'juice_analysis': juice_analysis,
            'value_analysis': value_analysis,
            'fair_odds': fair_odds,
            'recommendation': self.generate_recommendation(value_analysis, probabilities)
        }
    
    def calculate_implied_probability(self, odds: Dict[str, float]) -> Dict[str, float]:
        """
        从赔率计算隐含概率
        
        Args:
            odds: 赔率字典
            
        Returns:
            隐含概率字典
        """
        home = odds.get('home', 0)
        draw = odds.get('draw', 0)
        away = odds.get('away', 0)
        
        if home <= 0 or draw <= 0 or away <= 0:
            return {'home': 0, 'draw': 0, 'away': 0}
        
        # 计算隐含概率
        implied_home = 1 / home
        implied_draw = 1 / draw
        implied_away = 1 / away
        
        total = implied_home + implied_draw + implied_away
        
        if total == 0:
            return {'home': 0, 'draw': 0, 'away': 0}
        
        return {
            'home': implied_home / total,
            'draw': implied_draw / total,
            'away': implied_away / total
        }
    
    def analyze_bookmaker_juice(self, odds: Dict[str, float]) -> Dict:
        """
        分析庄家抽水
        
        Args:
            odds: 赔率字典
            
        Returns:
            抽水分析结果
        """
        home = odds.get('home', 0)
        draw = odds.get('draw', 0)
        away = odds.get('away', 0)
        
        if home <= 0 or draw <= 0 or away <= 0:
            return {'juice_percentage': 0, 'juice_type': 'unknown'}
        
        # 计算总隐含概率
        total_implied = (1/home + 1/draw + 1/away)
        
        # 抽水百分比
        juice_pct = (1 - 1/total_implied) * 100 if total_implied > 1 else 0
        
        # 判断抽水类型
        if juice_pct < 3:
            juice_type = 'low'  # 低抽水，赔率好
        elif juice_pct < 6:
            juice_type = 'normal'  # 正常抽水
        elif juice_pct < 10:
            juice_type = 'high'  # 高抽水
        else:
            juice_type = 'very_high'  # 极高抽水
        
        return {
            'juice_percentage': juice_pct,
            'juice_type': juice_type,
            'juice_interpretation': self._interpret_juice(juice_pct)
        }
    
    def _interpret_juice(self, juice_pct: float) -> str:
        """解释抽水"""
        if juice_pct < 3:
            return "赔率较好，对玩家有利"
        elif juice_pct < 6:
            return "正常抽水范围"
        elif juice_pct < 10:
            return "抽水较高，选择需谨慎"
        else:
            return "抽水极高，建议避开"
    
    def identify_value_bets(
        self,
        odds: Dict[str, float],
        probabilities: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        识别价值投注
        
        Args:
            odds: 赔率字典
            probabilities: 真实概率估算（可选，默认使用隐含概率）
            
        Returns:
            价值分析结果
        """
        if probabilities is None:
            probabilities = self.calculate_implied_probability(odds)
        
        home = odds.get('home', 0)
        draw = odds.get('draw', 0)
        away = odds.get('away', 0)
        
        home_prob = probabilities.get('home', 0)
        draw_prob = probabilities.get('draw', 0)
        away_prob = probabilities.get('away', 0)
        
        # 计算期望值（使用保守估计，假设真实概率 = 隐含概率 * 0.95）
        conservative_factor = 0.95
        
        home_ev = home * home_prob * conservative_factor - 1
        draw_ev = draw * draw_prob * conservative_factor - 1
        away_ev = away * away_prob * conservative_factor - 1
        
        # 计算价值百分比（相对于公平赔率）
        fair_home = 1 / home_prob if home_prob > 0 else 0
        fair_draw = 1 / draw_prob if draw_prob > 0 else 0
        fair_away = 1 / away_prob if away_prob > 0 else 0
        
        home_value_pct = ((home / fair_home) - 1) * 100 if fair_home > 0 else 0
        draw_value_pct = ((draw / fair_draw) - 1) * 100 if fair_draw > 0 else 0
        away_value_pct = ((away / fair_away) - 1) * 100 if fair_away > 0 else 0
        
        return {
            'home': {
                'odds': home,
                'probability': home_prob,
                'expected_value': home_ev,
                'value_percentage': home_value_pct,
                'has_value': home_value_pct > 5  # 超过5%视为有价值
            },
            'draw': {
                'odds': draw,
                'probability': draw_prob,
                'expected_value': draw_ev,
                'value_percentage': draw_value_pct,
                'has_value': draw_value_pct > 5
            },
            'away': {
                'odds': away,
                'probability': away_prob,
                'expected_value': away_ev,
                'value_percentage': away_value_pct,
                'has_value': away_value_pct > 5
            }
        }
    
    def calculate_fair_odds(self, probabilities: Dict[str, float]) -> Dict[str, float]:
        """
        计算公平赔率
        
        Args:
            probabilities: 概率字典
            
        Returns:
            公平赔率字典
        """
        home_prob = probabilities.get('home', 0)
        draw_prob = probabilities.get('draw', 0)
        away_prob = probabilities.get('away', 0)
        
        return {
            'home': 1 / home_prob if home_prob > 0 else 0,
            'draw': 1 / draw_prob if draw_prob > 0 else 0,
            'away': 1 / away_prob if away_prob > 0 else 0
        }
    
    def generate_recommendation(
        self,
        value_analysis: Dict,
        probabilities: Dict[str, float]
    ) -> Dict:
        """
        生成投注建议
        
        Args:
            value_analysis: 价值分析结果
            probabilities: 概率字典
            
        Returns:
            投注建议
        """
        valuable_options = []
        
        for outcome in ['home', 'draw', 'away']:
            if value_analysis.get(outcome, {}).get('has_value', False):
                valuable_options.append({
                    'outcome': outcome,
                    'odds': value_analysis[outcome]['odds'],
                    'value_percentage': value_analysis[outcome]['value_percentage'],
                    'probability': probabilities.get(outcome, 0)
                })
        
        if valuable_options:
            # 按价值排序
            valuable_options.sort(key=lambda x: x['value_percentage'], reverse=True)
            best = valuable_options[0]
            
            return {
                'action': 'bet',
                'primary_recommendation': best['outcome'],
                'confidence': min(best['value_percentage'] / 30, 0.9),  # 最高90%置信度
                'all_valuable': valuable_options,
                'summary': f"{best['outcome']} 有价值 (价值: {best['value_percentage']:.1f}%)"
            }
        else:
            return {
                'action': 'skip',
                'reason': '没有发现价值投注',
                'confidence': 0.5
            }
    
    def compare_bookmakers(
        self,
        odds_list: List[Dict[str, float]],
        bookmaker_names: Optional[List[str]] = None
    ) -> Dict:
        """
        比较多个庄家的赔率
        
        Args:
            odds_list: 赔率列表
            bookmaker_names: 庄家名称列表
            
        Returns:
            比较结果
        """
        if bookmaker_names is None:
            bookmaker_names = [f"庄家{i+1}" for i in range(len(odds_list))]
        
        results = []
        
        for i, odds in enumerate(odds_list):
            analysis = self.analyze_odds(odds)
            results.append({
                'bookmaker': bookmaker_names[i] if i < len(bookmaker_names) else f"庄家{i+1}",
                'analysis': analysis
            })
        
        # 找出最佳赔率
        best_odds = {}
        for outcome in ['home', 'draw', 'away']:
            max_odds = 0
            best_bookmaker = None
            for result in results:
                odds = result['analysis']['input_odds'].get(outcome, 0)
                if odds > max_odds:
                    max_odds = odds
                    best_bookmaker = result['bookmaker']
            best_odds[outcome] = {'odds': max_odds, 'bookmaker': best_bookmaker}
        
        return {
            'bookmakers': results,
            'best_odds': best_odds,
            'best_bookmaker': self._determine_best_overall(results)
        }
    
    def _determine_best_overall(self, results: List[Dict]) -> str:
        """确定总体最佳庄家"""
        if not results:
            return "未知"
        
        # 简单算法：选择抽水最低的
        min_juice = float('inf')
        best = results[0]['bookmaker']
        
        for result in results:
            juice = result['analysis']['juice_analysis']['juice_percentage']
            if juice < min_juice:
                min_juice = juice
                best = result['bookmaker']
        
        return best


def main():
    """测试函数"""
    print("=" * 60)
    print("赔率分析工具测试")
    print("=" * 60)
    
    analyzer = OddsAnalyzer()
    
    # 测试赔率
    test_odds = {'home': 1.85, 'draw': 3.40, 'away': 4.20}
    
    print(f"\n分析赔率: {test_odds}")
    result = analyzer.analyze_odds(test_odds)
    
    print(f"\n隐含概率:")
    print(f"  主胜: {result['probabilities']['home']*100:.1f}%")
    print(f"  平局: {result['probabilities']['draw']*100:.1f}%")
    print(f"  客胜: {result['probabilities']['away']*100:.1f}%")
    
    print(f"\n庄家抽水: {result['juice_analysis']['juice_percentage']:.2f}%")
    print(f"  类型: {result['juice_analysis']['juice_type']}")
    print(f"  评价: {result['juice_analysis']['juice_interpretation']}")
    
    print(f"\n价值分析:")
    for outcome in ['home', 'draw', 'away']:
        va = result['value_analysis'][outcome]
        value_status = "✓ 有价值" if va['has_value'] else "✗ 无价值"
        print(f"  {outcome}: 赔率 {va['odds']}, 价值 {va['value_percentage']:.1f}% {value_status}")
    
    print(f"\n建议: {result['recommendation']}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
