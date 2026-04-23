import hashlib
import json
import os
from typing import Dict, Optional


class EntityResolver:
    def __init__(self):
        self.team_alias: Dict[str, list[str]] = {
            "曼城": ["Manchester City", "Man City", "MCFC"],
            "皇家马德里": ["Real Madrid", "RMA"],
            "阿森纳": ["Arsenal", "ARS", "Gunners"],
            "热刺": ["Tottenham", "Tottenham Hotspur", "Spurs", "TOT"],
        }

        self._alias_to_canonical: Dict[str, str] = {}
        for canonical_cn, aliases in self.team_alias.items():
            self._alias_to_canonical[canonical_cn] = canonical_cn
            self._alias_to_canonical[canonical_cn.lower()] = canonical_cn
            for a in aliases:
                self._alias_to_canonical[a.lower()] = canonical_cn

        self._league_name_to_code: Dict[str, str] = {}
        self._init_league_mapping()

    def _init_league_mapping(self) -> None:
        here = os.path.dirname(os.path.abspath(__file__))
        mapping_path = os.path.join(here, "..", "data", "league_mapping.json")
        try:
            with open(mapping_path, "r", encoding="utf-8") as f:
                mapping = json.load(f)
        except Exception:
            mapping = {}

        for _, category in mapping.items():
            leagues = category.get("leagues", {})
            for code, info in leagues.items():
                name_cn = (info.get("name") or "").strip()
                name_en = (info.get("name_en") or "").strip()
                if name_cn:
                    self._league_name_to_code[name_cn.lower()] = code
                if name_en:
                    self._league_name_to_code[name_en.lower()] = code
                self._league_name_to_code[code.lower()] = code

        common_aliases = {"英超": "E0", "西甲": "SP1", "意甲": "I1", "德甲": "D1", "法甲": "F1", "欧冠": "C1"}
        for k, v in common_aliases.items():
            self._league_name_to_code[k.lower()] = v

    def _id(self, s: str) -> str:
        return hashlib.sha1(s.encode("utf-8")).hexdigest()[:16]

    def resolve_team(self, name: str) -> dict:
        if not name:
            return {
                "ok": False,
                "data": None,
                "error": {"code": "BAD_INPUT", "message": "empty team name"},
                "meta": {"mock": False, "source": "entity_resolver"},
            }

        canonical = self._alias_to_canonical.get(name.lower(), name)
        return {
            "ok": True,
            "data": {"team_id": self._id(canonical), "canonical_name": canonical, "input": name},
            "error": None,
            "meta": {"mock": False, "source": "entity_resolver"},
        }

    def resolve_league(self, name: str) -> dict:
        if not name:
            return {
                "ok": False,
                "data": None,
                "error": {"code": "BAD_INPUT", "message": "empty league name"},
                "meta": {"mock": False, "source": "entity_resolver"},
            }

        league_code = self._league_name_to_code.get(name.strip().lower())
        if not league_code:
            return {
                "ok": False,
                "data": None,
                "error": {"code": "NOT_FOUND", "message": "league resolve failed"},
                "meta": {"mock": False, "source": "entity_resolver"},
            }

        return {
            "ok": True,
            "data": {"league_code": league_code, "input": name},
            "error": None,
            "meta": {"mock": False, "source": "entity_resolver"},
        }
