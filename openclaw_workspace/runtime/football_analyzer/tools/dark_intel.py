import asyncio
import os
import json
import logging
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

class DarkIntelExtractor:
    """
    2026 版暗网情报提取器 (Dark Intel & Sentiment Extractor)
    提取社交媒体、论坛、记者推特上的“非结构化情绪”，
    并将其转化为 xG 衰减/增益因子。
    """
    def __init__(self):
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        api_key = os.getenv("OPENAI_API_KEY", "dummy-key-for-test")
        try:
            self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        except Exception:
            self.client = None

    async def analyze_social_sentiment(self, team_name: str, raw_tweets: str) -> dict:
        """
        将社交媒体的生肉文本，转化为可以用于数学计算的情绪得分 (Sentiment Score)。
        """
        print(f"\n    [🕵️ Dark Intel] 启动暗网情报提取。正在分析 '{team_name}' 的社交媒体舆情...")
        await asyncio.sleep(0.5) 
        
        if not self.client:
            return self._mock_dark_intel_analysis(team_name)
            
        prompt = f"""
        你是一个顶级的足彩量化情报分析师。
        请阅读以下关于 '{team_name}' 近期社交媒体的生肉文本，并评估其更衣室情绪、战意和士气。
        
        你需要输出一个 JSON 格式的结构化数据，包含：
        1. sentiment_score: 情绪得分，范围 -1.0 到 1.0 (-1 代表将帅不和、罢训、极度悲观；1 代表士气高昂、换帅如换刀；0 代表正常)
        2. xg_modifier: 预期进球(xG)修正系数。如果情绪极差，请输出负数（如 -0.15 表示进攻火力下降 15%）；如果情绪极好，输出正数（如 0.10）。
        3. reasoning: 一句简短的解释。
        
        生肉文本：
        {raw_tweets}
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            print(f"    [🕵️ Dark Intel] 情绪得分: {result.get('sentiment_score')}, xG 修正: {result.get('xg_modifier')}")
            return result
        except Exception as e:
            return {"sentiment_score": 0.0, "xg_modifier": 0.0, "reasoning": f"分析失败: {e}"}

    def _mock_dark_intel_analysis(self, team_name: str) -> dict:
        """无网络/Key 时的 Mock 数据"""
        is_bad = len(team_name) % 2 == 0 # 随机好坏
        if is_bad:
            return {
                "sentiment_score": -0.8,
                "xg_modifier": -0.12,
                "reasoning": f"检测到当地跟队记者爆料 {team_name} 主力中卫与主教练在训练场发生激烈争吵，更衣室气氛降至冰点，战意成疑。"
            }
        else:
            return {
                "sentiment_score": 0.6,
                "xg_modifier": 0.08,
                "reasoning": f"社交媒体显示 {team_name} 球迷对新任主教练极度狂热，主场门票售罄，'换帅红利'明显，士气高涨。"
            }

if __name__ == "__main__":
    extractor = DarkIntelExtractor()
    tweets = "The manager just walked out of the press conference. Players look miserable. The captain is refusing to sign a new contract."
    result = asyncio.run(extractor.analyze_social_sentiment("曼联", tweets))
    print(json.dumps(result, ensure_ascii=False, indent=2))
