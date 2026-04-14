import asyncio
import threading
from ddgs import DDGS
from tools.visual_browser import VisualBrowser

def _run_async_sync(coro):
    """
    一个能在同步方法中运行异步协程的辅助函数。
    即使当前线程已经有运行中的 event loop（比如被 run_live_decision 的 async main 内部同步调用时），
    也能通过启动新线程来避免 RuntimeError。
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result = None
    err = None

    def runner():
        nonlocal result, err
        try:
            result = asyncio.run(coro)
        except Exception as e:
            err = e

    t = threading.Thread(target=runner)
    t.start()
    t.join()
    if err:
        raise err
    return result

class AgentBrowser:
    """
    重构后的 AgentBrowser：不再写爬虫逻辑，而是将任务翻译为自然语言交给 VisualBrowser。
    同时保留 ddgs 作为极轻量级的文本搜索兜底。
    """
    def __init__(self):
        self.ddgs = DDGS()
        self.visual = VisualBrowser()

    def scrape_500_fixtures(self) -> list:
        """使用视觉浏览器获取今日赛程"""
        # 注意：此处我们需要将其包装为同步或通过 asyncio.run 执行，因为原有架构很多地方是同步调用
        task = "访问 http://zx.500.com/jczq/ ，找到今天（或者即将开赛）的所有竞彩足球比赛。请严格以JSON数组格式返回，包含 'home_team', 'away_team', 'status'(填'upcoming'或'played')。"
        
        try:
            res = _run_async_sync(self.visual.extract_info(task))
            
            # 简单清洗并解析 JSON
            import json
            import re
            match = re.search(r'\[.*\]', res, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            return []
        except Exception as e:
            print(f"[AgentBrowser] Visual scrape error: {e}")
            return []

    def search_dongqiudi_news(self, team_name: str) -> list:
        """使用视觉浏览器获取伤病情报"""
        task = f"访问懂球帝网站或直接搜索关于'{team_name}'的最新足球新闻，特别是伤停和首发情报。提炼出3条最关键的信息返回。"
        try:
            res = _run_async_sync(self.visual.extract_info(task))
            return [{"title": "视觉智能体情报提炼", "snippet": res, "url": "browser-use"}]
        except Exception as e:
            print(f"[AgentBrowser] Visual search error: {e}")
            return []

    def scrape_okooo_odds_search(self, home_team: str, away_team: str) -> list:
        """兜底：依然保留 ddgs 轻量搜索"""
        try:
            query = f"澳客 OR 捷报比分 {home_team} vs {away_team} 赔率 分析"
            results = list(self.ddgs.text(query, max_results=3))
            return [
                {"title": r.get('title', ''), "snippet": r.get('body', ''), "url": r.get('href', '')}
                for r in results
            ]
        except Exception:
            return []

    def search_web(self, query: str, max_results: int = 5) -> list:
        try:
            return list(self.ddgs.text(query, max_results=max_results))
        except Exception:
            return []
