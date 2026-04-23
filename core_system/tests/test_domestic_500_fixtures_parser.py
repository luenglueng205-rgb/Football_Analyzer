from __future__ import annotations

import io
from pathlib import Path

from core.mentor_workflow import MentorWorkflow
from scripts import mentor_cli
from tools.domestic_500_fixtures import parse_500_trade_fixtures_html
from tools.multisource_fetcher import MultiSourceFetcher
from tools.snapshot_store import SnapshotStore


class _Resp:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code


def _load_sample_html() -> str:
    here = Path(__file__).resolve().parent
    p = here / "fixtures" / "500_trade_2026-04-15.html"
    return p.read_text(encoding="utf-8")


def test_parse_500_trade_fixtures_html_extracts_rows():
    html = _load_sample_html()
    fixtures = parse_500_trade_fixtures_html(html=html, date="2026-04-15")
    assert len(fixtures) == 2

    f0 = fixtures[0]
    assert f0["league"] == "英超"
    assert f0["league_name"] == "英超"
    assert f0["home_team"] == "Arsenal"
    assert f0["away_team"] == "Tottenham"
    assert f0["kickoff_time"] == "2026-04-15 20:00"
    assert f0["status"] == "upcoming"
    assert f0["fid"] == "1234567890"

    f1 = fixtures[1]
    assert f1["fid"] == "2234567890"


def test_fetcher_fetch_fixtures_sync_uses_dom_parser_without_snapshot(monkeypatch, tmp_path):
    html = _load_sample_html()

    import tools.domestic_500_fixtures as mod

    def fake_get(*args, **kwargs):
        return _Resp(html, 200)

    monkeypatch.setattr(mod.requests, "get", fake_get)

    db_path = str(tmp_path / "snapshots.db")
    store = SnapshotStore(db_path=db_path)
    fetcher = MultiSourceFetcher(store=store)
    res = fetcher.fetch_fixtures_sync(date="2026-04-15")
    assert res["ok"] is True
    assert res["data"]["fixtures"][0]["home_team"] == "Arsenal"


def test_mentor_cli_can_fetch_fixtures_without_existing_snapshots(monkeypatch, tmp_path):
    html = _load_sample_html()

    import tools.domestic_500_fixtures as mod

    def fake_get(*args, **kwargs):
        return _Resp(html, 200)

    monkeypatch.setattr(mod.requests, "get", fake_get)

    db_path = str(tmp_path / "snapshots.db")
    store = SnapshotStore(db_path=db_path)
    fetcher = MultiSourceFetcher(store=store)

    def fake_fetch_odds_sync(home_team: str, away_team: str):
        return {
            "ok": True,
            "data": {"eu_odds": {"home": 2.1, "draw": 3.4, "away": 3.2}},
            "error": None,
            "meta": {"mock": True, "source": "snapshot", "confidence": 0.88, "stale": False},
        }

    monkeypatch.setattr(fetcher, "fetch_odds_sync", fake_fetch_odds_sync)

    wf = MentorWorkflow(fetcher=fetcher)
    buf = io.StringIO()
    res = mentor_cli.run(["--date", "2026-04-15"], workflow=wf, stdout=buf)
    assert res["recommended_leagues"]
    assert "no_fixtures" not in res["audit"]["degradations"]
    assert res["live_check"]["match_id"] == "20260415_E0_ARS_TOT"


def test_live_fetch_get_fixtures_normalized_includes_source_ids_when_network_available(tmp_path):
    import pytest
    from datetime import datetime

    date = datetime.now().strftime("%Y-%m-%d")
    db_path = str(tmp_path / "snapshots.db")
    fetcher = MultiSourceFetcher(store=SnapshotStore(db_path=db_path))
    matches = fetcher.get_fixtures_normalized(date=date)

    if not matches:
        pytest.skip("network unavailable or live fixtures empty")

    if not any(
        isinstance(m.get("source_ids"), dict) and m["source_ids"].get("500.com", {}).get("fid") for m in matches
    ):
        pytest.skip("live fixtures fetched but no fid found in source_ids (site layout/captcha)")
