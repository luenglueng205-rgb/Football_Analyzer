import json
from typing import Dict, Any, List

def get_scout_tools() -> List[Dict[str, Any]]:
    """
    获取 ScoutAgent 的 OpenAI Tool Calling Schemas
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "get_team_stats",
                "description": "获取球队历史统计数据（如进球率、控球率等基本面数据）",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "team_name": {
                            "type": "string",
                            "description": "球队名称，例如 '曼联'"
                        },
                        "league": {
                            "type": "string",
                            "description": "联赛代码，例如 'E0' 表示英超，可为空"
                        }
                    },
                    "required": ["team_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_recent_matches",
                "description": "获取球队近期比赛战绩",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "team_name": {
                            "type": "string",
                            "description": "球队名称"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "获取的比赛场数，默认 5"
                        }
                    },
                    "required": ["team_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_live_injuries",
                "description": "获取球队实时伤停情报（这是非常关键的临场基本面数据）",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "team_name": {
                            "type": "string",
                            "description": "球队名称"
                        }
                    },
                    "required": ["team_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_live_odds",
                "description": "获取实时盘口与水位变动数据（包含初盘、即时盘、以及必发交易量）",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "home_team": {
                            "type": "string",
                            "description": "主队名称"
                        },
                        "away_team": {
                            "type": "string",
                            "description": "客队名称"
                        }
                    },
                    "required": ["home_team", "away_team"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_knowledge",
                "description": "在 22万场历史 RAG 库中搜索相似盘口和操盘手法",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "搜索关键词，例如 '主队强队客场受让半一降水'"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ]
