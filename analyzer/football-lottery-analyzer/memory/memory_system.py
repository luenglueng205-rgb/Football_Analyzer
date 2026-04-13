# -*- coding: utf-8 -*-
"""
足球彩票分析系统 - Agent Memory System
核心记忆系统模块

提供三种记忆类型:
- EpisodicMemory: 历史投注案例（成功/失败）
- SemanticMemory: 联赛知识、球队特征
- ProceduralMemory: 策略执行流程
"""

import os
import json
import datetime
import uuid
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum


class MemoryType(Enum):
    """记忆类型枚举"""
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


@dataclass
class BettingRecord:
    """投注记录数据结构"""
    record_id: str
    timestamp: str
    league: str
    home_team: str
    away_team: str
    bet_type: str
    bet_selection: str
    odds: float
    stake: float
    result: str  # win/loss/pending
    actual_score: Optional[str] = None
    expected_value: Optional[float] = None
    confidence: float = 0.5
    analysis_context: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


@dataclass
class LeagueKnowledge:
    """联赛知识数据结构"""
    league_id: str
    league_name: str
    country: str
    characteristics: Dict[str, Any] = field(default_factory=dict)
    suitable_bet_types: List[str] = field(default_factory=list)
    avg_goals: float = 0.0
    home_win_rate: float = 0.0
    confidence_level: float = 0.5
    last_updated: str = ""


@dataclass
class TeamKnowledge:
    """球队知识数据结构"""
    team_id: str
    team_name: str
    league: str
    form: List[str] = field(default_factory=list)  # 最近5场比赛结果
    avg_goals_scored: float = 0.0
    avg_goals_conceded: float = 0.0
    home_away_performance: Dict[str, float] = field(default_factory=dict)
    key_players: List[str] = field(default_factory=list)
    tactical_style: str = ""
    confidence_level: float = 0.5


@dataclass
class StrategyProcedure:
    """策略执行流程数据结构"""
    strategy_id: str
    strategy_name: str
    description: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    success_conditions: List[str] = field(default_factory=list)
    failure_conditions: List[str] = field(default_factory=list)
    usage_count: int = 0
    success_count: int = 0
    avg_roi: float = 0.0


class BaseMemory:
    """记忆基类"""
    
    def __init__(self, storage_dir: str):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
    
    def _get_file_path(self, filename: str) -> str:
        return os.path.join(self.storage_dir, filename)
    
    def _load_json(self, filepath: str, default: Any = None) -> Any:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return default if default is not None else {}
    
    def _save_json(self, filepath: str, data: Any) -> None:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


class EpisodicMemory(BaseMemory):
    """情景记忆 - 历史投注案例"""
    
    def __init__(self, storage_dir: str):
        super().__init__(storage_dir)
        self.file_path = self._get_file_path("episodic_memory.json")
        self.records = self._load_json(self.file_path, {"records": []})
    
    def add_record(self, record: BettingRecord) -> str:
        """添加投注记录"""
        self.records["records"].append(asdict(record))
        self._save_json(self.file_path, self.records)
        return record.record_id
    
    def get_records(self, 
                   league: Optional[str] = None,
                   result: Optional[str] = None,
                   bet_type: Optional[str] = None,
                   limit: int = 100) -> List[BettingRecord]:
        """查询投注记录"""
        filtered = self.records["records"]
        
        if league:
            filtered = [r for r in filtered if r.get("league") == league]
        if result:
            filtered = [r for r in filtered if r.get("result") == result]
        if bet_type:
            filtered = [r for r in filtered if r.get("bet_type") == bet_type]
        
        filtered = sorted(filtered, key=lambda x: x.get("timestamp", ""), reverse=True)
        return [BettingRecord(**r) for r in filtered[:limit]]
    
    def get_success_cases(self, min_roi: float = 0.1) -> List[BettingRecord]:
        """获取成功案例"""
        success = [r for r in self.records["records"] 
                   if r.get("result") == "win"]
        return [BettingRecord(**r) for r in success]
    
    def get_failure_cases(self) -> List[BettingRecord]:
        """获取失败案例"""
        failures = [r for r in self.records["records"] 
                   if r.get("result") == "loss"]
        return [BettingRecord(**r) for r in failures]
    
    def calculate_stats(self) -> Dict[str, Any]:
        """计算统计数据"""
        records = self.records["records"]
        if not records:
            return {"total": 0, "wins": 0, "losses": 0, "win_rate": 0.0}
        
        total = len(records)
        wins = len([r for r in records if r.get("result") == "win"])
        losses = len([r for r in records if r.get("result") == "loss"])
        
        return {
            "total": total,
            "wins": wins,
            "losses": losses,
            "pending": total - wins - losses,
            "win_rate": wins / total if total > 0 else 0.0
        }
    
    def get_recent_patterns(self, days: int = 30) -> Dict[str, Any]:
        """获取近期模式"""
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
        recent = [r for r in self.records["records"] 
                  if r.get("timestamp", "") > cutoff]
        
        if not recent:
            return {"leagues": {}, "bet_types": {}, "avg_odds": 0.0}
        
        leagues = {}
        bet_types = {}
        total_odds = 0.0
        
        for r in recent:
            league = r.get("league", "unknown")
            leagues[league] = leagues.get(league, 0) + 1
            
            bet_type = r.get("bet_type", "unknown")
            bet_types[bet_type] = bet_types.get(bet_type, 0) + 1
            
            total_odds += r.get("odds", 0)
        
        return {
            "leagues": leagues,
            "bet_types": bet_types,
            "avg_odds": total_odds / len(recent),
            "count": len(recent)
        }


