# -*- coding: utf-8 -*-
"""
跨玩法协同策略模块 v2.0
功能：
1. 竞彩足球与北京单场协同分析
2. 跨玩法投注策略
3. 赔率对比与套利机会
4. 综合推荐引擎
"""

import json
import os
import sys
import math
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

# 路径设置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BASE_DIR = os.path.dirname(PROJECT_ROOT)
DATA_DIR = os.path.join(BASE_DIR, 'data', 'chinese_mapped')
RULES_DIR = PROJECT_ROOT


def load_all_data() -> Dict:
    """加载所有数据"""
    data = {}
    
    # 竞彩足球
    jingcai_path = os.path.join(DATA_DIR, '竞彩足球_chinese_data.json')
    if os.path.exists(jingcai_path):
        with open(jingcai_path, 'r', encoding='utf-8') as f:
            data["竞彩足球"] = json.load(f)
    
    # 北京单场
    beijing_path = os.path.join(DATA_DIR, '北京单场_chinese_data.json')
    if os.path.exists(beijing_path):
        with open(beijing_path, 'r', encoding='utf-8') as f:
            data["北京单场"] = json.load(f)
    
    # 传统足彩
    traditional_path = os.path.join(DATA_DIR, '传统足彩_chinese_data.json')
    if os.path.exists(traditional_path):
        with open(traditional_path, 'r', encoding='utf-8') as f:
            data["传统足彩"] = json.load(f)
    
    return data


def load_rules() -> Dict:
    """加载官方规则"""
    with open(os.path.join(RULES_DIR, 'official_rules.json'), 'r', encoding='utf-8') as f:
        return json.load(f)


