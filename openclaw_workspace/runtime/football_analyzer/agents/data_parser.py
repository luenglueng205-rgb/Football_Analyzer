import os
import json
from openai import AsyncOpenAI

class DataParserAgent:
    """
    P4 阶段：深度调优解析器 (Subagent)
    专门用于将 AgentBrowser 爬取回来的非结构化中文文本（如懂球帝的新闻、澳客的评论）
    强制清洗、结构化为干净的 JSON 数据。
    """
    def __init__(self):
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        api_key = os.getenv("OPENAI_API_KEY", "dummy-key-for-test")
        try:
            self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        except Exception as e:
            self.client = None

    async def parse_injuries(self, team_name: str, raw_text: str) -> dict:
        """
        将杂乱的新闻文本提取为伤停名单 JSON
        """
        if not self.client:
            return {"error": "Parser LLM client not initialized", "raw": raw_text}

        prompt = f"""
你是一个专业的足球情报提取专家。
请从以下给定的新闻文本中，提取出【{team_name}】的球员伤病和停赛情况。
严格以 JSON 格式返回，格式如下：
{{
    "team": "{team_name}",
    "injuries": [
        {{"player": "球员A", "status": "伤缺", "reason": "大腿肌肉拉伤"}},
        {{"player": "球员B", "status": "出战成疑", "reason": "生病"}}
    ]
}}
如果文本中没有明确的伤停信息，请返回空的 injuries 列表。不要输出任何多余的解释。

文本内容：
{raw_text}
"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={ "type": "json_object" }
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            print(f"[ParserAgent] Parse error: {e}")
            return {"error": str(e), "raw": raw_text}

    async def parse_odds(self, home_team: str, away_team: str, raw_text: str) -> dict:
        """
        从非结构化文本（如搜索片段）中尝试提炼出欧赔、亚盘
        """
        if not self.client:
            return {"error": "Parser LLM client not initialized", "raw": raw_text}

        prompt = f"""
你是一个专业的博彩数据提取专家。
请尝试从以下杂乱的文本片段中，提取出 {home_team} vs {away_team} 这场比赛的赔率和盘口数据。
严格以 JSON 格式返回，如果找不到具体的数字，就返回 null。
格式如下：
{{
    "match": "{home_team} vs {away_team}",
    "odds": {{
        "home_win": 2.15,
        "draw": 3.20,
        "away_win": 3.10
    }},
    "asian_handicap": "-0.25",
    "summary": "从文本中提炼出的一句话分析结论"
}}

文本内容：
{raw_text}
"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={ "type": "json_object" }
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            print(f"[ParserAgent] Parse error: {e}")
            return {"error": str(e), "raw": raw_text}

