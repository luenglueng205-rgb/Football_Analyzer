# P2 Data Fabric Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a resilient real-data layer (Browser/Search first, API optional) for odds/injuries/fixtures/news/scores, with entity normalization and snapshot storage, powering CLV/ROI calibration.

**Architecture:** Add `MultiSourceFetcher` + `EntityResolver` + `SnapshotStore`. Integrate via `AnalyzerAPI` and tool registry (SSOT). Primary sources: 500.com / 澳客 / 懂球帝 / 捷报比分. Optional APIs as fallback only.

**Tech Stack:** Python 3, sqlite3, pydantic v2, MCP (optional), httpx/requests, integrated browser tools (manual verification allowed).

---

### Task 1: Add SnapshotStore (SQLite) for Reproducible Data

**Files:**
- Create: `tools/snapshot_store.py`
- Test: `tests/test_snapshot_store.py`

- [ ] **Step 1: Write the failing test**

```python
import os
from tools.snapshot_store import SnapshotStore

def test_snapshot_store_roundtrip():
    db_path = "test_snapshots.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    store = SnapshotStore(db_path=db_path)
    match_id = "UCL_RM_MCI_20260414"

    store.upsert_match(
        match_id=match_id,
        league="欧冠",
        home_team="皇家马德里",
        away_team="曼城",
        kickoff_time="2026-04-14T20:00:00+08:00",
        source="500.com",
    )

    store.insert_snapshot(
        category="odds",
        match_id=match_id,
        source="500.com",
        payload={"eu_odds": {"home": 2.3, "draw": 3.4, "away": 2.8}},
        confidence=0.85,
        stale=False,
    )

    latest = store.get_latest_snapshot(category="odds", match_id=match_id)
    assert latest["ok"] is True
    assert latest["data"]["payload"]["eu_odds"]["home"] == 2.3
    assert latest["data"]["meta"]["confidence"] == 0.85

    if os.path.exists(db_path):
        os.remove(db_path)

if __name__ == "__main__":
    test_snapshot_store_roundtrip()
    print("test_snapshot_store_roundtrip PASSED")
```

- [ ] **Step 2: Run test to verify it fails**
Run: `PYTHONPATH=. python3 tests/test_snapshot_store.py`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Write minimal implementation**

```python
import os
import json
import sqlite3
from datetime import datetime, timezone

class SnapshotStore:
    def __init__(self, db_path="data/snapshots.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            match_id TEXT PRIMARY KEY,
            league TEXT,
            home_team TEXT,
            away_team TEXT,
            kickoff_time TEXT,
            source TEXT,
            created_at TEXT
        )
        """)
        c.execute("""
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
        """)
        conn.commit()
        conn.close()

    def upsert_match(self, match_id, league, home_team, away_team, kickoff_time, source):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        c.execute("""
        INSERT INTO matches(match_id, league, home_team, away_team, kickoff_time, source, created_at)
        VALUES(?,?,?,?,?,?,?)
        ON CONFLICT(match_id) DO UPDATE SET
          league=excluded.league,
          home_team=excluded.home_team,
          away_team=excluded.away_team,
          kickoff_time=excluded.kickoff_time,
          source=excluded.source
        """, (match_id, league, home_team, away_team, kickoff_time, source, now))
        conn.commit()
        conn.close()

    def insert_snapshot(self, category, match_id, source, payload, confidence, stale):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        c.execute("""
        INSERT INTO snapshots(category, match_id, captured_at, source, payload_json, confidence, stale)
        VALUES(?,?,?,?,?,?,?)
        """, (category, match_id, now, source, json.dumps(payload, ensure_ascii=False), float(confidence), 1 if stale else 0))
        conn.commit()
        conn.close()

    def get_latest_snapshot(self, category, match_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
        SELECT captured_at, source, payload_json, confidence, stale
        FROM snapshots
        WHERE category=? AND match_id=?
        ORDER BY id DESC
        LIMIT 1
        """, (category, match_id))
        row = c.fetchone()
        conn.close()
        if not row:
            return {"ok": False, "data": None, "error": {"code": "NOT_FOUND", "message": "No snapshot"}, "meta": {"mock": False}}
        captured_at, source, payload_json, confidence, stale = row
        return {
            "ok": True,
            "data": {
                "payload": json.loads(payload_json),
                "meta": {
                    "captured_at": captured_at,
                    "source": source,
                    "confidence": float(confidence),
                    "stale": bool(stale)
                }
            },
            "error": None,
            "meta": {"mock": False, "source": "snapshot_store"}
        }
```

