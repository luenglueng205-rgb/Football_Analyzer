#!/usr/bin/env python3
"""
风险管理Agent - OpenClaw规范版本
Risk Manager Agent
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from .base import BaseAgent, AgentStatus, Message

logger = logging.getLogger(__name__)

from core.domain_kernel import DomainKernel


class RiskManagerAgent(BaseAgent):
    """
    风险管理Agent
    
    职责：
    1. 仓位控制
    2. 止损机制
    3. 风险评估
    4. 资金管理
    """
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__("risk-manager", "风险管理", config)
        self.risk_rules = self._load_risk_rules()
    
    def _load_risk_rules(self) -> Dict:
        """加载风控规则"""
        return {
            "max_single_stake_ratio": 0.1,  # 单笔投注不超过总资金的10%
            "max_daily_loss_ratio": 0.2,     # 日损失不超过20%
            "max_consecutive_losses": 5,      # 连黑超过5场停止
            "kelly_fraction": 0.25,          # 凯利公式系数
            "min_odds": 1.5,                 # 最低赔率
            "max_odds": 10.0                 # 最高赔率
        }
    
    def process(self, task: Dict) -> Dict:
        """处理风险管理任务"""
        self.status = AgentStatus.RUNNING
        
        action = task.get('action', 'risk_assessment')
        params = task.get('params', {})
        
        if action == 'risk_assessment':
            result = self._risk_assessment(params)
        elif action == 'position_sizing':
            result = self._calculate_position_size(params)
        elif action == 'stop_loss_check':
            result = self._check_stop_loss(params)
        else:
            result = {"error": f"Unknown action: {action}"}
        
        self.status = AgentStatus.COMPLETED

        if isinstance(result, dict):
            result.setdefault("data_source", f"{self.agent_id}:{action}")
        
        # 如果子方法返回了 next_agent (如触发了打回)，保留它
        if "next_agent" not in result:
            result["next_agent"] = None
            
        return DomainKernel.attach("risk-manager", result)
    
    def _risk_assessment(self, params: Dict) -> Dict:
        """风险评估"""
        bet = params.get('bet', {})
        bankroll = params.get('bankroll', 1000)
        decision = params.get("decision")
        decision_reason = params.get("decision_reason")
        expected_value = params.get("expected_value")

        if decision == "skip" or not bet:
            return {
                "status": "success",
                "checks": {},
                "risk_score": 0.0,
                "recommendation": "skip",
                "reason": decision_reason or "策略建议不下注",
                "expected_value": expected_value
            }
        
        stake = bet.get('stake', 0)
        odds = bet.get('odds', 0)
        
        # 基础风险检查
        checks = {
            "stake_ratio": self._check_stake_ratio(stake, bankroll),
            "odds_range": self._check_odds_range(odds),
            "value": self._check_value(bet),
            "kelly_bet": self._calculate_kelly(stake, odds, bet.get('probability', 0.5))
        }
        
        # 综合风险评分
        risk_score = self._calculate_risk_score(checks)
        
        # 辩论机制 (Debate Mechanism)
        # 如果风险评分过高（或 Kelly 为 0），拒绝该策略并将其打回给 Strategist
        debate_count = params.get("debate_count", 0)
        max_debates = 1  # 允许最大辩论/打回次数
        
        is_approved = risk_score < 0.5 and checks["kelly_bet"]["has_edge"]
        
        if not is_approved and debate_count < max_debates:
            # 触发打回重审
            return {
                "status": "success",
                "checks": checks,
                "risk_score": risk_score,
                "recommendation": "reject_and_replan",
                "reason": f"风控拒绝(Kelly={checks['kelly_bet']['optimal_bet_ratio']:.2f}, Risk={risk_score:.2f})。要求 Strategist 重新寻找对冲(Hedge)或亚盘(Handicap)策略。",
                "next_agent": "strategist",
                "handoff_params": {
                    "debate_count": debate_count + 1,
                    "rejection_reason": self._get_risk_reason(checks),
                    "original_bet": bet
                }
            }
        
        return {
            "status": "success",
            "checks": checks,
            "risk_score": risk_score,
            "recommendation": "approve" if is_approved else "final_reject",
            "reason": self._get_risk_reason(checks),
            "next_agent": None
        }
    
    def _check_stake_ratio(self, stake: float, bankroll: float) -> Dict:
        """检查资金比例"""
        ratio = stake / bankroll if bankroll > 0 else 1
        max_ratio = self.risk_rules['max_single_stake_ratio']
        
        return {
            "ratio": ratio,
            "max_allowed": max_ratio,
            "passed": ratio <= max_ratio,
            "message": f"投注比例 {ratio:.1%} (限制: {max_ratio:.1%})"
        }
    
    def _check_odds_range(self, odds: float) -> Dict:
        """检查赔率范围"""
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
        """检查价值"""
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
    
    def _calculate_kelly(self, stake: float, odds: float, probability: float) -> Dict:
        """
        计算真实的凯利公式仓位 (Kelly Criterion)
        Kelly % = (bp - q) / b
        p = 获胜概率, q = 1 - p (失败概率)
        b = 赔率 - 1 (净赔率)
        """
        kelly_fraction = self.risk_rules['kelly_fraction']
        
        if probability <= 0 or odds <= 1:
            optimal_bet = 0
            has_edge = False
        else:
            q = 1 - probability
            p = probability
            b = odds - 1
            
            kelly = (b * p - q) / b if b > 0 else 0
            
            # 只在 Kelly > 0 (即有正向期望值) 时投注
            if kelly > 0:
                # 结合半凯利或分数凯利控制风险
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
        """计算风险评分"""
        score = 0.0
        
        if not checks['stake_ratio']['passed']:
            score += 0.4
        if not checks['odds_range']['passed']:
            score += 0.3
        if not checks['value']['has_value']:
            score += 0.2
        
        return min(1.0, score)
    
    def _get_risk_reason(self, checks: Dict) -> str:
        """获取风险原因"""
        reasons = []
        if not checks['stake_ratio']['passed']:
            reasons.append(checks['stake_ratio']['message'])
        if not checks['odds_range']['passed']:
            reasons.append(checks['odds_range']['message'])
        if not checks['value']['has_value']:
            reasons.append(checks['value']['message'])
        
        return "; ".join(reasons) if reasons else "通过风控检查"
    
    def _calculate_position_size(self, params: Dict) -> Dict:
        """计算仓位大小"""
        bankroll = params.get('bankroll', 1000)
        odds = params.get('odds', 2.0)
        probability = params.get('probability', 0.5)
        confidence = params.get('confidence', 0.7)
        
        kelly = self._calculate_kelly(100, odds, probability)
        
        return {
            "recommended_stake": bankroll * kelly['optimal_bet_ratio'] * confidence,
            "max_stake": bankroll * self.risk_rules['max_single_stake_ratio'],
            "unit": "金额"
        }
    
    def _check_stop_loss(self, params: Dict) -> Dict:
        """检查止损"""
        daily_loss = params.get('daily_loss', 0)
        bankroll = params.get('bankroll', 1000)
        consecutive_losses = params.get('consecutive_losses', 0)
        
        loss_ratio = daily_loss / bankroll if bankroll > 0 else 0
        max_loss = self.risk_rules['max_daily_loss_ratio']
        
        should_stop = (
            loss_ratio >= max_loss or
            consecutive_losses >= self.risk_rules['max_consecutive_losses']
        )
        
        return {
            "should_stop": should_stop,
            "loss_ratio": loss_ratio,
            "consecutive_losses": consecutive_losses,
            "message": "建议停止投注" if should_stop else "可以继续"
        }
