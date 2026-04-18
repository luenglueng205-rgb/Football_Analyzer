import asyncio
import threading
from datetime import datetime
import os
import json
import re
from typing import Any, Dict, List, Optional
from ddgs import DDGS
from tools.visual_browser import VisualBrowser
from tools.domestic_500_fixtures import fetch_500_trade_html, parse_500_trade_fixtures_html

def _env_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    s = str(v).strip().lower()
    return s in {"1", "true", "yes", "y", "on"}

def _looks_like_captcha(html: str) -> bool:
    t = html or ""
    return any(k in t for k in ("验证码", "安全验证", "人机验证", "verify", "captcha"))

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
        self.visual = None
        try:
            if VisualBrowser is not None:
                self.visual = VisualBrowser()
        except Exception:
            self.visual = None

    @staticmethod
    def _guess_league_name(text: str) -> Optional[str]:
        for name in ("英超", "西甲", "意甲", "德甲", "法甲", "欧冠"):
            if name in text:
                return name
        return None

    @staticmethod
    def _extract_fixtures_from_search_results(results: List[Dict[str, Any]], *, date: str) -> List[Dict[str, Any]]:
        fixtures: List[Dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()

        time_re = re.compile(r"(?P<h>\d{1,2}):(?P<m>\d{2})")
        vs_re = re.compile(
            r"(?P<home>[A-Za-z\u4e00-\u9fff][A-Za-z\u4e00-\u9fff\s·]{1,30})\s*(?:vs|VS|V\.S\.|对|vs\.|-)\s*(?P<away>[A-Za-z\u4e00-\u9fff][A-Za-z\u4e00-\u9fff\s·]{1,30})"
        )

        for r in results:
            url = str(r.get("href") or r.get("url") or "")
            if "500.com" not in url:
                continue

            text = f"{r.get('title') or ''} {r.get('body') or ''} {r.get('snippet') or ''}"
            if date not in text and "今日" not in text and "今天" not in text:
                continue
            tm = time_re.search(text)
            if not tm:
                continue

            m = vs_re.search(text)
            if not m:
                continue

            home = m.group("home").strip()
            away = m.group("away").strip()
            league = AgentBrowser._guess_league_name(text) or "UNK"
            if league != "UNK" and home.startswith(league):
                home = home[len(league) :].strip()
            if not home or not away or home == away:
                continue

            hh = int(tm.group("h"))
            mm = int(tm.group("m"))
            if hh > 23 or mm > 59:
                continue

            kickoff_time = f"{date} {hh:02d}:{mm:02d}"
            status = "played" if any(x in text for x in ("完场", "已结束", "FT")) else "upcoming"

            key = (league, home, away)
            if key in seen:
                continue
            seen.add(key)
            fixtures.append(
                {
                    "league": league,
                    "home_team": home,
                    "away_team": away,
                    "kickoff_time": kickoff_time,
                    "status": status,
                    "url": url,
                }
            )

        return fixtures

    def _scrape_500_fixtures_ddgs(self, *, date: Optional[str] = None) -> List[Dict[str, Any]]:
        target_date = date or datetime.now().strftime("%Y-%m-%d")
        query = f"site:zx.500.com jczq 竞彩足球 {target_date} 赛程"
        try:
            results = list(self.ddgs.text(query, max_results=10))
        except Exception:
            return []
        return self._extract_fixtures_from_search_results(results, date=target_date)

    def scrape_500_fixtures(self, date: Optional[str] = None) -> list:
        """使用视觉浏览器获取今日赛程"""
        html = fetch_500_trade_html(date=date)
        if html:
            if _looks_like_captcha(html) and _env_bool("INFO_FIRST_MODE", True):
                return self._scrape_500_fixtures_ddgs(date=date)
            fixtures = parse_500_trade_fixtures_html(html=html, date=date)
            if fixtures:
                return fixtures

        if self.visual is not None:
            task = "访问 http://zx.500.com/jczq/ ，找到今天（或者即将开赛）的所有竞彩足球比赛。请严格以JSON数组格式返回，包含 'home_team', 'away_team', 'status'(填'upcoming'或'played')。"

            try:
                res = _run_async_sync(self.visual.extract_info(task))

                match = re.search(r"\[.*\]", res, re.DOTALL)
                if match:
                    return json.loads(match.group(0))
            except Exception as e:
                print(f"[AgentBrowser] Visual scrape error: {e}")

        return self._scrape_500_fixtures_ddgs(date=date)

    def search_dongqiudi_news(self, team_name: str) -> list:
        """使用视觉浏览器获取伤病情报"""
        if self.visual is None:
            return []
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