class CrossPlayAnalyzer:
    """跨玩法协同分析器"""
    
    def __init__(self, data: Dict):
        self.data = data
        self.rules = load_rules()
    
    def compare_odds_between_lotteries(
        self,
        home_team: str,
        away_team: str,
        league: str = None
    ) -> Dict:
        """
        对比竞彩足球和北京单场的赔率差异
        
        Args:
            home_team: 主队
            away_team: 客队
            league: 联赛
        """
        jingcai_matches = self.data.get("竞彩足球", {}).get("matches", [])
        beijing_matches = self.data.get("北京单场", {}).get("matches", [])
        
        # 查找比赛
        jingcai_match = self._find_match(jingcai_matches, home_team, away_team)
        beijing_match = self._find_match(beijing_matches, home_team, away_team)
        
        comparison = {
            "match": f"{home_team} vs {away_team}",
            "jingcai_available": jingcai_match is not None,
            "beijing_available": beijing_match is not None
        }
        
        if jingcai_match:
            comparison["jingcai_odds"] = {
                "home": jingcai_match.get("主队赔率"),
                "draw": jingcai_match.get("平局赔率"),
                "away": jingcai_match.get("客队赔率"),
                "league": jingcai_match.get("联赛中文名")
            }
        
        if beijing_match:
            comparison["beijing_odds"] = {
                "home": beijing_match.get("主队赔率"),
                "draw": beijing_match.get("平局赔率"),
                "away": beijing_match.get("客队赔率"),
                "league": beijing_match.get("联赛中文名")
            }
        
        # 赔率差异分析
        if jingcai_match and beijing_match:
            comparison["odds_difference"] = self._calculate_odds_diff(
                jingcai_match, beijing_match
            )
            comparison["recommendation"] = self._generate_cross_recommendation(
                comparison["odds_difference"],
                jingcai_match,
                beijing_match
            )
        
        return comparison
    
    def _find_match(self, matches: List[Dict], home: str, away: str) -> Optional[Dict]:
        """查找匹配的比赛"""
        for m in matches:
            if home in m.get("主队", "") and away in m.get("客队", ""):
                return m
            if away in m.get("主队", "") and home in m.get("客队", ""):
                # 主客场可能相反
                return m
        return None
    
    def _calculate_odds_diff(
        self,
        jingcai: Dict,
        beijing: Dict
    ) -> Dict:
        """计算赔率差异"""
        j_home = jingcai.get("主队赔率", 0)
        j_draw = jingcai.get("平局赔率", 0)
        j_away = jingcai.get("客队赔率", 0)
        
        b_home = beijing.get("主队赔率", 0)
        b_draw = beijing.get("平局赔率", 0)
        b_away = beijing.get("客队赔率", 0)
        
        return {
            "home_diff": round(b_home - j_home, 3) if j_home and b_home else None,
            "draw_diff": round(b_draw - j_draw, 3) if j_draw and b_draw else None,
            "away_diff": round(b_away - j_away, 3) if j_away and b_away else None,
            "best_for_home": "竞彩" if j_home < b_home else "北京单场" if b_home < j_home else "相同",
            "best_for_draw": "竞彩" if j_draw < b_draw else "北京单场" if b_draw < j_draw else "相同",
            "best_for_away": "竞彩" if j_away < b_away else "北京单场" if b_away < j_away else "相同"
        }
    
    def _generate_cross_recommendation(
        self,
        diff: Dict,
        jingcai: Dict,
        beijing: Dict
    ) -> Dict:
        """生成跨玩法推荐"""
        recommendations = []
        
        # 找最有利的选择
        if diff["home_diff"] and diff["home_diff"] < -0.1:
            recommendations.append({
                "result": "主胜",
                "bet_on": "北京单场",
                "reason": "北京单场主胜赔率更高",
                "extra_value": abs(diff["home_diff"])
            })
        elif diff["home_diff"] and diff["home_diff"] > 0.1:
            recommendations.append({
                "result": "主胜",
                "bet_on": "竞彩足球",
                "reason": "竞彩足球主胜赔率更高",
                "extra_value": abs(diff["home_diff"])
            })
        
        return {"options": recommendations}
    
    def analyze_correlated_plays(
        self,
        match: Dict,
        play_types: List[str]
    ) -> Dict:
        """
        分析相关玩法的关联性
        
        Args:
            match: 比赛数据
            play_types: 玩法列表
        """
        correlations = {
            ("胜平负", "让球胜平负"): "强关联，胜平负是让球胜平负的基础",
            ("胜平负", "比分"): "中等关联，比分包含胜平负结果",
            ("胜平负", "总进球"): "弱关联，但有间接关系",
            ("比分", "总进球"): "强关联，总进球是比分进球数之和",
            ("半全场", "比分"): "强关联，半全场预测比分的一部分",
            ("半全场", "胜平负"): "强关联，半全场包含全场结果"
        }
        
        result = {
            "match_info": f"{match.get('主队', '?')} vs {match.get('客队', '?')}",
            "selected_plays": play_types,
            "correlations": [],
            "recommended_combinations": []
        }
        
        for i, pt1 in enumerate(play_types):
            for pt2 in play_types[i+1:]:
                key = (pt1, pt2)
                reverse_key = (pt2, pt1)
                
                if key in correlations:
                    result["correlations"].append({
                        "play1": pt1,
                        "play2": pt2,
                        "strength": correlations[key]
                    })
                elif reverse_key in correlations:
                    result["correlations"].append({
                        "play1": pt2,
                        "play2": pt1,
                        "strength": correlations[reverse_key]
                    })
        
        # 推荐组合
        result["recommended_combinations"] = self._recommend_play_combinations(play_types)
        
        return result
    
    def _recommend_play_combinations(self, play_types: List[str]) -> List[Dict]:
        """推荐玩法组合"""
        combinations = []
        
        if "胜平负" in play_types and "总进球" in play_types:
            combinations.append({
                "combination": ["胜平负", "总进球"],
                "reason": "互补性强，胜平负定方向，总进球定精度",
                "difficulty": "中等",
                "recommended": True
            })
        
        if "比分" in play_types and "半全场" in play_types:
            combinations.append({
                "combination": ["比分", "半全场"],
                "reason": "包含关系，比分可以拆分为半全场",
                "difficulty": "高",
                "recommended": False
            })
        
        if "胜平负" in play_types and "半全场" in play_types:
            combinations.append({
                "combination": ["胜平负", "半全场"],
                "reason": "全场结果重复，但能互相验证",
                "difficulty": "中等",
                "recommended": True
            })
        
        if "总进球" in play_types:
            combinations.append({
                "combination": ["总进球"],
                "reason": "单玩法，可与胜平负组合",
                "difficulty": "中等",
                "recommended": True
            })
        
        return combinations


