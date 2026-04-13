#!/usr/bin/env python3
"""
记忆系统 - OpenClaw规范版本
Memory System
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

# 路径设置
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_DIR = os.path.join(SKILL_DIR, 'memory', 'data')
os.makedirs(MEMORY_DIR, exist_ok=True)


class BaseMemory(ABC):
    """记忆基类"""
    
    def __init__(self, memory_type: str):
        self.memory_type = memory_type
        self.storage_path = os.path.join(MEMORY_DIR, f"{memory_type}.json")
        self.data = self._load()
    
    def _load(self) -> List[Dict]:
        """加载记忆"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save(self):
        """保存记忆"""
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def add(self, item: Dict) -> str:
        """添加记忆"""
        record_id = f"{self.memory_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        item['id'] = record_id
        item['created_at'] = datetime.now().isoformat()
        self.data.append(item)
        self._save()
        return record_id
    
    def get(self, record_id: str) -> Optional[Dict]:
        """获取记忆"""
        for item in self.data:
            if item.get('id') == record_id:
                return item
        return None
    
    def query(self, **filters) -> List[Dict]:
        """查询记忆"""
        results = self.data
        for key, value in filters.items():
            results = [r for r in results if r.get(key) == value]
        return results
    
    def clear(self):
        """清空记忆"""
        self.data = []
        self._save()


class EpisodicMemory(BaseMemory):
    """
    情景记忆 - 历史投注案例
    """
    
    def __init__(self):
        super().__init__("episodic")
    
    def record_bet(self, bet_data: Dict) -> str:
        """记录投注"""
        return self.add({
            "type": "bet",
            **bet_data
        })
    
    def record_result(self, bet_id: str, result: str, profit: float):
        """记录结果"""
        bet = self.get(bet_id)
        if bet:
            bet['result'] = result
            bet['profit'] = profit
            bet['resolved_at'] = datetime.now().isoformat()
            self._save()
    
    def get_recent_bets(self, limit: int = 10) -> List[Dict]:
        """获取最近投注"""
        bets = [r for r in self.data if r.get('type') == 'bet']
        return sorted(bets, key=lambda x: x.get('created_at', ''), reverse=True)[:limit]


class SemanticMemory(BaseMemory):
    """
    语义记忆 - 联赛知识和球队特征
    """
    
    def __init__(self):
        super().__init__("semantic")
    
    def store_league_knowledge(self, league: str, knowledge: Dict) -> str:
        """存储联赛知识"""
        return self.add({
            "entity_type": "league",
            "league": league,
            "knowledge": knowledge
        })
    
    def store_team_knowledge(self, team: str, knowledge: Dict) -> str:
        """存储球队知识"""
        return self.add({
            "entity_type": "team",
            "team": team,
            "knowledge": knowledge
        })
    
    def get_league(self, league: str) -> Optional[Dict]:
        """获取联赛知识"""
        results = self.query(entity_type="league", league=league)
        return results[-1] if results else None
    
    def get_team(self, team: str) -> Optional[Dict]:
        """获取球队知识"""
        results = self.query(entity_type="team", team=team)
        return results[-1] if results else None


class ProceduralMemory(BaseMemory):
    """
    程序记忆 - 策略执行流程
    """
    
    def __init__(self):
        super().__init__("procedural")
    
    def store_workflow(self, workflow_name: str, steps: List[Dict]) -> str:
        """存储工作流"""
        return self.add({
            "type": "workflow",
            "name": workflow_name,
            "steps": steps
        })
    
    def get_workflow(self, workflow_name: str) -> Optional[Dict]:
        """获取工作流"""
        results = self.query(type="workflow", name=workflow_name)
        return results[-1] if results else None


class Reflector:
    """
    反思引擎
    """
    
    def __init__(self):
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory()
    
    def reflect_on_result(self, bet_id: str) -> Dict:
        """反思投注结果"""
        bet = self.episodic.get(bet_id)
        if not bet:
            return {"error": "Bet not found"}
        
        result = bet.get('result')
        profit = bet.get('profit', 0)
        
        if result == 'win':
            return self._reflect_on_win(bet)
        elif result == 'loss':
            return self._reflect_on_loss(bet)
        else:
            return {"error": "Result not available"}
    
    def _reflect_on_win(self, bet: Dict) -> Dict:
        """反思盈利"""
        return {
            "type": "win",
            "bet_id": bet.get('id'),
            "analysis": "盈利策略有效",
            "lessons": ["保持当前策略", "注意仓位控制"],
            "confidence_adjustment": 0.05
        }
    
    def _reflect_on_loss(self, bet: Dict) -> Dict:
        """反思亏损"""
        return {
            "type": "loss",
            "bet_id": bet.get('id'),
            "analysis": "亏损原因分析",
            "lessons": ["重新评估赔率", "加强风控"],
            "confidence_adjustment": -0.1
        }
    
    def auto_reflect(self) -> Dict:
        """自动反思"""
        recent_bets = self.episodic.get_recent_bets(limit=10)
        wins = [b for b in recent_bets if b.get('result') == 'win']
        losses = [b for b in recent_bets if b.get('result') == 'loss']
        
        return {
            "period": "recent_10_bets",
            "total_bets": len(recent_bets),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": len(wins) / len(recent_bets) if recent_bets else 0,
            "recommendations": self._generate_recommendations(wins, losses)
        }
    
    def _generate_recommendations(self, wins: List, losses: List) -> List[str]:
        """生成建议"""
        recommendations = []
        
        if len(losses) > len(wins):
            recommendations.append("近期亏损较多，建议降低投注频率")
            recommendations.append("重新审视策略参数")
        
        if len(wins) > len(losses):
            recommendations.append("保持当前策略，但注意风险控制")
        
        return recommendations


def get_memory_system() -> Dict[str, BaseMemory]:
    """获取记忆系统"""
    return {
        "episodic": EpisodicMemory(),
        "semantic": SemanticMemory(),
        "procedural": ProceduralMemory(),
        "reflector": Reflector()
    }
