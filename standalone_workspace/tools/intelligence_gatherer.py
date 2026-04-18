import json
import logging
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

def gather_match_intelligence(team_a: str, team_b: str) -> str:
    """
    Search the web for breaking news, injuries, suspensions, or weather conditions for a specific match.
    The AI should use this to adjust the baseline quantitative model.
    """
    query = f"{team_a} {team_b} injuries suspensions news"
    results = []
    
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=3):
                results.append(r.get('body', ''))
    except Exception as e:
        logger.error(f"DDGS Search failed: {e}")
        return json.dumps({"error": "Failed to gather live intelligence. Proceed with historical data only."})
        
    if not results:
        return json.dumps({"insight": "No significant breaking news found."})
        
    return json.dumps({
        "query": query,
        "breaking_news": results,
        "ai_strategist_instruction": "【多模态感知建议】：请对以上抓取到的新闻进行情感分析。如果发现某队主力伤停，必须在 Poisson 期望模型中大幅下调其进攻/防守系数；如果是雨雪天气，必须大幅上调平局（Draw）或小球（Under 2.5）的发生概率。"
    }, ensure_ascii=False)
