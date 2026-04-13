#!/usr/bin/env python3
"""
策略制定Agent - OpenClaw规范版本
Strategist Agent
"""

import os
import sys
import json
import logging
import math
from typing import Dict, List, Any, Optional
from datetime import datetime
from itertools import combinations

# 确保能找到tools模块
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 注入 LotteryMathEngine
sys.path.insert(0, os.path.join(PROJECT_ROOT, "../../../analyzer/football-lottery-analyzer"))
try:
    from skills.lottery_math_engine import LotteryMathEngine
    MATH_ENGINE_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"LotteryMathEngine 导入失败: {e}")
    MATH_ENGINE_AVAILABLE = False

from .base import BaseAgent, AgentStatus, Message

logger = logging.getLogger(__name__)

def _breakeven_odds(probability: float):
    try:
        p = float(probability)
        if p <= 0:
            return None
        return 1.0 / p
    except Exception:
        return None

def _odds_move_to_positive_ev(current_odds: float, probability: float, epsilon: float = 0.0):
    """
    EV = odds * p - 1
    目标：EV > epsilon
    => odds > (1 + epsilon) / p
    """
    try:
        p = float(probability)
        o = float(current_odds)
        if p <= 0:
            return None
        target = (1.0 + float(epsilon)) / p
        delta = target - o
        return {
            "target_odds": target,
            "delta_odds": delta
        }
    except Exception:
        return None

def _odds_move_to_positive_ev_with_push(current_odds: float, p_win: float, p_push: float, epsilon: float = 0.0):
    """
    EV = p_win * odds + p_push - 1
    目标：EV > epsilon
    => odds > (1 + epsilon - p_push) / p_win
    """
    try:
        o = float(current_odds)
        pw = float(p_win)
        pp = float(p_push)
        if pw <= 0:
            return None
        target = (1.0 + float(epsilon) - pp) / pw
        delta = target - o
        return {
            "target_odds": target,
            "delta_odds": delta
        }
    except Exception:
        return None

try:
    from tools.llm_service import LLMService
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False
    logger.warning("LLMService 导入失败。")