class ArbitrageDetector:
    """套利检测器"""
    
    def __init__(self, data: Dict):
        self.data = data
    
    def detect_arbitrage(
        self,
        home_team: str,
        away_team: str
    ) -> Dict:
        """
        检测套利机会
        
        套利原理：同一比赛在不同玩法的赔率组合中，
        如果所有结果的倒数之和小于1，则存在套利机会
        """
        # 获取所有玩法的赔率
        odds_collections = self._collect_all_odds(home_team, away_team)
        
        if not odds_collections:
            return {"available": False, "reason": "无足够数据"}
        
        arbitrage_opportunities = []
        
        for lottery, odds_set in odds_collections.items():
            for play, odds in odds_set.items():
                if len(odds) >= 2:
                    # 检查是否存在套利
                    arb = self._check_single_play_arb(play, odds)
                    if arb["exists"]:
                        arbitrage_opportunities.append({
                            "lottery": lottery,
                            "play": play,
                            "strategy": arb["strategy"],
                            "profit_margin": arb["profit_margin"]
                        })
        
        return {
            "match": f"{home_team} vs {away_team}",
            "arbitrage_found": len(arbitrage_opportunities) > 0,
            "opportunities": arbitrage_opportunities,
            "note": "套利机会较少，即使存在利润也较薄"
        }
    
    def _collect_all_odds(
        self,
        home: str,
        away: str
    ) -> Dict:
        """收集所有赔率"""
        collections = {}
        
        for lottery, data in self.data.items():
            matches = data.get("matches", [])
            for m in matches:
                if home in m.get("主队", "") or away in m.get("主队", ""):
                    odds = {
                        "home": m.get("主队赔率"),
                        "draw": m.get("平局赔率"),
                        "away": m.get("客队赔率")
                    }
                    if any(odds.values()):
                        collections[lottery] = {"胜平负": odds}
                    break
        
        return collections
    
    def _check_single_play_arb(
        self,
        play: str,
        odds: Dict
    ) -> Dict:
        """检查单玩法套利"""
        # 提取有效赔率
        valid_odds = [v for v in odds.values() if v and v > 0]
        
        if len(valid_odds) < 2:
            return {"exists": False}
        
        # 计算倒数和（市场保证金）
        inverse_sum = sum(1 / o for o in valid_odds)
        
        # 如果倒数和小于1，存在套利机会
        if inverse_sum < 1:
            profit_margin = (1 - inverse_sum) * 100
            
            # 计算各结果应投金额
            total_stake = 100  # 假设总投入100
            strategy = {}
            for key, odd in odds.items():
                if odd and odd > 0:
                    strategy[key] = {
                        "odds": odd,
                        "stake": round(total_stake / (odd * inverse_sum), 2),
                        "profit": round(total_stake / (odd * inverse_sum) * (odd - 1), 2)
                    }
            
            return {
                "exists": True,
                "profit_margin": round(profit_margin, 2),
                "strategy": strategy
            }
        
        return {"exists": False}
    
    def recommend_bet_allocation(
        self,
        matches: List[Dict],
        total_budget: float,
        play_types: List[str]
    ) -> Dict:
        """
        推荐投注分配
        
        Args:
            matches: 比赛列表
            total_budget: 总预算
            play_types: 选择的玩法
        """
        n = len(matches)
        if n == 0:
            return {"error": "无比赛"}
        
        # 预算分配策略
        base_per_match = total_budget / n
        
        allocations = []
        
        for i, m in enumerate(matches):
            match_alloc = {
                "match_index": i + 1,
                "match": f"{m.get('主队', 'T{}'.format(i+1))} vs {m.get('客队', '')}",
                "base_allocation": round(base_per_match, 2)
            }
            
            # 根据玩法调整
            if "胜平负" in play_types:
                match_alloc["胜平负"] = round(base_per_match * 0.4, 2)
            if "让球胜平负" in play_types:
                match_alloc["让球胜平负"] = round(base_per_match * 0.2, 2)
            if "总进球" in play_types:
                match_alloc["总进球"] = round(base_per_match * 0.15, 2)
            if "比分" in play_types:
                match_alloc["比分"] = round(base_per_match * 0.15, 2)
            if "半全场" in play_types:
                match_alloc["半全场"] = round(base_per_match * 0.1, 2)
            
            allocations.append(match_alloc)
        
        # 风险控制
        risk_control = {
            "max_per_match": round(total_budget * 0.15, 2),
            "max_per_play": round(total_budget * 0.3, 2),
            "reserve_fund": round(total_budget * 0.1, 2),
            "usable_budget": round(total_budget * 0.9, 2)
        }
        
        return {
            "total_budget": total_budget,
            "matches": n,
            "play_types": play_types,
            "allocations": allocations,
            "risk_control": risk_control
        }


