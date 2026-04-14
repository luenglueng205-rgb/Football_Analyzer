import os
import requests
from typing import Dict, Any, List, Optional

from tools.multisource_fetcher import MultiSourceFetcher

ANALYZER_API_URL = os.getenv("ANALYZER_API_URL", "http://localhost:8000")

class AnalyzerAPI:
    """
    对接底层 Analyzer (System 2) 的工具类
    """

    _last_health_ok: Optional[bool] = None
    _fetcher: Optional[MultiSourceFetcher] = None

    @staticmethod
    def _get_fetcher() -> MultiSourceFetcher:
        if AnalyzerAPI._fetcher is None:
            AnalyzerAPI._fetcher = MultiSourceFetcher()
        return AnalyzerAPI._fetcher

    @staticmethod
    def health() -> bool:
        try:
            response = requests.get(f"{ANALYZER_API_URL}/health", timeout=2)
            response.raise_for_status()
            ok = response.json().get("status") == "ok"
            AnalyzerAPI._last_health_ok = ok
            return ok
        except Exception:
            AnalyzerAPI._last_health_ok = False
            return False

    @staticmethod
    def is_available() -> bool:
        if AnalyzerAPI._last_health_ok is True:
            return True
        return AnalyzerAPI.health()

    @staticmethod
    def _get(url: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        try:
            response = requests.get(url, params=params, timeout=3)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise RuntimeError(f"HTTP GET failed for {url}: {e}")

    @staticmethod
    def _post(url: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            response = requests.post(url, json=payload, timeout=3)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise RuntimeError(f"HTTP POST failed for {url}: {e}")
    
    @staticmethod
    def get_team_stats(team_name: str, league: str = None) -> Dict[str, Any]:
        """获取球队历史统计数据"""
        if not team_name:
            raise ValueError("team_name cannot be empty")
        if not AnalyzerAPI.is_available():
            raise ConnectionError("Analyzer API is not available")
        url = f"{ANALYZER_API_URL}/api/v1/data/team/{team_name}"
        params = {"league": league} if league else {}
        data = AnalyzerAPI._get(url, params=params) or {}
        return data.get("stats", {})

    @staticmethod
    def get_league_stats(league_code: str) -> Dict[str, Any]:
        """获取联赛统计数据"""
        if not league_code:
            return {}
        if not AnalyzerAPI.is_available():
            return {}
        url = f"{ANALYZER_API_URL}/api/v1/data/league/{league_code}"
        data = AnalyzerAPI._get(url) or {}
        return data.get("stats", {})

    @staticmethod
    def get_recent_matches(team_name: str, limit: int = 10) -> List[Dict]:
        """获取球队近期比赛"""
        if not team_name:
            return []
        if not AnalyzerAPI.is_available():
            return []
        url = f"{ANALYZER_API_URL}/api/v1/data/recent-matches/{team_name}"
        data = AnalyzerAPI._get(url, params={"n": limit}) or {}
        return data.get("recent_matches", [])

    @staticmethod
    def calculate_ev(odds: float, actual_probability: float) -> Dict[str, Any]:
        """计算期望值和价值投注"""
        if not AnalyzerAPI.is_available():
            return {}
        url = f"{ANALYZER_API_URL}/api/v1/odds/expected-value"
        payload = {
            "odds": odds,
            "actual_probability": actual_probability
        }
        return AnalyzerAPI._post(url, payload) or {}

    @staticmethod
    def search_knowledge(query: str) -> List[Dict]:
        """在 22万场历史 RAG 库中搜索"""
        if not query:
            return []
        if not AnalyzerAPI.is_available():
            return []
        url = f"{ANALYZER_API_URL}/api/v1/data/search"
        data = AnalyzerAPI._get(url, params={"query": query}) or {}
        return data.get("results", [])

    @staticmethod
    def get_live_news(team_name: str, limit: int = 5) -> List[Dict]:
        """获取球队实时新闻"""
        res = AnalyzerAPI.get_live_news_protocol(team_name=team_name, limit=limit)
        if res.get("ok"):
            return res.get("data", {}).get("articles", [])
        return []

    @staticmethod
    def get_live_injuries(team_name: str) -> List[Dict]:
        """获取球队实时伤停情报"""
        res = AnalyzerAPI.get_live_injuries_protocol(team_name=team_name)
        if res.get("ok"):
            return res.get("data", {}).get("injuries", [])
        return []

    @staticmethod
    def get_live_fixtures() -> List[Dict]:
        """获取今日赛事列表"""
        res = AnalyzerAPI.get_live_fixtures_protocol()
        if res.get("ok"):
            return res.get("data", {}).get("fixtures", [])
        return []

    @staticmethod
    def get_live_fixtures_protocol() -> Dict[str, Any]:
        try:
            url = f"{ANALYZER_API_URL}/api/v1/live/fixtures"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return {
                "ok": True,
                "data": response.json(),
                "error": None,
                "meta": {"mock": False, "source": "analyzer_api_http", "confidence": 0.7, "stale": False},
            }
        except Exception:
            fetcher = AnalyzerAPI._get_fetcher()
            return fetcher.fetch_fixtures_sync()

    @staticmethod
    def get_live_odds(home_team: str, away_team: str) -> Dict:
        """获取实时盘口与水位变动数据"""
        res = AnalyzerAPI.get_live_odds_protocol(home_team=home_team, away_team=away_team)
        if res.get("ok"):
            return res.get("data") or {}
        return {}

    @staticmethod
    def get_live_odds_protocol(home_team: str, away_team: str) -> Dict[str, Any]:
        try:
            url = f"{ANALYZER_API_URL}/api/v1/live/odds"
            response = requests.get(url, params={"home": home_team, "away": away_team}, timeout=5)
            response.raise_for_status()
            return {
                "ok": True,
                "data": response.json(),
                "error": None,
                "meta": {"mock": False, "source": "analyzer_api_http", "confidence": 0.7, "stale": False},
            }
        except Exception:
            fetcher = AnalyzerAPI._get_fetcher()
            return fetcher.fetch_odds_sync(home_team=home_team, away_team=away_team)

    @staticmethod
    def get_live_injuries_protocol(team_name: str) -> Dict[str, Any]:
        try:
            url = f"{ANALYZER_API_URL}/api/v1/live/injuries"
            response = requests.get(url, params={"team": team_name}, timeout=5)
            response.raise_for_status()
            return {
                "ok": True,
                "data": response.json().get("injuries", []),
                "error": None,
                "meta": {"mock": False, "source": "analyzer_api_http", "confidence": 0.7, "stale": False},
            }
        except Exception:
            fetcher = AnalyzerAPI._get_fetcher()
            return fetcher.fetch_injuries_sync(team_name=team_name)

    @staticmethod
    def get_live_news_protocol(team_name: str, limit: int = 5) -> Dict[str, Any]:
        try:
            url = f"{ANALYZER_API_URL}/api/v1/live/news"
            response = requests.get(url, params={"team": team_name, "limit": limit}, timeout=5)
            response.raise_for_status()
            return {
                "ok": True,
                "data": response.json().get("articles", []),
                "error": None,
                "meta": {"mock": False, "source": "analyzer_api_http", "confidence": 0.7, "stale": False},
            }
        except Exception:
            fetcher = AnalyzerAPI._get_fetcher()
            return fetcher.fetch_news_sync(team_name=team_name, limit=limit)

# 测试代码
if __name__ == "__main__":
    # 需要先启动 analyzer 的 api_server.py
    try:
        print(AnalyzerAPI.calculate_ev(2.5, 0.45))
    except Exception as e:
        print("API 未启动或调用失败:", e)
