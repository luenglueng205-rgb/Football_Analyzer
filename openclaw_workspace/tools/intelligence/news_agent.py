"""
新闻情报 Agent：抓取比赛相关新闻

职责：
- 并发获取两队最新新闻
- 识别交叉新闻（同时涉及两队：转会、恩怨、历史交锋等）
- 输出结构化新闻摘要供下游决策使用
"""
import asyncio
import logging

logger = logging.getLogger(__name__)


class NewsAgent:
    """新闻情报 Agent"""

    async def gather(self, team_a: str, team_b: str) -> dict:
        """
        并发获取两队新闻，返回聚合结果
        
        Args:
            team_a: 主队名称
            team_b: 客队名称
            
        Returns:
            dict: {
                "team_a_news": [...],
                "team_b_news": [...],
                "cross_news": [...]  # 同时涉及两队的新闻
            }
        """
        task_a = self._fetch_team_news(team_a)
        task_b = self._fetch_team_news(team_b)

        news_a, news_b = await asyncio.gather(task_a, task_b, return_exceptions=True)

        if isinstance(news_a, Exception):
            logger.warning(f"新闻抓取异常 {team_a}: {news_a}")
            news_a = []
        if isinstance(news_b, Exception):
            logger.warning(f"新闻抓取异常 {team_b}: {news_b}")
            news_b = []

        return {
            "team_a_news": news_a,
            "team_b_news": news_b,
            "cross_news": self._find_cross_news(news_a, news_b),
        }

    async def _fetch_team_news(self, team: str) -> list:
        """
        抓取单队新闻
        
        实际实现应调用新闻 API（如虎扑、懂球帝、ESPN 等），
        当前为模拟实现，保留原有 DDGS 搜索能力。
        """
        try:
            from duckduckgo_search import DDGS

            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(f"{team} football news today", max_results=3):
                    results.append({
                        "title": r.get("title", ""),
                        "body": r.get("body", ""),
                        "href": r.get("href", ""),
                    })
            return [{"team": team, "articles": results}]
        except ImportError:
            # DDGS 不可用时返回空列表，不阻塞其他 Agent
            logger.debug(f"DDGS 未安装，跳过 {team} 新闻抓取")
            return []
        except Exception as e:
            logger.warning(f"新闻抓取失败 {team}: {e}")
            return []

    def _find_cross_news(self, news_a: list, news_b: list) -> list:
        """
        找出同时涉及两队的新闻（转会、恩怨、历史交锋等）
        
        当前为骨架实现，后续可接入 NLP 相似度匹配。
        """
        # TODO: 接入实体识别 + 关系抽取
        return []
