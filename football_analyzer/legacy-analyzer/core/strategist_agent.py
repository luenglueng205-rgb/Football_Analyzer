#!/usr/bin/env python3
"""
策略制定Agent
功能：
1. M串N方案生成
2. 资金分配建议
3. 风险评估
"""

import os
import sys
import json
import itertools
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict
from math import comb

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BASE_DIR = os.path.dirname(PROJECT_ROOT)
DATA_DIR = os.path.join(BASE_DIR, 'data', 'chinese_mapped')
sys.path.insert(0, PROJECT_ROOT)

from core.base_agent import BaseAgent, AgentStatus, Task, get_registry


class StrategistAgent(BaseAgent):
    """策略制定Agent - 负责投注策略生成和优化"""
    
    def __init__(self, message_bus=None):
        super().__init__("StrategistAgent", message_bus)
        self._parlay_cache: Dict[str, List[Dict]] = {}
        self._strategy_templates: Dict[str, Dict] = {}
    
    def initialize(self) -> bool:
        """初始化Agent"""
        self.set_status(AgentStatus.IDLE)
        self._load_strategy_templates()
        get_registry().register(self)
        return True
    
    def _load_strategy_templates(self) -> None:
        """加载策略模板"""
        self._strategy_templates = {
            "conservative": {
                "name": "保守策略",
                "description": "以低赔率稳胆为主，控制风险",
                "max_odds": 1.5,
                "recommended_parlay": "2串1",
                "stake_ratio": 0.1
            },
            "balanced": {
                "name": "平衡策略",
                "description": "中等风险，适度追求收益",
                "max_odds": 2.0,
                "recommended_parlay": "3串1",
                "stake_ratio": 0.15
            },
            "aggressive": {
                "name": "激进策略",
                "description": "高风险高回报",
                "max_odds": 3.0,
                "recommended_parlay": "4串1",
                "stake_ratio": 0.2
            },
            "value_hunter": {
                "name": "价值猎人",
                "description": "专注价值投注",
                "min_value": 0.1,
                "stake_ratio": 0.08
            }
        }
    
    def process(self, task: Task) -> Dict[str, Any]:
        """处理任务"""
        self.set_status(AgentStatus.RUNNING)
        
        task_type = task.task_type
        payload = task.payload
        
        try:
            if task_type == "generate_parlay":
                result = self.generate_parlay_options(
                    payload.get("m", 2),
                    payload.get("matches", []),
                    payload.get("budget", 100)
                )
            elif task_type == "stake_allocation":
                result = self.calculate_stake_allocation(
                    payload.get("total_budget", 100),
                    payload.get("strategies", [])
                )
            elif task_type == "risk_assessment":
                result = self.assess_risk(
                    payload.get("bets", []),
                    payload.get("budget", 100)
                )
            elif task_type == "strategy_recommendation":
                result = self.recommend_strategy(
                    payload.get("risk_tolerance", "medium"),
                    payload.get("budget", 100)
                )
            elif task_type == "mxn_combinations":
                result = self.generate_mxn_options(
                    payload.get("m", 2),
                    payload.get("n", 1),
                    payload.get("matches", []),
                    payload.get("budget", 100)
                )
            elif task_type == "expected_value":
                result = self.calculate_expected_value(
                    payload.get("bets", [])
                )
            else:
                result = {"error": f"Unknown task type: {task_type}"}
            
            self.set_status(AgentStatus.COMPLETED)
            return {"status": "success", "result": result}
            
        except Exception as e:
            self.set_status(AgentStatus.ERROR)
            self._last_error = str(e)
            return {"status": "error", "error": str(e)}
    
    def generate_parlay_options(self, m: int, matches: List[Dict], budget: float) -> Dict:
        """生成串关方案"""
        if len(matches) < m:
            return {"error": f"比赛数量不足，需要{m}场，当前{len(matches)}场"}
        
        # 生成所有M串1组合
        combinations = list(itertools.combinations(matches, m))
        
        parlay_options = []
        for combo in combinations:
            # 计算预期回报
            total_odds = 1.0
            for match in combo:
                odds = match.get("odds", {}).get(match.get("recommended", "home_win"), 1.0)
                total_odds *= odds
            
            stake = budget / len(combinations)
            expected_return = stake * total_odds
            
            parlay_options.append({
                "matches": [m.get("match_id") for m in combo],
                "teams": [(m.get("home_team"), m.get("away_team")) for m in combo],
                "total_odds": round(total_odds, 2),
                "stake": round(stake, 2),
                "expected_return": round(expected_return, 2),
                "roi": round((expected_return - stake) / stake * 100, 1)
            })
        
        # 按ROI排序
        parlay_options.sort(key=lambda x: x["roi"], reverse=True)
        
        return {
            "parlay_type": f"{m}串1",
            "total_combinations": len(parlay_options),
            "budget": budget,
            "options": parlay_options[:10],
            "best_option": parlay_options[0] if parlay_options else None,
            "summary": {
                "avg_odds": round(sum(p["total_odds"] for p in parlay_options) / len(parlay_options), 2),
                "avg_roi": round(sum(p["roi"] for p in parlay_options) / len(parlay_options), 1)
            }
        }
    
    def generate_mxn_options(self, m: int, n: int, matches: List[Dict], budget: float) -> Dict:
        """生成M串N容错方案"""
        if len(matches) < m:
            return {"error": f"比赛数量不足"}
        
        # M串N意味着允许错N场
        # 计算实际需要选择的最少场次
        min_matches = m - n
        
        if min_matches < 1:
            return {"error": "N值不能大于M-1"}
        
        # 生成所有可能的组合
        all_combos = list(itertools.combinations(matches, min_matches))
        
        # 计算每个组合的预期值
        mxm_options = []
        for combo in all_combos:
            total_odds = 1.0
            valid = True
            
            for match in combo:
                rec = match.get("recommended", "home_win")
                odds = match.get("odds", {}).get(rec, 1.0)
                if odds <= 0:
                    valid = False
                    break
                total_odds *= odds
            
            if valid:
                stake_per_combo = budget / len(all_combos)
                expected = stake_per_combo * total_odds
                
                mxm_options.append({
                    "matches": [m.get("match_id") for m in combo],
                    "total_odds": round(total_odds, 2),
                    "stake": round(stake_per_combo, 2),
                    "expected_return": round(expected, 2)
                })
        
        mxm_options.sort(key=lambda x: x["expected_return"], reverse=True)
        
        return {
            "type": f"{m}串{n}",
            "min_required": min_matches,
            "total_options": len(mxm_options),
            "budget": budget,
            "options": mxm_options[:10],
            "total_cost": budget,
            "max_payout": mxm_options[0]["expected_return"] if mxm_options else 0
        }
    
    def calculate_stake_allocation(self, total_budget: float, strategies: List[Dict]) -> Dict:
        """计算资金分配"""
        if not strategies:
            return {"error": "未提供策略"}
        
        total_risk = sum(s.get("risk", 0.5) for s in strategies)
        
        allocations = []
        for strategy in strategies:
            risk_weight = strategy.get("risk", 0.5) / total_risk
            stake = total_budget * risk_weight
            
            allocations.append({
                "strategy": strategy.get("name", "unknown"),
                "stake": round(stake, 2),
                "percentage": round(risk_weight * 100, 1),
                "expected_return": strategy.get("expected_return", 0),
                "risk_level": strategy.get("risk_level", "medium")
            })
        
        return {
            "total_budget": total_budget,
            "strategies": allocations,
            "summary": {
                "total_allocated": sum(a["stake"] for a in allocations),
                "remaining": total_budget - sum(a["stake"] for a in allocations)
            }
        }
    
    def assess_risk(self, bets: List[Dict], budget: float) -> Dict:
        """风险评估"""
        if not bets:
            return {"error": "未提供投注"}
        
        total_stake = sum(b.get("stake", 0) for b in bets)
        max_loss = total_stake
        max_win = sum(b.get("expected_return", 0) for b in bets)
        
        # 计算组合赔率
        combined_odds = 1.0
        for bet in bets:
            combined_odds *= bet.get("odds", 1.0)
        
        # 风险指标
        win_prob = 1.0 / combined_odds if combined_odds > 0 else 0
        expected_value = (win_prob * max_win) - ((1 - win_prob) * max_loss)
        
        risk_level = "low"
        if total_stake / budget > 0.3:
            risk_level = "high"
        elif total_stake / budget > 0.15:
            risk_level = "medium"
        
        return {
            "bets": bets,
            "total_stake": round(total_stake, 2),
            "budget": budget,
            "exposure": round(total_stake / budget * 100, 1),
            "max_loss": round(max_loss, 2),
            "max_win": round(max_win, 2),
            "combined_odds": round(combined_odds, 2),
            "win_probability": round(win_prob * 100, 1),
            "expected_value": round(expected_value, 2),
            "risk_level": risk_level,
            "recommendations": self._get_risk_recommendations(risk_level, expected_value)
        }
    
    def _get_risk_recommendations(self, risk_level: str, ev: float) -> List[str]:
        """获取风险建议"""
        recommendations = []
        
        if risk_level == "high":
            recommendations.append("建议降低投注金额，控制风险")
        elif risk_level == "medium":
            recommendations.append("注意仓位控制，避免过度集中")
        
        if ev < 0:
            recommendations.append("期望值为负，不建议投注")
        elif ev > 10:
            recommendations.append("高价值投注，可适当增加仓位")
        
        return recommendations
    
    def recommend_strategy(self, risk_tolerance: str, budget: float) -> Dict:
        """推荐策略"""
        templates = {
            "low": "conservative",
            "medium": "balanced",
            "high": "aggressive"
        }
        
        template_key = templates.get(risk_tolerance, "balanced")
        template = self._strategy_templates.get(template_key, self._strategy_templates["balanced"])
        
        recommended_stake = budget * template.get("stake_ratio", 0.1)
        
        return {
            "risk_tolerance": risk_tolerance,
            "recommended_strategy": template["name"],
            "description": template["description"],
            "stake": round(recommended_stake, 2),
            "stake_percentage": round(template.get("stake_ratio", 0.1) * 100, 1),
            "recommended_parlay": template.get("recommended_parlay", "2串1"),
            "alternatives": [
                {"name": t["name"], "description": t["description"]}
                for k, t in self._strategy_templates.items()
                if k != template_key
            ]
        }
    
    def calculate_expected_value(self, bets: List[Dict]) -> Dict:
        """计算期望值"""
        if not bets:
            return {"error": "未提供投注"}
        
        results = []
        for bet in bets:
            odds = bet.get("odds", 1.0)
            prob = bet.get("probability", 0.5)
            
            # 期望值 = 赔率 * 概率 - (1 - 概率)
            ev = odds * prob - (1 - prob)
            
            results.append({
                "bet_id": bet.get("bet_id", ""),
                "odds": odds,
                "probability": round(prob * 100, 1),
                "expected_value": round(ev * 100, 1),
                "recommendation": "投注" if ev > 0 else "放弃"
            })
        
        total_ev = sum(r["expected_value"] for r in results)
        
        return {
            "bets": results,
            "total_bets": len(bets),
            "positive_ev_bets": sum(1 for r in results if r["expected_value"] > 0),
            "total_expected_value": round(total_ev, 1),
            "summary": "整体有利可图" if total_ev > 0 else "整体无利可图"
        }
    
    def get_capabilities(self) -> Dict[str, Any]:
        """获取Agent能力"""
        return {
            "name": self.name,
            "type": "strategist",
            "functions": [
                "generate_parlay - 串关方案生成",
                "mxn_combinations - M串N容错方案",
                "stake_allocation - 资金分配",
                "risk_assessment - 风险评估",
                "strategy_recommendation - 策略推荐",
                "expected_value - 期望值计算"
            ],
            "strategies": list(self._strategy_templates.keys()),
            "status": self.status.value
        }


# 便捷函数
def create_strategist_agent(message_bus=None) -> StrategistAgent:
    """创建StrategistAgent实例"""
    agent = StrategistAgent(message_bus)
    agent.initialize()
    return agent


__all__ = ['StrategistAgent', 'create_strategist_agent']