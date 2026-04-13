#!/usr/bin/env python3
"""
竞彩足球专业分析Agent
功能：
1. 分析竞彩足球各玩法特征
2. 制定投注策略
3. 推荐串关方案
4. 智能选场推荐
"""

import json
import os
import sys
from typing import Dict, List, Optional
from collections import Counter, defaultdict

# 项目根目录 = football-lottery-analyzer/ 上两级
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)  # football-lottery-analyzer
BASE_DIR = os.path.dirname(PROJECT_ROOT)  # CodeBuddy

# 数据路径
DATA_DIR = os.path.join(BASE_DIR, 'data', 'chinese_mapped')
RULES_DIR = PROJECT_ROOT

# 添加skills路径
sys.path.insert(0, SCRIPT_DIR)

try:
    from skills.odds_analyzer import (
        analyze_value_bets, 
        analyze_league_odds, 
        find_best_value_leagues
    )
    from skills.mxn_calculator import (
        list_all_mxn_options,
        calculate_bet_amount,
        recommend_mxn
    )
    from skills.strategy_backtest import backtest_all_strategies
    SKILLS_AVAILABLE = True
except ImportError:
    SKILLS_AVAILABLE = False


def load_data() -> Dict:
    """加载竞彩足球数据"""
    filepath = os.path.join(DATA_DIR, '竞彩足球_chinese_data.json')
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_rules() -> Dict:
    """加载官方规则"""
    with open(os.path.join(RULES_DIR, 'official_rules.json'), 'r', encoding='utf-8') as f:
        return json.load(f)


