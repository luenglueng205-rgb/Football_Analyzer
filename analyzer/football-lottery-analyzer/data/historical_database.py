# -*- coding: utf-8 -*-
"""
足球彩票分析系统 - 历史数据库加载器 v2.0
统一加载所有历史数据供专业分析模块使用

数据源:
1. data/raw/COMPLETE_FOOTBALL_DATA_FINAL_UPDATED.json - 原始历史数据(221,415条)
2. data/chinese_mapped/ - 转换后的中文数据
3. data/memory/rag_knowledge.json - RAG知识库
"""

import json
import os
import sys
import math
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, Counter
from datetime import datetime
import statistics

# 路径设置 - 使用相对于项目目录的路径（便于项目整体迁移）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))  # football-lottery-analyzer/data/
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)  # football-lottery-analyzer/

# 项目内部数据目录 (相对于项目根目录)
# 数据文件位于: football-lottery-analyzer/data/raw/
#               football-lottery-analyzer/data/chinese_mapped/
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
RAW_DATA_DIR = os.path.join(DATA_DIR, 'raw')
CHINESE_DATA_DIR = os.path.join(DATA_DIR, 'chinese_mapped')
MEMORY_DIR = os.path.join(DATA_DIR, 'memory')


class HistoricalDatabase:
    """
    历史数据库加载器
    
    提供:
    - 完整历史比赛数据 (221,415条)
    - 联赛统计特征
    - 球队历史表现
    - 赔率历史模型
    - RAG知识库
    """
    
    def __init__(self, lazy_load: bool = True):
        """
        初始化数据库
        
        Args:
            lazy_load: 是否延迟加载(仅按需加载大文件)
        """
        self.lazy_load = lazy_load
        self._raw_data = None
        self._chinese_data = None
        self._rag_knowledge = None
        self._league_stats = None
        self._team_stats = None
        
        # 轻量级数据立即加载
        self._load_league_mapping()
        self._load_summary()
        
        print(f"✅ 历史数据库初始化完成")
        print(f"   - 原始数据: {RAW_DATA_DIR}")
        print(f"   - 中文数据: {CHINESE_DATA_DIR}")
        print(f"   - 联赛数: {len(self.league_mapping)}")
    
    def _load_league_mapping(self):
        """加载联赛映射"""
        mapping_file = os.path.join(DATA_DIR, 'league_mapping.json')
        if os.path.exists(mapping_file):
            with open(mapping_file, 'r', encoding='utf-8') as f:
                self.league_mapping = json.load(f)
        else:
            self.league_mapping = {}
    
    def _load_summary(self):
        """加载摘要信息"""
        summary_file = os.path.join(CHINESE_DATA_DIR, 'lottery_leagues_summary.md')
        self.summary = ""
        if os.path.exists(summary_file):
            with open(summary_file, 'r', encoding='utf-8') as f:
                self.summary = f.read()
    
    @property
    def raw_data(self) -> Dict:
        """懒加载原始历史数据"""
        if self._raw_data is None:
            filepath = os.path.join(RAW_DATA_DIR, 'COMPLETE_FOOTBALL_DATA_FINAL_UPDATED.json')
            if os.path.exists(filepath):
                print(f"📊 加载原始历史数据 (221,415条比赛)...")
                with open(filepath, 'r', encoding='utf-8') as f:
                    self._raw_data = json.load(f)
                print(f"✅ 原始数据加载完成")
            else:
                self._raw_data = {"metadata": {}, "matches": []}
        return self._raw_data
    
    @property
    def chinese_data(self) -> Dict:
        """加载中文数据"""
        if self._chinese_data is None:
            self._chinese_data = {}
            for filename in ['竞彩足球_chinese_data.json', '北京单场_chinese_data.json', '传统足彩_chinese_data.json']:
                filepath = os.path.join(CHINESE_DATA_DIR, filename)
                if os.path.exists(filepath):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        name = filename.replace('_chinese_data.json', '')
                        self._chinese_data[name] = data
        return self._chinese_data
    
    @property
    def rag_knowledge(self) -> Dict:
        """加载RAG知识库"""
        if self._rag_knowledge is None:
            filepath = os.path.join(MEMORY_DIR, 'rag_knowledge.json')
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    self._rag_knowledge = json.load(f)
            else:
                self._rag_knowledge = {"knowledge": [], "patterns": []}
        return self._rag_knowledge
    
    def get_league_stats(self, league_code: str) -> Dict[str, Any]:
        """
        获取联赛统计信息
        
        Args:
            league_code: 联赛代码 (如 'E0', 'D1', 'I1')
        
        Returns:
            联赛统计字典
        """
        if self._league_stats is None:
            self._calculate_all_league_stats()
        
        return self._league_stats.get(league_code, {
            "avg_goals": 2.7,
            "home_win_rate": 0.45,
            "draw_rate": 0.25,
            "away_win_rate": 0.30,
            "over_2_5_rate": 0.52,
            "btts_rate": 0.47,
            "sample_size": 0
        })
    
    def _calculate_all_league_stats(self):
        """计算所有联赛统计"""
        print("📊 计算联赛统计参数...")
        self._league_stats = {}
        
        raw = self.raw_data
        matches = raw.get("matches", [])
        
        if not matches:
            print("⚠️ 原始数据为空，使用默认值")
            return
        
        # 按联赛分组统计
        league_matches = defaultdict(list)
        for match in matches:
            league = match.get("league", "unknown")
            league_matches[league].append(match)
        
        for league, league_data in league_matches.items():
            if len(league_data) < 100:
                continue
            
            home_goals = [m.get("home_goals", 0) for m in league_data if m.get("home_goals") is not None]
            away_goals = [m.get("away_goals", 0) for m in league_data if m.get("away_goals") is not None]
            results = [m.get("result", "H") for m in league_data]
            
            if not home_goals:
                continue
            
            total_goals = [h + a for h, a in zip(home_goals, away_goals)]
            
            self._league_stats[league] = {
                "avg_home_goals": statistics.mean(home_goals) if home_goals else 1.4,
                "avg_away_goals": statistics.mean(away_goals) if away_goals else 1.2,
                "avg_total_goals": statistics.mean(total_goals) if total_goals else 2.6,
                "home_wins": results.count("H"),
                "draws": results.count("D"),
                "away_wins": results.count("A"),
                "home_win_rate": results.count("H") / len(results) if results else 0.44,
                "draw_rate": results.count("D") / len(results) if results else 0.26,
                "away_win_rate": results.count("A") / len(results) if results else 0.30,
                "over_2_5_rate": sum(1 for t in total_goals if t > 2.5) / len(total_goals) if total_goals else 0.52,
                "under_2_5_rate": sum(1 for t in total_goals if t <= 2.5) / len(total_goals) if total_goals else 0.48,
                "btts_yes_rate": sum(1 for m in league_data if m.get("home_goals", 0) > 0 and m.get("away_goals", 0) > 0) / len(league_data) if league_data else 0.47,
                "sample_size": len(league_data),
                "goals_std": statistics.stdev(total_goals) if len(total_goals) > 1 else 1.5
            }
        
        print(f"✅ 已计算 {len(self._league_stats)} 个联赛的统计参数")
    
    def get_team_stats(self, team_name: str, league: str = None) -> Dict[str, Any]:
        """
        获取球队历史表现统计
        
        Args:
            team_name: 球队名称
            league: 联赛代码 (可选)
        
        Returns:
            球队统计字典
        """
        if self._team_stats is None:
            self._calculate_all_team_stats()
        
        # 精确匹配或模糊匹配
        team_key = team_name.lower()
        
        # 先尝试精确匹配
        if team_key in self._team_stats:
            return self._team_stats[team_key]
        
        # 模糊匹配
        for key, stats in self._team_stats.items():
            if team_key in key or key in team_name.lower():
                return stats
        
        # 默认返回值
        return {
            "avg_goals_scored": 1.4,
            "avg_goals_conceded": 1.2,
            "home_advantage": 0.3,
            "recent_form": [0, 0, 0, 0, 0],
            "win_rate": 0.44,
            "sample_size": 0
        }
    
    def _calculate_all_team_stats(self):
        """计算所有球队统计"""
        print("📊 计算球队统计参数...")
        self._team_stats = {}
        
        raw = self.raw_data
        matches = raw.get("matches", [])
        
        # 按主队分组
        team_matches = defaultdict(list)
        for match in matches:
            home = match.get("home_team", "").lower()
            away = match.get("away_team", "").lower()
            if home:
                team_matches[home].append(("home", match))
            if away:
                team_matches[away].append(("away", match))
        
        for team, records in team_matches.items():
            if len(records) < 20:
                continue
            
            home_matches = [m for loc, m in records if loc == "home"]
            away_matches = [m for loc, m in records if loc == "away"]
            
            home_goals = [m.get("home_goals", 0) for m in home_matches if m.get("home_goals") is not None]
            away_goals = [m.get("away_goals", 0) for m in away_matches if m.get("away_goals") is not None]
            
            if home_matches:
                home_scored = [m.get("home_goals", 0) for m in home_matches]
                home_conceded = [m.get("away_goals", 0) for m in home_matches]
            else:
                home_scored = home_conceded = []
            
            if away_matches:
                away_scored = [m.get("away_goals", 0) for m in away_matches]
                away_conceded = [m.get("home_goals", 0) for m in away_matches]
            else:
                away_scored = away_conceded = []
            
            all_scored = home_scored + away_scored
            all_conceded = home_conceded + away_conceded
            
            self._team_stats[team] = {
                "avg_home_goals": statistics.mean(home_scored) if home_scored else 1.4,
                "avg_away_goals": statistics.mean(away_scored) if away_scored else 1.1,
                "avg_goals_scored": statistics.mean(all_scored) if all_scored else 1.3,
                "avg_goals_conceded": statistics.mean(all_conceded) if all_conceded else 1.2,
                "home_advantage": (statistics.mean(home_scored) if home_scored else 1.4) - 
                                  (statistics.mean(away_scored) if away_scored else 1.1),
                "total_matches": len(records),
                "sample_size": len(records)
            }
        
        print(f"✅ 已计算 {len(self._team_stats)} 支球队的统计参数")
    
    def get_recent_matches(self, team_name: str, n: int = 10) -> List[Dict]:
        """获取球队最近N场比赛"""
        raw = self.raw_data
        matches = raw.get("matches", [])
        
        team_lower = team_name.lower()
        recent = []
        
        for match in reversed(matches):
            home = match.get("home_team", "").lower()
            away = match.get("away_team", "").lower()
            
            if home == team_lower or away == team_lower:
                recent.append(match)
                if len(recent) >= n:
                    break
        
        return recent
    
    def get_odds_model(self, league: str) -> Dict[str, float]:
        """
        获取赔率模型参数
        
        基于历史数据计算各结果的平均赔率
        """
        raw = self.raw_data
        matches = raw.get("matches", [])
        
        league_matches = [m for m in matches if m.get("league") == league]
        
        if len(league_matches) < 50:
            return {"home": 2.0, "draw": 3.3, "away": 3.5}
        
        # 从赔率数据计算平均赔率
        home_odds = [m.get("avg_home_odds", 2.0) for m in league_matches if m.get("avg_home_odds")]
        draw_odds = [m.get("avg_draw_odds", 3.3) for m in league_matches if m.get("avg_draw_odds")]
        away_odds = [m.get("avg_away_odds", 3.5) for m in league_matches if m.get("avg_away_odds")]
        
        return {
            "home": statistics.mean(home_odds) if home_odds else 2.0,
            "draw": statistics.mean(draw_odds) if draw_odds else 3.3,
            "away": statistics.mean(away_odds) if away_odds else 3.5
        }
    
    def get_league_recommendations(self, league_code: str) -> List[str]:
        """
        根据联赛特征推荐适合的玩法
        
        Returns:
            推荐的玩法列表
        """
        stats = self.get_league_stats(league_code)
        
        recommendations = []
        
        if stats.get("avg_total_goals", 2.5) > 2.8:
            recommendations.append("总进球 - 大球")
        elif stats.get("avg_total_goals", 2.5) < 2.3:
            recommendations.append("总进球 - 小球")
        
        if stats.get("draw_rate", 0.26) > 0.28:
            recommendations.append("平局预测")
        
        if stats.get("home_win_rate", 0.44) > 0.50:
            recommendations.append("让球胜主队")
        elif stats.get("away_win_rate", 0.30) > 0.35:
            recommendations.append("让球胜客队")
        
        if stats.get("over_2_5_rate", 0.52) > 0.55:
            recommendations.append("大2.5球")
        elif stats.get("over_2_5_rate", 0.52) < 0.48:
            recommendations.append("小2.5球")
        
        if stats.get("btts_yes_rate", 0.47) > 0.50:
            recommendations.append("双方进球")
        
        return recommendations
    
    def search_knowledge(self, query: str) -> List[Dict]:
        """
        搜索RAG知识库
        
        Args:
            query: 搜索关键词
        
        Returns:
            相关的知识条目
        """
        rag = self.rag_knowledge
        knowledge = rag.get("knowledge", [])
        
        query_lower = query.lower()
        results = []
        
        for item in knowledge:
            text = json.dumps(item, ensure_ascii=False).lower()
            if query_lower in text:
                results.append(item)
        
        return results[:10]  # 返回最多10条
    
    def get_database_summary(self) -> Dict:
        """获取数据库摘要"""
        raw = self.raw_data
        metadata = raw.get("metadata", {})
        
        return {
            "total_matches": metadata.get("total_matches", len(raw.get("matches", []))),
            "leagues_count": len(metadata.get("leagues", [])),
            "date_range": metadata.get("date_range", "N/A"),
            "odds_providers": metadata.get("odds_provider", "N/A"),
            "leagues_stats_calculated": len(self._league_stats) if self._league_stats else 0,
            "teams_stats_calculated": len(self._team_stats) if self._team_stats else 0,
            "data_sources": {
                "raw": os.path.exists(os.path.join(RAW_DATA_DIR, "COMPLETE_FOOTBALL_DATA_FINAL_UPDATED.json")),
                "chinese": os.path.exists(os.path.join(CHINESE_DATA_DIR, "竞彩足球_chinese_data.json")),
                "rag": os.path.exists(os.path.join(MEMORY_DIR, "rag_knowledge.json"))
            }
        }


