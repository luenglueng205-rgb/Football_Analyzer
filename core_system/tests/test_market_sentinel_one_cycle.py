from __future__ import annotations

from pathlib import Path
import pytest

try:
    from market_sentinel import MarketSentinel
except ImportError:
    pytest.importorskip("market_sentinel", reason="market_sentinel 模块不存在（见 docs/superpowers/plans/ 待实现）")
from tools.multisource_fetcher import MultiSourceFetcher
from tools.snapshot_store import SnapshotStore


def _load_fixture(name: str) -> str:
    here = Path(__file__).resolve().parent
    p = here / "fixtures" / name
    return p.read_text(encoding="utf-8")


def test_market_sentinel_one_cycle_persists_snapshots_and_reports(monkeypatch, tmp_path):
    fixtures_html = _load_fixture("500_trade_2026-04-15.html")
    results_trade_html = _load_fixture("500_trade_results_2026-04-15.html")
    live_html = _load_fixture("500_live_detail_1234567890.html")

    def fake_fetch_odds_sync(home_team: str, away_team: str):
        return {
            "ok": True,
            "data": {"eu_odds": {"home": 2.1, "draw": 3.4, "away": 3.2}},
            "error": None,
            "meta": {"mock": True, "source": "offline", "confidence": 0.88, "stale": False},
        }

    db_path = str(tmp_path / "snapshots.db")
    store = SnapshotStore(db_path=db_path)
    fetcher = MultiSourceFetcher(store=store)

    from tools.domestic_500_fixtures import parse_500_trade_fixtures_html
    from tools.domestic_500_live_state import parse_500_live_detail_html
    from tools.domestic_500_results import parse_500_trade_results_html

    parsed_fixtures = parse_500_trade_fixtures_html(html=fixtures_html, date="2026-04-15")
    parsed_results = parse_500_trade_results_html(html=results_trade_html, date="2026-04-15")
    live_parsed = parse_500_live_detail_html(html=live_html)
    live_data = live_parsed.get("data") if isinstance(live_parsed, dict) else None
    minute = int((live_data or {}).get("minute") or 76)
    ft_score = str((live_data or {}).get("ft_score") or "1-0")
    red_cards = (live_data or {}).get("red_cards") if isinstance(live_data, dict) else {"home": 0, "away": 0}
    if not isinstance(red_cards, dict):
        red_cards = {"home": 0, "away": 0}

    monkeypatch.setattr(
        fetcher,
        "fetch_fixtures_sync",
        lambda date=None: {
            "ok": True,
            "data": {"fixtures": parsed_fixtures},
            "error": None,
            "meta": {"mock": True, "source": "offline", "confidence": 0.9, "stale": False},
        },
    )
    monkeypatch.setattr(
        fetcher,
        "fetch_results_sync",
        lambda date: {
            "ok": True,
            "data": {"results": parsed_results},
            "error": None,
            "meta": {"mock": True, "source": "offline", "confidence": 0.88, "stale": False},
        },
    )
    monkeypatch.setattr(
        fetcher.domestic,
        "get_live_state",
        lambda match: {
            "ok": True,
            "data": {"minute": minute, "ft_score": ft_score, "red_cards": red_cards},
            "error": None,
            "meta": {"mock": True, "source": "live.500.com", "confidence": 0.9, "stale": False},
        },
    )

    monkeypatch.setattr(fetcher, "fetch_odds_sync", fake_fetch_odds_sync)

    reports_dir = tmp_path / "reports"
    snapshots_dir = tmp_path / "snapshots"
    sentinel = MarketSentinel(
        store=store,
        fetcher=fetcher,
        reports_dir=str(reports_dir),
        snapshots_dir=str(snapshots_dir),
        pre_match_interval_s=1,
        in_play_interval_s=1,
        post_match_interval_s=1,
    )

    out = sentinel.run_one_cycle(date="2026-04-15", match_id="20260415_E0_ARS_TOT")
    assert out["ok"] is True, out
    assert out["match_id"] == "20260415_E0_ARS_TOT"

    snap = Path(out["snapshot_path"])
    rep = Path(out["report_path"])
    assert snap.exists()
    assert rep.exists()

    latest = store.get_latest_snapshot("mentor_workflow", "20260415_E0_ARS_TOT")
    assert latest["ok"] is True
    payload = latest["data"]["payload"]
    assert payload["selected_match"]["match_id"] == "20260415_E0_ARS_TOT"
    assert isinstance(payload["workflow"], dict)
