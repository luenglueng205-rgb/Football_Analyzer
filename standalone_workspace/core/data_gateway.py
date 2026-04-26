# -*- coding: utf-8 -*-
"""
Phase 0.2: DataGateway — 统一数据网关
=====================================

强中心 LLM 的"感官器官"。
聚合所有数据源（API-Football / The Odds API / 500.com 爬虫 / Football-Data.org / TheSportsDB），
统一返回 NormalizedMatch / NormalizedOdds 等标准契约格式。

设计原则：
1. 聚合层 — 不做任何分析/推理，只做数据获取和格式化
2. 降级链 — API-Football → Football-Data.org → 500.com 爬虫 → 浏览器
3. 缓存优先 — Redis 缓存命中则直接返回
4. 质量检查 — 返回数据附带 DataQualityValidator 评分

用法：
    gw = DataGateway()
    fixtures = await gw.get_today_fixtures()
    odds = await gw.get_match_odds(match_id)
    stats = await gw.get_team_stats(team_id, league_id, season)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from dataclasses import asdict
from datetime import datetime, date, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DataGateway:
    """
    统一数据网关。
    提供所有数据获取能力，供中心 LLM 和边缘 Agent 使用。
    """

    def __init__(self, *, online: bool = False):
        self.online = online
        self._init_clients()

    def _init_clients(self):
        """延迟初始化所有客户端"""
        try:
            from tools.api_clients import ForeignAPIClient
            self.foreign_api = ForeignAPIClient()
        except Exception as e:
            logger.warning(f"[DataGateway] ForeignAPIClient 初始化失败: {e}")
            self.foreign_api = None

        try:
            from tools.multisource_fetcher import MultiSourceFetcher
            self.multisource = MultiSourceFetcher(online=self.online)
        except Exception as e:
            logger.warning(f"[DataGateway] MultiSourceFetcher 初始化失败: {e}")
            self.multisource = None

        try:
            from core.redis_cache import RedisCache
            self.cache = RedisCache.get_instance()
        except Exception:
            self.cache = None

        try:
            from core.data_quality_validator import DataQualityValidator
            self.quality = DataQualityValidator()
        except Exception:
            self.quality = None

    # ═══════════════════════════════════════════════════════════════════════════════
    # 赛程 (Fixtures)
    # ═══════════════════════════════════════════════════════════════════════════════

    def get_today_fixtures_sync(self, target_date: Optional[str] = None) -> Dict[str, Any]:
        """同步获取今日赛事"""
        target_date = target_date or date.today().isoformat()
        cache_key = f"fixtures:{target_date}"

        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        result = self._fetch_fixtures(target_date)
        self._cache_set(cache_key, result, ttl=3600)  # 缓存 1 小时
        return result

    async def get_today_fixtures(self, target_date: Optional[str] = None) -> Dict[str, Any]:
        """异步获取今日赛事"""
        target_date = target_date or date.today().isoformat()
        cache_key = f"fixtures:{target_date}"

        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        result = self._fetch_fixtures(target_date)
        self._cache_set(cache_key, result, ttl=3600)
        return result

    def _fetch_fixtures(self, target_date: str) -> Dict[str, Any]:
        """
        降级链获取赛程：
        1. API-Football（最全）
        2. MultiSourceFetcher（500.com 爬虫）
        3. Football-Data.org（欧洲备用）
        """
        # 1. API-Football
        if self.foreign_api:
            af_result = self.foreign_api.get_fixtures(date=target_date)
            if af_result.get("ok"):
                return self._format_api_football_fixtures(af_result)

        # 2. MultiSourceFetcher (500.com)
        if self.multisource:
            try:
                normalized = self.multisource.get_fixtures_normalized(target_date)
                if normalized:
                    return self._ok({
                        "date": target_date,
                        "fixtures": normalized,
                        "count": len(normalized),
                    }, "500.com")
            except Exception as e:
                logger.warning(f"[DataGateway] MultiSourceFetcher 失败: {e}")

        # 3. Football-Data.org
        if self.foreign_api and hasattr(self.foreign_api, "football_data"):
            fd_result = self.foreign_api.football_data.get_matches(date_from=target_date, date_to=target_date)
            if fd_result.get("ok"):
                return self._format_football_data_matches(fd_result)

        return self._err("NO_DATA", f"No fixtures found for {target_date}")

    def _format_api_football_fixtures(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """将 API-Football 返回转换为统一格式"""
        response = (result.get("data") or {}).get("response") or []
        fixtures = []
        for item in response:
            fixture = item.get("fixture") or {}
            teams = item.get("teams") or {}
            league = item.get("league") or {}
            goals = item.get("goals") or {}

            fx = {
                "match_id": str(fixture.get("id", "")),
                "league": league.get("name", "Unknown"),
                "league_id": league.get("id"),
                "league_country": league.get("country", ""),
                "home_team": teams.get("home", {}).get("name", ""),
                "home_team_id": str(teams.get("home", {}).get("id", "")),
                "away_team": teams.get("away", {}).get("name", ""),
                "away_team_id": str(teams.get("away", {}).get("id", "")),
                "home_logo": teams.get("home", {}).get("logo", ""),
                "away_logo": teams.get("away", {}).get("logo", ""),
                "kickoff_time": fixture.get("date", ""),
                "status": self._map_fixture_status(fixture.get("status", {}).get("short", "")),
                "home_score": goals.get("home"),
                "away_score": goals.get("away"),
                "source": "api_football",
                "confidence": 0.95,
            }
            fixtures.append(fx)

        return self._ok({
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "fixtures": fixtures,
            "count": len(fixtures),
        }, "api_football")

    def _format_football_data_matches(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """将 Football-Data.org 返回转换为统一格式"""
        matches = (result.get("data") or {}).get("matches") or []
        fixtures = []
        for m in matches:
            home = m.get("homeTeam") or {}
            away = m.get("awayTeam") or {}
            score = m.get("score") or {}
            fx = {
                "match_id": str(m.get("id", "")),
                "league": (m.get("competition") or {}).get("name", "Unknown"),
                "league_id": (m.get("competition") or {}).get("id"),
                "home_team": home.get("shortName") or home.get("name", ""),
                "home_team_id": str(home.get("id", "")),
                "away_team": away.get("shortName") or away.get("name", ""),
                "away_team_id": str(away.get("id", "")),
                "kickoff_time": m.get("utcDate", ""),
                "status": self._map_fd_status(m.get("status", "")),
                "home_score": (score.get("fullTime") or {}).get("home"),
                "away_score": (score.get("fullTime") or {}).get("away"),
                "source": "football_data_org",
                "confidence": 0.8,
            }
            fixtures.append(fx)

        return self._ok({
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "fixtures": fixtures,
            "count": len(fixtures),
        }, "football_data_org")

    # ═══════════════════════════════════════════════════════════════════════════════
    # 赔率 (Odds)
    # ═══════════════════════════════════════════════════════════════════════════════

    def get_match_odds_sync(self, match_id: str, league_name: str = "",
                             home_team: str = "", away_team: str = "",
                             kickoff_time: str = "") -> Dict[str, Any]:
        """同步获取单场赔率"""
        cache_key = f"odds:{match_id}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        result = self._fetch_odds(match_id, league_name, home_team, away_team, kickoff_time)
        self._cache_set(cache_key, result, ttl=600)  # 缓存 10 分钟
        return result

    async def get_match_odds(self, match_id: str, **kwargs) -> Dict[str, Any]:
        """异步获取单场赔率"""
        return self.get_match_odds_sync(match_id, **kwargs)

    def _fetch_odds(self, match_id: str, league_name: str,
                     home_team: str, away_team: str, kickoff_time: str) -> Dict[str, Any]:
        """
        降级链获取赔率：
        1. MultiSourceFetcher（竞彩/北单 SP + 500.com 欧赔）
        2. API-Football（外围赔率）
        3. The Odds API（多博彩公司对比）
        """
        results = []

        # 1. MultiSourceFetcher（国内数据）
        if self.multisource and home_team and away_team:
            try:
                ms_result = self.multisource.get_odds_normalized(
                    league_name=league_name,
                    home_team=home_team,
                    away_team=away_team,
                    kickoff_time=kickoff_time,
                )
                if ms_result.get("ok"):
                    results.append(ms_result)
            except Exception as e:
                logger.warning(f"[DataGateway] MultiSourceFetcher odds 失败: {e}")

        # 2. API-Football
        if self.foreign_api and match_id.isdigit():
            try:
                af_result = self.foreign_api.get_odds(fixture_id=int(match_id))
                if af_result.get("ok"):
                    results.append(self._format_api_football_odds(af_result))
            except Exception as e:
                logger.warning(f"[DataGateway] API-Football odds 失败: {e}")

        # 3. The Odds API
        if self.foreign_api and hasattr(self.foreign_api, "the_odds_api"):
            try:
                to_result = self.foreign_api.the_odds_api.get_odds()
                if to_result.get("ok"):
                    results.append(self._format_the_odds_api(to_result, home_team, away_team))
            except Exception as e:
                logger.warning(f"[DataGateway] The Odds API 失败: {e}")

        if results:
            # 合并所有来源的赔率
            merged = self._merge_odds(results)
            return self._ok(merged, "gateway_merged")

        return self._err("ODDS_UNAVAILABLE", f"No odds found for {match_id}")

    def _format_api_football_odds(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """格式化 API-Football 赔率"""
        response = (result.get("data") or {}).get("response") or []
        bookmakers = []
        for item in response[:3]:  # 取前 3 家博彩公司
            bm = item.get("bookmakers") or []
            for b in bm:
                values = {}
                for m in (b.get("bets") or []):
                    values[m.get("name", "")] = m.get("values") or []
                bookmakers.append({
                    "name": b.get("name", ""),
                    "values": values,
                })
        return {"source": "api_football", "bookmakers": bookmakers}

    def _format_the_odds_api(self, result: Dict[str, Any], home_team: str, away_team: str) -> Dict[str, Any]:
        """格式化 The Odds API 赔率"""
        matches = result.get("data") or []
        odds_list = []
        for m in matches:
            m_home = m.get("home_team", "")
            m_away = m.get("away_team", "")
            # 如果没指定球队，返回所有比赛的赔率
            if home_team and away_team:
                if home_team.lower() not in m_home.lower() and away_team.lower() not in m_away.lower():
                    continue
            bookmakers = []
            for bm in (m.get("bookmakers") or []):
                bm_name = bm.get("key") or bm.get("title", "")
                odds_values = {}
                for market in (bm.get("markets") or []):
                    market_key = market.get("key", "")
                    outcomes = {}
                    for o in (market.get("outcomes") or []):
                        outcomes[o.get("name", "")] = o.get("price")
                    odds_values[market_key] = outcomes
                bookmakers.append({"name": bm_name, "values": odds_values})
            odds_list.append({
                "home_team": m_home,
                "away_team": m_away,
                "commence_time": m.get("commence_time", ""),
                "bookmakers": bookmakers,
            })
        return {"source": "the_odds_api", "odds": odds_list}

    def _merge_odds(self, results: List[Dict]) -> Dict[str, Any]:
        """合并多来源赔率"""
        merged = {
            "domestic": None,  # 国内竞彩/北单 SP
            "foreign": [],     # 外围赔率列表
            "bookmakers": {},  # 博彩公司汇总
        }
        for r in results:
            source = r.get("source", "")
            if source in ("500.com", "multisource", "snapshot"):
                merged["domestic"] = r
            elif source in ("api_football", "the_odds_api", "odds_api_io"):
                if isinstance(r.get("odds"), list):
                    merged["foreign"].extend(r["odds"])
                if isinstance(r.get("bookmakers"), list):
                    for bm in r["bookmakers"]:
                        name = bm.get("name", "")
                        if name:
                            merged["bookmakers"][name] = bm.get("values", {})
        merged["source_count"] = len(results)
        return merged

    # ═══════════════════════════════════════════════════════════════════════════════
    # 球队统计 (Team Statistics)
    # ═══════════════════════════════════════════════════════════════════════════════

    def get_team_stats_sync(self, team_id: int, league_id: int, season: int) -> Dict[str, Any]:
        """获取球队赛季统计"""
        cache_key = f"team_stats:{team_id}:{league_id}:{season}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        result = self._fetch_team_stats(team_id, league_id, season)
        self._cache_set(cache_key, result, ttl=21600)  # 6 小时
        return result

    async def get_team_stats(self, team_id: int, league_id: int, season: int) -> Dict[str, Any]:
        return self.get_team_stats_sync(team_id, league_id, season)

    def _fetch_team_stats(self, team_id: int, league_id: int, season: int) -> Dict[str, Any]:
        if not self.foreign_api:
            return self._err("NO_CLIENT", "API clients not initialized")
        return self.foreign_api.get_team_stats(team_id, league_id, season)

    # ═══════════════════════════════════════════════════════════════════════════════
    # 历史交锋 (H2H)
    # ═══════════════════════════════════════════════════════════════════════════════

    def get_h2h_sync(self, team1_id: int, team2_id: int, last: int = 10) -> Dict[str, Any]:
        """获取历史交锋"""
        cache_key = f"h2h:{team1_id}:{team2_id}:{last}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        result = self._fetch_h2h(team1_id, team2_id, last)
        self._cache_set(cache_key, result, ttl=43200)  # 12 小时
        return result

    async def get_h2h(self, team1_id: int, team2_id: int, last: int = 10) -> Dict[str, Any]:
        return self.get_h2h_sync(team1_id, team2_id, last)

    def _fetch_h2h(self, team1_id: int, team2_id: int, last: int) -> Dict[str, Any]:
        if not self.foreign_api:
            return self._err("NO_CLIENT", "API clients not initialized")
        return self.foreign_api.get_h2h(team1_id, team2_id, last)

    # ═══════════════════════════════════════════════════════════════════════════════
    # 伤停 (Injuries)
    # ═══════════════════════════════════════════════════════════════════════════════

    def get_injuries_sync(self, fixture_id: Optional[int] = None,
                          team_name: Optional[str] = None) -> Dict[str, Any]:
        """获取伤停信息"""
        cache_key = f"injuries:{fixture_id or ''}:{team_name or ''}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        result = self._fetch_injuries(fixture_id, team_name)
        self._cache_set(cache_key, result, ttl=1800)  # 30 分钟
        return result

    async def get_injuries(self, fixture_id: Optional[int] = None,
                           team_name: Optional[str] = None) -> Dict[str, Any]:
        return self.get_injuries_sync(fixture_id, team_name)

    def _fetch_injuries(self, fixture_id: Optional[int], team_name: Optional[str]) -> Dict[str, Any]:
        # 1. API-Football (fixture ID)
        if self.foreign_api and fixture_id:
            result = self.foreign_api.get_injuries(fixture_id=fixture_id)
            if result.get("ok"):
                return result

        # 2. MultiSourceFetcher (球队名，爬懂球帝)
        if self.multisource and team_name:
            try:
                result = self.multisource.fetch_injuries_sync(team_name)
                if result.get("ok"):
                    return result
            except Exception as e:
                logger.warning(f"[DataGateway] injuries fetch failed: {e}")

        return self._err("INJURIES_UNAVAILABLE", f"No injury data for fixture={fixture_id} team={team_name}")

    # ═══════════════════════════════════════════════════════════════════════════════
    # 积分榜 (Standings)
    # ═══════════════════════════════════════════════════════════════════════════════

    def get_standings_sync(self, league_id: int, season: int) -> Dict[str, Any]:
        """获取积分榜"""
        cache_key = f"standings:{league_id}:{season}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        result = self._fetch_standings(league_id, season)
        self._cache_set(cache_key, result, ttl=43200)  # 12 小时
        return result

    async def get_standings(self, league_id: int, season: int) -> Dict[str, Any]:
        return self.get_standings_sync(league_id, season)

    def _fetch_standings(self, league_id: int, season: int) -> Dict[str, Any]:
        if not self.foreign_api:
            return self._err("NO_CLIENT", "API clients not initialized")
        return self.foreign_api.get_standings(league_id, season)

    # ═══════════════════════════════════════════════════════════════════════════════
    # 预测 (Predictions) — API-Football 自带的预测
    # ═══════════════════════════════════════════════════════════════════════════════

    def get_prediction_sync(self, fixture_id: int) -> Dict[str, Any]:
        """获取 API-Football 的预测（参考用，不代表系统决策）"""
        if not self.foreign_api:
            return self._err("NO_CLIENT", "API clients not initialized")
        return self.foreign_api.get_prediction(fixture_id)

    async def get_prediction(self, fixture_id: int) -> Dict[str, Any]:
        return self.get_prediction_sync(fixture_id)

    # ═══════════════════════════════════════════════════════════════════════════════
    # 赛果 (Results)
    # ═══════════════════════════════════════════════════════════════════════════════

    def get_results_sync(self, target_date: str) -> Dict[str, Any]:
        """同步获取赛果"""
        cache_key = f"results:{target_date}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        result = self._fetch_results(target_date)
        self._cache_set(cache_key, result, ttl=86400)  # 24 小时
        return result

    async def get_results(self, target_date: str) -> Dict[str, Any]:
        return self.get_results_sync(target_date)

    def _fetch_results(self, target_date: str) -> Dict[str, Any]:
        # 1. MultiSourceFetcher (500.com)
        if self.multisource:
            try:
                normalized = self.multisource.get_results_normalized(target_date)
                if normalized:
                    return self._ok({
                        "date": target_date,
                        "results": normalized,
                        "count": len(normalized),
                    }, "500.com")
            except Exception as e:
                logger.warning(f"[DataGateway] results fetch failed: {e}")

        # 2. API-Football
        if self.foreign_api:
            result = self.foreign_api.get_fixtures(date=target_date)
            if result.get("ok"):
                response = (result.get("data") or {}).get("response") or []
                results = []
                for item in response:
                    fixture = item.get("fixture") or {}
                    goals = item.get("goals") or {}
                    teams = item.get("teams") or {}
                    league = item.get("league") or {}
                    status_short = (fixture.get("status") or {}).get("short", "")
                    if status_short not in ("FT", "AET", "PEN"):
                        continue
                    results.append({
                        "match_id": str(fixture.get("id", "")),
                        "league": league.get("name", ""),
                        "home_team": teams.get("home", {}).get("name", ""),
                        "away_team": teams.get("away", {}).get("name", ""),
                        "home_score": goals.get("home"),
                        "away_score": goals.get("away"),
                        "status": "FINISHED",
                        "source": "api_football",
                    })
                if results:
                    return self._ok({
                        "date": target_date,
                        "results": results,
                        "count": len(results),
                    }, "api_football")

        return self._err("NO_RESULTS", f"No results for {target_date}")

    # ═══════════════════════════════════════════════════════════════════════════════
    # 新闻/情报 (News/Intel)
    # ═══════════════════════════════════════════════════════════════════════════════

    def get_news_sync(self, team_name: str, limit: int = 5) -> Dict[str, Any]:
        """获取球队新闻"""
        if self.multisource:
            return self.multisource.fetch_news_sync(team_name, limit)
        return self._err("NO_CLIENT", "MultiSourceFetcher not initialized")

    async def get_news(self, team_name: str, limit: int = 5) -> Dict[str, Any]:
        return self.get_news_sync(team_name, limit)

    # ═══════════════════════════════════════════════════════════════════════════════
    # 天气 (Weather)
    # ═══════════════════════════════════════════════════════════════════════════════

    def get_weather_sync(self, city: str, api_key: Optional[str] = None) -> Dict[str, Any]:
        """获取比赛城市天气"""
        if self.multisource:
            key = api_key or ""
            return self.multisource.fetch_weather_sync(city, key)
        return self._err("NO_CLIENT", "MultiSourceFetcher not initialized")

    async def get_weather(self, city: str, api_key: Optional[str] = None) -> Dict[str, Any]:
        return self.get_weather_sync(city, api_key)

    # ═══════════════════════════════════════════════════════════════════════════════
    # 内部工具方法
    # ═══════════════════════════════════════════════════════════════════════════════

    @staticmethod
    def _ok(data: Any, source: str, confidence: float = 0.9) -> Dict[str, Any]:
        return {
            "ok": True,
            "data": data,
            "error": None,
            "meta": {
                "source": source,
                "confidence": confidence,
                "mock": False,
                "stale": False,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            },
        }

    @staticmethod
    def _err(code: str, message: str, confidence: float = 0.0) -> Dict[str, Any]:
        return {
            "ok": False,
            "data": None,
            "error": {"code": code, "message": message},
            "meta": {
                "source": "data_gateway",
                "confidence": confidence,
                "mock": False,
                "stale": True,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            },
        }

    def _cache_get(self, key: str) -> Optional[Dict[str, Any]]:
        if not self.cache:
            return None
        try:
            val = self.cache.get(key)
            return json.loads(val) if isinstance(val, (str, bytes)) else val
        except Exception:
            return None

    def _cache_set(self, key: str, value: Any, ttl: int = 3600) -> None:
        if not self.cache:
            return
        try:
            self.cache.set(key, json.dumps(value, ensure_ascii=False), ttl=ttl)
        except Exception as e:
            logger.warning(f"[DataGateway] cache set failed: {e}")

    @staticmethod
    def _map_fixture_status(status_short: str) -> str:
        """API-Football status short → NormalizedMatch status"""
        mapping = {
            "TBD": "SCHEDULED", "NS": "SCHEDULED", "1H": "LIVE", "2H": "LIVE",
            "HT": "LIVE", "ET": "LIVE", "BT": "LIVE", "P": "LIVE",
            "SUSP": "LIVE", "INT": "LIVE", "LIVE": "LIVE",
            "FT": "FINISHED", "AET": "FINISHED", "PEN": "FINISHED",
            "PST": "POSTPONED", "CANC": "CANCELLED", "ABD": "ABANDONED",
            "AWD": "FINISHED", "WO": "FINISHED",
        }
        return mapping.get(status_short, "SCHEDULED")

    @staticmethod
    def _map_fd_status(status: str) -> str:
        """Football-Data.org status → NormalizedMatch status"""
        mapping = {
            "SCHEDULED": "SCHEDULED", "TIMED": "SCHEDULED",
            "IN_PLAY": "LIVE", "PAUSED": "LIVE", "HALFTIME": "LIVE",
            "FINISHED": "FINISHED", "AWARDED": "FINISHED",
            "POSTPONED": "POSTPONED", "SUSPENDED": "CANCELLED",
            "CANCELLED": "CANCELLED", "ABANDONED": "ABANDONED",
        }
        return mapping.get(status, "SCHEDULED")

    # ═══════════════════════════════════════════════════════════════════════════════
    # 健康检查
    # ═══════════════════════════════════════════════════════════════════════════════

    def health_check(self) -> Dict[str, Any]:
        """检查所有数据源的可用性"""
        status = {}
        today = date.today().isoformat()

        # API-Football
        if self.foreign_api:
            try:
                r = self.foreign_api.api_football.get_fixtures(date=today)
                status["api_football"] = {"ok": r.get("ok"), "error": r.get("error")}
            except Exception as e:
                status["api_football"] = {"ok": False, "error": str(e)}
        else:
            status["api_football"] = {"ok": False, "error": "not initialized"}

        # The Odds API
        if self.foreign_api:
            try:
                r = self.foreign_api.the_odds_api.get_sports()
                status["the_odds_api"] = {"ok": r.get("ok"), "error": r.get("error")}
            except Exception as e:
                status["the_odds_api"] = {"ok": False, "error": str(e)}

        # Redis
        if self.cache:
            try:
                self.cache.set("_health_check", "1", ttl=10)
                status["redis"] = {"ok": True}
            except Exception as e:
                status["redis"] = {"ok": False, "error": str(e)}
        else:
            status["redis"] = {"ok": False, "error": "not initialized"}

        return status
