import asyncio
import os
import sys
import json
import logging
from typing import Dict, Any, List
from itertools import combinations

from agents.async_base import AsyncBaseAgent
try:
    from tools.llm_service import LLMService
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False

logger = logging.getLogger(__name__)

def _breakeven_odds(probability: float):
    try:
        p = float(probability)
        if p <= 0: return None
        return 1.0 / p
    except Exception: return None

def _odds_move_to_positive_ev(current_odds: float, probability: float, epsilon: float = 0.0):
    try:
        p = float(probability)
        o = float(current_odds)
        if p <= 0: return None
        target = (1.0 + float(epsilon)) / p
        delta = target - o
        return {"target_odds": target, "delta_odds": delta}
    except Exception: return None

def _odds_move_to_positive_ev_with_push(current_odds: float, p_win: float, p_push: float, epsilon: float = 0.0):
    try:
        o = float(current_odds)
        pw = float(p_win)
        pp = float(p_push)
        if pw <= 0: return None
        target = (1.0 + float(epsilon) - pp) / pw
        delta = target - o
        return {"target_odds": target, "delta_odds": delta}
    except Exception: return None


class AsyncStrategistAgent(AsyncBaseAgent):
    """
    2026 Next-Gen Async Strategist Agent
    基于全局 State 生成投资策略和期望值，剥离了同步依赖。
    """
    def __init__(self, config=None):
        super().__init__("strategist", "策略制定", config)

    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """处理策略制定任务，从全局 state 获取 analyst 的输出"""
        self.status = "running"
        
        print(f"\n[AsyncStrategist] 正在制定投资组合策略...")
        
        # 使用 asyncio.to_thread 防止 CPU 密集型计算阻塞
        data = await asyncio.to_thread(self._generate_strategy_logic, state)

        # 异步 LLM 分析报告
        if API_AVAILABLE:
            system_prompt = "你是一名顶级的足彩策略大师。请阅读数学模型分配的资金比例、凯利指数和推荐策略，向用户生动地解释为什么推荐这个策略，以及如何控制风险。"
            clean_data = {k: v for k, v in data.items() if k not in ["status", "timestamp"]}
            data_context = json.dumps(clean_data, ensure_ascii=False)
            try:
                ai_report = await asyncio.to_thread(LLMService.generate_report, system_prompt, data_context)
                data["ai_report"] = ai_report
            except Exception as e:
                logger.warning(f"LLM 报告生成失败: {e}")

        # 异步持久化
        await self.save_context("latest_strategy", data)
        
        self.status = "completed"
        return {"strategist_data": data}

    def _generate_strategy_logic(self, state: Dict[str, Any]) -> Dict:
        """核心策略逻辑 (同步执行，被线程池包裹)"""
        analyst_data = state.get("analyst_data", {})
        params = state.get("params", {})
        debate_count = state.get("debate_count", 0)
        rejection_reason = state.get("rejection_reason", "")
        
        probabilities = analyst_data.get("probabilities", {})
        markets = analyst_data.get("markets", {})
        professional_data = analyst_data.get("professional_data", {})
        
        lottery_type = params.get("lottery_type", "jingcai")
        matches = params.get('matches', [])
        budget = params.get('budget', 100)
        risk_level = params.get('risk_level', 'medium')
        odds = analyst_data.get('odds', params.get('odds', {}))
        
        professional_strategy = None
        
        if not matches and odds:
            match_info = {'home': odds.get('home', 2.0), 'draw': odds.get('draw', 3.2), 'away': odds.get('away', 3.5)}
            matches = [{'odds': match_info, 'selection': 'home'}]

        if lottery_type == "jingcai" and "poisson" in professional_data:
            # 简化版竞彩单场推荐
            professional_strategy = {
                "type": "jingcai_single",
                "description": "竞彩单场价值投注",
                "risk": "medium"
            }
        elif lottery_type == "beijing":
            if "sxd" in professional_data:
                most_likely = professional_data["sxd"].get("most_likely")
                if most_likely:
                    professional_strategy = {
                        "type": "beijing_sxd",
                        "description": f"北单上下单双推荐: {most_likely}",
                        "risk": "medium"
                    }
        elif lottery_type == "traditional" and "trad_14" in professional_data:
            professional_strategy = {
                "type": "traditional_rx9",
                "description": "任选九场：建议 6胆3双选防冷",
                "risk": "high"
            }
            
        strategies = self._analyze_strategies(matches, budget, risk_level)
        best_strategy = professional_strategy if professional_strategy else self._select_best_strategy(strategies)
        budget_allocation = self._allocate_budget(budget, best_strategy)

        bankroll = params.get("bankroll", budget)
        max_single_stake_ratio = params.get("risk_rules", {}).get("max_single_stake_ratio", 0.1)
        bet = None
        expected_value = None
        thresholds = {"1x2": {}, "totals": {}, "handicap": {}}
        
        try:
            best_matches = best_strategy.get("matches", []) if isinstance(best_strategy, dict) else []
            if best_matches:
                first = best_matches[0]
                odds_map = first.get("odds", {}) if isinstance(first.get("odds", {}), dict) else {}
                candidates = []
                for selection in ["home", "draw", "away"]:
                    o = odds_map.get(selection)
                    p = probabilities.get(selection)
                    if o and p:
                        if lottery_type == "beijing":
                            actual_o = float(o) * 0.65
                        else:
                            actual_o = float(o)
                            
                        ev = (actual_o * float(p)) - 1
                        thresholds["1x2"][selection] = {
                            "breakeven_odds": _breakeven_odds(p),
                            "move_to_positive_ev": _odds_move_to_positive_ev(actual_o, p, epsilon=0.0)
                        }
                        candidates.append({"market": "1x2", "selection": selection, "odds": float(o), "probability": float(p), "expected_value": ev})

                candidates.sort(key=lambda x: x["expected_value"], reverse=True)
                best_candidate = candidates[0] if candidates else None
                if best_candidate:
                    selection = best_candidate["selection"]
                    proposed_stake = float(best_strategy.get("recommended_stake", budget_allocation.get("unit_bet", 0)))
                    stake_cap = float(bankroll) * float(max_single_stake_ratio)
                    stake = max(0.0, min(proposed_stake, stake_cap))
                    expected_value = best_candidate["expected_value"]
                    bet = {
                        "stake": stake,
                        "odds": best_candidate["odds"],
                        "probability": best_candidate["probability"],
                        "type": best_candidate.get("market", best_strategy.get("type", "single")),
                        "selection": selection,
                        "market": best_candidate.get("market"),
                        "line": best_candidate.get("line"),
                        "expected_value": expected_value
                    }
        except Exception:
            pass

        decision = "bet"
        decision_reason = None
        
        if debate_count > 0:
            decision = "skip"
            decision_reason = f"风控驳回后重新评估: {rejection_reason}。系统当前无法找到更好的对冲或亚指替代方案，放弃投注。"
        else:
            if expected_value is None:
                decision = "skip"
                decision_reason = "无法计算期望值"
            elif expected_value <= 0:
                decision = "skip"
                decision_reason = f"期望值为负 ({expected_value:.4f})"
            elif bet and bet.get("stake", 0) <= 0:
                decision = "skip"
                decision_reason = "投注金额为0"

        return {
            "status": "success",
            "strategies": strategies,
            "recommended": best_strategy,
            "budget_allocation": budget_allocation,
            "decision": decision,
            "expected_value": expected_value,
            "decision_reason": decision_reason,
            "thresholds": thresholds,
            "bet": bet if decision == "bet" else None
        }

    def _analyze_strategies(self, matches: List, budget: float, risk_level: str) -> List[Dict]:
        strategies = []
        if risk_level in ['low', 'medium']:
            strategies.append({
                "type": "single",
                "description": "单关投注",
                "matches": matches[:1],
                "risk": "low",
                "min_odds": 1.5,
                "recommended_stake": budget * 0.2
            })
        return strategies

    def _select_best_strategy(self, strategies: List[Dict]) -> Dict:
        if not strategies: return {"type": "none", "reason": "无可用策略"}
        for strategy in strategies:
            if strategy.get('risk') == 'medium': return strategy
        return strategies[0]

    def _allocate_budget(self, total_budget: float, strategy: Dict) -> Dict:
        stake = strategy.get('recommended_stake', total_budget * 0.3)
        matches = strategy.get('matches', [])
        match_count = len(matches) if matches else 1
        return {
            "total_budget": total_budget,
            "allocated_stake": stake,
            "reserve": total_budget - stake,
            "unit_bet": stake / match_count if match_count > 0 else stake
        }
