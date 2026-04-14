import hashlib
from typing import Dict, Optional


class EntityResolver:
    def __init__(self):
        self.team_alias: Dict[str, list[str]] = {
            "曼城": ["Manchester City", "Man City", "MCFC"],
            "皇家马德里": ["Real Madrid", "RMA"],
        }

        self._alias_to_canonical: Dict[str, str] = {}
        for canonical_cn, aliases in self.team_alias.items():
            self._alias_to_canonical[canonical_cn] = canonical_cn
            self._alias_to_canonical[canonical_cn.lower()] = canonical_cn
            for a in aliases:
                self._alias_to_canonical[a.lower()] = canonical_cn

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

