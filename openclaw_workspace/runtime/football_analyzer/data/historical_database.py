# -*- coding: utf-8 -*-
"""
Football Lottery Multi-Agent System - 历史数据库加载器 v3.0 Pro
OpenClaw规范版本专用

数据源:
1. data/raw/COMPLETE_FOOTBALL_DATA_FINAL_UPDATED.json - 原始历史数据(221,415条)
2. data/chinese_mapped/ - 转换后的中文数据

注意: 使用相对于项目目录的路径，便于整体迁移
"""

import json
import os
import sys
import math
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, Counter
from datetime import datetime
import statistics

from tools.paths import data_dir, datasets_dir

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RAW_DATA_DIR = os.path.join(datasets_dir(), "raw")
CHINESE_DATA_DIR = os.path.join(datasets_dir(), "chinese_mapped")


class HistoricalDatabase:
    """
    历史数据库加载器 (OpenClaw版本)
    
    提供:
    - 完整历史比赛数据 (221,415条)
    - 联赛统计特征
    - 球队历史表现
    - 赔率历史模型
    """
    
    def __init__(self, lazy_load: bool = True):
        self.lazy_load = lazy_load
        self._raw_data = None
        self._chinese_data = None
        self._league_stats = None
        self._team_stats = None
        self.league_mapping = {}
        
        self._load_league_mapping()
        print(f"✅ OpenClaw历史数据库初始化完成")
        print(f"   - 原始数据: {RAW_DATA_DIR}")
        print(f"   - 中文数据: {CHINESE_DATA_DIR}")
    
    def _load_league_mapping(self):
        """加载联赛映射"""
        mapping_file = os.path.join(data_dir(), "league_mapping.json")
        if os.path.exists(mapping_file):
            with open(mapping_file, 'r', encoding='utf-8') as f:
                self.league_mapping = json.load(f)
    
    @property
    def raw_data(self) -> Dict:
        """懒加载原始历史数据"""
        if self._raw_data is None:
            filepath = os.path.join(RAW_DATA_DIR, 'COMPLETE_FOOTBALL_DATA_FINAL_UPDATED.json')
            if os.path.exists(filepath):
                print(f"📊 OpenClaw: 加载原始历史数据...")
                with open(filepath, 'r', encoding='utf-8') as f:
                    self._raw_data = json.load(f)
                print(f"✅ OpenClaw: 原始数据加载完成")
            else:
                self._raw_data = {"metadata": {}, "matches": []}
                print(f"⚠️ OpenClaw: 原始数据文件不存在")
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
    
    def get_league_stats(self, league_code: str) -> Dict[str, Any]:
        """获取联赛统计信息"""
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
        print("📊 OpenClaw: 计算联赛统计参数...")
        self._league_stats = {}
        
        raw = self.raw_data
        matches = raw.get("matches", [])
        
        if not matches:
            print("⚠️ OpenClaw: 原始数据为空")
            return
        
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
                "home_win_rate": results.count("H") / len(results) if results else 0.44,
                "draw_rate": results.count("D") / len(results) if results else 0.26,
                "away_win_rate": results.count("A") / len(results) if results else 0.30,
                "over_2_5_rate": sum(1 for t in total_goals if t > 2.5) / len(total_goals) if total_goals else 0.52,
                "under_2_5_rate": sum(1 for t in total_goals if t <= 2.5) / len(total_goals) if total_goals else 0.48,
                "btts_yes_rate": sum(1 for m in league_data if m.get("home_goals", 0) > 0 and m.get("away_goals", 0) > 0) / len(league_data) if league_data else 0.47,
                "sample_size": len(league_data),
                "goals_std": statistics.stdev(total_goals) if len(total_goals) > 1 else 1.5
            }
        
        print(f"✅ OpenClaw: 已计算 {len(self._league_stats)} 个联赛的统计参数")
    
    def get_team_stats(self, team_name: str, recent_n: int = 10) -> Dict[str, Any]:
        """
        获取球队的历史统计基准 (进失球)
        """
        matches = self.raw_data().get("data", [])
        
        team_matches = []
        for match in matches:
            home = match.get("home_team", "")
            away = match.get("away_team", "")
            if home == team_name or away == team_name:
                team_matches.append(match)
        
        if not team_matches:
            return {"team": team_name, "baseline_mu_scored": 1.45, "baseline_mu_conceded": 1.10, "message": "未找到历史数据，使用默认基准"}
            
        # 排序取最近 N 场
        team_matches.sort(key=lambda x: x.get("date", ""), reverse=True)
        recent_matches = team_matches[:recent_n]
        
        scored = []
        conceded = []
        for match in recent_matches:
            home = match.get("home_team", "")
            if home == team_name:
                scored.append(match.get("home_score", 0))
                conceded.append(match.get("away_score", 0))
            else:
                scored.append(match.get("away_score", 0))
                conceded.append(match.get("home_score", 0))
                
        mu_scored = sum(scored) / len(scored) if scored else 1.45
        mu_conceded = sum(conceded) / len(conceded) if conceded else 1.10
        
        return {
            "team": team_name,
            "baseline_mu_scored": round(mu_scored, 2),
            "baseline_mu_conceded": round(mu_conceded, 2),
            "matches_analyzed": len(recent_matches),
            "message": f"基于最近 {len(recent_matches)} 场历史数据计算。请根据最新伤停新闻进行微调(+-0.2)。"
        }

    def get_league_recommendations(self, league_code: str) -> List[str]:
        """根据联赛特征推荐适合的玩法"""
        stats = self.get_league_stats(league_code)
        
        recommendations = []
        
        if stats.get("avg_total_goals", 2.5) > 2.8:
            recommendations.append("总进球 - 大球")
        elif stats.get("avg_total_goals", 2.5) < 2.3:
            recommendations.append("总进球 - 小球")
        
        if stats.get("draw_rate", 0.26) > 0.28:
            recommendations.append("平局预测")
        
        if stats.get("over_2_5_rate", 0.52) > 0.55:
            recommendations.append("大2.5球")
        elif stats.get("over_2_5_rate", 0.52) < 0.48:
            recommendations.append("小2.5球")
        
        if stats.get("btts_yes_rate", 0.47) > 0.50:
            recommendations.append("双方进球")
        
        return recommendations
    
    def get_database_summary(self) -> Dict:
        """获取数据库摘要"""
        raw = self.raw_data
        metadata = raw.get("metadata", {})
        
        return {
            "total_matches": metadata.get("total_matches", len(raw.get("matches", []))),
            "leagues_count": len(metadata.get("leagues", [])),
            "date_range": metadata.get("date_range", "N/A"),
            "leagues_stats_calculated": len(self._league_stats) if self._league_stats else 0,
            "data_sources": {
                "raw": os.path.exists(os.path.join(RAW_DATA_DIR, "COMPLETE_FOOTBALL_DATA_FINAL_UPDATED.json")),
                "chinese": os.path.exists(os.path.join(CHINESE_DATA_DIR, "竞彩足球_chinese_data.json"))
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


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("OpenClaw 历史数据库测试")
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
