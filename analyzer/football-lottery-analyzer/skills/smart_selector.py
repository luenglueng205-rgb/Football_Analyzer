#!/usr/bin/env python3
"""
智能选场推荐系统
功能：
1. 基于多维度筛选高价值比赛
2. AI预测结果整合
3. 个性化风险偏好推荐
4. 串关方案智能生成
"""

import json
import os
import sys
from typing import Dict, List, Optional, Tuple
from collections import Counter, defaultdict
import random

# 路径设置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BASE_DIR = os.path.dirname(PROJECT_ROOT)
DATA_DIR = os.path.join(BASE_DIR, 'data', 'chinese_mapped')

sys.path.insert(0, SCRIPT_DIR)
try:
    from odds_analyzer import (
        load_data as load_odds_data,
        calculate_theoretical_probability,
        calculate_bookmaker_margin,
        find_best_value_combinations
    )
    from ai_predictor import AIPredictor
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False


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


# ============================================================
# 智能选场核心算法
# ============================================================

class SmartSelector:
    """智能选场器"""
    
    def __init__(self, lottery_type: str = "竞彩足球"):
        self.lottery_type = lottery_type
        self.data = load_data(lottery_type)
        self.matches = self.data["matches"]
        
        # 预计算联赛统计数据
        self.league_stats = self._calculate_league_stats()
        
        # 初始化AI预测器
        if AI_AVAILABLE:
            self.ai_predictor = AIPredictor()
        else:
            self.ai_predictor = None
    
    def _calculate_league_stats(self) -> Dict:
        """计算各联赛统计"""
        leagues = defaultdict(lambda: {
            "home_wins": 0, "draws": 0, "away_wins": 0,
            "total": 0, "total_goals": []
        })
        
        for match in self.matches:
            if not match.get('主队赔率'):
                continue
            
            league = match.get('联赛代码', 'UNKNOWN')
            leagues[league]["total"] += 1
            
            result = get_match_result(match)
            if result == 'H':
                leagues[league]["home_wins"] += 1
            elif result == 'D':
                leagues[league]["draws"] += 1
            else:
                leagues[league]["away_wins"] += 1
            
            try:
                goals = int(match.get('主队进球', 0)) + int(match.get('客队进球', 0))
                leagues[league]["total_goals"].append(goals)
            except:
                pass
        
        # 计算比率
        for league in leagues:
            total = leagues[league]["total"]
            if total > 0:
                leagues[league]["home_win_rate"] = leagues[league]["home_wins"] / total
                leagues[league]["draw_rate"] = leagues[league]["draws"] / total
                leagues[league]["away_win_rate"] = leagues[league]["away_wins"] / total
                leagues[league]["avg_goals"] = sum(leagues[league]["total_goals"]) / len(leagues[league]["total_goals"])
        
        return leagues
    
    def score_match(self, match: Dict, risk_tolerance: str = "medium") -> Dict:
        """
        给比赛打分
        
        Args:
            match: 比赛数据
            risk_tolerance: 风险承受度 (low/medium/high)
        
        Returns:
            评分结果
        """
        league = match.get('联赛代码', 'UNKNOWN')
        stats = self.league_stats.get(league, {})
        
        # 基础数据
        home_odds = match.get('主队赔率', 0)
        draw_odds = match.get('平局赔率', 0)
        away_odds = match.get('客队赔率', 0)
        
        if not all([home_odds, draw_odds, away_odds]):
            return {"score": 0, "reason": "缺少赔率数据"}
        
        scores = {}
        reasons = []
        
        # 1. 理论概率分析
        theoretical_home = calculate_theoretical_probability(home_odds)
        theoretical_draw = calculate_theoretical_probability(draw_odds)
        theoretical_away = calculate_theoretical_probability(away_odds)
        
        # 2. 实际概率（基于历史）
        historical_home = stats.get("home_win_rate", 0.45) * 100
        historical_draw = stats.get("draw_rate", 0.25) * 100
        historical_away = stats.get("away_win_rate", 0.30) * 100
        
        # 3. 计算各选项价值
        home_value = historical_home - theoretical_home
        draw_value = historical_draw - theoretical_draw
        away_value = historical_away - theoretical_away
        
        # 4. 根据风险偏好选择
        if risk_tolerance == "low":
            # 低风险：偏好低赔主胜
            if home_odds < 1.5:
                scores["home"] = 80 + home_value * 5
                reasons.append(f"低赔主胜({home_odds})，历史胜率{historical_home:.1f}%")
            elif home_odds < 1.8:
                scores["home"] = 60 + home_value * 3
                reasons.append(f"中低赔主胜({home_odds})")
            
            scores["draw"] = 30 + draw_value * 2
            scores["away"] = 20 + away_value * 2
            
        elif risk_tolerance == "medium":
            # 中等风险：平衡选择
            scores["home"] = 60 + home_value * 4
            scores["draw"] = 40 + draw_value * 3
            scores["away"] = 30 + away_value * 3
            
            if home_value > 5:
                reasons.append(f"主胜价值{home_value:.1f}%")
            if draw_value > 5:
                reasons.append(f"平局价值{draw_value:.1f}%")
            if away_value > 5:
                reasons.append(f"客胜价值{away_value:.1f}%")
                
        else:  # high
            # 高风险：偏好高价值
            scores["home"] = 40 + home_value * 5
            scores["draw"] = 50 + draw_value * 4
            scores["away"] = 40 + away_value * 4
            
            # 关注价值最高的选项
            max_value = max(home_value, draw_value, away_value)
            if max_value > 8:
                if max_value == home_value:
                    reasons.append(f"高价值主胜(+{home_value:.1f}%)")
                elif max_value == draw_value:
                    reasons.append(f"高价值平局(+{draw_value:.1f}%)")
                else:
                    reasons.append(f"高价值客胜(+{away_value:.1f}%)")
        
        # 5. AI预测增强（如果有）
        if self.ai_predictor and self.ai_predictor.model:
            ai_pred = self.ai_predictor.predict_match(match)
            if ai_pred:
                # 融合AI预测
                for key in scores:
                    ai_key = {"home": "home", "draw": "draw", "away": "away"}[key]
                    if ai_pred.get(ai_key):
                        scores[key] = scores[key] * 0.7 + ai_pred[ai_key] * 30 * 0.3
        
        # 6. 计算综合评分
        best_option = max(scores, key=scores.get)
        best_score = scores.get(best_option, 0)
        
        # 获取最佳赔率
        odds_map = {"home": "主队赔率", "draw": "平局赔率", "away": "客队赔率"}
        best_odds = match.get(odds_map.get(best_option, '主队赔率'), 0)
        
        return {
            "match": f"{match.get('主队', '')} vs {match.get('客队', '')}",
            "league": match.get('联赛中文名', league),
            "date": match.get('比赛日期', ''),
            "best_option": best_option,
            "best_odds": best_odds,
            "score": round(best_score, 1),
            "home_odds": home_odds,
            "draw_odds": draw_odds,
            "away_odds": away_odds,
            "home_value": round(home_value, 1),
            "draw_value": round(draw_value, 1),
            "away_value": round(away_value, 1),
            "historical_rates": {
                "home": round(historical_home, 1),
                "draw": round(historical_draw, 1),
                "away": round(historical_away, 1)
            },
            "reasons": reasons
        }
    
    def select_matches(
        self,
        min_score: float = 50,
        max_matches: int = 10,
        risk_tolerance: str = "medium"
    ) -> List[Dict]:
        """
        筛选高价值比赛
        
        Args:
            min_score: 最低评分
            max_matches: 最大返回数量
            risk_tolerance: 风险偏好
        
        Returns:
            筛选结果列表
        """
        scored_matches = []
        
        for match in self.matches:
            if not match.get('主队赔率'):
                continue
            
            score_result = self.score_match(match, risk_tolerance)
            
            if score_result["score"] >= min_score:
                scored_matches.append(score_result)
        
        # 按评分排序
        scored_matches.sort(key=lambda x: -x["score"])
        
        return scored_matches[:max_matches]
    
    def generate_parlay_recommendation(
        self,
        n_games: int = 3,
        risk_tolerance: str = "medium",
        budget: float = 100
    ) -> Dict:
        """
        生成串关推荐
        
        Args:
            n_games: 选择比赛数
            risk_tolerance: 风险偏好
            budget: 预算金额
        
        Returns:
            串关推荐
        """
        selected = self.select_matches(
            min_score=40 if risk_tolerance == "low" else 50,
            max_matches=n_games * 2,  # 多选一些备选
            risk_tolerance=risk_tolerance
        )
        
        # 选择评分最高的n场
        top_matches = selected[:n_games]
        
        if len(top_matches) < n_games:
            return {"error": f"可用比赛不足{n_games}场"}
        
        # 计算串关赔率
        total_odds = 1
        for match in top_matches:
            odds = match["best_odds"]
            if odds > 0:
                total_odds *= odds
        
        # 计算预期收益
        expected_return = total_odds * budget - budget
        
        # M串N计算
        mxn_result = self._calculate_mxn(n_games, budget)
        
        return {
            "lottery_type": self.lottery_type,
            "risk_tolerance": risk_tolerance,
            "parlay_type": f"{n_games}串1",
            "selected_games": top_matches,
            "total_odds": round(total_odds, 2),
            "budget": budget,
            "potential_return": round(expected_return, 2),
            "mxn_options": mxn_result,
            "recommendation": self._get_recommendation_text(risk_tolerance, total_odds)
        }
    
    def _calculate_mxn(self, m: int, budget: float) -> List[Dict]:
        """计算M串N选项"""
        options = []
        
        # 基础2串1到M串1
        options.append({
            "type": f"{m}串1",
            "bets": 1,
            "min_bet": budget,
            "description": "基础串关"
        })
        
        # 3串3, 3串4
        if m == 3:
            options.append({
                "type": "3串3",
                "bets": 3,
                "min_bet": budget / 3,
                "description": "3单选拆3注2串1"
            })
            options.append({
                "type": "3串4",
                "bets": 4,
                "min_bet": budget / 4,
                "description": "含容错"
            })
        
        # 4串5, 4串6, 4串11
        if m == 4:
            options.append({
                "type": "4串5",
                "bets": 5,
                "min_bet": budget / 5,
                "description": "4单选+1注4串1"
            })
            options.append({
                "type": "4串6",
                "bets": 6,
                "min_bet": budget / 6,
                "description": "6注2串1"
            })
            options.append({
                "type": "4串11",
                "bets": 11,
                "min_bet": budget / 11,
                "description": "完整容错"
            })
        
        # 5串16, 5串26
        if m == 5:
            options.append({
                "type": "5串16",
                "bets": 16,
                "min_bet": budget / 16,
                "description": "5串含3串4串5"
            })
            options.append({
                "type": "5串26",
                "bets": 26,
                "min_bet": budget / 26,
                "description": "完整容错"
            })
        
        return options
    
    def _get_recommendation_text(self, risk_tolerance: str, total_odds: float) -> str:
        """生成推荐说明"""
        if risk_tolerance == "low":
            if total_odds < 3:
                return "保守策略，低赔率高稳定性"
            else:
                return "稳健策略，平衡收益与风险"
        elif risk_tolerance == "medium":
            if total_odds < 5:
                return "平衡策略，追求稳定收益"
            else:
                return "进取策略，高赔率高回报"
        else:
            return "激进策略，追求高回报"


