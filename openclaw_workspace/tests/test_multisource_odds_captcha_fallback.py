from tools.multisource_fetcher import MultiSourceFetcher
from tools.snapshot_store import SnapshotStore
from core.mentor_workflow import MentorWorkflow


def test_odds_captcha_falls_back_to_foreign_eu_odds(monkeypatch, tmp_path):
    db_path = str(tmp_path / "snapshots.db")
    fetcher = MultiSourceFetcher(store=SnapshotStore(db_path=db_path))

    def fake_domestic_sp(*, home_team: str, away_team: str, kickoff_time=None, fid=None):
        return {
            "ok": False,
            "data": None,
            "error": {"code": "CAPTCHA_REQUIRED", "message": "domestic blocked"},
            "meta": {"mock": True, "source": "500.com", "confidence": 0.0, "stale": True},
        }

    def fake_foreign_odds(home_team: str, away_team: str):
        return {
            "ok": True,
            "data": {"eu_odds": {"home": 2.2, "draw": 3.3, "away": 3.1}},
            "error": None,
            "meta": {"mock": True, "source": "the_odds_api", "confidence": 0.95, "stale": False},
        }

    monkeypatch.setattr(fetcher.domestic, "get_jingcai_sp", fake_domestic_sp)
    monkeypatch.setattr(fetcher.foreign_api, "get_odds", fake_foreign_odds)

    odds = fetcher.get_odds_normalized(
        league_name="英超",
        home_team="Arsenal",
        away_team="Tottenham",
        kickoff_time="2026-04-15 20:00",
        lottery_type="JINGCAI",
        play_type="JINGCAI_WDL",
        market="WDL",
    )
    assert odds["ok"] is True
    assert "H" in odds["selections"] and "D" in odds["selections"] and "A" in odds["selections"]
    assert float(odds["selections"]["H"]["odds"]) == 2.2
    assert float(odds["confidence"]) <= 0.4
    assert any("captcha_required" in str(x) for x in odds.get("degradations") or [])


def test_mentor_workflow_audit_records_captcha_degradation(monkeypatch, tmp_path):
    db_path = str(tmp_path / "snapshots.db")
    fetcher = MultiSourceFetcher(store=SnapshotStore(db_path=db_path))

    def fake_fetch_fixtures_sync(date=None):
        return {
            "ok": True,
            "data": {
                "fixtures": [
                    {
                        "league": "英超",
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

    def fake_domestic_sp(*, home_team: str, away_team: str, kickoff_time=None, fid=None):
        return {
            "ok": False,
            "data": None,
            "error": {"code": "CAPTCHA_REQUIRED", "message": "domestic blocked"},
            "meta": {"mock": True, "source": "500.com", "confidence": 0.0, "stale": True},
        }

    def fake_foreign_odds(home_team: str, away_team: str):
        return {
            "ok": True,
            "data": {"eu_odds": {"home": 2.2, "draw": 3.3, "away": 3.1}},
            "error": None,
            "meta": {"mock": True, "source": "the_odds_api", "confidence": 0.95, "stale": False},
        }

    def fake_get_results_normalized(date: str):
        return [
            {
                "match_id": "20260415_E0_ARS_TOT",
                "status": "FINISHED",
                "score_ft": "2-1",
                "source": "500.com",
                "confidence": 0.9,
                "raw_ref": "snapshot:results:500.com:test",
                "source_ids": {},
                "league": "英超",
                "kickoff_time": "2026-04-15 20:00",
                "home_team": "Arsenal",
                "away_team": "Tottenham",
            }
        ]

    monkeypatch.setattr(fetcher, "fetch_fixtures_sync", fake_fetch_fixtures_sync)
    monkeypatch.setattr(fetcher.domestic, "get_jingcai_sp", fake_domestic_sp)
    monkeypatch.setattr(fetcher.foreign_api, "get_odds", fake_foreign_odds)
    monkeypatch.setattr(fetcher, "get_results_normalized", fake_get_results_normalized)

    wf = MentorWorkflow(fetcher=fetcher)
    res = wf.run(date="2026-04-15")
    assert any("captcha_required" in str(x) for x in (res.get("audit") or {}).get("degradations") or [])

