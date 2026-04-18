from __future__ import annotations

import time
import json
from typing import Any, Dict, List, Optional

from tools.memory_manager import MemoryManager


class MemoryWriter:
    def __init__(self, *, manager: Optional[MemoryManager] = None):
        self.manager = manager or MemoryManager()

    def _sanitize_metadata_value(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, (dict, list, tuple)):
            try:
                return json.dumps(value, ensure_ascii=False, sort_keys=True)
            except Exception:
                return str(value)
        return str(value)

    def write_match_summary(
        self,
        *,
        match_id: str,
        league_code: str,
        stage: str,
        summary: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        tags = tags or []
        metadata = metadata or {}
        doc_id = f"match_summary::{match_id}::{stage}::{int(time.time() * 1000)}"
        sanitized = {k: self._sanitize_metadata_value(v) for k, v in metadata.items()}
        meta = {
            "type": "match_summary",
            "stage": str(stage),
            "match_id": str(match_id),
            "league_code": str(league_code),
            "tags": ",".join([str(t) for t in tags]),
            **{k: v for k, v in sanitized.items() if v is not None},
        }
        self.manager.collection.add(documents=[str(summary)], metadatas=[meta], ids=[doc_id])
        return {"ok": True, "doc_id": doc_id, "meta": meta}

    def write_pre_match(
        self,
        *,
        match: Dict[str, Any],
        summary: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        match_id = str(match.get("match_id") or "UNKNOWN")
        league_code = str(match.get("league_code") or "UNK")
        meta = {
            "home_team": match.get("home_team"),
            "away_team": match.get("away_team"),
            "kickoff_time": match.get("kickoff_time"),
            **(metadata or {}),
        }
        return self.write_match_summary(
            match_id=match_id,
            league_code=league_code,
            stage="pre_match",
            summary=summary,
            tags=tags,
            metadata=meta,
        )

    def write_post_match(
        self,
        *,
        match: Dict[str, Any],
        summary: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        match_id = str(match.get("match_id") or "UNKNOWN")
        league_code = str(match.get("league_code") or "UNK")
        meta = {
            "home_team": match.get("home_team"),
            "away_team": match.get("away_team"),
            "kickoff_time": match.get("kickoff_time"),
            **(metadata or {}),
        }
        return self.write_match_summary(
            match_id=match_id,
            league_code=league_code,
            stage="post_match",
            summary=summary,
            tags=tags,
            metadata=meta,
        )
