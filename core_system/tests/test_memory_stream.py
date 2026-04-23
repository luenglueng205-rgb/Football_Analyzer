from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path
from typing import List

import pytest

from core.mentor_workflow import MentorWorkflow
from tools.memory_manager import MemoryManager
from tools.memory_retriever import MemoryRetriever
from tools.memory_writer import MemoryWriter
from tools.multisource_fetcher import MultiSourceFetcher
from tools.odds_analyzer import OddsAnalyzer
from tools.snapshot_store import SnapshotStore


class FakeEmbeddingFunction:
    def __call__(self, texts: List[str]):
        vectors = []
        for text in texts:
            h = 0
            for ch in str(text):
                h = (h * 131 + ord(ch)) % 1_000_003
            vectors.append([((h >> (i * 8)) & 0xFF) / 255.0 for i in range(8)])
        return vectors


@pytest.fixture()
def isolated_data_dir(monkeypatch):
    standalone_root = Path(__file__).resolve().parents[1]
    base = standalone_root / "data" / f"tmp_test_memory_{uuid.uuid4().hex}"
    base.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("STANDALONE_FOOTBALL_DATA_DIR", str(base))
    yield base
    shutil.rmtree(base, ignore_errors=True)


def test_memory_writer_and_retriever_roundtrip(isolated_data_dir):
    manager = MemoryManager(db_path=str(isolated_data_dir / "chroma_db"), embedding_function=FakeEmbeddingFunction())
    writer = MemoryWriter(manager=manager)
    retriever = MemoryRetriever(manager=manager)

    writer.write_match_summary(
        match_id="M1",
        league_code="E0",
        stage="post_match",
        summary="E0 复盘：强队主场降水诱上，最终2-1打穿。",
        tags=["E0", "post_match", "odds_move"],
        metadata={"importance": 0.8},
    )
    writer.write_match_summary(
        match_id="M_D1",
        league_code="D1",
        stage="post_match",
        summary="D1 复盘：节奏慢，小球。",
        tags=["D1", "post_match"],
    )

    match = {
        "match_id": "M2",
        "league_code": "E0",
        "home_team": "Arsenal",
        "away_team": "Tottenham",
        "kickoff_time": "2099-01-01 20:00",
    }
    out = retriever.retrieve_for_match(match=match, top_k=5)
    assert out["ok"] is True
    assert any(m.get("match_id") == "M1" for m in out["data"])
    assert all(m.get("league_code") == "E0" for m in out["data"])


def test_odds_analyzer_schema_includes_memory_explain():
    analyzer = OddsAnalyzer(use_historical=False)
    memories = [{"doc_id": "x1", "summary": "历史复盘：临场降赔多为真实看好。", "league_code": "E0", "stage": "post_match"}]
    out = analyzer.analyze({"home": 2.0, "draw": 3.4, "away": 3.8}, league="E0", calibrate=False, memories=memories)
    schema = out["recommendation_schema"]
    assert "audit" in schema
    assert "explain" in schema["audit"]
    assert schema["audit"]["explain"]
    assert schema["audit"]["explain"][0]["type"] == "memory"


def test_mentor_workflow_writes_and_reads_memories(monkeypatch, isolated_data_dir, tmp_path):
    store = SnapshotStore(db_path=str(tmp_path / "snapshots.db"))
    fetcher = MultiSourceFetcher(store=store)

    def fake_fetch_fixtures_sync(date=None):
        return {
            "ok": True,
            "data": {
                "fixtures": [
                    {
                        "league": "英超",
                        "league_code": "E0",
                        "home_team": "Arsenal",
                        "away_team": "Tottenham",
                        "kickoff_time": "2026-04-15 20:00",
                        "status": "upcoming",
                    }
                ]
            },
            "error": None,
            "meta": {"mock": True, "source": "500.com", "confidence": 0.9, "stale": False},
        }

    def fake_fetch_odds_sync(home_team: str, away_team: str):
        return {
            "ok": True,
            "data": {"eu_odds": {"home": 2.1, "draw": 3.4, "away": 3.2}},
            "error": None,
            "meta": {"mock": True, "source": "snapshot", "confidence": 0.88, "stale": False},
        }

    monkeypatch.setattr(fetcher, "fetch_fixtures_sync", fake_fetch_fixtures_sync)
    monkeypatch.setattr(fetcher, "fetch_odds_sync", fake_fetch_odds_sync)

    store.insert_snapshot(
        category="results",
        match_id="RESULTS::2026-04-15",
        source="500.com",
        payload={
            "results": [
                {
                    "match_id": "20260415_E0_ARS_TOT",
                    "status": "FINISHED",
                    "score_ht": "0-1",
                    "score_ft": "2-1",
                    "source": "500.com",
                    "confidence": 0.9,
                    "raw_ref": "snapshot:results:500.com:test",
                }
            ]
        },
        confidence=0.9,
        stale=False,
    )

    manager = MemoryManager(db_path=str(isolated_data_dir / "chroma_db"), embedding_function=FakeEmbeddingFunction())
    wf = MentorWorkflow(fetcher=fetcher, memory_manager=manager)
    res = wf.run(date="2026-04-15")

    mem = res["post_match_review"]["memory_injection"]
    assert mem["pre_match"]["ok"] is True
    assert mem["pre_match"].get("stored", {}).get("ok") is True
    assert mem["post_match"].get("ok") is True

    docs = manager.collection.get(where={"type": {"$eq": "match_summary"}})
    assert docs.get("ids")
    assert any("pre_match" in (m.get("stage") or "") for m in docs.get("metadatas") or [])
    assert any("post_match" in (m.get("stage") or "") for m in docs.get("metadatas") or [])

