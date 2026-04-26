"""
舆情 Agent：抓取社媒情绪、投注倾向

职责：
- 并发获取两队社媒舆情得分
- 计算市场整体倾向偏差
- 为逆向投注策略提供情绪信号
"""
import asyncio
import logging

logger = logging.getLogger(__name__)


class SocialAgent:
    """舆情情报 Agent"""

    async def gather(self, team_a: str, team_b: str) -> dict:
        """
        并发获取两队社媒情绪
        
        Returns:
            dict: {
                "team_a_sentiment": {...},
                "team_b_sentiment": {...},
                "overall_bias": "HOME_FAVORED" | "AWAY_FAVORED" | "NEUTRAL"
            }
        """
        task_a = self._fetch_sentiment(team_a)
        task_b = self._fetch_sentiment(team_b)

        sent_a, sent_b = await asyncio.gather(task_a, task_b, return_exceptions=True)

        if isinstance(sent_a, Exception):
            logger.warning(f"舆情抓取异常 {team_a}: {sent_a}")
            sent_a = {"team": team_a, "sentiment_score": 0.5}
        if isinstance(sent_b, Exception):
            logger.warning(f"舆情抓取异常 {team_b}: {sent_b}")
            sent_b = {"team": team_b, "sentiment_score": 0.5}

        return {
            "team_a_sentiment": sent_a,
            "team_b_sentiment": sent_b,
            "overall_bias": self._compute_bias(sent_a, sent_b),
        }

    async def _fetch_sentiment(self, team: str) -> dict:
        """
        抓取单队社媒情绪得分
        
        数据源候选：
        - Twitter/X API (球队标签情感分析)
        - Reddit r/soccer 热帖情绪
        - 国内：懂球帝评论区、虎扑话题热度
        - 投注平台资金流向（冷热指数的补充视角）
        
        sentiment_score 范围 [0.0, 1.0]：
        - 0.0 = 极度看衰
        - 0.5 = 中性
        - 1.0 = 极度看好
        """
        try:
            # 骨架实现 — 实际应接真实舆情数据源
            return {
                "team": team,
                "sentiment_score": 0.5,
                "social_volume": 0,
                "betting_flow_bias": 0.0,
                "source": "placeholder",
            }
        except Exception as e:
            logger.warning(f"舆情抓取失败 {team}: {e}")
            return {"team": team, "sentiment_score": 0.5}

    def _compute_bias(self, sent_a: dict, sent_b: dict) -> str:
        """
        计算市场整体倾向
        
        偏差阈值：
        - |diff| < 0.1 → NEUTRAL（市场无明显偏向）
        - diff >= 0.1 → HOME_FAVORED / AWAY_FAVORED
        
        该信号用于：
        - 逆向投注：当市场一边倒时考虑反向
        - Kelly 公式调整：降低热门方仓位
        """
        score_a = sent_a.get("sentiment_score", 0.5)
        score_b = sent_b.get("sentiment_score", 0.5)
        diff = score_a - score_b

        if abs(diff) < 0.1:
            return "NEUTRAL"
        return "HOME_FAVORED" if diff > 0 else "AWAY_FAVORED"