- [ ] **Step 4: Run test to verify it passes**
Run: `PYTHONPATH=. python3 tests/test_snapshot_store.py`
Expected: PASS

- [ ] **Step 5: Commit**
Run:
```bash
git add tools/snapshot_store.py tests/test_snapshot_store.py
git commit -m "feat(p2): add snapshot store for reproducible data"
```

---

### Task 2: Add EntityResolver (Chinese-first IDs + aliases)

**Files:**
- Create: `tools/entity_resolver.py`
- Test: `tests/test_entity_resolver.py`

- [ ] **Step 1: Write the failing test**

```python
from tools.entity_resolver import EntityResolver

def test_entity_resolver_aliases():
    r = EntityResolver()
    team = r.resolve_team("曼城")
    assert team["ok"] is True
    assert team["data"]["canonical_name"] == "曼城"
    assert isinstance(team["data"]["team_id"], str)

    team2 = r.resolve_team("Manchester City")
    assert team2["ok"] is True
    assert team2["data"]["team_id"] == team["data"]["team_id"]

if __name__ == "__main__":
    test_entity_resolver_aliases()
    print("test_entity_resolver_aliases PASSED")
```

- [ ] **Step 2: Run test to verify it fails**
Run: `PYTHONPATH=. python3 tests/test_entity_resolver.py`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
import hashlib

class EntityResolver:
    def __init__(self):
        self.team_alias = {
            "曼城": ["Manchester City", "Man City", "MCFC"],
            "皇家马德里": ["Real Madrid", "RMA"]
        }
        self._alias_to_canonical = {}
        for cn, aliases in self.team_alias.items():
            self._alias_to_canonical[cn] = cn
            for a in aliases:
                self._alias_to_canonical[a.lower()] = cn

    def _id(self, s: str) -> str:
        return hashlib.sha1(s.encode("utf-8")).hexdigest()[:16]

    def resolve_team(self, name: str) -> dict:
        if not name:
            return {"ok": False, "data": None, "error": {"code": "BAD_INPUT", "message": "empty team name"}, "meta": {"mock": False}}
        canonical = self._alias_to_canonical.get(name.lower(), name)
        return {
            "ok": True,
            "data": {"team_id": self._id(canonical), "canonical_name": canonical, "input": name},
            "error": None,
            "meta": {"mock": False, "source": "entity_resolver"}
        }
```

- [ ] **Step 4: Run test to verify it passes**
Run: `PYTHONPATH=. python3 tests/test_entity_resolver.py`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add tools/entity_resolver.py tests/test_entity_resolver.py
git commit -m "feat(p2): add entity resolver for multilingual normalization"
```

---

### Task 3: Implement MultiSourceFetcher Skeleton (Odds/Injuries/Fixtures/News/Scores)

**Files:**
- Create: `tools/multisource_fetcher.py`
- Test: `tests/test_multisource_fetcher_fallback.py`

- [ ] **Step 1: Write failing test (fallback works, never crashes)**

```python
import asyncio
from tools.multisource_fetcher import MultiSourceFetcher

async def test_fallback_never_crash():
    f = MultiSourceFetcher()
    res = await f.fetch_odds(home_team="皇家马德里", away_team="曼城")
    assert "ok" in res and "meta" in res
    # If no browser configured, it should fall back to search/snapshot and set low confidence
    if res["ok"]:
        assert "confidence" in res["meta"]
    else:
        assert res["error"]["code"] in ["CAPTCHA_REQUIRED", "NOT_FOUND", "FETCH_FAILED"]

if __name__ == "__main__":
    asyncio.run(test_fallback_never_crash())
    print("test_fallback_never_crash PASSED")
```

- [ ] **Step 2: Run test to verify it fails**
Run: `PYTHONPATH=. python3 tests/test_multisource_fetcher_fallback.py`
Expected: FAIL

- [ ] **Step 3: Minimal implementation (no real scraping yet; correct protocol + snapshot integration)**

