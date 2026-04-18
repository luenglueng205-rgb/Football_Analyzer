from core.beidan_workflow import BeidanWorkflow
from tools.multisource_fetcher import MultiSourceFetcher
from tools.snapshot_store import SnapshotStore


def test_beidan_workflow_outputs_recommendation_ticket_and_historical_impact(monkeypatch, tmp_path):
    store = SnapshotStore(db_path=str(tmp_path / "snapshots.db"))
    fetcher = MultiSourceFetcher(store=store)

    monkeypatch.setattr(
        fetcher,
        "fetch_fixtures_sync",
        lambda date=None: {
            "ok": True,
            "data": {
                "fixtures": [
                    {
                        "league": "英超",
                        "home_team": "Arsenal",
                        "away_team": "Tottenham",
                        "kickoff_time": "2026-04-15 20:00",
                    }
                ]
            },
            "error": None,
            "meta": {"mock": True, "source": "test", "confidence": 0.9, "stale": False},
        },
    )
    monkeypatch.setattr(
        fetcher,
        "fetch_odds_sync",
        lambda home_team, away_team: {
            "ok": True,
            "data": {"beidan_sp": {"WDL": {"home": 2.4, "draw": 3.2, "away": 2.9, "handicap": 0}}},
            "error": None,
            "meta": {"mock": True, "source": "test", "confidence": 0.9, "stale": False},
        },
    )
    monkeypatch.setattr(fetcher, "get_results_normalized", lambda date: [])

    wf = BeidanWorkflow(fetcher=fetcher)
    out = wf.run(date="2026-04-15", stake=100.0, auto_trade=False)
    assert out["recommended_bets"]
    assert out["recommended_bets"][0]["lottery_type"] == "BEIDAN"
    assert out["ticket"] is not None
    assert "historical_impact" in out
    assert any(x.get("type") == "historical_impact" for x in (out["audit"].get("explain") or []))

