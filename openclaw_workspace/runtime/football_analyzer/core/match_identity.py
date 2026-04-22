from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha1
from typing import Dict, Optional


def _normalize_text(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[\u00a0\s]+", " ", s)
    s = re.sub(r"[-_./()]+", " ", s)
    return s.strip()


def _load_league_mapping() -> Dict[str, Dict]:
    here = os.path.dirname(os.path.abspath(__file__))
    mapping_path = os.path.join(here, "..", "data", "league_mapping.json")
    with open(mapping_path, "r", encoding="utf-8") as f:
        return json.load(f)


class LeagueResolver:
    def __init__(self, mapping: Optional[Dict] = None):
        self._mapping = mapping or _load_league_mapping()
        self._name_to_code: Dict[str, str] = {}
        self._index_mapping()
        self._install_common_aliases()

    def _index_mapping(self) -> None:
        for _, category in self._mapping.items():
            leagues = category.get("leagues", {})
            for code, info in leagues.items():
                name_cn = info.get("name", "")
                name_en = info.get("name_en", "")
                if name_cn:
                    self._name_to_code[_normalize_text(name_cn)] = code
                if name_en:
                    self._name_to_code[_normalize_text(name_en)] = code
                self._name_to_code[_normalize_text(code)] = code

    def _install_common_aliases(self) -> None:
        aliases = {
            "英超": "E0",
            "西甲": "SP1",
            "意甲": "I1",
            "德甲": "D1",
            "法甲": "F1",
            "中超": "CHN",
            "欧冠": "C1",
        }
        for k, v in aliases.items():
            self._name_to_code[_normalize_text(k)] = v

    def resolve_code(self, league_name: str) -> str:
        if not league_name:
            return "UNK"

        key = _normalize_text(league_name)
        if key in self._name_to_code:
            return self._name_to_code[key]

        for candidate, code in self._name_to_code.items():
            if key and candidate and (key in candidate or candidate in key):
                return code

        return "UNK"


@dataclass(frozen=True)
class ResolvedTeam:
    team_id: str
    canonical_name: str


class TeamResolver:
    def __init__(self):
        self._alias_to_team: Dict[str, ResolvedTeam] = {}
        self._install_aliases()

    def _install_aliases(self) -> None:
        mapping = {
            "ARS": ["arsenal", "阿森纳", "枪手"],
            "TOT": ["tottenham", "tottenham hotspur", "spurs", "热刺"],
            "MCI": ["manchester city", "man city", "mcfc", "曼城"],
            "RMA": ["real madrid", "rm", "rma", "皇家马德里"],
        }
        canonical_names = {
            "ARS": "Arsenal",
            "TOT": "Tottenham",
            "MCI": "Manchester City",
            "RMA": "Real Madrid",
        }

        for team_id, aliases in mapping.items():
            canonical = canonical_names.get(team_id, team_id)
            self._alias_to_team[_normalize_text(canonical)] = ResolvedTeam(team_id=team_id, canonical_name=canonical)
            for a in aliases:
                self._alias_to_team[_normalize_text(a)] = ResolvedTeam(team_id=team_id, canonical_name=canonical)

    def resolve(self, team_name: str) -> ResolvedTeam:
        if not team_name:
            raise ValueError("team_name cannot be empty")

        key = _normalize_text(team_name)
        if key in self._alias_to_team:
            return self._alias_to_team[key]

        fallback_id = sha1(key.encode("utf-8")).hexdigest()[:8].upper()
        return ResolvedTeam(team_id=fallback_id, canonical_name=team_name.strip())

    def resolve_team_id(self, team_name: str) -> str:
        return self.resolve(team_name).team_id


class MatchIdentityBuilder:
    def __init__(self, league_resolver: Optional[LeagueResolver] = None, team_resolver: Optional[TeamResolver] = None):
        self.league_resolver = league_resolver or LeagueResolver()
        self.team_resolver = team_resolver or TeamResolver()

    def build(self, league_name: str, home_team: str, away_team: str, kickoff_time: str) -> str:
        league_code = self.league_resolver.resolve_code(league_name)
        home_id = self.team_resolver.resolve_team_id(home_team)
        away_id = self.team_resolver.resolve_team_id(away_team)
        date_utc = self._kickoff_date_utc(kickoff_time)
        return f"{date_utc}_{league_code}_{home_id}_{away_id}"

    def _kickoff_date_utc(self, kickoff_time: str) -> str:
        kickoff_time = kickoff_time.strip()
        if not kickoff_time:
            raise ValueError("kickoff_time cannot be empty")

        iso_candidate = kickoff_time.replace(" ", "T")
        try:
            dt = datetime.fromisoformat(iso_candidate)
            if dt.tzinfo is None:
                return dt.strftime("%Y%m%d")
            return dt.astimezone(timezone.utc).strftime("%Y%m%d")
        except Exception:
            m = re.search(r"(\d{4})-(\d{2})-(\d{2})", kickoff_time)
            if m:
                y, mm, d = m.group(1), m.group(2), m.group(3)
                return f"{y}{mm}{d}"
            raise ValueError(f"unsupported kickoff_time format: {kickoff_time}")
