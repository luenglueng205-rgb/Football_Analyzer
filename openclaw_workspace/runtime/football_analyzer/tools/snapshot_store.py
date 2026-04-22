import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from tools.paths import data_dir


class SnapshotStore:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.join(data_dir(), "snapshots.db")
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            """
        CREATE TABLE IF NOT EXISTS matches (
            match_id TEXT PRIMARY KEY,
            league TEXT,
            home_team TEXT,
            away_team TEXT,
            kickoff_time TEXT,
            source TEXT,
            created_at TEXT
        )
        """
        )
        c.execute(
            """
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            match_id TEXT,
            captured_at TEXT,
            source TEXT,
            payload_json TEXT,
            confidence REAL,
            stale INTEGER
        )
        """
        )
        conn.commit()
        conn.close()

    def upsert_match(
        self,
        match_id: str,
        league: str,
        home_team: str,
        away_team: str,
        kickoff_time: str,
        source: str,
    ) -> None:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        c.execute(
            """
        INSERT INTO matches(match_id, league, home_team, away_team, kickoff_time, source, created_at)
        VALUES(?,?,?,?,?,?,?)
        ON CONFLICT(match_id) DO UPDATE SET
          league=excluded.league,
          home_team=excluded.home_team,
          away_team=excluded.away_team,
          kickoff_time=excluded.kickoff_time,
          source=excluded.source
        """,
            (match_id, league, home_team, away_team, kickoff_time, source, now),
        )
        conn.commit()
        conn.close()

    def insert_snapshot(
        self,
        category: str,
        match_id: str,
        source: str,
        payload: Dict[str, Any],
        confidence: float,
        stale: bool,
    ) -> None:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        c.execute(
            """
        INSERT INTO snapshots(category, match_id, captured_at, source, payload_json, confidence, stale)
        VALUES(?,?,?,?,?,?,?)
        """,
            (
                category,
                match_id,
                now,
                source,
                json.dumps(payload, ensure_ascii=False),
                float(confidence),
                1 if stale else 0,
            ),
        )
        conn.commit()
        conn.close()

    def get_latest_snapshot(self, category: str, match_id: str) -> Dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            """
        SELECT captured_at, source, payload_json, confidence, stale
        FROM snapshots
        WHERE category=? AND match_id=?
        ORDER BY id DESC
        LIMIT 1
        """,
            (category, match_id),
        )
        row = c.fetchone()
        conn.close()
        if not row:
            return {
                "ok": False,
                "data": None,
                "error": {"code": "NOT_FOUND", "message": "No snapshot"},
                "meta": {"mock": False, "source": "snapshot_store"},
            }

        captured_at, source, payload_json, confidence, stale = row
        return {
            "ok": True,
            "data": {
                "payload": json.loads(payload_json),
                "meta": {
                    "captured_at": captured_at,
                    "source": source,
                    "confidence": float(confidence),
                    "stale": bool(stale),
                },
            },
            "error": None,
            "meta": {"mock": False, "source": "snapshot_store"},
        }

    def get_match(self, match_id: str) -> Dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            """
        SELECT league, home_team, away_team, kickoff_time, source, created_at
        FROM matches
        WHERE match_id=?
        LIMIT 1
        """,
            (match_id,),
        )
        row = c.fetchone()
        conn.close()
        if not row:
            return {
                "ok": False,
                "data": None,
                "error": {"code": "NOT_FOUND", "message": "match not found"},
                "meta": {"mock": False, "source": "snapshot_store"},
            }
        league, home_team, away_team, kickoff_time, source, created_at = row
        return {
            "ok": True,
            "data": {
                "match_id": match_id,
                "league": league,
                "home_team": home_team,
                "away_team": away_team,
                "kickoff_time": kickoff_time,
                "source": source,
                "created_at": created_at,
            },
            "error": None,
            "meta": {"mock": False, "source": "snapshot_store"},
        }