```python
import asyncio
from tools.snapshot_store import SnapshotStore
from tools.entity_resolver import EntityResolver

class MultiSourceFetcher:
    def __init__(self, store: SnapshotStore | None = None, resolver: EntityResolver | None = None):
        self.store = store or SnapshotStore()
        self.resolver = resolver or EntityResolver()

    async def fetch_odds(self, home_team: str, away_team: str) -> dict:
        # P2 Step: start with snapshot fallback (works offline), then later add browser/search providers.
        home = self.resolver.resolve_team(home_team)
        away = self.resolver.resolve_team(away_team)
        if not home["ok"] or not away["ok"]:
            return {"ok": False, "data": None, "error": {"code": "BAD_INPUT", "message": "team resolve failed"}, "meta": {"mock": False, "source": "multisource"}}

        match_id = f"ODDS::{home['data']['team_id']}::{away['data']['team_id']}"
        latest = self.store.get_latest_snapshot("odds", match_id)
        if latest["ok"]:
            # stale fallback
            latest["meta"] = {"mock": False, "source": "snapshot", "confidence": latest["data"]["meta"]["confidence"], "stale": True}
            return {"ok": True, "data": latest["data"]["payload"], "error": None, "meta": latest["meta"]}

        return {"ok": False, "data": None, "error": {"code": "NOT_FOUND", "message": "no odds snapshot and providers not enabled"}, "meta": {"mock": False, "source": "multisource", "confidence": 0.0, "stale": True}}
```

- [ ] **Step 4: Run test to verify it passes**
Run: `PYTHONPATH=. python3 tests/test_multisource_fetcher_fallback.py`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add tools/multisource_fetcher.py tests/test_multisource_fetcher_fallback.py
git commit -m "feat(p2): add multisource fetcher skeleton with snapshot fallback"
```

---

### Task 4: Integrate into AnalyzerAPI (get_live_* becomes multi-source)

**Files:**
- Modify: `tools/analyzer_api.py`
- Test: `tests/test_analyzer_api_multisource.py`

- [ ] **Step 1: Add MultiSourceFetcher usage for live endpoints**
Implement:
- `AnalyzerAPI.get_live_odds(home_team, away_team)` -> `await fetcher.fetch_odds(...)` (or sync wrapper)
- `AnalyzerAPI.get_live_injuries(team_name)` -> `await fetcher.fetch_injuries(...)` (stub for now)
- `AnalyzerAPI.get_live_news(team_name)` -> `await fetcher.fetch_news(...)` (stub for now)

Keep existing HTTP API as fallback provider.

- [ ] **Step 2: Write a minimal test**
Test that calling `AnalyzerAPI.get_live_odds(...)` returns the standard protocol even when API server is down.

- [ ] **Step 3: Commit**
`git commit -am "refactor(p2): route AnalyzerAPI live endpoints through multisource fetcher"`

---

### Task 5: Expose new real-data tools via SSOT Tool Registry

**Files:**
- Modify: `tools/tool_registry_v2.py`
- Modify: `tools/mcp_tools.py`
- Test: `tests/test_tool_registry.py` (extend)

- [ ] **Step 1: Add tools**
- `get_live_odds(home_team, away_team)`
- `get_live_injuries(team_name)`
- `get_today_fixtures(date, lottery_type)`
- `get_match_result(match_id)`
- `search_news(query)`

Each tool must:
- return `{ok,data,error,meta}`
- store snapshots on success
- return `CAPTCHA_REQUIRED` when a provider requires manual verification

- [ ] **Step 2: Update tests**
Verify invalid args -> `VALIDATION_ERROR`.

- [ ] **Step 3: Commit**
`git commit -am "feat(p2): expose real-data tools in SSOT registry"`

---

### Task 6: CLV/Result Backfill (Scores provider + ledger link)

**Files:**
- Modify: `tools/betting_ledger.py`
- Create: `tools/clv_calculator.py`
- Test: `tests/test_clv_calculator.py`

- [ ] **Step 1: Implement `record_closing_odds(match_id, closing_odds)` and `record_result(match_id, result, pnl)`**
- [ ] **Step 2: Implement CLV metric**
CLV example:
`clv = log(closing_odds / placed_odds)` per bet.

- [ ] **Step 3: Commit**
`git commit -am "feat(p2): add CLV calculation and result backfill"`

---

## Execution Handoff
Plan complete and saved to:
- `docs/superpowers/specs/2026-04-14-p2-data-fabric-design.md`
- `docs/superpowers/plans/2026-04-14-p2-data-fabric-plan.md`

Two execution options:
1) **Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks
2) **Inline Execution** - Execute tasks in this session using executing-plans

Which approach?

