#!/usr/bin/env python3
"""
北京单场专业分析Agent
功能：
1. 分析北京单场各玩法特征
2. 制定投注策略（上下盘/单双/胜平负）
3. 推荐串关方案（最高15关）
4. SP值分析
"""

import json
import os
import sys
from typing import Dict, List, Optional

# 项目根目录路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BASE_DIR = os.path.dirname(PROJECT_ROOT)

# 数据和规则路径
DATA_DIR = os.path.join(BASE_DIR, 'data', 'chinese_mapped')
RULES_DIR = PROJECT_ROOT

sys.path.insert(0, SCRIPT_DIR)

try:
    from skills.odds_analyzer import analyze_league_odds
    from skills.mxn_calculator import list_all_mxn_options, recommend_mxn
    SKILLS_AVAILABLE = True
except ImportError:
    SKILLS_AVAILABLE = False


def load_data() -> Dict:
    """加载北京单场数据"""
    filepath = os.path.join(DATA_DIR, '北京单场_chinese_data.json')
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_rules() -> Dict:
    """加载官方规则"""
    with open(os.path.join(RULES_DIR, 'official_rules.json'), 'r', encoding='utf-8') as f:
        return json.load(f)


class BeijingAgent:
    """北京单场分析Agent"""
    
    def __init__(self):
        self.name = "北京单场策略师"
        self.data = load_data()
        self.rules = load_rules()
    
    def get_overview(self) -> Dict:
        """获取北京单场概览"""
        return {
            "name": self.name,
            "lottery_type": "北京单场",
            "total_matches": len(self.data["matches"]),
            "total_leagues": len(self.data["leagues"]),
            "supported_plays": list(self.rules["北京单场"]["玩法"].keys()),
            "features": {
                "sp_odds": "浮动SP值，赛后公布",
                "max_parlay": "最多15关",
                "support_mxn": "支持M串N"
            }
        }
    
    def analyze_up_down(self) -> Dict:
        """
        分析上下盘特征
        
        北京单场规则：
        - 上盘：总进球 ≥ 3
        - 下盘：总进球 ≤ 2
        """
        matches = self.data["matches"]
        
        # 统计总进球
        total_goals = []
        for m in matches:
            if m["主队进球"] is not None and m["客队进球"] is not None:
                total = m["主队进球"] + m["客队进球"]
                total_goals.append(total)
        
        if not total_goals:
            return {"error": "没有有效数据"}
        
        # 计算上下盘比例
        up_count = sum(1 for g in total_goals if g >= 3)
        down_count = len(total_goals) - up_count
        
        # 按联赛分析
        league_stats = {}
        for m in matches:
            if m["主队进球"] is None:
                continue
            total = m["主队进球"] + m["客队进球"]
            league = m["联赛代码"]
            
            if league not in league_stats:
                league_stats[league] = {"up": 0, "down": 0, "total": 0}
            
            league_stats[league]["total"] += 1
            if total >= 3:
                league_stats[league]["up"] += 1
            else:
                league_stats[league]["down"] += 1
        
        # 找出上盘率最高的联赛
        best_up = []
        for league, stats in league_stats.items():
            if stats["total"] > 100:
                rate = stats["up"] / stats["total"] * 100
                best_up.append({
                    "league": league,
                    "up_rate": round(rate, 1),
                    "total_matches": stats["total"]
                })
        
        best_up.sort(key=lambda x: -x["up_rate"])
        
        return {
            "overall": {
                "total": len(total_goals),
                "up_rate": round(up_count / len(total_goals) * 100, 1),
                "down_rate": round(down_count / len(total_goals) * 100, 1)
            },
            "best_up_leagues": best_up[:5]
        }
    
    def analyze_odd_even(self) -> Dict:
        """
        分析单双特征
        
        北京单场规则：
        - 单：总进球为奇数
        - 双：总进球为偶数
        """
        matches = self.data["matches"]
        
        total_goals = []
        for m in matches:
            if m["主队进球"] is not None and m["客队进球"] is not None:
                total = m["主队进球"] + m["客队进球"]
                total_goals.append(total)
        
        odd_count = sum(1 for g in total_goals if g % 2 == 1)
        even_count = len(total_goals) - odd_count
        
        return {
            "total": len(total_goals),
            "odd_rate": round(odd_count / len(total_goals) * 100, 1),
            "even_rate": round(even_count / len(total_goals) * 100, 1),
            "note": "理论上单双概率各约50%"
        }
    
    def analyze_sfgg(self) -> Dict:
        """
        分析胜负过关特征
        
        胜负过关只有两个选项，类似平手盘
        """
        matches = self.data["matches"]
        
        # 统计胜负分布
        home_wins = sum(1 for m in matches if m.get("比赛结果") == "H")
        away_wins = sum(1 for m in matches if m.get("比赛结果") == "A")
        total = home_wins + away_wins
        
        if total == 0:
            return {"error": "没有有效数据"}
        
        return {
            "total": total,
            "home_win_rate": round(home_wins / total * 100, 1),
            "away_win_rate": round(away_wins / total * 100, 1),
            "suggestion": "胜负过关无平局，关注主客场因素"
        }
    
    def recommend_long_parlay(self, m: int, budget: float) -> List[Dict]:
        """
        推荐长串方案
        
        Args:
            m: 串关场数(最高15)
            budget: 预算
        
        Returns:
            推荐组合
        """
        if m > 15:
            return [{"error": "北京单场最高15关"}]
        
        return recommend_mxn(m, budget, "北京单场")
    
    def analyze_league_features(self, league_code: str) -> Dict:
        """分析特定联赛特征"""
        return analyze_league_odds(league_code, "北京单场")
    
    def generate_report(self) -> str:
        """生成完整分析报告"""
        overview = self.get_overview()
        up_down = self.analyze_up_down()
        odd_even = self.analyze_odd_even()
        sfgg = self.analyze_sfgg()
        
        report = f"""
{'='*60}
北京单场专业分析报告
{'='*60}

【概览】
- 支持联赛: {overview['total_leagues']} 个
- 历史比赛: {overview['total_matches']:,} 场
- 支持玩法: {', '.join(overview['supported_plays'])}

【上下盘分析】
- 总体上盘率: {up_down['overall']['up_rate']}%
- 总体下盘率: {up_down['overall']['down_rate']}%
- 上盘率最高联赛: {', '.join([f"{l['league']}({l['up_rate']}%)" for l in up_down['best_up_leagues'][:3]])}

【单双分析】
- 单数率: {odd_even['odd_rate']}%
- 双数率: {odd_even['even_rate']}%

【胜负过关分析】
- 主胜率: {sfgg['home_win_rate']}%
- 客胜率: {sfgg['away_win_rate']}%

【投注建议】
1. 上下盘：关注联赛特点，不同联赛上下盘分布差异大
2. 单双：无明显规律，接近50/50
3. 胜负过关：关注主客场因素
4. 串关：可使用M串N容错，最多15关
"""
        return report


def main():
    """测试函数"""
    agent = BeijingAgent()
    print(agent.generate_report())


if __name__ == "__main__":
    main()
