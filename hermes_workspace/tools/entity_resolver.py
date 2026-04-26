import difflib
from typing import Optional, Dict, Any

class EntityResolver:
    """
    实体消歧引擎 (Entity Resolution Engine)
    用于弥合自然语言 (LLM 输出) 与强类型数据库接口 (DataGateway) 之间的断层。
    """
    def __init__(self):
        # 标准化联赛 ID 映射 (以 API-Football 的 ID 为例)
        self.standard_leagues = {
            "英超": 39, "英格兰超级联赛": 39, "Premier League": 39, "EPL": 39,
            "西甲": 140, "西班牙甲级联赛": 140, "La Liga": 140,
            "意甲": 135, "意大利甲级联赛": 135, "Serie A": 135,
            "德甲": 78, "德国甲级联赛": 78, "Bundesliga": 78,
            "法甲": 61, "法国甲级联赛": 61, "Ligue 1": 61,
            "欧冠": 2, "欧洲冠军联赛": 2, "UEFA Champions League": 2,
            "日职": 98, "日职联": 98, "J1 League": 98
        }
        
        # 标准化球队 ID 映射 (局部缓存，实盘应从本地 SQLite 加载)
        self.standard_teams = {
            "阿森纳": 42, "Arsenal": 42,
            "切尔西": 49, "Chelsea": 49,
            "曼城": 50, "Manchester City": 50,
            "曼联": 33, "Manchester United": 33,
            "皇马": 541, "Real Madrid": 541,
            "拜仁": 157, "Bayern Munich": 157,
            "横滨水手": 234, "Yokohama F. Marinos": 234,
            "川崎前锋": 235, "Kawasaki Frontale": 235
        }

    def resolve_league_id(self, raw_name: str) -> int:
        """模糊匹配联赛名称，返回标准 ID。如果失败则回退到默认值 39(英超) 防止崩溃"""
        if not raw_name:
            return 39
            
        # 1. 精确匹配
        if raw_name in self.standard_leagues:
            return self.standard_leagues[raw_name]
            
        # 2. 模糊匹配
        matches = difflib.get_close_matches(raw_name, self.standard_leagues.keys(), n=1, cutoff=0.4)
        if matches:
            resolved = matches[0]
            print(f"   -> 🔤 [Entity Resolver] 将联赛 '{raw_name}' 模糊纠正为 '{resolved}' (ID: {self.standard_leagues[resolved]})")
            return self.standard_leagues[resolved]
            
        print(f"   -> ⚠️ [Entity Resolver] 无法识别联赛 '{raw_name}'，安全降级回退至英超 (ID: 39)")
        return 39

    def resolve_team_id(self, raw_name: str) -> int:
        """模糊匹配球队名称，返回标准 ID。失败回退到 0"""
        if not raw_name:
            return 0
            
        if raw_name in self.standard_teams:
            return self.standard_teams[raw_name]
            
        matches = difflib.get_close_matches(raw_name, self.standard_teams.keys(), n=1, cutoff=0.4)
        if matches:
            resolved = matches[0]
            return self.standard_teams[resolved]
            
        return 0

    def resolve_match_id(self, home_team: str, away_team: str, date: Optional[str] = None) -> str:
        """
        生成标准化的 Match ID
        由于 API 接口强制要求 match_id，此处将模糊的队名转为标准 ID 拼接。
        """
        home_id = self.resolve_team_id(home_team)
        away_id = self.resolve_team_id(away_team)
        
        # 如果能查到真实的球队 ID，就拼接真实 ID；否则使用清洗后的名字拼音/英文
        home_part = str(home_id) if home_id != 0 else home_team.replace(" ", "_")
        away_part = str(away_id) if away_id != 0 else away_team.replace(" ", "_")
        
        date_part = f"_{date}" if date else ""
        match_id = f"MATCH_{home_part}_{away_part}{date_part}"
        
        return match_id

# 单例模式，供全局调用
resolver = EntityResolver()