class IntegratedRecommendationEngine:
    """综合推荐引擎"""
    
    def __init__(self, data: Dict):
        self.data = data
        self.cross_analyzer = CrossPlayAnalyzer(data)
        self.arb_detector = ArbitrageDetector(data)
    
    def generate_integrated_recommendation(
        self,
        home_team: str,
        away_team: str,
        user_preference: str = "balanced"  # aggressive/balanced/conservative
    ) -> Dict:
        """
        生成综合推荐
        
        Args:
            home_team: 主队
            away_team: 客队
            user_preference: 用户偏好
        """
        # 1. 跨玩法赔率对比
        odds_comparison = self.cross_analyzer.compare_odds_between_lotteries(
            home_team, away_team
        )
        
        # 2. 套利检测
        arbitrage = self.arb_detector.detect_arbitrage(home_team, away_team)
        
        # 3. 基于偏好生成推荐
        recommendation = self._generate_by_preference(
            odds_comparison,
            arbitrage,
            user_preference
        )
        
        return {
            "match": f"{home_team} vs {away_team}",
            "odds_comparison": odds_comparison,
            "arbitrage_opportunity": arbitrage,
            "recommendation": recommendation,
            "strategy": self._generate_strategy_summary(recommendation)
        }
    
    def _generate_by_preference(
        self,
        odds: Dict,
        arbitrage: Dict,
        preference: str
    ) -> Dict:
        """基于偏好生成推荐"""
        
        if preference == "conservative":
            return {
                "strategy": "保守策略",
                "play": "胜平负",
                "bet_on": self._get_best_odds_lottery(odds, "home"),
                "stake": "低",
                "reason": "选择最稳定的胜平负玩法"
            }
        elif preference == "aggressive":
            return {
                "strategy": "进取策略",
                "play": "比分/半全场",
                "bet_on": "竞彩足球",
                "stake": "中",
                "reason": "追求高赔率回报"
            }
        else:  # balanced
            return {
                "strategy": "平衡策略",
                "play": "胜平负 + 总进球组合",
                "bet_on": "竞彩足球",
                "stake": "中",
                "reason": "兼顾稳定性与回报"
            }
    
    def _get_best_odds_lottery(self, odds: Dict, result: str) -> str:
        """获取最佳赔率的玩法"""
        if odds.get("jingcai_available") and odds.get("beijing_available"):
            j = odds["jingcai_odds"].get(result)
            b = odds["beijing_odds"].get(result)
            if j and b:
                return "竞彩足球" if j > b else "北京单场"
        return "竞彩足球" if odds.get("jingcai_available") else "北京单场"
    
    def _generate_strategy_summary(self, recommendation: Dict) -> Dict:
        """生成策略摘要"""
        return {
            "primary_strategy": recommendation.get("strategy", ""),
            "risk_level": "低" if "保守" in str(recommendation) else "中" if "平衡" in str(recommendation) else "高",
            "expected_return": "5-15%" if "保守" in str(recommendation) else "15-30%" if "平衡" in str(recommendation) else "30%+",
            "key_points": [
                "选择赔率更高的平台",
                "控制单场投注金额",
                "避免追逐高赔率冷门"
            ]
        }
    
    def recommend_multi_play_parlay(
        self,
        matches: List[Dict],
        play_types: List[str],
        target_odds: float = 10.0
    ) -> Dict:
        """
        推荐多玩法串关
        
        Args:
            matches: 比赛列表
            play_types: 玩法列表
            target_odds: 目标赔率
        """
        n = len(matches)
        if n < 2:
            return {"error": "串关至少需要2场"}
        
        # 计算推荐的玩法组合
        recommended_plays = []
        
        for m in matches:
            # 根据比赛特点推荐玩法
            home_odds = m.get("主队赔率", 2.0)
            
            if home_odds < 1.5:
                recommended_plays.append({
                    "match": f"{m.get('主队', '?')} vs {m.get('客队', '?')}",
                    "recommended_play": "胜平负",
                    "recommended_option": "主胜",
                    "odds": home_odds
                })
            elif home_odds < 2.5:
                recommended_plays.append({
                    "match": f"{m.get('主队', '?')} vs {m.get('客队', '?')}",
                    "recommended_play": "让球胜平负",
                    "recommended_option": "主胜",
                    "odds": 1.8
                })
            else:
                recommended_plays.append({
                    "match": f"{m.get('主队', '?')} vs {m.get('客队', '?')}",
                    "recommended_play": "总进球",
                    "recommended_option": "2-3球",
                    "odds": 2.0
                })
        
        # 计算组合赔率
        total_odds = math.prod(p["odds"] for p in recommended_plays)
        
        return {
            "matches": n,
            "play_types": play_types,
            "recommended_plays": recommended_plays,
            "combined_odds": round(total_odds, 2),
            "meets_target": total_odds >= target_odds,
            "adjustment_needed": "减少高赔选项" if total_odds > target_odds * 1.5 else "增加高赔选项" if total_odds < target_odds * 0.5 else "合适"
        }


