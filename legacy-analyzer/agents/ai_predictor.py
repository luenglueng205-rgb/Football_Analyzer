#!/usr/bin/env python3
"""
AI预测模块
功能：
1. 基于历史数据的统计预测
2. 赔率概率转换与价值分析
3. 机器学习预测接口（可扩展）
4. 球队状态评估

注意：足球预测准确率有限，此工具仅供参考
"""

import json
import os
import sys
from typing import Dict, List, Optional, Tuple
from collections import Counter, defaultdict
import math

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


class AIPredictor:
    """AI预测器"""
    
    def __init__(self, lottery_type: str = "竞彩足球"):
        self.lottery_type = lottery_type
        self.data = load_data(lottery_type)
        self.matches = self.data["matches"]
        self.model = None  # 可扩展：加载训练好的模型
        
        # 预计算联赛统计
        self.league_stats = self._calculate_league_stats()
    
    def _calculate_league_stats(self) -> Dict:
        """计算各联赛统计"""
        leagues = defaultdict(lambda: {
            "total": 0, "home_wins": 0, "draws": 0, "away_wins": 0,
            "total_goals": [], "home_goals": [], "away_goals": []
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
                home_goals = int(match.get('主队进球', 0))
                away_goals = int(match.get('客队进球', 0))
                leagues[league]["total_goals"].append(home_goals + away_goals)
                leagues[league]["home_goals"].append(home_goals)
                leagues[league]["away_goals"].append(away_goals)
            except:
                pass
        
        # 计算比率
        for league in leagues:
            total = leagues[league]["total"]
            if total > 0:
                leagues[league]["home_win_rate"] = leagues[league]["home_wins"] / total
                leagues[league]["draw_rate"] = leagues[league]["draws"] / total
                leagues[league]["away_win_rate"] = leagues[league]["away_wins"] / total
                
                goals = leagues[league]["total_goals"]
                leagues[league]["avg_total_goals"] = sum(goals) / len(goals) if goals else 2.5
                
                home_g = leagues[league]["home_goals"]
                leagues[league]["avg_home_goals"] = sum(home_g) / len(home_g) if home_g else 1.3
                
                away_g = leagues[league]["away_goals"]
                leagues[league]["avg_away_goals"] = sum(away_g) / len(away_g) if away_g else 1.2
        
        return leagues
    
    def predict_match(self, match: Dict) -> Optional[Dict]:
        """
        预测单场比赛
        
        Args:
            match: 比赛数据
        
        Returns:
            预测结果
        """
        league = match.get('联赛代码', 'UNKNOWN')
        stats = self.league_stats.get(league, {})
        
        home_odds = match.get('主队赔率', 0)
        draw_odds = match.get('平局赔率', 0)
        away_odds = match.get('客队赔率', 0)
        
        if not all([home_odds, draw_odds, away_odds]):
            return None
        
        # 赔率隐含概率
        implied_home = 100 / home_odds
        implied_draw = 100 / draw_odds
        implied_away = 100 / away_odds
        
        # 历史统计概率
        historical_home = stats.get("home_win_rate", 0.45) * 100
        historical_draw = stats.get("draw_rate", 0.25) * 100
        historical_away = stats.get("away_win_rate", 0.30) * 100
        
        # 融合预测（赔率60% + 历史40%）
        final_home = implied_home * 0.6 + historical_home * 0.4
        final_draw = implied_draw * 0.6 + historical_draw * 0.4
        final_away = implied_away * 0.6 + historical_away * 0.4
        
        # 归一化
        total = final_home + final_draw + final_away
        final_home = final_home / total * 100
        final_draw = final_draw / total * 100
        final_away = final_away / total * 100
        
        return {
            "home": round(final_home, 1),
            "draw": round(final_draw, 1),
            "away": round(final_away, 1),
            "confidence": self._calculate_confidence(stats),
            "prediction": "home" if final_home > final_away else ("away" if final_away > final_home else "draw")
        }
    
    def _calculate_confidence(self, stats: Dict) -> str:
        """计算预测置信度"""
        total = stats.get("total", 0)
        if total > 5000:
            return "high"
        elif total > 1000:
            return "medium"
        else:
            return "low"
    
    def predict_batch(self, matches: List[Dict]) -> List[Dict]:
        """批量预测"""
        results = []
        for match in matches:
            pred = self.predict_match(match)
            if pred:
                results.append({
                    "match": f"{match.get('主队', '')} vs {match.get('客队', '')}",
                    "league": match.get('联赛中文名', ''),
                    **pred
                })
        return results
    
    def analyze_team_form(self, team_name: str, league: str = None, recent_n: int = 10) -> Dict:
        """
        分析球队近期状态
        
        Args:
            team_name: 球队名称
            league: 联赛（可选）
            recent_n: 分析最近N场
        
        Returns:
            状态分析结果
        """
        team_matches = []
        for m in self.matches:
            if m.get('主队') == team_name or m.get('客队') == team_name:
                if league is None or m.get('联赛代码') == league:
                    team_matches.append(m)
        
        # 按时间排序（假设数据按时间排列）
        team_matches = team_matches[-recent_n:] if len(team_matches) > recent_n else team_matches
        
        wins = 0
        draws = 0
        losses = 0
        goals_scored = 0
        goals_conceded = 0
        
        for m in team_matches:
            result = get_match_result(m)
            
            if m.get('主队') == team_name:
                goals_scored += int(m.get('主队进球', 0))
                goals_conceded += int(m.get('客队进球', 0))
                if result == 'H':
                    wins += 1
                elif result == 'D':
                    draws += 1
                else:
                    losses += 1
            else:
                goals_scored += int(m.get('客队进球', 0))
                goals_conceded += int(m.get('主队进球', 0))
                if result == 'A':
                    wins += 1
                elif result == 'D':
                    draws += 1
                else:
                    losses += 1
        
        total = wins + draws + losses
        if total == 0:
            return {"error": "没有足够数据"}
        
        return {
            "team": team_name,
            "recent_matches": total,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "win_rate": round(wins / total * 100, 1),
            "goals_scored": goals_scored,
            "goals_conceded": goals_conceded,
            "avg_goals_scored": round(goals_scored / total, 2),
            "avg_goals_conceded": round(goals_conceded / total, 2),
            "form": "good" if wins / total > 0.5 else ("neutral" if wins / total > 0.3 else "poor")
        }


# ============================================================
# 统计预测函数
# ============================================================

def odds_to_probability(home_odds: float, draw_odds: float, away_odds: float) -> Dict:
    """赔率转概率（去除抽水后）"""
    if not all([home_odds, draw_odds, away_odds]):
        return {"error": "缺少赔率数据"}
    
    raw_home = 1 / home_odds
    raw_draw = 1 / draw_odds
    raw_away = 1 / away_odds
    
    total = raw_home + raw_draw + raw_away
    
    prob_home = raw_home / total
    prob_draw = raw_draw / total
    prob_away = raw_away / total
    
    return {
        "home": round(prob_home * 100, 1),
        "draw": round(prob_draw * 100, 1),
        "away": round(prob_away * 100, 1),
        "margin": round((total - 1) * 100, 1)
    }


def calculate_value_bet(odds: float, predicted_prob: float) -> Dict:
    """计算价值投注"""
    if odds <= 0:
        return {"error": "赔率无效"}
    
    fair_prob = 100 / odds
    value = predicted_prob - fair_prob
    expected_value = (predicted_prob / 100 * odds - 1) * 100
    
    return {
        "odds": odds,
        "fair_probability": round(fair_prob, 1),
        "predicted_probability": predicted_prob,
        "value": round(value, 1),
        "expected_value": round(expected_value, 2),
        "recommendation": "值得投注" if value > 5 else ("谨慎" if value > 0 else "避免")
    }


def predict_score_distribution(
    league_code: str,
    lottery_type: str = "竞彩足球"
) -> Dict:
    """预测比分分布"""
    data = load_data(lottery_type)
    league_matches = [m for m in data["matches"] if m["联赛代码"] == league_code]
    
    total_goals = 0
    for m in league_matches:
        if m.get('主队进球') is not None and m.get('客队进球') is not None:
            total_goals += int(m.get('主队进球', 0)) + int(m.get('客队进球', 0))
    
    avg_total = total_goals / len(league_matches) if league_matches else 2.5
    
    # 联赛常见比分
    scores = Counter()
    for m in league_matches[:5000]:
        try:
            score = f"{int(m.get('主队进球', 0))}-{int(m.get('客队进球', 0))}"
            scores[score] += 1
        except:
            pass
    
    total = sum(scores.values())
    probable_scores = {k: round(v / total, 3) for k, v in scores.most_common(10)}
    
    return {
        "league_avg_goals": round(avg_total, 2),
        "probable_scores": probable_scores
    }


# ============================================================
# 测试
# ============================================================

def main():
    """测试函数"""
    print("=" * 70)
    print("AI预测模块 - 测试")
    print("=" * 70)
    
    predictor = AIPredictor("竞彩足球")
    
    # 测试预测
    print("\n【单场预测测试】")
    test_match = predictor.matches[100]
    pred = predictor.predict_match(test_match)
    if pred:
        print(f"比赛: {test_match.get('主队')} vs {test_match.get('客队')}")
        print(f"预测: 主胜{pred['home']}%, 平局{pred['draw']}%, 客胜{pred['away']}%")
        print(f"推荐: {pred['prediction']} (置信度: {pred['confidence']})")
    
    # 测试批量预测
    print("\n【批量预测测试】")
    batch = predictor.matches[100:110]
    results = predictor.predict_batch(batch)
    for r in results[:3]:
        print(f"  {r['match']}: {r['prediction']} ({r['home']}/{r['draw']}/{r['away']})")
    
    # 测试球队状态
    print("\n【球队状态分析】")
    form = predictor.analyze_team_form("Bayern Munich")
    if "error" not in form:
        print(f"球队: {form['team']}")
        print(f"近期: {form['recent_matches']}场, 胜{form['wins']}平{form['draws']}负{form['losses']}")
        print(f"胜率: {form['win_rate']}%, 状态: {form['form']}")
    
    print("\n" + "=" * 70)
    print("✓ 测试完成!")


if __name__ == "__main__":
    main()