# ============================================================
# 风险偏好推荐
# ============================================================

def recommend_by_risk_profile(lottery_type: str = "竞彩足球", 
                              risk_level: str = "medium") -> Dict:
    """
    根据风险偏好推荐
    
    Args:
        lottery_type: 彩票类型
        risk_level: 风险等级 (low/medium/high)
    
    Returns:
        推荐结果
    """
    selector = SmartSelector(lottery_type)
    
    if risk_level == "low":
        # 低风险：选择评分最高的低赔比赛
        games = selector.select_matches(min_score=60, max_matches=5, risk_tolerance="low")
        parlay = selector.generate_parlay_recommendation(2, "low", 100)
        
        return {
            "risk_level": "低风险",
            "strategy": "稳胆策略",
            "description": "选择赔率1.3-1.5的主队，追求稳定胜率",
            "selected_games": games,
            "parlay_recommendation": parlay,
            "expected_roi": "~0-5%",
            "suitable_for": "资金充裕、追求稳定的玩家"
        }
    
    elif risk_level == "medium":
        # 中等风险
        games = selector.select_matches(min_score=50, max_matches=5, risk_tolerance="medium")
        parlay = selector.generate_parlay_recommendation(3, "medium", 100)
        
        return {
            "risk_level": "中等风险",
            "strategy": "平衡策略",
            "description": "选择评分较高的比赛，平衡收益与风险",
            "selected_games": games,
            "parlay_recommendation": parlay,
            "expected_roi": "-5% to +10%",
            "suitable_for": "有一定投注经验的玩家"
        }
    
    else:  # high
        # 高风险
        games = selector.select_matches(min_score=40, max_matches=5, risk_tolerance="high")
        parlay = selector.generate_parlay_recommendation(4, "high", 50)
        
        return {
            "risk_level": "高风险",
            "strategy": "价值策略",
            "description": "追求高价值比赛，可能有高回报但风险也大",
            "selected_games": games,
            "parlay_recommendation": parlay,
            "expected_roi": "波动较大",
            "suitable_for": "追求刺激、高风险偏好的玩家"
        }


