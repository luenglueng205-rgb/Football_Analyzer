import pytest

from core.zucai_workflow import ZucaiWorkflow
from tools.multisource_fetcher import MultiSourceFetcher
from tools.snapshot_store import SnapshotStore


class _DummyDB:
    def __init__(self, draw_rate: float = 0.25):
        self.draw_rate = draw_rate

    def get_league_stats(self, league_code: str):
        return {
            "avg_goals": 2.6,
            "home_win_rate": 0.46,
            "draw_rate": self.draw_rate,
            "away_win_rate": 0.28,
            "over_2_5_rate": 0.51,
            "btts_rate": 0.47,
            "sample_size": 1200,
        }


def _fixtures(n: int = 14):
    out = []
    for i in range(n):
        out.append(
            {
                "match_id": f"M{i}",
                "league_code": "E0",
                "home_team": f"H{i}",
                "away_team": f"A{i}",
                "kickoff_time_utc": "2026-04-15 20:00",
                "confidence": 0.9,
                "raw_ref": f"fixture_ref:{i}",
            }
        )
    return out


def _results(n: int = 14, *, ft_score: str = "1-0"):
    out = []
    for i in range(n):
        out.append({"match_id": f"M{i}", "status": "FINISHED", "score_ft": ft_score, "raw_ref": f"result_ref:{i}", "source": "test"})
    return out


def test_zucai_workflow_14_match_outputs_ticket_and_historical_impact(monkeypatch, tmp_path):
    store = SnapshotStore(db_path=str(tmp_path / "snapshots.db"))
    fetcher = MultiSourceFetcher(store=store)
    monkeypatch.setattr(fetcher, "get_fixtures_normalized", lambda date=None: _fixtures(14))
    monkeypatch.setattr(fetcher, "get_results_normalized", lambda date=None: _results(14, ft_score="1-0"))

    import core.zucai_workflow as mod

    monkeypatch.setattr(mod, "get_historical_database", lambda lazy_load=True: _DummyDB(draw_rate=0.25))

    wf = ZucaiWorkflow(fetcher=fetcher)
    out = wf.run(date="2026-04-15", stake=100.0, play_type="14_match")

    assert len(out["recommended_bets"]) == 14
    assert all(b["lottery_type"] == "ZUCAI" for b in out["recommended_bets"])
    assert out["ticket"] is not None
    assert out["ticket"]["ticket"]["lottery_type"] == "ZUCAI"
    assert out["ticket"]["ticket"]["play_type"] == "14_match"
    assert len(out["ticket"]["ticket"]["legs"]) == 14
    assert all(("odds" not in leg) or (leg["odds"] is None) for leg in out["ticket"]["ticket"]["legs"])
    assert out["ticket"]["validation"]["router"]["status"] in {"SUCCESS", "VALIDATED"}

    assert "historical_impact" in out
    assert "similar_odds_not_applicable:zucai_no_fixed_odds" in (out["historical_impact"].get("degradations") or [])
    assert any(x.get("type") == "historical_impact" for x in (out["audit"].get("explain") or []))


def test_zucai_workflow_renjiu_limits_to_9_legs(monkeypatch, tmp_path):
    store = SnapshotStore(db_path=str(tmp_path / "snapshots.db"))
    fetcher = MultiSourceFetcher(store=store)
    monkeypatch.setattr(fetcher, "get_fixtures_normalized", lambda date=None: _fixtures(14))
    monkeypatch.setattr(fetcher, "get_results_normalized", lambda date=None: _results(14, ft_score="0-0"))

    import core.zucai_workflow as mod

    monkeypatch.setattr(mod, "get_historical_database", lambda lazy_load=True: _DummyDB(draw_rate=0.35))

    wf = ZucaiWorkflow(fetcher=fetcher)
    out = wf.run(date="2026-04-15", stake=100.0, play_type="renjiu")

    assert len(out["recommended_bets"]) == 9
    assert out["ticket"] is not None
    assert out["ticket"]["ticket"]["play_type"] == "renjiu"
    assert len(out["ticket"]["ticket"]["legs"]) == 9

