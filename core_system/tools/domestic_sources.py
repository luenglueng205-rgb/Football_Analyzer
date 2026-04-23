from __future__ import annotations

import os

from typing import Any, Dict, List, Optional

from tools.domestic_500_fixtures import fetch_500_trade_html, parse_500_trade_fixtures_html
from tools.agent_browser import AgentBrowser
from tools.domestic_odds_500 import fetch_500_eu_odds_by_teams
from tools.domestic_500_jczq_sp import fetch_500_jczq_sp_by_teams
from tools.domestic_500_beidan_sp import fetch_500_beidan_sp_by_teams
from tools.domestic_500_results import fetch_500_trade_results_by_date, fetch_500_zx_results_by_date
from tools.domestic_500_live_state import fetch_500_live_state_by_fid


def _env_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    s = str(v).strip().lower()
    return s in {"1", "true", "yes", "y", "on"}


def _looks_like_captcha(html: str) -> bool:
    t = str(html or "")
    return any(k in t for k in ("验证码", "安全验证", "人机验证", "verify", "captcha"))


class DomesticSources:
    def __init__(self, browser: Optional[AgentBrowser] = None):
        self.browser = browser or AgentBrowser()
        self.info_first_mode = _env_bool("INFO_FIRST_MODE", True)

    def get_fixtures(self, date: Optional[str] = None) -> List[Dict[str, Any]]:
        html = fetch_500_trade_html(date=date)
        if html:
            if _looks_like_captcha(html) and self.info_first_mode:
                return []
            fixtures = parse_500_trade_fixtures_html(html=html, date=date)
            if fixtures:
                return fixtures
        return self.browser.scrape_500_fixtures(date=date)

    def get_odds_search(self, home_team: str, away_team: str) -> List[Dict[str, Any]]:
        return self.browser.scrape_okooo_odds_search(home_team=home_team, away_team=away_team)

    def get_eu_odds(
        self, *, home_team: str, away_team: str, kickoff_time: Optional[str] = None, fid: Optional[str] = None
    ) -> Dict[str, Any]:
        res = fetch_500_eu_odds_by_teams(home_team=home_team, away_team=away_team, kickoff_time=kickoff_time, fid=fid)
        if res.get("ok"):
            return res

        if (res.get("error") or {}).get("code") == "CAPTCHA_REQUIRED":
            return res

        vis = self.browser.scrape_500_eu_odds_visual(home_team=home_team, away_team=away_team, kickoff_time=kickoff_time)
        if vis.get("ok"):
            return vis

        return res

    def get_jingcai_sp(
        self, *, home_team: str, away_team: str, kickoff_time: Optional[str] = None, fid: Optional[str] = None
    ) -> Dict[str, Any]:
        res = fetch_500_jczq_sp_by_teams(home_team=home_team, away_team=away_team, kickoff_time=kickoff_time, fid=fid)
        if res.get("ok"):
            return res
        if (res.get("error") or {}).get("code") == "CAPTCHA_REQUIRED":
            if self.info_first_mode:
                return res
            vis = self.browser.scrape_500_jingcai_sp_visual(home_team=home_team, away_team=away_team, kickoff_time=kickoff_time)
            if vis.get("ok"):
                return vis
            return res
        return res

    def get_beidan_sp(
        self, *, home_team: str, away_team: str, kickoff_time: Optional[str] = None, fid: Optional[str] = None
    ) -> Dict[str, Any]:
        res = fetch_500_beidan_sp_by_teams(home_team=home_team, away_team=away_team, kickoff_time=kickoff_time, fid=fid)
        if res.get("ok"):
            return res
        if (res.get("error") or {}).get("code") == "CAPTCHA_REQUIRED":
            if self.info_first_mode:
                return res
            vis = self.browser.scrape_500_beidan_sp_visual(home_team=home_team, away_team=away_team, kickoff_time=kickoff_time)
            if vis.get("ok"):
                return vis
            return res
        return res

    def get_results(self, *, date: str) -> Dict[str, Any]:
        a = fetch_500_trade_results_by_date(date=date)
        if a.get("ok"):
            return a

        b = fetch_500_zx_results_by_date(date=date)
        if b.get("ok"):
            return b

        captcha = ((a.get("error") or {}).get("code") == "CAPTCHA_REQUIRED") or ((b.get("error") or {}).get("code") == "CAPTCHA_REQUIRED")
        if captcha:
            if self.info_first_mode:
                return b if b.get("error") else a
            vis = self.browser.scrape_500_results_visual(date=date)
            if vis.get("ok"):
                return vis
            return b if b.get("error") else a

        return b if b.get("error") else a

    def get_live_state(self, match: Dict[str, Any]) -> Dict[str, Any]:
        fid: Optional[str] = None
        if isinstance(match, dict):
            sids = match.get("source_ids")
            if isinstance(sids, dict):
                if isinstance(sids.get("500.com"), dict) and sids["500.com"].get("fid"):
                    fid = str(sids["500.com"]["fid"])
                elif sids.get("fid"):
                    fid = str(sids.get("fid"))
            if not fid and match.get("fid"):
                fid = str(match.get("fid"))

        if not fid:
            return {
                "ok": False,
                "data": None,
                "error": {"code": "BAD_INPUT", "message": "fid missing in match.source_ids"},
                "meta": {"mock": False, "source": "domestic", "confidence": 0.0, "stale": True},
            }

        return fetch_500_live_state_by_fid(fid=fid)