class SemanticMemory(BaseMemory):
    """语义记忆 - 联赛和球队知识"""
    
    def __init__(self, storage_dir: str):
        super().__init__(storage_dir)
        self.leagues_file = self._get_file_path("semantic_leagues.json")
        self.teams_file = self._get_file_path("semantic_teams.json")
        self.leagues = self._load_json(self.leagues_file, {"leagues": []})
        self.teams = self._load_json(self.teams_file, {"teams": []})
    
    def add_league(self, league: LeagueKnowledge) -> str:
        """添加联赛知识"""
        existing = [i for i, l in enumerate(self.leagues["leagues"]) 
                   if l["league_id"] == league.league_id]
        
        if existing:
            self.leagues["leagues"][existing[0]] = asdict(league)
        else:
            self.leagues["leagues"].append(asdict(league))
        
        self._save_json(self.leagues_file, self.leagues)
        return league.league_id
    
    def get_league(self, league_id: str) -> Optional[LeagueKnowledge]:
        """获取联赛知识"""
        for l in self.leagues["leagues"]:
            if l["league_id"] == league_id:
                return LeagueKnowledge(**l)
        return None
    
    def get_all_leagues(self) -> List[LeagueKnowledge]:
        """获取所有联赛"""
        return [LeagueKnowledge(**l) for l in self.leagues["leagues"]]
    
    def add_team(self, team: TeamKnowledge) -> str:
        """添加球队知识"""
        existing = [i for i, t in enumerate(self.teams["teams"]) 
                   if t["team_id"] == team.team_id]
        
        if existing:
            self.teams["teams"][existing[0]] = asdict(team)
        else:
            self.teams["teams"].append(asdict(team))
        
        self._save_json(self.teams_file, self.teams)
        return team.team_id
    
    def get_team(self, team_id: str) -> Optional[TeamKnowledge]:
        """获取球队知识"""
        for t in self.teams["teams"]:
            if t["team_id"] == team_id:
                return TeamKnowledge(**t)
        return None
    
    def get_teams_by_league(self, league: str) -> List[TeamKnowledge]:
        """获取特定联赛的所有球队"""
        teams = [TeamKnowledge(**t) for t in self.teams["teams"] 
                if t.get("league") == league]
        return teams
    
    def get_suitable_bet_types(self, league_id: str) -> List[str]:
        """获取适合联赛的投注类型"""
        league = self.get_league(league_id)
        if league:
            return league.suitable_bet_types
        return []
    
    def update_confidence(self, league_id: Optional[str] = None,
                         team_id: Optional[str] = None,
                         delta: float = 0.1) -> None:
        """更新置信度"""
        if league_id:
            for i, l in enumerate(self.leagues["leagues"]):
                if l["league_id"] == league_id:
                    self.leagues["leagues"][i]["confidence_level"] = min(1.0, l.get("confidence_level", 0.5) + delta)
                    break
            self._save_json(self.leagues_file, self.leagues)
        
        if team_id:
            for i, t in enumerate(self.teams["teams"]):
                if t["team_id"] == team_id:
                    self.teams["teams"][i]["confidence_level"] = min(1.0, t.get("confidence_level", 0.5) + delta)
                    break
            self._save_json(self.teams_file, self.teams)


