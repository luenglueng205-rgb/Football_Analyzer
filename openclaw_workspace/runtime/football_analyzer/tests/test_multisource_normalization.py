from tools.multisource_fetcher import MultiSourceFetcher
from tools.snapshot_store import SnapshotStore


def test_multisource_fixtures_normalized_schema(monkeypatch, tmp_path):
    db_path = str(tmp_path / "snapshots.db")
    f = MultiSourceFetcher(store=SnapshotStore(db_path=db_path))

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

    monkeypatch.setattr(f, "fetch_fixtures_sync", fake_fetch_fixtures_sync)

    matches = f.get_fixtures_normalized(date="2026-04-15")
    assert isinstance(matches, list)
    assert matches[0]["match_id"] == "20260415_E0_ARS_TOT"
    assert matches[0]["source"] == "500.com"
    assert matches[0]["confidence"] == 0.9
    assert "raw_ref" in matches[0]
    assert matches[0]["source_ids"] == {}


def test_multisource_odds_normalized_schema(monkeypatch, tmp_path):
    db_path = str(tmp_path / "snapshots.db")
    f = MultiSourceFetcher(store=SnapshotStore(db_path=db_path))

    def fake_fetch_odds_sync(home_team: str, away_team: str):
        return {
            "ok": True,
            "data": {"eu_odds": {"home": 2.1, "draw": 3.4, "away": 3.2}},
            "error": None,
            "meta": {"mock": True, "source": "snapshot", "confidence": 0.88, "stale": False},
        }

    monkeypatch.setattr(f, "fetch_odds_sync", fake_fetch_odds_sync)

    odds = f.get_odds_normalized(
        league_name="Premier League",
        home_team="阿森纳",
        away_team="热刺",
        kickoff_time="2026-04-15 20:00",
    )
    assert odds["ok"] is True
    assert odds["match_id"] == "20260415_E0_ARS_TOT"
    assert odds["market"] == "WDL"
    assert odds["source"] == "snapshot"
    assert odds["confidence"] == 0.88
    assert "H" in odds["selections"] and "D" in odds["selections"] and "A" in odds["selections"]
    assert "raw_ref" in odds
