#!/usr/bin/env python3
"""
情报搜集Agent
功能：
1. 球队状态分析（伤病、阵容）
2. 历史对战数据
3. 近期表现趋势
"""

import os
import sys
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
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


def load_beijing_data() -> Dict:
    """加载北京单场数据"""
    filepath = os.path.join(DATA_DIR, '北京单场_chinese_data.json')
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


class ScoutAgent(BaseAgent):
    """情报搜集Agent - 负责收集和分析比赛相关信息"""
    
    def __init__(self, message_bus=None):
        super().__init__("ScoutAgent", message_bus)
        self.jingcai_data = load_jingcai_data()
        self.beijing_data = load_beijing_data()
        self._team_cache: Dict[str, Dict] = {}
        self._match_cache: List[Dict] = []
    
    def initialize(self) -> bool:
        """初始化Agent"""
        self.set_status(AgentStatus.IDLE)
        self._load_team_data()
        get_registry().register(self)
        return True
    
    def _load_team_data(self) -> None:
        """加载球队数据"""
        if "matches" in self.jingcai_data:
            self._match_cache = self.jingcai_data["matches"]
            
        # 构建球队索引
        for match in self._match_cache:
            home_team = match.get("home_team", "")
            away_team = match.get("away_team", "")
            for team in [home_team, away_team]:
                if team and team not in self._team_cache:
                    self._team_cache[team] = {
                        "name": team,
                        "home_matches": [],
                        "away_matches": [],
                        "recent_form": [],
                        "goals_scored": 0,
                        "goals_conceded": 0,
                        "total_matches": 0
                    }
            
            # 更新主队数据
            if home_team:
                self._team_cache[home_team]["home_matches"].append(match)
            # 更新客队数据
            if away_team:
                self._team_cache[away_team]["away_matches"].append(match)
    
    def process(self, task: Task) -> Dict[str, Any]:
        """处理任务"""
        self.set_status(AgentStatus.RUNNING)
        
        task_type = task.task_type
        payload = task.payload
        
        try:
            if task_type == "team_status":
                result = self.analyze_team_status(
                    payload.get("team_name", ""),
                    payload.get("match_id", "")
                )
            elif task_type == "head_to_head":
                result = self.analyze_head_to_head(
                    payload.get("home_team", ""),
                    payload.get("away_team", "")
                )
            elif task_type == "recent_form":
                result = self.analyze_recent_form(
                    payload.get("team_name", ""),
                    payload.get("matches", 5)
                )
            elif task_type == "match_intelligence":
                result = self.get_match_intelligence(
                    payload.get("match_id", "")
                )
            elif task_type == "league_trends":
                result = self.analyze_league_trends(
                    payload.get("league", "")
                )
            elif task_type == "scout_report":
                result = self.generate_scout_report(
                    payload.get("matches", [])
                )
            else:
                result = {"error": f"Unknown task type: {task_type}"}
            
            self.set_status(AgentStatus.COMPLETED)
            return {"status": "success", "result": result}
            
        except Exception as e:
            self.set_status(AgentStatus.ERROR)
            self._last_error = str(e)
            return {"status": "error", "error": str(e)}
    
    def analyze_team_status(self, team_name: str, match_id: str = "") -> Dict:
        """分析球队状态"""
        if team_name not in self._team_cache:
            return {"error": f"球队未找到: {team_name}"}
        
        team_data = self._team_cache[team_name]
        
        # 计算最近5场表现
        recent = team_data["home_matches"][:5] + team_data["away_matches"][:5]
        wins = sum(1 for m in recent if m.get("result") == "win")
        draws = sum(1 for m in recent if m.get("result") == "draw")
        losses = sum(1 for m in recent if m.get("result") == "loss")
        
        return {
            "team": team_name,
            "total_matches": len(team_data["home_matches"]) + len(team_data["away_matches"]),
            "home_matches": len(team_data["home_matches"]),
            "away_matches": len(team_data["away_matches"]),
            "recent_form": {
                "wins": wins,
                "draws": draws,
                "losses": losses,
                "form_string": f"{'W' * wins}{'D' * draws}{'L' * losses}"
            },
            "goals": {
                "scored": team_data.get("goals_scored", 0),
                "conceded": team_data.get("goals_conceded", 0)
            }
        }
    
    def analyze_head_to_head(self, home_team: str, away_team: str) -> Dict:
        """历史对战分析"""
        home_matches = self._team_cache.get(home_team, {}).get("home_matches", [])
        away_matches = self._team_cache.get(away_team, {}).get("away_matches", [])
        
        # 找出两队交手的比赛
        h2h_matches = [
            m for m in home_matches 
            if m.get("away_team") == away_team
        ] + [
            m for m in away_matches 
            if m.get("home_team") == home_team
        ]
        
        if not h2h_matches:
            return {
                "home_team": home_team,
                "away_team": away_team,
                "matches": 0,
                "message": "暂无历史交锋记录"
            }
        
        home_wins = sum(1 for m in h2h_matches if m.get("result") == "win" and m.get("home_team") == home_team)
        away_wins = sum(1 for m in h2h_matches if m.get("result") == "win" and m.get("away_team") == away_team)
        draws = len(h2h_matches) - home_wins - away_wins
        
        return {
            "home_team": home_team,
            "away_team": away_team,
            "total_matches": len(h2h_matches),
            "home_wins": home_wins,
            "away_wins": away_wins,
            "draws": draws,
            "win_rate": {
                "home": round(home_wins / len(h2h_matches) * 100, 1),
                "away": round(away_wins / len(h2h_matches) * 100, 1)
            }
        }
    
    def analyze_recent_form(self, team_name: str, matches: int = 5) -> Dict:
        """近期表现趋势分析"""
        if team_name not in self._team_cache:
            return {"error": f"球队未找到: {team_name}"}
        
        team_data = self._team_cache[team_name]
        all_matches = team_data["home_matches"] + team_data["away_matches"]
        
        # 取最近的比赛
        recent = all_matches[:matches]
        
        results = []
        for match in recent:
            is_home = match.get("home_team") == team_name
            result = match.get("result", "unknown")
            score = match.get("score", {})
            
            results.append({
                "venue": "home" if is_home else "away",
                "opponent": match.get("away_team" if is_home else "home_team", ""),
                "result": result,
                "score": f"{score.get('home', 0)}-{score.get('away', 0)}"
            })
        
        return {
            "team": team_name,
            "recent_matches": results,
            "form": "".join([r["result"][0].upper() for r in results if r["result"] != "unknown"])
        }
    
    def get_match_intelligence(self, match_id: str) -> Dict:
        """获取比赛情报"""
        match = None
        for m in self._match_cache:
            if m.get("match_id") == match_id:
                match = m
                break
        
        if not match:
            return {"error": f"比赛未找到: {match_id}"}
        
        home_team = match.get("home_team", "")
        away_team = match.get("away_team", "")
        
        return {
            "match_id": match_id,
            "home_team": home_team,
            "away_team": away_team,
            "league": match.get("league", ""),
            "home_status": self.analyze_team_status(home_team),
            "away_status": self.analyze_team_status(away_team),
            "h2h": self.analyze_head_to_head(home_team, away_team),
            "home_form": self.analyze_recent_form(home_team),
            "away_form": self.analyze_recent_form(away_team)
        }
    
    def analyze_league_trends(self, league: str) -> Dict:
        """联赛趋势分析"""
        league_matches = [m for m in self._match_cache if m.get("league") == league]
        
        if not league_matches:
            return {"error": f"联赛未找到: {league}"}
        
        total_matches = len(league_matches)
        home_wins = sum(1 for m in league_matches if m.get("result") == "win" and m.get("is_home_win"))
        away_wins = sum(1 for m in league_matches if m.get("result") == "win" and not m.get("is_home_win"))
        draws = total_matches - home_wins - away_wins
        
        return {
            "league": league,
            "total_matches": total_matches,
            "home_wins": home_wins,
            "away_wins": away_wins,
            "draws": draws,
            "win_rates": {
                "home": round(home_wins / total_matches * 100, 1),
                "away": round(away_wins / total_matches * 100, 1),
                "draw": round(draws / total_matches * 100, 1)
            }
        }
    
    def generate_scout_report(self, matches: List[Dict]) -> Dict:
        """生成情报报告"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "matches": []
        }
        
        for match in matches:
            match_id = match.get("match_id", "")
            intel = self.get_match_intelligence(match_id)
            report["matches"].append(intel)
        
        # 汇总统计
        total = len(report["matches"])
        high_confidence = sum(
            1 for m in report["matches"] 
            if m.get("home_status", {}).get("total_matches", 0) > 10
        )
        
        report["summary"] = {
            "total_matches": total,
            "high_confidence_matches": high_confidence,
            "confidence_rate": round(high_confidence / total * 100, 1) if total > 0 else 0
        }
        
        return report
    
    def get_capabilities(self) -> Dict[str, Any]:
        """获取Agent能力"""
        return {
            "name": self.name,
            "type": "scout",
            "functions": [
                "team_status - 球队状态分析",
                "head_to_head - 历史对战数据",
                "recent_form - 近期表现趋势",
                "match_intelligence - 比赛情报",
                "league_trends - 联赛趋势",
                "scout_report - 情报报告生成"
            ],
            "data_sources": ["竞彩足球", "北京单场"],
            "status": self.status.value
        }


# 便捷函数
def create_scout_agent(message_bus=None) -> ScoutAgent:
    """创建ScoutAgent实例"""
    agent = ScoutAgent(message_bus)
    agent.initialize()
    return agent


__all__ = ['ScoutAgent', 'create_scout_agent']