#!/usr/bin/env python3
"""
风控Agent
功能：
1. 仓位控制
2. 止损机制
3. 预期值验证
"""

import os
import sys
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import deque
from dataclasses import dataclass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BASE_DIR = os.path.dirname(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)

from core.base_agent import BaseAgent, AgentStatus, Task, get_registry


@dataclass
class Position:
    """仓位记录"""
    bet_id: str
    stake: float
    odds: float
    timestamp: datetime
    status: str = "open"  # open, won, lost


class RiskManagerAgent(BaseAgent):
    """风控Agent - 负责风险管理和仓位控制"""
    
    # 风控参数
    MAX_DAILY_LOSS = 50.0  # 每日最大亏损
    MAX_POSITION_RATIO = 0.2  # 最大仓位比例
    MIN_ODDS = 1.1  # 最小赔率
    MAX_ODDS = 5.0  # 最大赔率
    STOP_LOSS_RATIO = -0.15  # 止损线 -15%
    
    def __init__(self, message_bus=None):
        super().__init__("RiskManagerAgent", message_bus)
        self._positions: List[Position] = []
        self._daily_pnl: float = 0.0
        self._history: deque = deque(maxlen=100)
        self._stop_loss_triggered = False
    
    def initialize(self) -> bool:
        """初始化Agent"""
        self.set_status(AgentStatus.IDLE)
        get_registry().register(self)
        return True
    
    def process(self, task: Task) -> Dict[str, Any]:
        """处理任务"""
        self.set_status(AgentStatus.RUNNING)
        
        task_type = task.task_type
        payload = task.payload
        
        try:
            if task_type == "position_check":
                result = self.check_position(
                    payload.get("stake", 0),
                    payload.get("odds", 1.0),
                    payload.get("budget", 100)
                )
            elif task_type == "stop_loss":
                result = self.check_stop_loss(
                    payload.get("current_loss", 0),
                    payload.get("budget", 100)
                )
            elif task_type == "validate_bet":
                result = self.validate_bet(
                    payload.get("bet", {})
                )
            elif task_type == "risk_report":
                result = self.get_risk_report()
            elif task_type == "position_size":
                result = self.calculate_position_size(
                    payload.get("budget", 100),
                    payload.get("odds", 1.5),
                    payload.get("win_prob", 0.5),
                    payload.get("risk_tolerance", "medium")
                )
            elif task_type == "kelly_criterion":
                result = self.kelly_criterion(
                    payload.get("odds", 1.5),
                    payload.get("win_prob", 0.5)
                )
            elif task_type == "daily_limit":
                result = self.check_daily_limit(
                    payload.get("proposed_stake", 0)
                )
            else:
                result = {"error": f"Unknown task type: {task_type}"}
            
            self.set_status(AgentStatus.COMPLETED)
            return {"status": "success", "result": result}
            
        except Exception as e:
            self.set_status(AgentStatus.ERROR)
            self._last_error = str(e)
            return {"status": "error", "error": str(e)}
    
    def check_position(self, stake: float, odds: float, budget: float) -> Dict:
        """检查仓位是否合理"""
        position_ratio = stake / budget
        exposure = stake * odds / budget
        
        # 检查各项指标
        issues = []
        if position_ratio > self.MAX_POSITION_RATIO:
            issues.append(f"仓位过重: {position_ratio*100:.1f}% (最大{self.MAX_POSITION_RATIO*100}%)")
        if odds < self.MIN_ODDS:
            issues.append(f"赔率过低: {odds:.2f} (最小{self.MIN_ODDS})")
        if odds > self.MAX_ODDS:
            issues.append(f"赔率过高: {odds:.2f} (最大{self.MAX_ODDS})")
        
        # Kelly计算
        kelly = self.kelly_criterion(odds, 0.5)
        recommended_kelly = kelly.get("optimal_fraction", 0) * budget
        
        return {
            "stake": stake,
            "odds": odds,
            "budget": budget,
            "position_ratio": round(position_ratio * 100, 1),
            "exposure": round(exposure * 100, 1),
            "is_safe": len(issues) == 0,
            "issues": issues,
            "kelly_recommendation": round(recommended_kelly, 2),
            "recommendation": "通过" if len(issues) == 0 else "建议调整"
        }
    
    def check_stop_loss(self, current_loss: float, budget: float) -> Dict:
        """检查是否触发止损"""
        loss_ratio = current_loss / budget if budget > 0 else 0
        should_stop = loss_ratio <= self.STOP_LOSS_RATIO
        
        if should_stop and not self._stop_loss_triggered:
            self._stop_loss_triggered = True
        
        return {
            "current_loss": current_loss,
            "budget": budget,
            "loss_ratio": round(loss_ratio * 100, 1),
            "stop_loss_threshold": round(self.STOP_LOSS_RATIO * 100, 1),
            "should_stop": should_stop,
            "stop_loss_triggered": self._stop_loss_triggered,
            "recommendation": "立即止损" if should_stop else "继续观察"
        }
    
    def validate_bet(self, bet: Dict) -> Dict:
        """验证投注是否可行"""
        errors = []
        warnings = []
        
        # 必填字段检查
        required = ["stake", "odds", "match_id"]
        for field in required:
            if field not in bet or bet[field] is None:
                errors.append(f"缺少必填字段: {field}")
        
        if errors:
            return {"valid": False, "errors": errors}
        
        # 数值检查
        if bet["stake"] <= 0:
            errors.append("投注金额必须大于0")
        if bet["odds"] < self.MIN_ODDS:
            errors.append(f"赔率过低: {bet['odds']}")
        if bet["odds"] > self.MAX_ODDS:
            warnings.append(f"赔率偏高: {bet['odds']}")
        
        # 价值检查
        implied_prob = 1 / bet["odds"] if bet["odds"] > 0 else 0
        estimated_prob = bet.get("estimated_prob", 0.5)
        value = implied_prob - estimated_prob
        
        if value < -0.1:
            warnings.append("负价值投注")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "analysis": {
                "implied_prob": round(implied_prob * 100, 1),
                "estimated_prob": round(estimated_prob * 100, 1),
                "value": round(value * 100, 1),
                "recommendation": "建议投注" if value > 0 else "不建议" if value < -0.05 else "谨慎"
            }
        }
    
    def get_risk_report(self) -> Dict:
        """获取风控报告"""
        open_positions = [p for p in self._positions if p.status == "open"]
        total_exposure = sum(p.stake * p.odds for p in open_positions)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "daily_pnl": round(self._daily_pnl, 2),
            "total_positions": len(self._positions),
            "open_positions": len(open_positions),
            "total_exposure": round(total_exposure, 2),
            "stop_loss_triggered": self._stop_loss_triggered,
            "recent_history": list(self._history)[-5:],
            "risk_metrics": {
                "max_daily_loss": self.MAX_DAILY_LOSS,
                "max_position_ratio": self.MAX_POSITION_RATIO,
                "stop_loss_ratio": self.STOP_LOSS_RATIO
            }
        }
    
    def calculate_position_size(self, budget: float, odds: float, 
                                  win_prob: float, risk_tolerance: str) -> Dict:
        """计算仓位大小"""
        # Kelly fraction
        kelly = self.kelly_criterion(odds, win_prob)
        optimal_kelly = kelly.get("optimal_fraction", 0)
        
        # 根据风险偏好调整
        risk_multipliers = {
            "low": 0.25,      # 保守：使用1/4 Kelly
            "medium": 0.5,   # 中等：使用1/2 Kelly
            "high": 0.75     # 激进：使用3/4 Kelly
        }
        
        multiplier = risk_multipliers.get(risk_tolerance, 0.5)
        adjusted_kelly = optimal_kelly * multiplier
        
        # 限制最大仓位
        max_position = budget * self.MAX_POSITION_RATIO
        recommended_stake = min(budget * adjusted_kelly, max_position)
        
        return {
            "budget": budget,
            "odds": odds,
            "win_probability": round(win_prob * 100, 1),
            "risk_tolerance": risk_tolerance,
            "kelly_fraction": round(optimal_kelly * 100, 1),
            "adjusted_kelly": round(adjusted_kelly * 100, 1),
            "recommended_stake": round(recommended_stake, 2),
            "max_allowed_stake": round(max_position, 2),
            "expected_value": round(kelly.get("expected_value", 0) * 100, 1),
            "recommendation": self._get_position_recommendation(recommended_stake, max_position)
        }
    
    def _get_position_recommendation(self, recommended: float, max_allowed: float) -> str:
        """获取仓位建议"""
        if recommended < max_allowed * 0.5:
            return "低仓位，安全"
        elif recommended < max_allowed * 0.8:
            return "适中仓位，可接受"
        else:
            return "高仓位，注意风险"
    
    def kelly_criterion(self, odds: float, win_prob: float) -> Dict:
        """Kelly公式计算"""
        # Kelly = (bp - q) / b
        # b = odds - 1, p = win_prob, q = 1 - p
        b = odds - 1
        p = win_prob
        q = 1 - p
        
        if b <= 0:
            return {
                "optimal_fraction": 0,
                "expected_value": 0,
                "recommendation": "不建议投注"
            }
        
        kelly = (b * p - q) / b
        expected_value = p * (odds - 1) - q
        
        return {
            "optimal_fraction": max(0, kelly),
            "expected_value": expected_value,
            "win_probability": p,
            "odds": odds,
            "recommendation": "投注" if kelly > 0 else "不建议投注"
        }
    
    def check_daily_limit(self, proposed_stake: float) -> Dict:
        """检查每日限额"""
        today_pnl = self._daily_pnl
        
        # 计算今日已用额度
        today_stake = sum(
            p.stake for p in self._positions
            if p.timestamp.date() == datetime.now().date()
        )
        
        remaining_budget = self.MAX_DAILY_LOSS - today_pnl
        
        return {
            "proposed_stake": proposed_stake,
            "today_stake": round(today_stake, 2),
            "remaining_budget": round(remaining_budget, 2),
            "can_bet": proposed_stake <= remaining_budget,
            "recommendation": "可以投注" if proposed_stake <= remaining_budget else "超出限额"
        }
    
    def record_bet(self, bet_id: str, stake: float, odds: float) -> None:
        """记录投注"""
        position = Position(
            bet_id=bet_id,
            stake=stake,
            odds=odds,
            timestamp=datetime.now()
        )
        self._positions.append(position)
    
    def settle_bet(self, bet_id: str, won: bool, actual_odds: float = None) -> None:
        """结算投注"""
        for pos in self._positions:
            if pos.bet_id == bet_id:
                pos.status = "won" if won else "lost"
                actual_odds = actual_odds or pos.odds
                
                if won:
                    pnl = pos.stake * (actual_odds - 1)
                else:
                    pnl = -pos.stake
                
                self._daily_pnl += pnl
                self._history.append({
                    "bet_id": bet_id,
                    "stake": pos.stake,
                    "pnl": round(pnl, 2),
                    "timestamp": pos.timestamp.isoformat()
                })
                break
    
    def reset_daily(self) -> None:
        """重置每日状态"""
        self._daily_pnl = 0.0
        self._stop_loss_triggered = False
    
    def get_capabilities(self) -> Dict[str, Any]:
        """获取Agent能力"""
        return {
            "name": self.name,
            "type": "risk_manager",
            "functions": [
                "position_check - 仓位检查",
                "stop_loss - 止损检查",
                "validate_bet - 投注验证",
                "risk_report - 风控报告",
                "position_size - 仓位计算",
                "kelly_criterion - Kelly公式",
                "daily_limit - 每日限额"
            ],
            "parameters": {
                "max_daily_loss": self.MAX_DAILY_LOSS,
                "max_position_ratio": self.MAX_POSITION_RATIO,
                "min_odds": self.MIN_ODDS,
                "max_odds": self.MAX_ODDS,
                "stop_loss_ratio": self.STOP_LOSS_RATIO
            },
            "status": self.status.value
        }


# 便捷函数
def create_risk_manager_agent(message_bus=None) -> RiskManagerAgent:
    """创建RiskManagerAgent实例"""
    agent = RiskManagerAgent(message_bus)
    agent.initialize()
    return agent


__all__ = ['RiskManagerAgent', 'create_risk_manager_agent', 'Position']