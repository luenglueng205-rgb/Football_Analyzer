import asyncio
import json
import requests
from tools.entity_resolver import EntityResolver
from tools.snapshot_store import SnapshotStore
from tools.agent_browser import AgentBrowser
from tools.api_clients import ForeignAPIClient
from tools.web_intel_extractor import WebIntelExtractor


class MultiSourceFetcher:
    def __init__(self, store: SnapshotStore | None = None, resolver: EntityResolver | None = None):
        self.store = store or SnapshotStore()
        self.resolver = resolver or EntityResolver()
        self.browser = AgentBrowser()
        self.foreign_api = ForeignAPIClient()
        self.web_intel = WebIntelExtractor(browser=self.browser)

    def fetch_odds_sync(self, home_team: str, away_team: str) -> dict:
        return self._fetch_odds_impl(home_team=home_team, away_team=away_team)

    async def fetch_odds(self, home_team: str, away_team: str) -> dict:
        return self._fetch_odds_impl(home_team=home_team, away_team=away_team)

    def _fetch_odds_impl(self, home_team: str, away_team: str) -> dict:
        home = self.resolver.resolve_team(home_team)
        away = self.resolver.resolve_team(away_team)
        if not home["ok"] or not away["ok"]:
            return {
                "ok": False,
                "data": None,
                "error": {"code": "BAD_INPUT", "message": "team resolve failed"},
                "meta": {"mock": False, "source": "multisource", "confidence": 0.0, "stale": True},
            }

        match_id = f"ODDS::{home['data']['team_id']}::{away['data']['team_id']}"
        self.store.upsert_match(match_id, "Unknown", home_team, away_team, "Unknown", "agent_browser")
        
        latest = self.store.get_latest_snapshot("odds", match_id)
        if latest["ok"]:
            return {
                "ok": True,
                "data": latest["data"]["payload"],
                "error": None,
                "meta": {
                    "mock": False,
                    "source": "snapshot",
                    "confidence": float(latest["data"]["meta"]["confidence"]),
                    "stale": True,
                },
            }

        intel = self.web_intel.extract_odds(home_team=home_team, away_team=away_team)
        if intel.get("ok"):
            meta = intel.get("meta") or {}
            self.store.insert_snapshot("odds", match_id, str(meta.get("source") or "web_intel"), intel.get("data") or {}, float(meta.get("confidence") or 0.0), False)
            return intel

        # Priority 1: Foreign APIs (The Odds API)
        foreign_odds = self.foreign_api.get_odds(home_team, away_team)
        if foreign_odds.get("ok"):
            self.store.insert_snapshot("odds", match_id, "foreign_api", foreign_odds["data"], 0.9, False)
            return foreign_odds

        # Priority 2: Fallback to AgentBrowser if no snapshot found
        browser_results = self.browser.scrape_okooo_odds_search(home_team, away_team)
        if browser_results:
            # We save this unstructured data as a snapshot
            payload = {"raw_analysis": browser_results, "home_team": home_team, "away_team": away_team}
            self.store.insert_snapshot("odds", match_id, "agent_browser", payload, 0.6, False)
            return {
                "ok": True,
                "data": payload,
                "error": None,
                "meta": {"mock": False, "source": "agent_browser", "confidence": 0.6, "stale": False},
            }

        return {
            "ok": False,
            "data": None,
            "error": {"code": "NOT_FOUND", "message": "no odds snapshot and browser fallback failed"},
            "meta": {"mock": False, "source": "multisource", "confidence": 0.0, "stale": True},
        }

    def fetch_fixtures_sync(self, date: str | None = None) -> dict:
        if date:
            latest = self.store.get_latest_snapshot(category="fixtures", match_id=f"FIXTURES::{date}")
            if latest.get("ok"):
                payload = latest.get("data", {}).get("payload") or {}
                if isinstance(payload, dict) and isinstance(payload.get("fixtures"), list) and payload.get("fixtures"):
                    meta = latest.get("data", {}).get("meta") or {}
                    return {
                        "ok": True,
                        "data": {"fixtures": payload.get("fixtures")},
                        "error": None,
                        "meta": {
                            "mock": False,
                            "source": str(meta.get("source") or "snapshot"),
                            "confidence": float(meta.get("confidence") or 0.0),
                            "stale": True,
                        },
                    }

        fixtures = self.browser.scrape_500_fixtures(date=date)
        if fixtures:
            return {
                "ok": True,
                "data": {"fixtures": fixtures},
                "error": None,
                "meta": {"mock": False, "source": "500.com", "confidence": 0.9, "stale": False},
            }

        if date:
            intel_fx = self.web_intel.extract_fixtures(date=date)
            if intel_fx:
                return {
                    "ok": True,
                    "data": {"fixtures": intel_fx},
                    "error": None,
                    "meta": {"mock": False, "source": "web_intel", "confidence": 0.25, "stale": False},
                }
        return {
            "ok": False,
            "data": None,
            "error": {"code": "NOT_FOUND", "message": "failed to fetch fixtures from 500.com"},
            "meta": {"mock": False, "source": "multisource", "confidence": 0.0, "stale": True},
        }

    def fetch_injuries_sync(self, team_name: str) -> dict:
        """Fetch injuries using Dongqiudi search via AgentBrowser"""
        news = self.browser.search_dongqiudi_news(team_name)
        if news:
            return {
                "ok": True,
                "data": {"injuries": news},
                "error": None,
                "meta": {"mock": False, "source": "dongqiudi", "confidence": 0.8, "stale": False},
            }
        return {
            "ok": False,
            "data": None,
            "error": {"code": "NOT_FOUND", "message": "failed to fetch injuries/news from dongqiudi"},
            "meta": {"mock": False, "source": "multisource", "confidence": 0.0, "stale": True},
        }

    def fetch_news_sync(self, team_name: str, limit: int = 5) -> dict:
        news = self.browser.search_dongqiudi_news(team_name)
        if news:
            return {
                "ok": True,
                "data": {"articles": news},
                "error": None,
                "meta": {"mock": False, "source": "dongqiudi", "confidence": 0.8, "stale": False},
            }
        return {
            "ok": False,
            "data": None,
            "error": {"code": "NOT_FOUND", "message": "failed to fetch news from dongqiudi"},
            "meta": {"mock": False, "source": "multisource", "confidence": 0.0, "stale": True},
        }

    def fetch_weather_sync(self, city: str, api_key: str) -> dict:
        """Fetch real weather data using OpenWeatherMap API"""
        # 如果没有传入 city，设置一个默认的足球城市用于测试，实际应由外部传入比赛所在城市
        if not city:
            city = "London"
            
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                # 转换 OpenWeatherMap condition 匹配 EnvironmentAnalyzer 的认知
                raw_condition = data["weather"][0]["main"].lower()
                condition_map = {
                    "rain": "heavy_rain",
                    "drizzle": "heavy_rain",
                    "thunderstorm": "heavy_rain",
                    "snow": "snow",
                    "clear": "clear",
                    "clouds": "clear", # 多云对比赛影响不大，视为 clear
                    "extreme": "extreme_heat" # 简化处理
                }
                mapped_condition = condition_map.get(raw_condition, "clear")
                
                return {
                    "ok": True,
                    "data": {
                        "temperature": data["main"]["temp"],
                        "condition": mapped_condition,
                        "wind": "strong" if data["wind"]["speed"] > 8 else "light",
                    },
                    "error": None,
                    "meta": {"mock": False, "source": "openweathermap", "confidence": 1.0, "stale": False}
                }
            return {
                "ok": False,
                "data": None,
                "error": {"code": "API_ERROR", "message": f"Status: {response.status_code}"},
                "meta": {"mock": False, "source": "multisource", "confidence": 0.0, "stale": True}
            }
        except Exception as e:
            return {
                "ok": False,
                "data": None,
                "error": {"code": "REQUEST_FAILED", "message": str(e)},
                "meta": {"mock": False, "source": "multisource", "confidence": 0.0, "stale": True}
            }
