# -*- coding: utf-8 -*-
"""
Phase 0.1: Foreign API Clients — 统一外部数据源接入
====================================================

接入 5 个外部 API：
1. API-Football (api-football.com)  — 主力，覆盖最全
2. The Odds API (the-odds-api.com)  — 外围赔率对比
3. Football-Data.org                — 备用欧洲数据
4. TheSportsDB (thesportsdb.com)   — 队伍/联赛信息
5. Odds-API.io                      — 额外赔率源

所有 API 从 .env 读取 key，统一异常处理，统一返回 ProviderResponse 格式。
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ── API Key 从环境变量读取 ──────────────────────────────────────────────────

_API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_API_KEY", "")
_THE_ODDS_API_KEY = os.getenv("THE_ODDS_API_KEY", "")
_FOOTBALL_DATA_KEY = os.getenv("FOOTBALL_DATA_API_KEY", "")
_THESPORTSDB_KEY = os.getenv("THESPORTSDB_API_KEY", "3")
_ODDS_API_IO_KEY = os.getenv("ODDS_API_IO_KEY", "")

# ── 通用响应格式（与 DataProvider Protocol 一致）───────────────────────────


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


def _err(code: str, message: str, source: str, confidence: float = 0.0) -> Dict[str, Any]:
    return {
        "ok": False,
        "data": None,
        "error": {"code": code, "message": message},
        "meta": {
            "source": source,
            "confidence": confidence,
            "mock": False,
            "stale": True,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        },
    }


def _rate_limit_err(source: str, reset_ts: Optional[float] = None) -> Dict[str, Any]:
    meta_extra: Dict[str, Any] = {}
    if reset_ts:
        meta_extra["rate_limit_reset"] = datetime.fromtimestamp(reset_ts, tz=timezone.utc).isoformat()
    return {
        "ok": False,
        "data": None,
        "error": {"code": "RATE_LIMITED", "message": "API rate limit reached"},
        "meta": {
            "source": source,
            "confidence": 0.0,
            "mock": False,
            "stale": True,
            **meta_extra,
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 1. API-Football (api-football.com) — 主力数据源
# ═══════════════════════════════════════════════════════════════════════════════
# 免费层：100 requests/day（UTC 0:00 重置）
# 付费层：无限制
# 文档：https://www.api-football.com/documentation-v3
# 覆盖：赛程、赔率、伤停、阵容、历史交锋、球队统计、联赛排名

class APIFootballClient:
    """
    API-Football v3 客户端。
    主力数据源，覆盖赛程、赔率、伤停、阵容、历史、统计。
    """

    BASE_URL = "https://v3.football.api-sports.com"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or _API_FOOTBALL_KEY
        self._session = requests.Session()
        self._session.headers.update({"x-apisports-key": self.api_key})
        # 处理某些网络环境下的 SSL 问题
        self._session.verify = False
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """统一的 GET 请求封装"""
        url = f"{self.BASE_URL}/{endpoint}"
        try:
            resp = self._session.get(url, params=params, timeout=10)
            if resp.status_code == 429:
                reset_ts = resp.headers.get("X-RateLimit-Requests-Reset")
                return _rate_limit_err("api_football", float(reset_ts) if reset_ts else None)
            resp.raise_for_status()
            body = resp.json()
            # API-Football 标准格式：{"response": [...], "paging": {...}}
            if body.get("errors"):
                err_msg = str(body["errors"])
                logger.warning(f"[APIFootball] API error: {err_msg}")
                return _err("API_ERROR", err_msg, "api_football")
            return _ok(body, "api_football")
        except requests.Timeout:
            return _err("TIMEOUT", "Request timed out (10s)", "api_football")
        except requests.ConnectionError:
            return _err("CONNECTION_ERROR", "Cannot connect to API-Football", "api_football")
        except Exception as e:
            return _err("UNKNOWN", str(e), "api_football")

    # ── 赛程 (Fixtures) ─────────────────────────────────────────────────

    def get_fixtures(self, date: Optional[str] = None, league_id: Optional[int] = None,
                     season: Optional[int] = None, live: bool = False) -> Dict[str, Any]:
        """获取赛程。date 格式 YYYY-MM-DD"""
        params: Dict[str, Any] = {}
        if date:
            params["date"] = date
        if league_id:
            params["league"] = league_id
        if season:
            params["season"] = season
        if live:
            params["live"] = "all"
        return self._get("fixtures", params)

    def get_fixture_by_id(self, fixture_id: int) -> Dict[str, Any]:
        """获取单场详情"""
        return self._get("fixtures", {"id": fixture_id})

    # ── 赔率 (Odds) ────────────────────────────────────────────────────

    def get_odds(self, fixture_id: int, bookmaker: Optional[int] = None) -> Dict[str, Any]:
        """获取单场赔率。bookmaker=6 为 Pinnacle"""
        params: Dict[str, Any] = {"fixture": fixture_id}
        if bookmaker:
            params["bookmaker"] = bookmaker
        return self._get("odds", params)

    def get_prematch_odds(self, fixture_id: int) -> Dict[str, Any]:
        """获取赛前赔率"""
        return self._get("odds/pre", {"fixture": fixture_id})

    def get_live_odds(self, fixture_id: int) -> Dict[str, Any]:
        """获取滚球赔率"""
        return self._get("odds/live", {"fixture": fixture_id})

    # ── 伤停 (Injuries) ───────────────────────────────────────────────

    def get_injuries(self, fixture_id: Optional[int] = None,
                     league_id: Optional[int] = None, season: Optional[int] = None) -> Dict[str, Any]:
        """获取伤停信息"""
        params: Dict[str, Any] = {}
        if fixture_id:
            params["fixture"] = fixture_id
        if league_id and season:
            params["league"] = league_id
            params["season"] = season
        return self._get("injuries", params)

    # ── 预测 (Predictions) ────────────────────────────────────────────

    def get_prediction(self, fixture_id: int) -> Dict[str, Any]:
        """获取 API-Football 的预测（含胜率、进球数、建议）"""
        return self._get("predictions", {"fixture": fixture_id})

    # ── 历史 (H2H) ────────────────────────────────────────────────────

    def get_h2h(self, h2h: str, last: int = 10) -> Dict[str, Any]:
        """
        获取历史交锋。
        h2h 格式："{team1_id}-{team2_id}" 或 "{team1_id}-{team2_id}"
        """
        return self._get("fixtures/headtohead", {"h2h": h2h, "last": last})

    # ── 球队 (Teams) ──────────────────────────────────────────────────

    def get_team_statistics(self, team_id: int, league_id: int, season: int) -> Dict[str, Any]:
        """球队赛季统计（进球、失球、xG、控球率等）"""
        return self._get("teams/statistics", {
            "team": team_id, "league": league_id, "season": season
        })

    def get_team_info(self, team_id: int) -> Dict[str, Any]:
        """球队基本信息（主场、容量、教练等）"""
        return self._get("teams", {"id": team_id})

    # ── 联赛 (Leagues) ────────────────────────────────────────────────

    def get_leagues(self, country: Optional[str] = None, season: Optional[int] = None) -> Dict[str, Any]:
        """获取联赛列表"""
        params: Dict[str, Any] = {}
        if country:
            params["country"] = country
        if season:
            params["season"] = season
        return self._get("leagues", params)

    def get_standings(self, league_id: int, season: int) -> Dict[str, Any]:
        """联赛积分榜"""
        return self._get("standings", {"league": league_id, "season": season})

    def get_top_scorers(self, league_id: int, season: int) -> Dict[str, Any]:
        """射手榜"""
        return self._get("players/topscorers", {"league": league_id, "season": season})

    # ── 赛季日历 (Fixtures Rounds) ────────────────────────────────────

    def get_fixture_rounds(self, league_id: int, season: int) -> Dict[str, Any]:
        """获取轮次"""
        return self._get("fixtures/rounds", {"league": league_id, "season": season})


# ═══════════════════════════════════════════════════════════════════════════════
# 2. The Odds API (the-odds-api.com) — 外围赔率对比
# ═══════════════════════════════════════════════════════════════════════════════
# 免费层：500 requests/month
# 文档：https://the-odds-api.com/liveapi/guides/v4/
# 覆盖：多博彩公司赔率对比、盘口、大小球、让球

class TheOddsAPIClient:
    """
    The Odds API v4 客户端。
    外围赔率对比（Pinnacle / Betfair / Bet365 等）。
    """

    BASE_URL = "https://api.the-odds-api.com/v4"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or _THE_ODDS_API_KEY

    def _get(self, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        params = params or {}
        params["apiKey"] = self.api_key
        url = f"{self.BASE_URL}{path}"
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 429:
                remaining = resp.headers.get("X-Requests-Remaining", "0")
                return _rate_limit_err("the_odds_api")
            resp.raise_for_status()
            body = resp.json()
            if isinstance(body, dict) and body.get("message"):
                return _err("API_ERROR", body["message"], "the_odds_api")
            return _ok(body, "the_odds_api")
        except requests.Timeout:
            return _err("TIMEOUT", "Request timed out (10s)", "the_odds_api")
        except requests.ConnectionError:
            return _err("CONNECTION_ERROR", "Cannot connect to The Odds API", "the_odds_api")
        except Exception as e:
            return _err("UNKNOWN", str(e), "the_odds_api")

    def get_sports(self) -> Dict[str, Any]:
        """获取可用运动列表"""
        return self._get("/sports")

    def get_odds(self, sport: str = "soccer", regions: str = "eu,uk,us,au",
                 markets: str = "h2h,spreads,totals", odds_format: str = "decimal",
                 event_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        获取赔率。
        sport: "soccer", "soccer_epl", "soccer_la_liga" 等
        regions: "eu" (欧洲), "uk" (英国), "us" (美国)
        markets: "h2h" (胜负平), "spreads" (让球), "totals" (大小球)
        """
        params: Dict[str, Any] = {
            "regions": regions,
            "markets": markets,
            "oddsFormat": odds_format,
        }
        if event_ids:
            params["eventIds"] = ",".join(event_ids)
        return self._get(f"/sports/{sport}/odds", params)

    def get_odds_by_fixture(self, fixture_ids: List[str], markets: str = "h2h,spreads,totals") -> Dict[str, Any]:
        """按 fixture ID 批量获取赔率"""
        return self.get_odds(event_ids=fixture_ids, markets=markets)

    def get_scores(self, sport: str = "soccer", days_from: int = 1) -> Dict[str, Any]:
        """获取比分"""
        return self._get(f"/sports/{sport}/scores", {"daysFrom": days_from})

    def get_event(self, event_id: str) -> Dict[str, Any]:
        """获取单场赛事详情"""
        return self._get(f"/sports/soccer/events/{event_id}")

    # ── 常用快捷方法 ──────────────────────────────────────────────────

    def get_epl_odds(self, markets: str = "h2h") -> Dict[str, Any]:
        """英超赔率"""
        return self.get_odds(sport="soccer_epl", markets=markets)

    def get_la_liga_odds(self, markets: str = "h2h") -> Dict[str, Any]:
        """西甲赔率"""
        return self.get_odds(sport="soccer_spain_la_liga", markets=markets)

    def get_serie_a_odds(self, markets: str = "h2h") -> Dict[str, Any]:
        """意甲赔率"""
        return self.get_odds(sport="soccer_italy_serie_a", markets=markets)

    def get_bundesliga_odds(self, markets: str = "h2h") -> Dict[str, Any]:
        """德甲赔率"""
        return self.get_odds(sport="soccer_germany_bundesliga", markets=markets)

    def get_ligue_1_odds(self, markets: str = "h2h") -> Dict[str, Any]:
        """法甲赔率"""
        return self.get_odds(sport="soccer_france_ligue_one", markets=markets)

    def get_ucl_odds(self, markets: str = "h2h") -> Dict[str, Any]:
        """欧冠赔率"""
        return self.get_odds(sport="soccer_uefa_champs_league", markets=markets)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Football-Data.org — 备用欧洲数据
