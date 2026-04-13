#!/usr/bin/env python3
"""
传统足彩专业分析Agent
功能：
1. 分析传统足彩各玩法特征
2. 制定14场/任9/6场半全场/4场进球策略
3. 胆拖投注计算
4. 复式优化
"""

import json
import os
import sys
import math
from typing import Dict, List, Optional, Tuple

# 项目根目录路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BASE_DIR = os.path.dirname(PROJECT_ROOT)

# 数据和规则路径
DATA_DIR = os.path.join(BASE_DIR, 'data', 'chinese_mapped')
RULES_DIR = PROJECT_ROOT

sys.path.insert(0, SCRIPT_DIR)

try:
    from skills.odds_analyzer import find_best_value_leagues
    from skills.prize_calculator import calculate_dantuo_bet, calculate_traditional_prize
    SKILLS_AVAILABLE = True
except ImportError:
    SKILLS_AVAILABLE = False


def load_data() -> Dict:
    """加载传统足彩数据"""
    filepath = os.path.join(DATA_DIR, '传统足彩_chinese_data.json')
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_rules() -> Dict:
    """加载官方规则"""
    with open(os.path.join(RULES_DIR, 'official_rules.json'), 'r', encoding='utf-8') as f:
        return json.load(f)


class TraditionalAgent:
    """传统足彩分析Agent"""
    
    def __init__(self):
        self.name = "传统足彩策略师"
        self.data = load_data()
        self.rules = load_rules()
    
    def get_overview(self) -> Dict:
        """获取传统足彩概览"""
        return {
            "name": self.name,
            "lottery_type": "传统足彩",
            "total_matches": len(self.data["matches"]),
            "total_leagues": len(self.data["leagues"]),
            "supported_plays": list(self.rules["传统足彩"]["玩法"].keys()),
            "features": {
                "prize_pool": "奖池浮动，64%返奖率",
                "max_prize": "单注封顶500万",
                "bet_types": "支持单式/复式/胆拖"
            }
        }
    
    def analyze_14_match(self) -> Dict:
        """
        分析14场胜负特征
        """
        matches = self.data["matches"]
        
        # 统计各结果分布
        results = {"H": 0, "D": 0, "A": 0}
        for m in matches:
            if m.get("比赛结果") in results:
                results[m["比赛结果"]] += 1
        
        total = sum(results.values())
        
        # 按联赛统计
        league_stats = {}
        for m in matches:
            league = m["联赛代码"]
            if league not in league_stats:
                league_stats[league] = {"H": 0, "D": 0, "A": 0, "total": 0}
            
            if m.get("比赛结果") in league_stats[league]:
                league_stats[league][m.get("比赛结果")] += 1
                league_stats[league]["total"] += 1
        
        # 找出主胜率最低的联赛（冷门联赛）
        cold_leagues = []
        for league, stats in league_stats.items():
            if stats["total"] > 50:
                home_rate = stats["H"] / stats["total"] * 100
                cold_leagues.append({
                    "league": league,
                    "home_rate": round(home_rate, 1),
                    "total": stats["total"]
                })
        
        cold_leagues.sort(key=lambda x: x["home_rate"])
        
        return {
            "overall": {
                "total": total,
                "home_win_rate": round(results["H"] / total * 100, 1),
                "draw_rate": round(results["D"] / total * 100, 1),
                "away_win_rate": round(results["A"] / total * 100, 1)
            },
            "cold_leagues": cold_leagues[:5],
            "note": "传统足彩需要14场全对才能中一等奖"
        }
    
    def analyze_rx9(self) -> Dict:
        """
        分析任选9场策略
        """
        # 14场分析作为任选9场的基础
        analysis_14 = self.analyze_14_match()
        
        return {
            "strategy": "任选9场投注策略",
            "description": "从14场中选择9场有把握的比赛",
            "dan_count_range": "建议选择5-7个胆",
            "tuo_count_range": "对应选择2-4个拖",
            "recommended": {
                "dan": 6,
                "tuo_options": "每拖选2个结果",
                "total_bets": math.comb(6, 6) * (2 ** 4),
                "cost": math.comb(6, 6) * (2 ** 4) * 2
            },
            "tips": [
                "选择历史冷门较少的联赛做胆",
                "拖的选择应覆盖不确定性",
                "考虑使用双选降低风险"
            ]
        }
    
    def analyze_6bqc(self) -> Dict:
        """
        分析6场半全场策略
        半全场需要预测12个结果（上半场+全场）
        """
        matches = self.data["matches"]
        
        # 统计半全场结果分布
        half_full_results = {}
        for m in matches:
            # 简化处理：使用全场结果模拟
            if m.get("比赛结果") in ["H", "D", "A"]:
                result = m["比赛结果"]
                half_full_results[result] = half_full_results.get(result, 0) + 1
        
        return {
            "strategy": "6场半全场投注策略",
            "description": "预测6场比赛的半场和全场共12个结果",
            "difficulty": "极高",
            "tips": [
                "优先选择半场结果确定的比赛",
                "关注强队上半场领先的情况",
                "组合使用: 胜胜、胜平、平胜等"
            ],
            "estimated_odds": {
                "6场全对": "极高",
                "5场对": "高",
                "4场对": "中"
            }
        }
    
    def analyze_4jqc(self) -> Dict:
        """
        分析4场进球策略
        预测4场比赛的主客队进球数（共8个结果）
        """
        matches = self.data["matches"]
        
        # 统计进球分布
        home_goals = []
        away_goals = []
        for m in matches:
            if m["主队进球"] is not None:
                home_goals.append(m["主队进球"])
            if m["客队进球"] is not None:
                away_goals.append(m["客队进球"])
        
        def stats(goals):
            if not goals:
                return {}
            from collections import Counter
            c = Counter(goals)
            total = len(goals)
            return {k: round(v / total * 100, 1) for k, v in c.items()}
        
        return {
            "strategy": "4场进球投注策略",
            "description": "预测4场比赛主客队进球数，共8个结果",
            "difficulty": "极高",
            "home_goal_distribution": stats(home_goals),
            "away_goal_distribution": stats(away_goals),
            "tips": [
                "关注进攻型球队的进球分布",
                "主场球队通常进球更多",
                "0-2球是最常见的进球区间"
            ]
        }
    
    def calculate_dantuo_plan(
        self,
        dan_matches: List[str],
        tuo_matches: List[Tuple[str, List[str]]]
    ) -> Dict:
        """
        计算胆拖投注方案
        
        Args:
            dan_matches: 胆的比赛列表
            tuo_matches: 拖的比赛及选项列表 [(联赛, [选项])]
        
        Returns:
            投注方案
        """
        dan_count = len(dan_matches)
        tuo_count = len(tuo_matches)
        tuo_options = [len(opts) for _, opts in tuo_matches]
        
        plan = calculate_dantuo_bet(
            dan_count=dan_count,
            dan_options=1,  # 胆通常只选1个
            tuo_count=tuo_count,
            tuo_options=tuo_options
        )
        
        return {
            "dan_matches": dan_matches,
            "tuo_matches": tuo_matches,
            "total_bets": plan["total_bets"],
            "total_cost": plan["total_cost"],
            "note": f"胆{dan_count}场 + 拖{tuo_count}场(多选)"
        }
    
    def recommend_leagues_for_14(self) -> List[Dict]:
        """
        推荐适合14场的联赛
        稳定性高的联赛适合做胆，冷门多的适合做拖
        """
        leagues = find_best_value_leagues("传统足彩", 10)
        
        stable = []
        cold = []
        
        for league in leagues:
            if league["value"] > 0:
                stable.append(league)
            else:
                cold.append(league)
        
        return {
            "recommended_dan_leagues": stable[:5],
            "recommended_tuo_leagues": cold[:5],
            "note": "稳定联赛做胆，冷门联赛做拖"
        }
    
    def calculate_potential_prize(
        self,
        total_sales: float,
        prize_pool: float = 0
    ) -> Dict:
        """
        计算潜在奖金
        
        Args:
            total_sales: 当期销售额
            prize_pool: 奖池余额
        """
        return calculate_traditional_prize(
            total_sales=total_sales,
            prize_pool_balance=prize_pool,
            winner_count=1
        )
    
    def generate_report(self) -> str:
        """生成完整分析报告"""
        overview = self.get_overview()
        analysis_14 = self.analyze_14_match()
        rx9 = self.analyze_rx9()
        leagues_rec = self.recommend_leagues_for_14()
        
        report = f"""
{'='*60}
传统足彩专业分析报告
{'='*60}

【概览】
- 支持联赛: {overview['total_leagues']} 个
- 历史比赛: {overview['total_matches']:,} 场
- 支持玩法: {', '.join(overview['supported_plays'])}

【14场胜负分析】
- 主胜率: {analysis_14['overall']['home_win_rate']}%
- 平局率: {analysis_14['overall']['draw_rate']}%
- 客胜率: {analysis_14['overall']['away_win_rate']}%

【任选9场策略】
- 建议胆数: {rx9['recommended']['dan']}个
- 建议拖数: {rx9['recommended']['total_bets'] // rx9['recommended']['cost'] // 2}个
- 预计成本: {rx9['recommended']['cost']}元

【联赛推荐】
适合做胆的联赛(稳定):
{chr(10).join([f"  • {l['league_name']}: 主胜率{l['home_win_rate']:.1f}%" for l in leagues_rec['recommended_dan_leagues'][:3]])}

适合做拖的联赛(冷门):
{chr(10).join([f"  • {l['league_name']}: 价值{l['value']:.1f}%" for l in leagues_rec['recommended_tuo_leagues'][:3]])}

【投注建议】
1. 14场：使用胆拖策略降低成本
2. 任9：选择6-7个稳定胆 + 2-3个拖
3. 6场半全场：优先选择强队
4. 4场进球：关注进球分布规律
"""
        return report


def main():
    """测试函数"""
    agent = TraditionalAgent()
    print(agent.generate_report())


if __name__ == "__main__":
    main()
