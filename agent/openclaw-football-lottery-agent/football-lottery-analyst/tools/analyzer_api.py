import os
import requests
from typing import Dict, Any, List, Optional

ANALYZER_API_URL = os.getenv("ANALYZER_API_URL", "http://localhost:8000")

class AnalyzerAPI:
    """
    对接底层 Analyzer (System 2) 的工具类
    """

    _last_health_ok: Optional[bool] = None

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
        except Exception:
            return None

    @staticmethod
    def _post(url: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            response = requests.post(url, json=payload, timeout=3)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None
    
    @staticmethod
    def get_team_stats(team_name: str, league: str = None) -> Dict[str, Any]:
        """获取球队历史统计数据"""
        if not team_name:
            return {}
        if not AnalyzerAPI.is_available():
            return {}
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
        try:
            url = f"{ANALYZER_API_URL}/api/v1/live/news"
            response = requests.get(url, params={"team": team_name, "limit": limit}, timeout=5)
            response.raise_for_status()
            return response.json().get("articles", [])
        except Exception as e:
            print(f"Warning: Live news fetch failed: {e}")
            return []

    @staticmethod
    def get_live_injuries(team_name: str) -> List[Dict]:
        """获取球队实时伤停情报"""
        try:
            url = f"{ANALYZER_API_URL}/api/v1/live/injuries"
            response = requests.get(url, params={"team": team_name}, timeout=5)
            response.raise_for_status()
            return response.json().get("injuries", [])
        except Exception as e:
            print(f"Warning: Live injuries fetch failed: {e}")
            return []

    @staticmethod
    def get_live_odds(home_team: str, away_team: str) -> Dict:
        """获取实时盘口与水位变动数据"""
        try:
            url = f"{ANALYZER_API_URL}/api/v1/live/odds"
            response = requests.get(url, params={"home": home_team, "away": away_team}, timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Warning: Live odds fetch failed: {e}")
            return {}

# 测试代码
if __name__ == "__main__":
    # 需要先启动 analyzer 的 api_server.py
    try:
        print(AnalyzerAPI.calculate_ev(2.5, 0.45))
    except Exception as e:
        print("API 未启动或调用失败:", e)
