#!/usr/bin/env python3
"""
赔率分析Agent
功能：
1. 赔率异常检测
2. 盘口解读
3. 价值识别
"""

import os
import sys
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BASE_DIR = os.path.dirname(PROJECT_ROOT)
DATA_DIR = os.path.join(BASE_DIR, 'data', 'chinese_mapped')
sys.path.insert(0, PROJECT_ROOT)

from core.base_agent import BaseAgent, AgentStatus, Task, get_registry


def load_jingcai_data() -> Dict:
    """加载竞彩足球数据"""
    filepath = os.path.join(DATA_DIR, '竞彩足球_chinese_data.json')
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def load_odds_rules() -> Dict:
    """加载赔率规则"""
    filepath = os.path.join(PROJECT_ROOT, 'official_rules.json')
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


class AnalystAgent(BaseAgent):
    """赔率分析Agent - 负责赔率分析和价值识别"""
    
    # 赔率价值阈值
    VALUE_THRESHOLD = 0.05  # 5%以上为有价值
    ODDS_ANOMALY_THRESHOLD = 0.3  # 30%变化为异常
    
    def __init__(self, message_bus=None):
        super().__init__("AnalystAgent", message_bus)
        self.data = load_jingcai_data()
        self.rules = load_odds_rules()
        self._odds_cache: Dict[str, Dict] = {}
        self._historical_odds: Dict[str, List[Dict]] = defaultdict(list)
    
    def initialize(self) -> bool:
        """初始化Agent"""
        self.set_status(AgentStatus.IDLE)
        self._load_odds_data()
        get_registry().register(self)
        return True
    
    def _load_odds_data(self) -> None:
        """加载赔率数据"""
        if "matches" in self.data:
            for match in self.data["matches"]:
                match_id = match.get("match_id", "")
                if match_id:
                    self._odds_cache[match_id] = match
    
    def process(self, task: Task) -> Dict[str, Any]:
        """处理任务"""
        self.set_status(AgentStatus.RUNNING)
        
        task_type = task.task_type
        payload = task.payload
        
        try:
            if task_type == "odds_anomaly":
                result = self.detect_odds_anomaly(
                    payload.get("match_id", "")
                )
            elif task_type == "handicap_analysis":
                result = self.analyze_handicap(
                    payload.get("match_id", ""),
                    payload.get("handicap", 0)
                )
            elif task_type == "value_bets":
                result = self.find_value_bets(
                    payload.get("matches", [])
                )
            elif task_type == "odds_comparison":
                result = self.compare_odds(
                    payload.get("match_id", "")
                )
            elif task_type == "market_analysis":
                result = self.analyze_market(
                    payload.get("league", "")
                )
            elif task_type == "implied_probability":
                result = self.calculate_implied_prob(
                    payload.get("odds", {})
                )
            else:
                result = {"error": f"Unknown task type: {task_type}"}
            
            self.set_status(AgentStatus.COMPLETED)
            return {"status": "success", "result": result}
            
        except Exception as e:
            self.set_status(AgentStatus.ERROR)
            self._last_error = str(e)
            return {"status": "error", "error": str(e)}
    
    def detect_odds_anomaly(self, match_id: str) -> Dict:
        """检测赔率异常"""
        if match_id not in self._odds_cache:
            return {"error": f"比赛未找到: {match_id}"}
        
        match = self._odds_cache[match_id]
        odds = match.get("odds", {})
        
        if not odds:
            return {"error": "无赔率数据"}
        
        # 检测各选项赔率
        anomalies = []
        for option, odd_value in odds.items():
            # 与历史平均对比
            hist_key = f"{match_id}_{option}"
            hist = self._historical_odds.get(hist_key, [])
            
            if hist:
                avg_odds = sum(h["odds"] for h in hist) / len(hist)
                change_pct = abs(odd_value - avg_odds) / avg_odds
                
                if change_pct > self.ODDS_ANOMALY_THRESHOLD:
                    anomalies.append({
                        "option": option,
                        "current_odds": odd_value,
                        "historical_avg": round(avg_odds, 2),
                        "change_pct": round(change_pct * 100, 1),
                        "level": "high" if change_pct > 0.5 else "medium"
                    })
        
        return {
            "match_id": match_id,
            "home_team": match.get("home_team", ""),
            "away_team": match.get("away_team", ""),
            "anomalies": anomalies,
            "has_anomaly": len(anomalies) > 0,
            "risk_level": "high" if any(a["level"] == "high" for a in anomalies) else "normal"
        }
    
    def analyze_handicap(self, match_id: str, handicap: float = 0) -> Dict:
        """盘口分析"""
        if match_id not in self._odds_cache:
            return {"error": f"比赛未找到: {match_id}"}
        
        match = self._odds_cache[match_id]
        
        return {
            "match_id": match_id,
            "home_team": match.get("home_team", ""),
            "away_team": match.get("away_team", ""),
            "handicap": handicap,
            "handicap_type": self._get_handicap_type(handicap),
            "recommendation": self._get_handicap_recommendation(handicap)
        }
    
    def _get_handicap_type(self, handicap: float) -> str:
        """获取盘口类型"""
        if handicap == 0:
            return "平手"
        elif handicap > 0:
            return f"主队让{handicap}"
        else:
            return f"客队让{abs(handicap)}"
    
    def _get_handicap_recommendation(self, handicap: float) -> str:
        """获取盘口建议"""
        if handicap > 0.5:
            return "主队让球偏深，关注冷门"
        elif handicap < -0.5:
            return "客队让球偏深，关注主队反弹"
        else:
            return "盘口合理，关注基本面"
    
    def find_value_bets(self, matches: List[Dict]) -> Dict:
        """寻找价值投注"""
        value_bets = []
        
        for match in matches:
            match_id = match.get("match_id", "")
            if match_id not in self._odds_cache:
                continue
            
            match_data = self._odds_cache[match_id]
            odds = match_data.get("odds", {})
            
            if not odds:
                continue
            
            # 计算每个选项的价值
            for option, odd_value in odds.items():
                # 基于历史胜率估算真实概率
                true_prob = self._estimate_true_probability(match_data, option)
                implied_prob = 1 / odd_value if odd_value > 0 else 0
                
                value = implied_prob - true_prob
                
                if value > self.VALUE_THRESHOLD:
                    value_bets.append({
                        "match_id": match_id,
                        "home_team": match_data.get("home_team", ""),
                        "away_team": match_data.get("away_team", ""),
                        "option": option,
                        "odds": odd_value,
                        "implied_prob": round(implied_prob * 100, 1),
                        "estimated_prob": round(true_prob * 100, 1),
                        "value": round(value * 100, 1),
                        "recommendation": "强烈推荐" if value > 0.1 else "建议关注"
                    })
        
        # 按价值排序
        value_bets.sort(key=lambda x: x["value"], reverse=True)
        
        return {
            "total_matches": len(matches),
            "value_bets": value_bets[:10],
            "best_bet": value_bets[0] if value_bets else None,
            "summary": {
                "total_value_bets": len(value_bets),
                "avg_value": round(sum(b["value"] for b in value_bets) / len(value_bets), 1) if value_bets else 0
            }
        }
    
    def _estimate_true_probability(self, match: Dict, option: str) -> float:
        """估算真实概率（简化版）"""
        # 基于主客场和历史战绩估算
        is_home = option in ["主胜", "胜"]
        league = match.get("league", "")
        
        # 简化：假设主场胜率55%，客场胜率45%
        base_prob = 0.55 if is_home else 0.45
        
        # 根据联赛调整
        league_adjust = {
            "英超": 0.02,
            "西甲": 0.01,
            "德甲": 0.02,
            "意甲": 0.01,
            "法甲": 0.0
        }.get(league, 0)
        
        return base_prob + league_adjust
    
    def compare_odds(self, match_id: str) -> Dict:
        """赔率对比分析"""
        if match_id not in self._odds_cache:
            return {"error": f"比赛未找到: {match_id}"}
        
        match = self._odds_cache[match_id]
        odds = match.get("odds", {})
        
        if not odds:
            return {"error": "无赔率数据"}
        
        # 转换赔率为概率
        probabilities = {}
        for option, odd_value in odds.items():
            if odd_value > 0:
                probabilities[option] = 1 / odd_value
        
        # 检测是否有价值
        total_prob = sum(probabilities.values())
        overround = (total_prob - 1) * 100  # 抽水
        
        return {
            "match_id": match_id,
            "odds": odds,
            "implied_probabilities": {k: round(v * 100, 1) for k, v in probabilities.items()},
            "overround": round(overround, 1),
            "best_option": max(probabilities, key=probabilities.get) if probabilities else None,
            "fair_odds": self._calculate_fair_odds(probabilities)
        }
    
    def _calculate_fair_odds(self, probabilities: Dict[str, float]) -> Dict[str, float]:
        """计算公平赔率"""
        total = sum(probabilities.values())
        if total == 0:
            return {}
        
        return {
            option: round(1 / (prob / total), 2)
            for option, prob in probabilities.items()
        }
    
    def analyze_market(self, league: str) -> Dict:
        """市场分析"""
        league_matches = [
            m for m in self._odds_cache.values()
            if m.get("league") == league
        ]
        
        if not league_matches:
            return {"error": f"联赛未找到: {league}"}
        
        # 统计赔率分布
        odds_distribution = defaultdict(list)
        for match in league_matches:
            for option, odd in match.get("odds", {}).items():
                if odd > 0:
                    odds_distribution[option].append(odd)
        
        # 计算各选项平均赔率
        avg_odds = {}
        for option, odds_list in odds_distribution.items():
            avg_odds[option] = round(sum(odds_list) / len(odds_list), 2) if odds_list else 0
        
        return {
            "league": league,
            "total_matches": len(league_matches),
            "average_odds": avg_odds,
            "market_sentiment": self._analyze_sentiment(avg_odds)
        }
    
    def _analyze_sentiment(self, avg_odds: Dict) -> str:
        """分析市场情绪"""
        if not avg_odds:
            return "未知"
        
        min_odds = min(avg_odds.values())
        if min_odds < 1.5:
            return "市场看好强队"
        elif min_odds > 2.5:
            return "市场倾向分散"
        else:
            return "市场均衡"
    
    def calculate_implied_prob(self, odds: Dict) -> Dict:
        """计算隐含概率"""
        probabilities = {}
        
        for option, odd_value in odds.items():
            if odd_value > 0:
                probabilities[option] = round(1 / odd_value * 100, 1)
        
        total = sum(probabilities.values()) / 100
        
        return {
            "odds": odds,
            "implied_probabilities": probabilities,
            "total_probability": round(total * 100, 1),
            "margin": round((total - 1) * 100, 1) if total > 1 else 0,
            "recommendation": max(probabilities, key=probabilities.get) if probabilities else None
        }
    
    def get_capabilities(self) -> Dict[str, Any]:
        """获取Agent能力"""
        return {
            "name": self.name,
            "type": "analyst",
            "functions": [
                "odds_anomaly - 赔率异常检测",
                "handicap_analysis - 盘口解读",
                "value_bets - 价值投注识别",
                "odds_comparison - 赔率对比",
                "market_analysis - 市场分析",
                "implied_probability - 隐含概率计算"
            ],
            "status": self.status.value
        }


# 便捷函数
def create_analyst_agent(message_bus=None) -> AnalystAgent:
    """创建AnalystAgent实例"""
    agent = AnalystAgent(message_bus)
    agent.initialize()
    return agent


__all__ = ['AnalystAgent', 'create_analyst_agent']