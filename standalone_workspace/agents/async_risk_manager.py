import asyncio
import os
import json
import logging
from typing import Dict, Any

from agents.async_base import AsyncBaseAgent
from tools.smart_money_tracker import SmartMoneyTracker

logger = logging.getLogger(__name__)

class AsyncRiskManagerAgent(AsyncBaseAgent):
    """
    2026 Next-Gen Async Risk Manager Agent
    提供仓位控制和止损机制，将打回重审(Debate)逻辑转化为 Graph 的状态反馈。
    """
    def __init__(self, config=None):
        super().__init__("risk_manager", "风险管理", config)
        self.risk_rules = self._load_risk_rules()
        
    def _load_risk_rules(self) -> Dict:
        return {
            "max_single_stake_ratio": 0.1,  
            "max_daily_loss_ratio": 0.2,     
            "max_consecutive_losses": 5,      
            "kelly_fraction": 0.25,          
            "min_odds": 1.5,                 
            "max_odds": 10.0                 
        }

    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """处理风险管理任务，并更新状态增量"""
        self.status = "running"
        print(f"\n[AsyncRiskManager] 正在进行凯利公式风控核查...")
        
        # 将 CPU 密集或复杂的风控逻辑丢入线程池
        data = await asyncio.to_thread(self._risk_assessment_logic, state)
        
        # 异步持久化
        await self.save_context("latest_risk_check", data)
        self.status = "completed"
        return {"risk_manager_data": data}

    def _risk_assessment_logic(self, state: Dict[str, Any]) -> Dict:
        strategist_data = state.get("strategist_data", {})
        params = state.get("params", {})
        analyst_data = state.get("analyst_data", {})
        lottery_type = params.get("lottery_type", "jingcai")
        
        bet = strategist_data.get('bet', {})
        bankroll = params.get('bankroll', 1000)
        decision = strategist_data.get("decision")
        decision_reason = strategist_data.get("decision_reason")
        expected_value = strategist_data.get("expected_value")

        if decision == "skip" or not bet:
            return {
                "status": "success",
                "checks": {},
                "risk_score": 0.0,
                "recommendation": "skip",
                "reason": decision_reason or "策略建议不下注",
                "expected_value": expected_value,
                "debate_trigger": False
            }
            
        stake = bet.get('stake', 0)
        odds = bet.get('odds', 0)
        selection = bet.get('selection', 'home')
        
        # 1. 聪明资金追踪 (Smart Money Tracking)
        opening_odds = analyst_data.get("professional_data", {}).get("water_changes", {}).get("initial", {})
        live_odds = analyst_data.get("odds", {})
        
        # 降级处理：如果没有拿到初盘，模拟一个微小的偏移
        if not opening_odds:
            opening_odds = {"home": live_odds.get("home", 2.0) + 0.15, "draw": live_odds.get("draw", 3.2), "away": live_odds.get("away", 3.5) - 0.1}
            
        sharp_report = SmartMoneyTracker.detect_sharp_money(opening_odds, live_odds)
        if sharp_report.get("has_sharp_money"):
            print(f"    {sharp_report.get('report')}")
        
        checks = {
            "stake_ratio": self._check_stake_ratio(stake, bankroll),
            "odds_range": self._check_odds_range(odds),
            "value": self._check_value(bet),
            "kelly_bet": self._calculate_kelly(stake, odds, bet.get('probability', 0.5), lottery_type)
        }
        
        # 如果聪明资金砸的是对家，极大增加风险分
        risk_score = self._calculate_risk_score(checks)
        if sharp_report.get("has_sharp_money") and sharp_report.get("direction") != selection:
            risk_score += 0.4
            checks["smart_money"] = {"passed": False, "message": f"被聪明资金反向狙击: {sharp_report.get('report')}"}
        else:
            checks["smart_money"] = {"passed": True, "message": "资金面安全或顺势"}
            
        debate_count = state.get("debate_count", 0)
        max_debates = 1
        
        is_approved = risk_score < 0.5 and checks["kelly_bet"]["has_edge"]
        
        if not is_approved and debate_count < max_debates:
            # 触发打回重审
            print(f"⚠️ [AsyncRiskManager] 触发风控红线，打回重审！(Risk={risk_score:.2f})")
            return {
                "status": "success",
                "checks": checks,
                "risk_score": risk_score,
                "recommendation": "reject_and_replan",
                "reason": f"风控拒绝。要求 Strategist 重新寻找对冲策略。",
                "debate_trigger": True,
                "rejection_reason": self._get_risk_reason(checks)
            }
        
        print(f"✅ [AsyncRiskManager] 风控审核通过。")
        return {
            "status": "success",
            "checks": checks,
            "risk_score": risk_score,
            "recommendation": "approve" if is_approved else "final_reject",
            "reason": self._get_risk_reason(checks),
            "debate_trigger": False
        }

    def _check_stake_ratio(self, stake: float, bankroll: float) -> Dict:
        ratio = stake / bankroll if bankroll > 0 else 1
        max_ratio = self.risk_rules['max_single_stake_ratio']
        return {
            "ratio": ratio,
            "max_allowed": max_ratio,
            "passed": ratio <= max_ratio,
            "message": f"投注比例 {ratio:.1%} (限制: {max_ratio:.1%})"
        }
    
    def _check_odds_range(self, odds: float) -> Dict:
        min_odds = self.risk_rules['min_odds']
        max_odds = self.risk_rules['max_odds']
        in_range = min_odds <= odds <= max_odds
        return {
            "odds": odds,
            "min_allowed": min_odds,
            "max_allowed": max_odds,
            "passed": in_range,
            "message": f"赔率 {odds} 在范围内" if in_range else f"赔率 {odds} 超出范围"
        }
    
    def _check_value(self, bet: Dict) -> Dict:
        if bet.get("expected_value") is not None:
            expected_value = float(bet.get("expected_value"))
        else:
            odds = bet.get('odds', 0)
            probability = bet.get('probability', 0)
            expected_value = (odds * probability) - 1
        has_value = expected_value > 0
        return {
            "expected_value": expected_value,
            "has_value": has_value,
            "message": f"期望值 {expected_value:.2%}" if has_value else "无正向期望值"
        }
    
    def _calculate_kelly(self, stake: float, odds: float, probability: float, lottery_type: str = "jingcai") -> Dict:
        kelly_fraction = self.risk_rules['kelly_fraction']
        if probability <= 0 or odds <= 1:
            optimal_bet = 0
            has_edge = False
        else:
            # 2. 北单与竞彩的 EV/Kelly 隔离
            if lottery_type == "beijing":
                # 北单官方要扣除 35% 调节基金，返奖率为 65%
                actual_odds = odds * 0.65
                print(f"    [Kelly] 识别为北单，名义SP: {odds:.2f} -> 实际SP: {actual_odds:.2f}")
            else:
                actual_odds = odds
                
            q = 1 - probability
            p = probability
            b = actual_odds - 1
            kelly = (b * p - q) / b if b > 0 else 0
            
            if kelly > 0:
                optimal_bet = min(kelly * kelly_fraction, self.risk_rules['max_single_stake_ratio'])
                has_edge = True
            else:
                optimal_bet = 0
                has_edge = False
        
        return {
            "has_edge": has_edge,
            "kelly_fraction": kelly_fraction,
            "optimal_bet_ratio": optimal_bet,
            "recommended_stake": stake * optimal_bet if optimal_bet > 0 else 0,
            "message": f"建议动用总本金的: {optimal_bet:.1%}" if has_edge else "无投注价值(Kelly <= 0)"
        }
    
    def _calculate_risk_score(self, checks: Dict) -> float:
        score = 0.0
        if not checks['stake_ratio']['passed']: score += 0.4
        if not checks['odds_range']['passed']: score += 0.3
        if not checks['value']['has_value']: score += 0.2
        return min(1.0, score)
    
    def _get_risk_reason(self, checks: Dict) -> str:
        reasons = []
        if not checks['stake_ratio']['passed']: reasons.append(checks['stake_ratio']['message'])
        if not checks['odds_range']['passed']: reasons.append(checks['odds_range']['message'])
        if not checks['value']['has_value']: reasons.append(checks['value']['message'])
        return "; ".join(reasons) if reasons else "通过风控检查"