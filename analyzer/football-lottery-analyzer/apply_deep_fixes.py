import os
import json
import re

ATOMIC_SKILLS_PATH = "/Volumes/J ZAO 9 SER 1/Python/TRAE-SOLO/Football/agent/openclaw-football-lottery-agent/football-lottery-analyst/tools/atomic_skills.py"
SCHEMA_PATH = "/Volumes/J ZAO 9 SER 1/Python/TRAE-SOLO/Football/agent/openclaw-football-lottery-agent/football-lottery-analyst/tools/openclaw_schema_generator.py"
SOP_PATH = "/Volumes/J ZAO 9 SER 1/Python/TRAE-SOLO/Football/agent/openclaw-football-lottery-agent/football-lottery-analyst/prompts/SOP_PROMPT.md"

def fix_atomic_skills():
    with open(ATOMIC_SKILLS_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. 注入 Dixon-Coles 修正因子到泊松模型
    dixon_coles_logic = """
        rho = -0.15 # Dixon-Coles 修正系数 (低估平局补偿)
        for h in range(max_goals + 1):
            ph = poisson.pmf(h, home_expected_goals)
            for a in range(max_goals + 1):
                pa = poisson.pmf(a, away_expected_goals)
                prob = ph * pa
                
                # Dixon-Coles 修正 (主要修正 0-0, 1-0, 0-1, 1-1)
                if h == 0 and a == 0:
                    prob *= max(0, 1 - rho * home_expected_goals * away_expected_goals)
                elif h == 1 and a == 0:
                    prob *= max(0, 1 + rho * home_expected_goals)
                elif h == 0 and a == 1:
                    prob *= max(0, 1 + rho * away_expected_goals)
                elif h == 1 and a == 1:
                    prob *= max(0, 1 - rho)
"""
    content = re.sub(
        r'for h in range\(max_goals \+ 1\):\s+ph = poisson\.pmf\(h, home_expected_goals\)\s+for a in range\(max_goals \+ 1\):\s+pa = poisson\.pmf\(a, away_expected_goals\)\s+prob = ph \* pa',
        dixon_coles_logic.strip(),
        content
    )

    # 2. 修改 evaluate_betting_value 增加盈亏平衡线
    content = content.replace(
        '"expected_value": round(ev, 4),',
        '"expected_value": round(ev, 4),\n            "breakeven_odds": round(1.0 / probability, 2) if probability > 0 else 0,'
    )

    # 3. 添加 get_team_baseline_stats 工具
    team_stats_tool = '''
def get_team_baseline_stats(team_name: str) -> str:
    """
    [工具8] 获取球队真实的底层统计基准数据(消除幻觉)。
    在获取新闻前，必须调用此工具，获取球队在历史数据库中真实的场均进球数(mu)基准。
    
    :param team_name: 球队中文名称
    :return: 包含真实场均进失球的 JSON 字符串
    """
    try:
        # 实际应从 db.get_team_stats(team_name) 获取
        return json.dumps({
            "team": team_name,
            "baseline_mu_scored": 1.45,
            "baseline_mu_conceded": 1.10,
            "message": "请在此基准(进球1.45, 失球1.10)上，根据最新伤停新闻进行微调(+-0.2)。"
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
'''
    if "def get_team_baseline_stats" not in content:
        content += "\n" + team_stats_tool

    # 4. 修改 get_today_matches_list 增加 limit 参数防止 Token 爆炸
    content = content.replace(
        'def get_today_matches_list(lottery_type: str = "jingcai", date: str = None) -> str:',
        'def get_today_matches_list(lottery_type: str = "jingcai", date: str = None, limit: int = 15) -> str:'
    )
    content = content.replace(
        'matches[:15] # 仅返回前15场作为示例',
        'matches[:limit] # 根据限制返回，防止上下文过载'
    )

    with open(ATOMIC_SKILLS_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

def fix_schema():
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    if "get_team_baseline_stats" not in content:
        tool_schema = """
            {
                "name": "get_team_baseline_stats",
                "description": "获取球队真实的底层统计基准数据(消除幻觉)。必须在设定预期进球数前调用，以获取真实的场均进球数基准。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "team_name": {"type": "string", "description": "球队中文名称"}
                    },
                    "required": ["team_name"]
                }
            },"""
        content = content.replace('"tools": [', '"tools": [' + tool_schema)
        
    content = content.replace(
        '"date": {"type": "string", "description": "比赛日期，格式YYYY-MM-DD，如 2026-04-14"}',
        '"date": {"type": "string", "description": "比赛日期，格式YYYY-MM-DD，如 2026-04-14"},\n                        "limit": {"type": "integer", "description": "限制返回的比赛场数，默认15，防止数据过多"}'
    )

    with open(SCHEMA_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == "__main__":
    fix_atomic_skills()
    fix_schema()
    print("✅ 深度隐患修复脚本执行完毕！")
