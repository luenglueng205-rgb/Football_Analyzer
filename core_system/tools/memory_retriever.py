from __future__ import annotations

from typing import Any, Dict, List, Optional

from tools.memory_manager import MemoryManager


class MemoryRetriever:
    def __init__(self, *, manager: Optional[MemoryManager] = None):
        self.manager = manager or MemoryManager()

    def retrieve_for_match(
        self,
        *,
        match: Dict[str, Any],
        top_k: int = 5,
        query_context: str = "",
    ) -> Dict[str, Any]:
        match_id = str(match.get("match_id") or "UNKNOWN")
        league_code = str(match.get("league_code") or "UNK")
        home = str(match.get("home_team") or "")
        away = str(match.get("away_team") or "")
        kickoff = str(match.get("kickoff_time") or "")

        query_text = (
            str(query_context).strip()
            or f"{league_code} {home} vs {away} {kickoff} 赛前赛后复盘要点与投注经验"
        )

        where = {"type": {"$eq": "match_summary"}}
        if league_code and league_code != "UNK":
            where = {"$and": [{"type": {"$eq": "match_summary"}}, {"league_code": {"$eq": league_code}}]}

        try:
            results = self.manager.collection.query(query_texts=[query_text], n_results=int(top_k), where=where)
        except Exception as e:
            return {
                "ok": False,
                "query": {"match_id": match_id, "league_code": league_code, "query_text": query_text},
                "data": [],
                "error": {"type": type(e).__name__, "message": str(e)},
            }

        docs = (results.get("documents") or [[]])[0] or []
        metas = (results.get("metadatas") or [[]])[0] or []
        ids = (results.get("ids") or [[]])[0] or []
        distances = (results.get("distances") or [[]])[0] or []

        memories: List[Dict[str, Any]] = []
        for i, doc in enumerate(docs):
            meta = metas[i] if i < len(metas) else {}
            memories.append(
                {
                    "doc_id": ids[i] if i < len(ids) else None,
                    "summary": doc,
                    "match_id": meta.get("match_id"),
                    "league_code": meta.get("league_code"),
                    "stage": meta.get("stage"),
                    "tags": meta.get("tags"),
                    "distance": distances[i] if i < len(distances) else None,
                    "meta": meta,
                }
            )

        filtered = [m for m in memories if m.get("match_id") != match_id]
        return {
            "ok": True,
            "query": {"match_id": match_id, "league_code": league_code, "query_text": query_text},
            "data": filtered,
        }
