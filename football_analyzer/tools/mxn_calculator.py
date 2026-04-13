#!/usr/bin/env python3
"""
M串N计算器 - OpenClaw规范版本
MxN Calculator Tool
"""

from typing import Dict, List, Tuple
from itertools import combinations
import logging

logger = logging.getLogger(__name__)


class MxnCalculator:
    """
    M串N投注计算器
    
    功能：
    1. 生成M串N组合
    2. 计算复式投注
    3. 奖金计算
    4. 优化分析
    """
    
    def __init__(self):
        self.combinations_cache = {}
    
    def calculate(
        self,
        matches: List[Dict],
        m: int,
        n: int = 1,
        stake: float = 100
    ) -> Dict:
        """
        计算M串N投注
        
        Args:
            matches: 比赛列表 [{"id": "1", "odds": {"home": 1.8, "draw": 3.2, "away": 4.5}}]
            m: 串关场数
            n: 过关方式 (n=1 表示M串1全中)
            stake: 总投注金额
            
        Returns:
            计算结果
        """
        if len(matches) < m:
            return {"error": f"Need at least {m} matches"}
        
        # 生成所有M串1组合
        all_combinations = list(combinations(range(len(matches)), m))
        
        # 过滤掉不满足n条件的组合（简化处理）
        valid_combinations = self._filter_combinations(all_combinations, matches, n)
        
        # 计算每种组合的赔率和奖金
        combination_details = []
        total_combinations = len(valid_combinations)
        
        for combo_indices in valid_combinations:
            combo_matches = [matches[i] for i in combo_indices]
            combined_odds = self._calculate_combined_odds(combo_matches)
            bet_amount = stake / total_combinations if total_combinations > 0 else stake
            potential_prize = bet_amount * combined_odds
            
            combination_details.append({
                "indices": list(combo_indices),
                "matches": [m.get('id') for m in combo_matches],
                "combined_odds": combined_odds,
                "bet_amount": round(bet_amount, 2),
                "potential_prize": round(potential_prize, 2)
            })
        
        return {
            "type": f"{m}串{n}",
            "total_matches": len(matches),
            "total_combinations": total_combinations,
            "stake": stake,
            "stake_per_combination": round(stake / total_combinations, 2) if total_combinations > 0 else 0,
            "combinations": combination_details,
            "summary": self._generate_summary(combination_details, stake)
        }
    
    def _filter_combinations(
        self,
        combinations_list: List[Tuple],
        matches: List[Dict],
        n: int
    ) -> List[Tuple]:
        """过滤组合（简化处理）"""
        # n=1 表示只要中m场就中奖
        # 这里简化处理，返回所有组合
        return combinations_list
    
    def _calculate_combined_odds(self, matches: List[Dict]) -> float:
        """计算组合赔率"""
        total_odds = 1.0
        
        for match in matches:
            # 简化处理，选择赔率最高的选项
            odds = match.get('odds', {})
            max_odds = max(odds.values()) if odds else 1.0
            total_odds *= max_odds
        
        return total_odds
    
    def _generate_summary(
        self,
        combinations: List[Dict],
        stake: float
    ) -> Dict:
        """生成汇总"""
        if not combinations:
            return {}
        
        odds_list = [c['combined_odds'] for c in combinations]
        
        return {
            "min_odds": min(odds_list),
            "max_odds": max(odds_list),
            "avg_odds": sum(odds_list) / len(odds_list),
            "min_prize": min(c['potential_prize'] for c in combinations),
            "max_prize": max(c['potential_prize'] for c in combinations),
            "total_stake": stake,
            "roi_if_all_win": sum(c['potential_prize'] for c in combinations) / stake - 1 if stake > 0 else 0
        }
    
    def calculate_free_pass(
        self,
        matches: List[Dict],
        stake: float = 100
    ) -> Dict:
        """
        计算自由过关（2串1到M串1）
        
        Args:
            matches: 比赛列表
            stake: 总投注金额
            
        Returns:
            各种串关方案
        """
        results = {}
        
        for m in range(2, len(matches) + 1):
            result = self.calculate(matches, m, n=1, stake=stake)
            results[f"{m}串1"] = result
        
        return results
    
    def optimize_stake(
        self,
        matches: List[Dict],
        target_return: float = 1000,
        m: int = 2
    ) -> Dict:
        """
        优化投注金额以达到目标奖金
        
        Args:
            matches: 比赛列表
            target_return: 目标奖金
            m: 串关场数
            
        Returns:
            优化结果
        """
        if len(matches) < m:
            return {"error": "Not enough matches"}
        
        combined_odds = self._calculate_combined_odds(matches)
        
        if combined_odds <= 0:
            return {"error": "Invalid odds"}
        
        # 计算所需投注金额
        required_stake = target_return / combined_odds
        
        return {
            "matches": len(matches),
            "combined_odds": combined_odds,
            "target_return": target_return,
            "required_stake": round(required_stake, 2),
            "roi": (target_return - required_stake) / required_stake if required_stake > 0 else 0
        }
    
    def hedge_calculator(
        self,
        original_bet: Dict,
        new_odds: Dict,
        original_stake: float = 100
    ) -> Dict:
        """
        对冲计算器
        
        当原始投注结果不利于自己时，计算对冲投注
        """
        original_odds = original_bet.get('odds', 0)
        original_selection = original_bet.get('selection', 'home')
        
        if new_odds <= 0:
            return {"error": "Invalid new odds"}
        
        # 计算原始投注的潜在损失/盈利
        original_potential = original_stake * original_odds
        
        # 计算对冲金额
        hedge_stake = original_potential / new_odds
        
        # 计算对冲后的结果
        if original_bet.get('result') == 'win':
            # 原始投注赢了，对冲金额亏
            net_profit = original_potential - original_stake - hedge_stake
        else:
            # 原始投注输了，对冲中了
            net_profit = hedge_stake * new_odds - original_stake - hedge_stake
        
        return {
            "original_bet": original_bet,
            "original_stake": original_stake,
            "original_odds": original_odds,
            "new_odds": new_odds,
            "hedge_stake": round(hedge_stake, 2),
            "original_potential": original_potential,
            "net_profit": round(net_profit, 2),
            "guaranteed_return": round(-net_profit, 2)  # 对冲后的保证收益
        }
