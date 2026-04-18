from __future__ import annotations

from pathlib import Path

from tools.multisource_fetcher import MultiSourceFetcher
from tools.snapshot_store import SnapshotStore


class _Resp:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code
        self.encoding = "utf-8"
        self.apparent_encoding = "utf-8"


def _load_fixture(name: str) -> str:
    here = Path(__file__).resolve().parent
    return (here / "fixtures" / name).read_text(encoding="utf-8")


def test_parse_500_trade_results_html_extracts_finished_scores():
    from tools.domestic_500_results import parse_500_trade_results_html

    html = _load_fixture("500_trade_results_2026-04-15.html")
    results = parse_500_trade_results_html(html=html, date="2026-04-15")
    assert len(results) == 2
    r0 = results[0]
    assert r0["league"] == "英超"
    assert r0["league_name"] == "英超"
    assert r0["home_team"] == "Arsenal"
    assert r0["away_team"] == "Tottenham"
    assert r0["kickoff_time"] == "2026-04-15 20:00"
    assert r0["status"] == "FINISHED"
    assert r0["score_ft"] == "2-1"
    assert r0["score_ht"] == "0-1"
    assert r0["fid"] == "1234567890"


def test_parse_500_zx_results_html_extracts_finished_scores():
    from tools.domestic_500_results import parse_500_zx_results_html

    html = _load_fixture("500_zx_results_2026-04-15.html")
    results = parse_500_zx_results_html(html=html, date="2026-04-15")
    assert len(results) == 1
    r0 = results[0]
    assert r0["home_team"] == "Arsenal"
    assert r0["away_team"] == "Tottenham"
    assert r0["score_ft"] == "2-1"


def test_fetcher_get_results_normalized_prefers_trade_first(monkeypatch, tmp_path):
    trade_html = _load_fixture("500_trade_results_2026-04-15.html")

    import tools.domestic_500_results as mod

    def fake_get(url: str, *args, **kwargs):
        if "trade.500.com/jczq" in url:
            return _Resp(trade_html, 200)
        raise RuntimeError("unexpected url in test")

    monkeypatch.setattr(mod.requests, "get", fake_get)

    db_path = str(tmp_path / "snapshots.db")
    fetcher = MultiSourceFetcher(store=SnapshotStore(db_path=db_path))
    results = fetcher.get_results_normalized(date="2026-04-15")
    assert results
    assert results[0]["match_id"] == "20260415_E0_ARS_TOT"
    assert results[0]["score_ft"] == "2-1"
    assert results[0]["source"] == "trade.500.com"
    assert results[0]["source_ids"]["500.com"]["fid"] == "1234567890"
    assert "raw_ref" in results[0]

    def should_not_call(*args, **kwargs):
        raise AssertionError("network should not be called when results snapshot exists")

    monkeypatch.setattr(mod.requests, "get", should_not_call)
    results2 = fetcher.get_results_normalized(date="2026-04-15")
    assert results2 and results2[0]["match_id"] == "20260415_E0_ARS_TOT"


def test_fetcher_get_results_normalized_falls_back_to_zx(monkeypatch, tmp_path):
    upcoming_trade_html = _load_fixture("500_trade_2026-04-15.html")
    zx_html = _load_fixture("500_zx_results_2026-04-15.html")

    import tools.domestic_500_results as mod

    def fake_get(url: str, *args, **kwargs):
        if "trade.500.com/jczq" in url:
            return _Resp(upcoming_trade_html, 200)
        if "zx.500.com/jczq" in url:
            return _Resp(zx_html, 200)
        raise RuntimeError("unexpected url in test")

    monkeypatch.setattr(mod.requests, "get", fake_get)

    db_path = str(tmp_path / "snapshots.db")
    fetcher = MultiSourceFetcher(store=SnapshotStore(db_path=db_path))
    results = fetcher.get_results_normalized(date="2026-04-15")
    assert results
    assert results[0]["match_id"] == "20260415_E0_ARS_TOT"
    assert results[0]["source"] == "zx.500.com"