class ProceduralMemory(BaseMemory):
    """程序记忆 - 策略执行流程"""
    
    def __init__(self, storage_dir: str):
        super().__init__(storage_dir)
        self.file_path = self._get_file_path("procedural_memory.json")
        self.strategies = self._load_json(self.file_path, {"strategies": []})
    
    def add_strategy(self, strategy: StrategyProcedure) -> str:
        """添加策略流程"""
        existing = [i for i, s in enumerate(self.strategies["strategies"]) 
                   if s["strategy_id"] == strategy.strategy_id]
        
        if existing:
            self.strategies["strategies"][existing[0]] = asdict(strategy)
        else:
            self.strategies["strategies"].append(asdict(strategy))
        
        self._save_json(self.file_path, self.strategies)
        return strategy.strategy_id
    
    def get_strategy(self, strategy_id: str) -> Optional[StrategyProcedure]:
        """获取策略"""
        for s in self.strategies["strategies"]:
            if s["strategy_id"] == strategy_id:
                return StrategyProcedure(**s)
        return None
    
    def get_all_strategies(self) -> List[StrategyProcedure]:
        """获取所有策略"""
        return [StrategyProcedure(**s) for s in self.strategies["strategies"]]
    
    def record_usage(self, strategy_id: str, success: bool, roi: float = 0.0) -> None:
        """记录策略使用结果"""
        for i, s in enumerate(self.strategies["strategies"]):
            if s["strategy_id"] == strategy_id:
                self.strategies["strategies"][i]["usage_count"] += 1
                if success:
                    self.strategies["strategies"][i]["success_count"] += 1
                
                # 更新平均ROI
                current_avg = self.strategies["strategies"][i]["avg_roi"]
                count = self.strategies["strategies"][i]["usage_count"]
                self.strategies["strategies"][i]["avg_roi"] = (current_avg * (count - 1) + roi) / count
                break
        
        self._save_json(self.file_path, self.strategies)
    
    def get_best_strategies(self, limit: int = 5) -> List[StrategyProcedure]:
        """获取最佳策略"""
        strategies = [StrategyProcedure(**s) for s in self.strategies["strategies"]]
        valid = [s for s in strategies if s.usage_count >= 5]
        sorted_strategies = sorted(valid, 
                                   key=lambda x: x.avg_roi if x.usage_count > 0 else 0,
                                   reverse=True)
        return sorted_strategies[:limit]
    
    def get_recommended_strategy(self, context: Dict[str, Any]) -> Optional[StrategyProcedure]:
        """根据上下文推荐策略"""
        strategies = self.get_all_strategies()
        if not strategies:
            return None
        
        # 根据上下文过滤
        league = context.get("league", "")
        bet_type = context.get("bet_type", "")
        
        suitable = []
        for s in strategies:
            if s.usage_count < 3:
                continue
            score = 0
            # ROI权重
            score += s.avg_roi * 0.5
            # 成功率权重
            success_rate = s.success_count / s.usage_count if s.usage_count > 0 else 0
            score += success_rate * 0.3
            # 使用次数权重（不宜过高也不能太低）
            usage_score = min(s.usage_count / 20, 1.0) * 0.2
            score += usage_score
            
            suitable.append((s, score))
        
        if suitable:
            suitable.sort(key=lambda x: x[1], reverse=True)
            return suitable[0][0]
        
        return None