# 全局单例
_history_db = None

def get_historical_database(lazy_load: bool = True) -> HistoricalDatabase:
    """获取历史数据库单例"""
    global _history_db
    if _history_db is None:
        _history_db = HistoricalDatabase(lazy_load=lazy_load)
    return _history_db


def load_all_historical_data() -> Dict:
    """
    加载所有历史数据（兼容旧接口）
    
    Returns:
        包含所有数据的字典
    """
    db = get_historical_database(lazy_load=False)
    return {
        "raw": db.raw_data,
        "chinese": db.chinese_data,
        "rag": db.rag_knowledge,
        "league_stats": db._league_stats or {},
        "team_stats": db._team_stats or {}
    }


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("历史数据库测试")
    print("=" * 60)
    
    db = get_historical_database()
    
    print("\n📊 数据库摘要:")
    summary = db.get_database_summary()
    for k, v in summary.items():
        print(f"   {k}: {v}")
    
    print("\n🏆 联赛推荐 (英超 E0):")
    recs = db.get_league_recommendations("E0")
    for r in recs:
        print(f"   - {r}")
    
    print("\n📈 英超统计 (E0):")
    stats = db.get_league_stats("E0")
    for k, v in stats.items():
        if k != "sample_size":
            print(f"   {k}: {v:.3f}" if isinstance(v, float) else f"   {k}: {v}")