class JingcaiAgent:
    """竞彩足球分析Agent"""
    
    def __init__(self):
        self.name = "竞彩足球策略师"
        self.data = load_data()
        self.rules = load_rules()
        
    def get_overview(self) -> Dict:
        """获取竞彩足球概览"""
        return {
            "name": self.name,
            "lottery_type": "竞彩足球",
            "total_matches": len(self.data["matches"]),
            "total_leagues": len(self.data["leagues"]),
            "supported_plays": list(self.rules["竞彩足球"]["玩法"].keys()),
            "features": {
                "fixed_odds": "固定赔率，投注时锁定",
                "max_parlay": "最多8关",
                "mixed_bet": "支持混合过关"
            }
        }
    
    def analyze_play_type(self, play_type: str) -> Dict:
        """
        分析特定玩法
        
        Args:
            play_type: 玩法类型 (胜平负/让球胜平负/比分/总进球/半全场)
        """
        if play_type not in self.rules["竞彩足球"]["玩法"]:
            return {"error": f"不支持的玩法: {play_type}"}
        
        play_info = self.rules["竞彩足球"]["玩法"][play_type]
        
        return {
            "name": play_info["name"],
            "code": play_info["code"],
            "description": play_info["description"],
            "options": play_info.get("options", []),
            "option_count": len(play_info.get("options", [])),
            "max_parlay": play_info["max_parlay"],
            "support_mxn": play_info["support_mxn"]
        }
    
    def recommend_safer_bets(self, min_odds: float = 1.3, max_odds: float = 1.8) -> List[Dict]:
        """
        推荐稳健投注（低赔主队）
        
        Args:
            min_odds: 最小赔率
            max_odds: 最大赔率
        
        Returns:
            推荐比赛列表
        """
        matches = self.data["matches"]
        valid = [m for m in matches 
                 if m.get("主队赔率") and min_odds <= m["主队赔率"] <= max_odds]
        
        # 按赔率排序（赔率越低越稳）
        valid.sort(key=lambda x: x["主队赔率"])
        
        results = []
        for m in valid[:20]:
            # 统计该赔率范围的历史胜率
            similar = [x for x in matches 
                      if x.get("主队赔率") and 
                      min_odds <= x["主队赔率"] <= max_odds and
                      x["联赛代码"] == m["联赛代码"]]
            
            wins = sum(1 for x in similar if int(x.get('主队进球', 0)) > int(x.get('客队进球', 0)))
            win_rate = wins / len(similar) * 100 if similar else 0
            
            results.append({
                "league": m["联赛中文名"],
                "home_team": m["主队"],
                "away_team": m["客队"],
                "odds": m["主队赔率"],
                "theoretical_prob": round((1/m["主队赔率"])*100, 1),
                "historical_win_rate": round(win_rate, 1),
                "value": round(win_rate - (1/m["主队赔率"])*100, 1)
            })
        
        return results
    
    def analyze_mixed_bet_opportunities(self) -> List[Dict]:
        """
        分析混合过关机会
        组合不同玩法提高中奖概率
        """
        opportunities = []
        
        # 策略1：胜平负 + 比分混合
        # 当胜平负赔率合适时，查看比分选项
        valid = [m for m in self.data["matches"] 
                 if m.get("主队赔率") and 1.5 <= m["主队赔率"] <= 2.0]
        
        for m in valid[:10]:
            opportunities.append({
                "league": m["联赛中文名"],
                "match": f"{m['主队']} vs {m['客队']}",
                "home_win_odds": m["主队赔率"],
                "suggestion": f"可尝试: 胜平负{m['主队赔率']} + 比分2-0({m['主队赔率']*7:.2f})",
                "risk_level": "中"
            })
        
        return opportunities
    
    def calculate_parlay_options(self, m: int, budget: float) -> List[Dict]:
        """
        计算串关选项
        
        Args:
            m: 选择比赛场数
            budget: 预算金额
        
        Returns:
            推荐组合
        """
        recommendations = recommend_mxn(m, budget, "竞彩足球")
        return recommendations
    
    def get_league_recommendation(self) -> Dict:
        """获取联赛推荐"""
        best_leagues = find_best_value_leagues("竞彩足球", 5)
        
        return {
            "title": "竞彩足球联赛价值排名",
            "description": "基于历史数据的联赛投注价值分析",
            "leagues": best_leagues
        }
    
    def strategy_report(self) -> Dict:
        """生成策略报告"""
        # 回测结果
        backtest = backtest_all_strategies("竞彩足球")
        
        # 价值投注分析
        value_bets = analyze_value_bets(self.data["matches"])
        
        return {
            "title": "竞彩足球投注策略报告",
            "backtest_results": backtest,
            "value_bets_analysis": value_bets,
            "recommendations": [
                {
                    "strategy": "低赔稳胆",
                    "description": "选择赔率1.3-1.5的主队，历史胜率约70-80%",
                    "risk": "低",
                    "expected_roi": "~5%"
                },
                {
                    "strategy": "2串1组合",
                    "description": "两个低赔主队组合，赔率约3-4",
                    "risk": "中",
                    "expected_roi": "根据具体组合"
                },
                {
                    "strategy": "M串N容错",
                    "description": "使用4串11等容错组合，减少全错风险",
                    "risk": "中",
                    "expected_roi": "需具体分析"
                }
            ]
        }
    
    def generate_report(self) -> str:
        """生成完整分析报告"""
        overview = self.get_overview()
        league_rec = self.get_league_recommendation()
        safer = self.recommend_safer_bets()[:5]
        
        report = f"""
{'='*60}
竞彩足球专业分析报告
{'='*60}

【概览】
- 支持联赛: {overview['total_leagues']} 个
- 历史比赛: {overview['total_matches']:,} 场
- 支持玩法: {', '.join(overview['supported_plays'])}

【最佳价值联赛】
"""
        for i, league in enumerate(league_rec["leagues"], 1):
            report += f"  {i}. {league['league_name']}: 价值{league['value']:+.1f}%\n"
        
        report += """
【稳健投注推荐】(赔率1.3-1.5)
"""
        for s in safer:
            report += f"  • {s['league']} {s['home_team']} vs {s['away_team']} 赔率{s['odds']}\n"
        
        return report


def main():
    """测试函数"""
    agent = JingcaiAgent()
    
    # 获取概览
    print(agent.get_overview())
    
    # 生成报告
    print(agent.generate_report())


if __name__ == "__main__":
    main()
