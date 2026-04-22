from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.match_identity import MatchIdentityBuilder
from tools.agent_browser import AgentBrowser


def _env_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    s = str(v).strip().lower()
    return s in {"1", "true", "yes", "y", "on"}


def _sha1_ref(prefix: str, payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return f"{prefix}:{hashlib.sha1(encoded).hexdigest()[:12]}"


class WebIntelExtractor:
    def __init__(self, *, browser: Optional[AgentBrowser] = None, identity: Optional[MatchIdentityBuilder] = None):
        self.browser = browser or AgentBrowser()
        self.identity = identity or MatchIdentityBuilder()

    def _allow_network(self) -> bool:
        if not getattr(self.browser, "online", False):
            return False
        if os.getenv("PYTEST_CURRENT_TEST") and not _env_bool("WEB_INTEL_TEST_NETWORK", False):
            return False
        return True

    @staticmethod
    def _guess_league_name(text: str) -> str:
        for name in ("英超", "西甲", "意甲", "德甲", "法甲", "欧冠", "中超", "亚冠"):
            if name in text:
                return name
        return "UNK"

    def extract_fixtures_normalized(self, *, date: str, max_results: int = 8) -> List[Dict[str, Any]]:
        if not self._allow_network():
            return []

        query = f"{date} 足球 赛程 开赛时间 vs"
        rows = self.browser.search_web(query, max_results=max_results) or []
        time_re = re.compile(r"(?P<h>\d{1,2}):(?P<m>\d{2})")
        vs_re = re.compile(
            r"(?P<home>[A-Za-z\u4e00-\u9fff][A-Za-z\u4e00-\u9fff\s·]{1,30})\s*(?:vs|VS|V\.S\.|对|vs\.|-)\s*(?P<away>[A-Za-z\u4e00-\u9fff][A-Za-z\u4e00-\u9fff\s·]{1,30})"
        )

        seen: set[tuple[str, str, str]] = set()
        out: List[Dict[str, Any]] = []
        raw_ref = _sha1_ref("web_intel:fixtures", rows)
        confidence = 0.25

        for r in rows:
            text = f"{r.get('title') or ''} {r.get('body') or ''} {r.get('snippet') or ''}"
            if date not in text and "今日" not in text and "今天" not in text:
                continue
            tm = time_re.search(text)
            m = vs_re.search(text)
            if not tm or not m:
                continue

            home_team = m.group("home").strip()
            away_team = m.group("away").strip()
            if not home_team or not away_team or home_team == away_team:
                continue

            hh = int(tm.group("h"))
            mm = int(tm.group("m"))
            if hh > 23 or mm > 59:
                continue

            league_name = self._guess_league_name(text)
            kickoff_time = f"{date} {hh:02d}:{mm:02d}"
            status = "FINISHED" if any(x in text for x in ("完场", "已结束", "FT")) else "SCHEDULED"

            key = (league_name, home_team, away_team)
            if key in seen:
                continue
            seen.add(key)

            match_id = self.identity.build(league_name, home_team, away_team, kickoff_time)
            league_code = self.identity.league_resolver.resolve_code(league_name)
            home_id = self.identity.team_resolver.resolve_team_id(home_team)
            away_id = self.identity.team_resolver.resolve_team_id(away_team)

            out.append(
                {
                    "match_id": match_id,
                    "league_code": league_code,
                    "home_team_id": home_id,
                    "away_team_id": away_id,
                    "kickoff_time_utc": kickoff_time,
                    "status": status,
                    "source": "web_intel",
                    "confidence": confidence,
                    "raw_ref": raw_ref,
                    "degradations": ["low_confidence:web_intel"],
                    "source_ids": {},
                    "league_name": league_name,
                    "home_team": home_team,
                    "away_team": away_team,
                }
            )

        return out

    def extract_odds_normalized(
        self,
        *,
        league_name: str,
        home_team: str,
        away_team: str,
        kickoff_time: str,
        lottery_type: str,
        play_type: str,
        market: str,
        handicap: Optional[float] = None,
        max_results: int = 6,
    ) -> Dict[str, Any]:
        if not self._allow_network():
            return {"ok": False, "error": {"code": "DISABLED", "message": "web intel disabled in tests"}}

        query = f"{home_team} {away_team} 胜 平 负 赔率"
        rows = self.browser.search_web(query, max_results=max_results) or []
        blob = " ".join([f"{r.get('title') or ''} {r.get('body') or ''} {r.get('snippet') or ''}" for r in rows])

        nums = [float(x) for x in re.findall(r"(?<!\d)(?:[1-9]\d?\.\d{1,2})(?!\d)", blob)]
        triplet: Optional[tuple[float, float, float]] = None
        for i in range(len(nums) - 2):
            a, b, c = nums[i], nums[i + 1], nums[i + 2]
            if 1.01 <= a <= 25 and 1.01 <= b <= 25 and 1.01 <= c <= 25:
                triplet = (a, b, c)
                break

        if not triplet:
            return {"ok": False, "error": {"code": "NOT_FOUND", "message": "no odds triplet parsed"}}

        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        match_id = self.identity.build(league_name, home_team, away_team, kickoff_time)
        raw_ref = _sha1_ref("web_intel:odds", rows)
        confidence = 0.25

        selections = {
            "H": {"odds": float(triplet[0]), "last_update": now},
            "D": {"odds": float(triplet[1]), "last_update": now},
            "A": {"odds": float(triplet[2]), "last_update": now},
        }
        return {
            "ok": True,
            "match_id": match_id,
            "lottery_type": lottery_type,
            "play_type": play_type,
            "market": market,
            "handicap": handicap,
            "selections": selections,
            "source": "web_intel",
            "confidence": confidence,
            "raw_ref": raw_ref,
            "degradations": ["low_confidence:web_intel"],
        }

    def extract_results_normalized(self, *, date: str, max_results: int = 10) -> List[Dict[str, Any]]:
        if not self._allow_network():
            return []

        query = f"{date} 足球 比分 完场"
        rows = self.browser.search_web(query, max_results=max_results) or []
        raw_ref = _sha1_ref("web_intel:results", rows)
        confidence = 0.2

        vs_re = re.compile(
            r"(?P<home>[A-Za-z\u4e00-\u9fff][A-Za-z\u4e00-\u9fff\s·]{1,30})\s*(?:vs|VS|V\.S\.|对|vs\.|-)\s*(?P<away>[A-Za-z\u4e00-\u9fff][A-Za-z\u4e00-\u9fff\s·]{1,30})"
        )
        score_re = re.compile(r"(?P<h>\d{1,2})\s*[-:]\s*(?P<a>\d{1,2})")

        out: List[Dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()

        for r in rows:
            text = f"{r.get('title') or ''} {r.get('body') or ''} {r.get('snippet') or ''}"
            if date not in text and "今日" not in text and "今天" not in text:
                continue
            m = vs_re.search(text)
            s = score_re.search(text)
            if not m or not s:
                continue
            home_team = m.group("home").strip()
            away_team = m.group("away").strip()
            if not home_team or not away_team or home_team == away_team:
                continue
            score_ft = f"{int(s.group('h'))}-{int(s.group('a'))}"
            if not re.fullmatch(r"\d{1,2}-\d{1,2}", score_ft):
                continue
            key = (home_team, away_team)
            if key in seen:
                continue
            seen.add(key)

            league_name = self._guess_league_name(text)
            kickoff_time = f"{date} 00:00"
            match_id = self.identity.build(league_name, home_team, away_team, kickoff_time)
            out.append(
                {
                    "match_id": match_id,
                    "status": "FINISHED",
                    "score_ft": score_ft,
                    "source": "web_intel",
                    "confidence": confidence,
                    "raw_ref": raw_ref,
                    "degradations": ["low_confidence:web_intel"],
                    "source_ids": {},
                    "league": league_name,
                    "kickoff_time": kickoff_time,
                    "home_team": home_team,
                    "away_team": away_team,
                }
            )

        return out
