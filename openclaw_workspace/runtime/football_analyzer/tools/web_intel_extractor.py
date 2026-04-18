from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

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
    def __init__(self, *, browser: Optional[AgentBrowser] = None):
        self.browser = browser or AgentBrowser()

    def _allow_network(self) -> bool:
        if os.getenv("PYTEST_CURRENT_TEST") and not _env_bool("WEB_INTEL_TEST_NETWORK", False):
            return False
        return True

    def extract_fixtures(self, *, date: str, max_results: int = 8) -> List[Dict[str, Any]]:
        if not self._allow_network():
            return []

        query = f"{date} 足球 赛程 开赛时间 vs"
        rows = self.browser.search_web(query, max_results=max_results) or []
        time_re = re.compile(r"(?P<h>\d{1,2}):(?P<m>\d{2})")
        vs_re = re.compile(
            r"(?P<home>[A-Za-z\u4e00-\u9fff][A-Za-z\u4e00-\u9fff\s·]{1,30})\s*(?:vs|VS|V\.S\.|对|vs\.|-)\s*(?P<away>[A-Za-z\u4e00-\u9fff][A-Za-z\u4e00-\u9fff\s·]{1,30})"
        )

        out: List[Dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
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
            key = (home_team, away_team)
            if key in seen:
                continue
            seen.add(key)
            kickoff_time = f"{date} {int(tm.group('h')):02d}:{int(tm.group('m')):02d}"
            out.append(
                {
                    "league": "UNK",
                    "home_team": home_team,
                    "away_team": away_team,
                    "kickoff_time": kickoff_time,
                    "status": "upcoming",
                }
            )

        return out

    def extract_odds(self, *, home_team: str, away_team: str, max_results: int = 6) -> Dict[str, Any]:
        if not self._allow_network():
            return {
                "ok": False,
                "data": None,
                "error": {"code": "DISABLED", "message": "web intel disabled in tests"},
                "meta": {"mock": False, "source": "web_intel", "confidence": 0.0, "stale": True},
            }

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
            return {
                "ok": False,
                "data": None,
                "error": {"code": "NOT_FOUND", "message": "no odds triplet parsed"},
                "meta": {"mock": False, "source": "web_intel", "confidence": 0.0, "stale": True},
            }

        return {
            "ok": True,
            "data": {"eu_odds": {"home": float(triplet[0]), "draw": float(triplet[1]), "away": float(triplet[2])}},
            "error": None,
            "meta": {"mock": False, "source": "web_intel", "confidence": 0.25, "stale": False, "raw_ref": _sha1_ref("web_intel:odds", rows)},
        }

    def extract_results(self, *, date: str, max_results: int = 10) -> List[Dict[str, Any]]:
        if not self._allow_network():
            return []

        query = f"{date} 足球 比分 完场"
        rows = self.browser.search_web(query, max_results=max_results) or []
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
            key = (home_team, away_team)
            if key in seen:
                continue
            seen.add(key)
            out.append(
                {
                    "league": "UNK",
                    "kickoff_time": f"{date} 00:00",
                    "home_team": home_team,
                    "away_team": away_team,
                    "score_ft": f"{int(s.group('h'))}-{int(s.group('a'))}",
                    "status": "FINISHED",
                }
            )
        return out