def main():
    """测试跨玩法分析"""
    data = load_all_data()
    
    print("=" * 60)
    print("跨玩法协同策略模块 v2.0")
    print("=" * 60)
    
    if not data:
        print("无数据")
        return
    
    # 跨玩法分析
    print("\n【跨玩法分析】")
    cross = CrossPlayAnalyzer(data)
    
    # 获取第一场比赛测试
    for lottery, d in data.items():
        if d.get("matches"):
            sample = d["matches"][0]
            result = cross.compare_odds_between_lotteries(
                sample.get("主队", ""),
                sample.get("客队", "")
            )
            print(f"比赛: {result['match']}")
            print(f"竞彩可用: {result['jingcai_available']}")
            print(f"北单可用: {result['beijing_available']}")
            break
    
    # 综合推荐
    print("\n【综合推荐引擎】")
    engine = IntegratedRecommendationEngine(data)
    
    # 套利检测
    print("\n【套利检测】")
    arb = ArbitrageDetector(data)
    # 测试一场比赛
    if data:
        for lottery, d in data.items():
            if d.get("matches"):
                m = d["matches"][0]
                arb_result = arb.detect_arbitrage(
                    m.get("主队", ""),
                    m.get("客队", "")
                )
                print(f"套利机会: {arb_result.get('arbitrage_found', False)}")
                break


if __name__ == "__main__":
    main()