# ═══════════════════════════════════════════════════════════════════════════════
# 免费层：10 requests/minute
# 文档：https://www.football-data.org/documentation/api
# 覆盖：欧洲主流联赛赛程、积分榜、球队信息

class FootballDataOrgClient:
    """
    Football-Data.org 客户端。
    免费 10 req/min，适合备用。
    """

    BASE_URL = "https://api.football-data.org/v4"

    # 常用联赛代码
    COMPETITIONS = {
        "PL": 2021,    # 英超
        "BL": 2002,    # 德甲
        "SA": 2019,    # 意甲
        "PD": 2014,    # 西甲
        "FL": 2015,    # 法甲
        "CL": 2001,    # 欧冠
        "EL": 2013,    # 欧联
        "EC": 2018,    # 英冠
        "DED": 2003,   # 荷甲
        "PPL": 2017,   # 葡超
        "BSA": 2016,   # 巴甲
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or _FOOTBALL_DATA_KEY
        self._session = requests.Session()
        self._session.headers.update({"X-Auth-Token": self.api_key})

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        url = f"{self.BASE_URL}{endpoint}"
        try:
            resp = self._session.get(url, params=params, timeout=10)
            if resp.status_code == 429:
                return _rate_limit_err("football_data_org")
            resp.raise_for_status()
            return _ok(resp.json(), "football_data_org")
        except requests.Timeout:
            return _err("TIMEOUT", "Request timed out (10s)", "football_data_org")
        except requests.ConnectionError:
            return _err("CONNECTION_ERROR", "Cannot connect to Football-Data.org", "football_data_org")
        except Exception as e:
            return _err("UNKNOWN", str(e), "football_data_org")

    def get_competitions(self) -> Dict[str, Any]:
        """获取可用联赛列表"""
        return self._get("/competitions")

    def get_standings(self, competition: str = "PL", standing_type: str = "TOTAL") -> Dict[str, Any]:
        """获取积分榜"""
        code = self.COMPETITIONS.get(competition, competition)
        return self._get(f"/competitions/{code}/standings", {"type": standing_type})

    def get_matches(self, competition: str = "PL", matchday: Optional[int] = None,
                    date_from: Optional[str] = None, date_to: Optional[str] = None,
                    status: str = "SCHEDULED") -> Dict[str, Any]:
        """获取赛程"""
        code = self.COMPETITIONS.get(competition, competition)
        params: Dict[str, Any] = {"status": status}
        if matchday:
            params["matchday"] = matchday
        if date_from:
            params["dateFrom"] = date_from
        if date_to:
            params["dateTo"] = date_to
        return self._get(f"/competitions/{code}/matches", params)

    def get_match(self, match_id: int) -> Dict[str, Any]:
        """获取单场详情"""
        return self._get(f"/matches/{match_id}")

    def get_team(self, team_id: int) -> Dict[str, Any]:
        """获取球队信息"""
        return self._get(f"/teams/{team_id}")

    def get_team_matches(self, team_id: int, date_from: Optional[str] = None,
                         date_to: Optional[str] = None, status: str = "FINISHED") -> Dict[str, Any]:
        """获取球队近期比赛"""
        params: Dict[str, Any] = {"status": status}
        if date_from:
            params["dateFrom"] = date_from
        if date_to:
            params["dateTo"] = date_to
        return self._get(f"/teams/{team_id}/matches", params)

    def get_team_squad(self, team_id: int) -> Dict[str, Any]:
        """获取球队阵容"""
        return self._get(f"/teams/{team_id}")

    def get_head_to_head(self, team1: int, team2: int, limit: int = 10) -> Dict[str, Any]:
        """获取历史交锋"""
        return self._get(f"/teams/{team1}/matches", {
            "opponent": team2,
            "limit": limit,
        })

    def get_person(self, person_id: int) -> Dict[str, Any]:
        """获取球员/教练信息"""
        return self._get(f"/persons/{person_id}")

    def get_scorers(self, competition: str = "PL", limit: int = 10) -> Dict[str, Any]:
        """获取射手榜"""
        code = self.COMPETITIONS.get(competition, competition)
        return self._get(f"/competitions/{code}/scorers", {"limit": limit})


# ═══════════════════════════════════════════════════════════════════════════════
# 4. TheSportsDB (thesportsdb.com) — 队伍/联赛信息补充
# ═══════════════════════════════════════════════════════════════════════════════
# 免费层：无限制（但部分端点需要 Patreon 支持）
# 文档：https://www.thesportsdb.com/api.php
# 覆盖：球队资料、联赛资料、历史赛果、球员信息

class TheSportsDBClient:
    """
    TheSportsDB 客户端。
    免费，适合查球队/联赛资料。
    """

    BASE_URL = "https://www.thesportsdb.com/api/v1/json"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or _THESPORTSDB_KEY

    def _get(self, endpoint: str) -> Dict[str, Any]:
        url = f"{self.BASE_URL}/{self.api_key}/{endpoint}"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            return _ok(resp.json(), "thesportsdb", confidence=0.7)
        except requests.Timeout:
            return _err("TIMEOUT", "Request timed out (10s)", "thesportsdb")
        except requests.ConnectionError:
            return _err("CONNECTION_ERROR", "Cannot connect to TheSportsDB", "thesportsdb")
        except Exception as e:
            return _err("UNKNOWN", str(e), "thesportsdb")

    # ── 联赛 ──────────────────────────────────────────────────────────

    def search_league(self, query: str) -> Dict[str, Any]:
        """搜索联赛"""
        return self._get(f"search_all_leagues.php?l={query}")

    def get_league_details(self, league_id: str) -> Dict[str, Any]:
        """联赛详情"""
        return self._get(f"lookupleague.php?id={league_id}")

    # ── 球队 ──────────────────────────────────────────────────────────

    def search_team(self, query: str) -> Dict[str, Any]:
        """搜索球队"""
        return self._get(f"searchteams.php?t={query}")

    def get_team_details(self, team_id: str) -> Dict[str, Any]:
        """球队详情"""
        return self._get(f"lookupteam.php?id={team_id}")

    def get_team_last_events(self, team_id: str) -> Dict[str, Any]:
        """球队最近 5 场"""
        return self._get(f"eventslast.php?id={team_id}")

    def get_team_next_events(self, team_id: str) -> Dict[str, Any]:
        """球队未来 5 场"""
        return self._get(f"eventsnext.php?id={team_id}")

    # ── 赛事 ──────────────────────────────────────────────────────────

    def get_events_by_round(self, league_id: str, round_num: str, season: str) -> Dict[str, Any]:
        """按轮次查赛事"""
        return self._get(f"eventsround.php?id={league_id}&r={round_num}&s={season}")

    def get_event_details(self, event_id: str) -> Dict[str, Any]:
        """赛事详情"""
        return self._get(f"lookupevent.php?id={event_id}")

    # ── 球员 ──────────────────────────────────────────────────────────

    def search_player(self, query: str) -> Dict[str, Any]:
        """搜索球员"""
        return self._get(f"searchplayers.php?p={query}")

    def get_player_honors(self, player_id: str) -> Dict[str, Any]:
        """球员荣誉"""
        return self._get(f"lookuphonors.php?id={player_id}")

    # ── 表格数据 ──────────────────────────────────────────────────────

    def get_league_table(self, league_id: str, season: str) -> Dict[str, Any]:
        """积分榜"""
        return self._get(f"lookuptable.php?l={league_id}&s={season}")


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Odds-API.io — 额外赔率源
# ═══════════════════════════════════════════════════════════════════════════════
# 文档：https://api.odds-api.io/
# API Key: 订阅密钥

class OddsAPIIOClient:
    """
    Odds-API.io 客户端。
    额外赔率源，作为 The Odds API 的补充。
    """

    BASE_URL = "https://api.odds-api.io/v4"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or _ODDS_API_IO_KEY

    def _get(self, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        params = params or {}
        params["apiKey"] = self.api_key
        params["region"] = params.get("region", "eu")
        url = f"{self.BASE_URL}{path}"
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 429:
                return _rate_limit_err("odds_api_io")
            resp.raise_for_status()
            body = resp.json()
            return _ok(body, "odds_api_io")
        except requests.Timeout:
            return _err("TIMEOUT", "Request timed out (10s)", "odds_api_io")
        except requests.ConnectionError:
            return _err("CONNECTION_ERROR", "Cannot connect to Odds-API.io", "odds_api_io")
        except Exception as e:
            return _err("UNKNOWN", str(e), "odds_api_io")

    def get_odds(self, sport: str = "soccer", markets: str = "h2h") -> Dict[str, Any]:
        """获取赔率"""
        return self._get(f"/sports/{sport}/odds", {"markets": markets})


# ═══════════════════════════════════════════════════════════════════════════════
# 兼容层：保留旧的 ForeignAPIClient 接口
# ═══════════════════════════════════════════════════════════════════════════════

class ForeignAPIClient:
    """
    向后兼容的统一接口。
    内部委托给各专用客户端。
    """
    def __init__(self):
        self.api_football = APIFootballClient()
        self.the_odds_api = TheOddsAPIClient()
        self.football_data = FootballDataOrgClient()
        self.thesportsdb = TheSportsDBClient()
        self.odds_api_io = OddsAPIIOClient()

    def get_odds(self, home_team: str, away_team: str) -> Dict[str, Any]:
        """
        向后兼容的 get_odds 方法。
        尝试 The Odds API 获取外围赔率。
        """
        return self.the_odds_api.get_odds()

    def get_fixtures(self, date: str) -> Dict[str, Any]:
        """通过 API-Football 获取赛程"""
        return self.api_football.get_fixtures(date=date)

    def get_team_stats(self, team_id: int, league_id: int, season: int) -> Dict[str, Any]:
        """通过 API-Football 获取球队统计"""
        return self.api_football.get_team_statistics(team_id, league_id, season)

    def get_h2h(self, team1_id: int, team2_id: int, last: int = 10) -> Dict[str, Any]:
        """通过 API-Football 获取历史交锋"""
        return self.api_football.get_h2h(f"{team1_id}-{team2_id}", last)

    def get_standings(self, league_id: int, season: int) -> Dict[str, Any]:
        """通过 API-Football 获取积分榜"""
        return self.api_football.get_standings(league_id, season)

    def get_injuries(self, fixture_id: int) -> Dict[str, Any]:
        """通过 API-Football 获取伤停"""
        return self.api_football.get_injuries(fixture_id=fixture_id)

    def get_prediction(self, fixture_id: int) -> Dict[str, Any]:
        """通过 API-Football 获取预测"""
        return self.api_football.get_prediction(fixture_id)

    def get_epl_standings(self, season: int = 2024) -> Dict[str, Any]:
        """快捷方法：英超积分榜"""
        return self.api_football.get_standings(39, season)  # API-Football 英超 ID=39