class MemorySystem:
    """统一记忆系统"""
    
    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        
        memory_dir = os.path.join(os.path.dirname(base_dir), "data", "memory")
        os.makedirs(memory_dir, exist_ok=True)
        
        self.episodic = EpisodicMemory(memory_dir)
        self.semantic = SemanticMemory(memory_dir)
        self.procedural = ProceduralMemory(memory_dir)
        self.base_dir = base_dir
        self.memory_dir = memory_dir
    
    def create_betting_record(self,
                             league: str,
                             home_team: str,
                             away_team: str,
                             bet_type: str,
                             bet_selection: str,
                             odds: float,
                             stake: float,
                             confidence: float = 0.5,
                             analysis_context: Optional[Dict[str, Any]] = None,
                             tags: Optional[List[str]] = None) -> BettingRecord:
        """创建投注记录"""
        record = BettingRecord(
            record_id=str(uuid.uuid4())[:8],
            timestamp=datetime.datetime.now().isoformat(),
            league=league,
            home_team=home_team,
            away_team=away_team,
            bet_type=bet_type,
            bet_selection=bet_selection,
            odds=odds,
            stake=stake,
            result="pending",
            confidence=confidence,
            analysis_context=analysis_context or {},
            tags=tags or []
        )
        self.episodic.add_record(record)
        return record
    
    def update_betting_result(self, record_id: str, result: str, 
                             actual_score: Optional[str] = None) -> bool:
        """更新投注结果"""
        for record in self.episodic.records["records"]:
            if record["record_id"] == record_id:
                record["result"] = result
                if actual_score:
                    record["actual_score"] = actual_score
                self.episodic._save_json(self.episodic.file_path, self.episodic.records)
                return True
        return False
    
    def add_league_knowledge(self,
                            league_id: str,
                            league_name: str,
                            country: str,
                            characteristics: Optional[Dict[str, Any]] = None,
                            suitable_bet_types: Optional[List[str]] = None) -> LeagueKnowledge:
        """添加联赛知识"""
        league = LeagueKnowledge(
            league_id=league_id,
            league_name=league_name,
            country=country,
            characteristics=characteristics or {},
            suitable_bet_types=suitable_bet_types or [],
            last_updated=datetime.datetime.now().isoformat()
        )
        self.semantic.add_league(league)
        return league
    
    def add_team_knowledge(self,
                           team_id: str,
                           team_name: str,
                           league: str,
                           form: Optional[List[str]] = None,
                           avg_goals_scored: float = 0.0,
                           avg_goals_conceded: float = 0.0) -> TeamKnowledge:
        """添加球队知识"""
        team = TeamKnowledge(
            team_id=team_id,
            team_name=team_name,
            league=league,
            form=form or [],
            avg_goals_scored=avg_goals_scored,
            avg_goals_conceded=avg_goals_conceded
        )
        self.semantic.add_team(team)
        return team
    
    def add_strategy(self,
                    strategy_name: str,
                    description: str,
                    steps: List[Dict[str, Any]],
                    success_conditions: Optional[List[str]] = None,
                    failure_conditions: Optional[List[str]] = None) -> StrategyProcedure:
        """添加策略"""
        strategy = StrategyProcedure(
            strategy_id=str(uuid.uuid4())[:8],
            strategy_name=strategy_name,
            description=description,
            steps=steps,
            success_conditions=success_conditions or [],
            failure_conditions=failure_conditions or []
        )
        self.procedural.add_strategy(strategy)
        return strategy
    
    def get_full_stats(self) -> Dict[str, Any]:
        """获取完整统计"""
        return {
            "episodic": self.episodic.calculate_stats(),
            "episodic_patterns": self.episodic.get_recent_patterns(),
            "leagues_count": len(self.semantic.leagues["leagues"]),
            "teams_count": len(self.semantic.teams["teams"]),
            "strategies_count": len(self.procedural.strategies["strategies"]),
            "best_strategies": [
                {"id": s.strategy_id, "name": s.strategy_name, "roi": s.avg_roi}
                for s in self.procedural.get_best_strategies()
            ]
        }
    
    def export_memory(self, filepath: str) -> bool:
        """导出记忆数据"""
        try:
            data = {
                "episodic": self.episodic.records,
                "semantic_leagues": self.semantic.leagues,
                "semantic_teams": self.semantic.teams,
                "procedural": self.procedural.strategies,
                "export_time": datetime.datetime.now().isoformat()
            }
            self._save_json(filepath, data)
            return True
        except Exception as e:
            print(f"导出失败: {e}")
            return False
    
    def import_memory(self, filepath: str) -> bool:
        """导入记忆数据"""
        try:
            data = self._load_json(filepath)
            if "episodic" in data:
                self.episodic.records = data["episodic"]
                self.episodic._save_json(self.episodic.file_path, self.episodic.records)
            if "semantic_leagues" in data:
                self.semantic.leagues = data["semantic_leagues"]
                self.semantic._save_json(self.semantic.leagues_file, self.semantic.leagues)
            if "semantic_teams" in data:
                self.semantic.teams = data["semantic_teams"]
                self.semantic._save_json(self.semantic.teams_file, self.semantic.teams)
            if "procedural" in data:
                self.procedural.strategies = data["procedural"]
                self.procedural._save_json(self.procedural.file_path, self.procedural.strategies)
            return True
        except Exception as e:
            print(f"导入失败: {e}")
            return False


# 全局单例
_memory_system_instance: Optional[MemorySystem] = None

def get_memory_system() -> MemorySystem:
    """获取记忆系统单例"""
    global _memory_system_instance
    if _memory_system_instance is None:
        _memory_system_instance = MemorySystem()
    return _memory_system_instance


if __name__ == "__main__":
    # 测试代码
    memory = MemorySystem()
    
    # 添加测试数据
    record = memory.create_betting_record(
        league="英超",
        home_team="曼联",
        away_team="利物浦",
        bet_type="胜平负",
        bet_selection="胜",
        odds=2.5,
        stake=100.0,
        confidence=0.7
    )
    print(f"创建记录: {record.record_id}")
    
    # 添加联赛知识
    memory.add_league_knowledge(
        league_id="epl",
        league_name="英格兰超级联赛",
        country="英格兰",
        characteristics={"avg_goals": 2.8, "competitiveness": "high"},
        suitable_bet_types=["胜平负", "大小球", "角球"]
    )
    
    # 获取统计
    stats = memory.get_full_stats()
    print(f"记忆统计: {stats}")