# ============================================================
# 测试
# ============================================================

def main():
    """测试函数"""
    print("=" * 70)
    print("智能选场推荐系统 - 测试")
    print("=" * 70)
    
    selector = SmartSelector("竞彩足球")
    
    # 测试评分
    print("\n【测试比赛评分】")
    test_match = selector.matches[100]
    score = selector.score_match(test_match, "medium")
    print(f"比赛: {score['match']}")
    print(f"最佳选项: {score['best_option']} @ {score['best_odds']}")
    print(f"评分: {score['score']}")
    print(f"价值: 主胜{score['home_value']:+.1f}%, 平局{score['draw_value']:+.1f}%, 客胜{score['away_value']:+.1f}%")
    
    # 测试选场
    print("\n【测试智能选场】")
    selected = selector.select_matches(min_score=55, max_matches=5, risk_tolerance="medium")
    print(f"筛选到 {len(selected)} 场高价值比赛:")
    for i, s in enumerate(selected[:5], 1):
        print(f"  {i}. {s['match']} ({s['league']}) 评分:{s['score']} 选项:{s['best_option']}")
    
    # 测试串关推荐
    print("\n【测试串关推荐】")
    parlay = selector.generate_parlay_recommendation(3, "medium", 100)
    print(f"推荐: {parlay['parlay_type']}")
    print(f"总赔率: {parlay['total_odds']}")
    print(f"预期收益: {parlay['potential_return']}")
    
    # 测试风险偏好
    print("\n【测试风险偏好推荐】")
    for risk in ["low", "medium", "high"]:
        rec = recommend_by_risk_profile("竞彩足球", risk)
        print(f"\n{risk.upper()}风险:")
        print(f"  策略: {rec['strategy']}")
        print(f"  描述: {rec['description']}")
        print(f"  预期ROI: {rec['expected_roi']}")
    
    print("\n" + "=" * 70)
    print("✓ 测试完成!")


if __name__ == "__main__":
    main()