class StrategistAgent(BaseAgent):
    """
    策略制定Agent
    
    职责：
    1. 生成M串N投注方案
    2. 资金分配建议
    3. 风险收益评估
    4. 最优组合推荐
    """
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__("strategist", "策略制定", config)
    
    def process(self, task: Dict) -> Dict:
        """处理策略制定任务"""
        self.status = AgentStatus.RUNNING
        
        action = task.get('action', 'generate_strategy')
        params = task.get('params', {})
        
        # 检查是否是被 RiskManager 打回的辩论任务
        debate_count = params.get('debate_count', 0)
        rejection_reason = params.get('rejection_reason', '')
        
        if action == 'generate_strategy':
            result = self._generate_strategy(task)
        elif action == 'quick_recommend':
            result = self._quick_recommend(params)
        elif action == 'generate_parlay':
            result = self._generate_parlay(params)
        else:
            result = {"error": f"Unknown action: {action}"}
            
        # 如果是辩论状态，将其记录到输出中
        if debate_count > 0:
            result['debate_context'] = {
                'rejection_reason': rejection_reason,
                'debate_count': debate_count
            }
        
        self.status = AgentStatus.COMPLETED
        
        result["next_agent"] = "risk_manager"
        
        return result
    
    def _generate_strategy(self, task: Dict) -> Dict:
        """生成投注策略"""
        params = task.get('params', {})
        probabilities = task.get("probabilities", {}) if isinstance(task.get("probabilities", {}), dict) else {}
        markets = task.get("markets", {}) if isinstance(task.get("markets", {}), dict) else {}
        professional_data = task.get("professional_data", {})
        lottery_type = params.get("lottery_type", "jingcai")
        matches = params.get('matches', [])
        budget = params.get('budget', 100)
        risk_level = params.get('risk_level', 'medium')
        odds = params.get('odds', {})
        debate_count = params.get('debate_count', 0)
        rejection_reason = params.get('rejection_reason', '')
        
        # ====== 路由调用专业策略模块 ======
        professional_strategy = None
        
        # 如果没有提供matches，从odds构建
        if not matches and odds:
            # 构建单一比赛匹配
            match_info = {
                'home': odds.get('home', 2.0),
                'draw': odds.get('draw', 3.2),
                'away': odds.get('away', 3.5)
            }
            matches = [{'odds': match_info, 'selection': 'home'}]
            
        if lottery_type == "jingcai":
            # 如果是竞彩，且有多场比赛，理论上应该调用 ParlayOptimizer
            if len(matches) >= 2:
                sys.path.insert(0, os.path.join(PROJECT_ROOT, "../../../analyzer/football-lottery-analyzer/agents"))
                try:
                    from jingcai_professional import ParlayOptimizer
                    optimizer = ParlayOptimizer({"matches": matches})
                    selected_matches = []
                    for i, m in enumerate(matches):
                        # 简单地选主胜构建mock结构
                        o = m.get('odds', {}).get('home', 2.0)
                        selected_matches.append({'match': f'Match {i+1}', 'odds': o, 'confidence': 0.8})
                    
                    res = optimizer.optimize_mxn(selected_matches, budget, risk_level)
                    if "error" not in res:
                        professional_strategy = {
                            "type": "jingcai_mxn",
                            "description": f"竞彩串关推荐: {res.get('recommended', {}).get('description', 'M串N')}",
                            "risk": risk_level,
                            "details": res
                        }
                except Exception as e:
                    logger.warning(f"竞彩串关优化失败: {e}")
            else:
                # 单场模式，提取半全场推荐
                if "poisson" in professional_data:
                    pass
        elif lottery_type == "beijing":
            # 北单：结合上下单双生成串关
            if len(matches) >= 2:
                sys.path.insert(0, os.path.join(PROJECT_ROOT, "../../../analyzer/football-lottery-analyzer/agents"))
                try:
                    from beijing_analyzer_v2 import BeijingParlayOptimizer
                    optimizer = BeijingParlayOptimizer({"matches": matches})
                    selected_matches = []
                    for i, m in enumerate(matches):
                        # 北单是浮动奖金，我们取平均SP模拟
                        o = m.get('odds', {}).get('home', 3.0)
                        selected_matches.append({'match': f'Match {i+1}', 'odds': o, 'confidence': 0.8})
                    
                    res = optimizer.optimize_parlay(selected_matches, budget)
                    if "error" not in res:
                        # 选出最推荐的组合（比如成本在预算内，注数适中的）
                        rec = res.get("recommended_combinations", [])
                        best_rec = rec[0] if rec else {}
                        if best_rec:
                            professional_strategy = {
                                "type": "beijing_parlay",
                                "description": f"北单串关推荐: {best_rec.get('type')}",
                                "risk": "high",
                                "details": res
                            }
                except Exception as e:
                    logger.warning(f"北单串关优化失败: {e}")
            elif "sxd" in professional_data:
                # 从 sxd 提取推荐
                most_likely = professional_data["sxd"].get("most_likely")
                if most_likely:
                    professional_strategy = {
                        "type": "beijing_sxd",
                        "description": f"北单上下单双推荐: {most_likely}",
                        "risk": "medium"
                    }
        elif lottery_type == "traditional":
            # 传统足彩：生成胆拖方案
            if len(matches) == 14:
                sys.path.insert(0, os.path.join(PROJECT_ROOT, "../../../analyzer/football-lottery-analyzer/agents"))
                try:
                    from traditional_professional import RX9Optimizer
                    optimizer = RX9Optimizer({"matches": matches})
                    confidence_levels = [0.8] * 14 # 模拟
                    res = optimizer.optimize_rx9(matches, budget, confidence_levels)
                    if "error" not in res:
                        professional_strategy = {
                            "type": "traditional_rx9",
                            "description": f"任选九场：建议 {res.get('dan_tuo_plan', {}).get('dan_count')}胆{res.get('dan_tuo_plan', {}).get('tuo_count')}拖",
                            "risk": "medium",
                            "details": res
                        }
                except Exception as e:
                    logger.warning(f"任九优化失败: {e}")
            elif "trad_14" in professional_data:
                professional_strategy = {
                    "type": "traditional_rx9",
                    "description": "任选九场：建议 6胆3双选防冷",
                    "risk": "high"
                }
        # ===============================
        
        # 分析可用方案
        strategies = self._analyze_strategies(matches, budget, risk_level)
        
        # 选择最优策略
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
                        ev = (float(o) * float(p)) - 1
                        thresholds["1x2"][selection] = {
                            "breakeven_odds": _breakeven_odds(p),
                            "move_to_positive_ev": _odds_move_to_positive_ev(o, p, epsilon=0.0)
                        }
                        candidates.append({"market": "1x2", "selection": selection, "odds": float(o), "probability": float(p), "expected_value": ev})

                totals = markets.get("totals", {}) if isinstance(markets.get("totals", {}), dict) else {}
                totals_probs = totals.get("probabilities", {}) if isinstance(totals.get("probabilities", {}), dict) else {}
                totals_odds = totals.get("odds", {}) if isinstance(totals.get("odds", {}), dict) else {}
                totals_line = totals.get("line")
                for selection in ["over", "under"]:
                    o = totals_odds.get(selection)
                    p = totals_probs.get(selection)
                    if o and p:
                        ev = (float(o) * float(p)) - 1
                        thresholds["totals"][selection] = {
                            "line": totals_line,
                            "breakeven_odds": _breakeven_odds(p),
                            "move_to_positive_ev": _odds_move_to_positive_ev(o, p, epsilon=0.0)
                        }
                        candidates.append({"market": "totals", "line": totals_line, "selection": selection, "odds": float(o), "probability": float(p), "expected_value": ev})

                handicap = markets.get("handicap", {}) if isinstance(markets.get("handicap", {}), dict) else {}
                handicap_probs = handicap.get("probabilities", {}) if isinstance(handicap.get("probabilities", {}), dict) else {}
                handicap_odds = handicap.get("odds", {}) if isinstance(handicap.get("odds", {}), dict) else {}
                handicap_line = handicap.get("line")
                p_push = handicap_probs.get("push", 0)
                for selection, win_key in [("home", "home_win"), ("away", "away_win")]:
                    o = handicap_odds.get(selection)
                    p_win = handicap_probs.get(win_key)
                    if o and p_win is not None:
                        ev = (float(o) * float(p_win)) + float(p_push) - 1
                        thresholds["handicap"][selection] = {
                            "line": handicap_line,
                            "breakeven_odds": (1 - float(p_push)) / float(p_win) if float(p_win) > 0 else None,
                            "move_to_positive_ev": _odds_move_to_positive_ev_with_push(o, p_win, p_push, epsilon=0.0)
                        }
                        candidates.append({"market": "handicap", "line": handicap_line, "selection": selection, "odds": float(o), "probability": float(p_win), "push_probability": float(p_push), "expected_value": ev})

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
                    if "push_probability" in best_candidate:
                        bet["push_probability"] = best_candidate.get("push_probability")
                    try:
                        if best_candidate.get("market") == "1x2":
                            first["selection"] = selection
                    except Exception:
                        pass
        except Exception:
            bet = None
            expected_value = None

        decision = "bet"
        decision_reason = None
        
        # 辩论机制响应: 如果是风控打回重审
        if debate_count > 0:
            decision = "skip"
            decision_reason = f"风控驳回后重新评估: {rejection_reason}。系统当前无法找到更好的对冲或亚指替代方案，放弃投注。"
            # 在真实的 LLM 驱动下，这里会让 LLM 重新挑选 candidates 里的第二优选（比如放弃主胜，选大球）
            # 由于目前是规则引擎驱动，如果最优 candidate 被打回，我们就记录下辩论结果并 skip。
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
        
        # 结构化数据
        data = {
            "status": "success",
            "strategies": strategies,
            "recommended": best_strategy,
            "budget_allocation": budget_allocation,
            "decision": decision,
            "expected_value": expected_value,
            "decision_reason": decision_reason,
            "thresholds": thresholds,
            "timestamp": datetime.now().isoformat()
        }
        if bet and decision == "bet":
            data["bet"] = bet
            data["next_agent"] = "risk_manager"
            data["handoff_params"] = {
                "bankroll": bankroll,
                "bet": bet,
                "strategies": strategies,
                "recommended": best_strategy
            }
        else:
            data["next_agent"] = "risk_manager"
            data["handoff_params"] = {
                "bankroll": bankroll,
                "bet": None,
                "decision": decision,
                "decision_reason": decision_reason,
                "expected_value": expected_value,
                "thresholds": thresholds,
                "strategies": strategies,
                "recommended": best_strategy
            }
        
        # --- LLM 智能生成自然语言分析报告 ---
        if API_AVAILABLE:
            system_prompt = "你是一名顶级的 Strategist (足彩策略大师)。你的任务是阅读数学模型为你分配的资金比例、凯利指数和推荐策略，并向用户生动地解释为什么推荐这个策略，以及如何控制风险。"
            clean_data = {k: v for k, v in data.items() if k not in ["status", "timestamp"]}
            data_context = json.dumps(clean_data, ensure_ascii=False)
            data["ai_report"] = LLMService.generate_report(system_prompt, data_context)
            
        return data
    
    def _analyze_strategies(self, matches: List, budget: float, risk_level: str) -> List[Dict]:
        """分析各种策略"""
        strategies = []
        
        # 单关策略
        if risk_level in ['low', 'medium']:
            strategies.append({
                "type": "single",
                "description": "单关投注",
                "matches": matches[:1],
                "risk": "low",
                "min_odds": 1.5,
                "recommended_stake": budget * 0.2
            })
        
        # 2串1策略
        if len(matches) >= 2:
            strategies.append({
                "type": "2串1",
                "description": "2串1过关",
                "matches": matches[:2],
                "risk": "medium",
                "combined_odds": 2.5,
                "recommended_stake": budget * 0.3
            })
        
        # 3串1策略
        if len(matches) >= 3:
            strategies.append({
                "type": "3串1",
                "description": "3串1过关",
                "matches": matches[:3],
                "risk": "high",
                "combined_odds": 4.0,
                "recommended_stake": budget * 0.2
            })
        
        # 自由过关策略
        if len(matches) >= 2:
            strategies.append({
                "type": "自由过关",
                "description": "2串1+3串1组合",
                "matches": matches[:3],
                "risk": "medium",
                "total_stake": budget * 0.3
            })
        
        return strategies
    
    def _select_best_strategy(self, strategies: List[Dict]) -> Dict:
        """选择最优策略"""
        if not strategies:
            return {"type": "none", "reason": "无可用策略"}
        
        # 简单选择逻辑：选择风险适中、期望收益最高的
        for strategy in strategies:
            if strategy.get('risk') == 'medium':
                return strategy
        
        return strategies[0]
    
    def _allocate_budget(self, total_budget: float, strategy: Dict) -> Dict:
        """分配资金"""
        stake = strategy.get('recommended_stake', total_budget * 0.3)
        matches = strategy.get('matches', [])
        match_count = len(matches) if matches else 1
        
        return {
            "total_budget": total_budget,
            "allocated_stake": stake,
            "reserve": total_budget - stake,
            "unit_bet": stake / match_count if match_count > 0 else stake
        }
    
    def _quick_recommend(self, params: Dict) -> Dict:
        """快速推荐"""
        max_bet = params.get('max_bet', 100)
        
        return {
            "status": "success",
            "recommendation": {
                "type": "2串1",
                "matches": ["曼联 胜", "皇马 胜"],
                "combined_odds": 2.2,
                "stake": max_bet * 0.3,
                "potential_return": max_bet * 0.3 * 2.2
            },
            "confidence": 0.75
        }
    
    def _generate_parlay(self, params: Dict) -> Dict:
        """生成串关方案"""
        matches = params.get('matches', [])
        m = params.get('m', 2)  # M串N
        n = params.get('n', 1)
        stake = params.get('stake', 100)
        
        if len(matches) < m:
            return {"error": "比赛数量不足"}
        
        # 生成所有可能的M串N组合
        combinations_list = list(combinations(matches, m))
        
        return {
            "status": "success",
            "type": f"{m}串{n}",
            "total_combinations": len(combinations_list),
            "stake_per_combination": stake / len(combinations_list) if combinations_list else 0,
            "combinations": [
                {"id": i, "matches": list(combo)}
                for i, combo in enumerate(combinations_list)
            ]
        }
