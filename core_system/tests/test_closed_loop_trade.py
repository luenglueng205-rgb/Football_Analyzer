from __future__ import annotations

import io
import sqlite3
from pathlib import Path

from core.beidan_workflow import BeidanWorkflow
from core.mentor_workflow import MentorWorkflow
from core.zucai_workflow import ZucaiWorkflow
from scripts import mentor_cli
from tools.betting_ledger import BettingLedger
from tools.live_match_monitor import LiveMatchMonitor
from tools.memory_manager import MemoryManager
from tools.multisource_fetcher import MultiSourceFetcher
from tools.odds_analyzer import OddsAnalyzer
from tools.simulated_execution_engine import SimulatedExecutionEngine
from tools.snapshot_store import SnapshotStore


def test_closed_loop_trade_build_execute_settle_offline(monkeypatch, tmp_path):
    here = Path(__file__).resolve().parent
    fixtures_html = (here / "fixtures" / "500_trade_2026-04-15.html").read_text(encoding="utf-8")
    sp_html = (here / "fixtures" / "500_trade_jczq_sp_2026-04-15.html").read_text(encoding="utf-8")
    live_html = (here / "fixtures" / "500_live_detail_1234567890.html").read_text(encoding="utf-8")
    results_html = (here / "fixtures" / "500_trade_results_2026-04-15.html").read_text(encoding="utf-8")

    import tools.domestic_500_jczq_sp as sp_mod
    import tools.domestic_500_live_state as live_mod
    import tools.domestic_500_results as results_mod
    import tools.domestic_sources as src_mod

    monkeypatch.setattr(src_mod, "fetch_500_trade_html", lambda date=None, timeout_s=3.0: fixtures_html)
    monkeypatch.setattr(
        sp_mod,
        "fetch_500_jczq_trade_html",
        lambda date=None, timeout_s=4.0: {"ok": True, "html": sp_html, "url": "https://trade.500.com/jczq/", "error": None},
    )
    monkeypatch.setattr(
        live_mod,
        "fetch_500_live_detail_html",
        lambda fid, timeout_s=4.0: {"ok": True, "html": live_html, "url": f"https://live.500.com/detail.php?fid={fid}", "error": None},
    )
    monkeypatch.setattr(
        results_mod,
        "fetch_500_trade_results_html",
        lambda date=None, timeout_s=4.0: {"ok": True, "html": results_html, "url": "https://trade.500.com/jczq/", "error": None},
    )

    store = SnapshotStore(db_path=str(tmp_path / "snapshots.db"))
    fetcher = MultiSourceFetcher(store=store)

    ledger = BettingLedger(db_path=str(tmp_path / "ledger.db"))
    monitor = LiveMatchMonitor()
    engine = SimulatedExecutionEngine(ledger=ledger, live_monitor=monitor)
    wf = MentorWorkflow(fetcher=fetcher, live_monitor=monitor, ledger=ledger, execution_engine=engine)

    buf = io.StringIO()
    res = mentor_cli.run(["--date", "2026-04-15", "--auto-trade"], workflow=wf, stdout=buf)

    assert isinstance(res, dict)
    assert isinstance(res.get("ticket"), dict)
    ticket = res["ticket"]["ticket"]
    assert isinstance(ticket, dict) and ticket.get("ticket_id")
    assert isinstance(ticket.get("legs"), list) and ticket["legs"]

    assert isinstance(res.get("execution"), dict)
    assert res["execution"]["ok"] is True
    assert res["execution"]["ledger"]["status"] == "success"

    match_id = str(ticket["legs"][0]["match_id"])
    assert match_id in monitor.active_bets

    conn = sqlite3.connect(str(tmp_path / "ledger.db"))
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*), SUM(CASE WHEN pnl IS NULL THEN 1 ELSE 0 END) FROM bets")
    total, pnl_null = cur.fetchone()
    cur.execute("SELECT pnl FROM bets WHERE match_id=? ORDER BY id DESC LIMIT 1", (ticket["ticket_id"],))
    pnl_row = cur.fetchone()
    conn.close()

    assert int(total) == 1
    assert int(pnl_null) == 0
    assert pnl_row is not None
    assert abs(float(pnl_row[0]) - float(res["post_match_review"]["pnl"])) < 1e-9


def test_closed_loop_trade_beidan_offline_mentor_cli(monkeypatch, tmp_path):
    store = SnapshotStore(db_path=str(tmp_path / "snapshots.db"))
    fetcher = MultiSourceFetcher(store=store)

    monkeypatch.setattr(
        fetcher,
        "fetch_fixtures_sync",
        lambda date=None: {
            "ok": True,
            "data": {"fixtures": [{"league": "英超", "home_team": "Arsenal", "away_team": "Tottenham", "kickoff_time": "2026-04-15 20:00"}]},
            "error": None,
            "meta": {"mock": True, "source": "test", "confidence": 0.9, "stale": False},
        },
    )
    monkeypatch.setattr(
        fetcher,
        "fetch_odds_sync",
        lambda home_team, away_team: {
            "ok": True,
            "data": {"beidan_sp": {"WDL": {"home": 1.5, "draw": 4.0, "away": 6.0, "handicap": 0}}},
            "error": None,
            "meta": {"mock": True, "source": "test", "confidence": 0.9, "stale": False},
        },
    )

    match_id = fetcher.identity.build("英超", "Arsenal", "Tottenham", "2026-04-15 20:00")
    monkeypatch.setattr(
        fetcher,
        "get_results_normalized",
        lambda date: [{"match_id": match_id, "status": "FINISHED", "score_ft": "1-0", "source": "test", "raw_ref": "snapshot:results:test:1"}],
    )
    monkeypatch.setattr(
        fetcher,
        "get_live_state_normalized",
        lambda **kwargs: {"ok": True, "match_id": match_id, "minute": 76, "score_ft": "1-0", "red_cards": {"home": 0, "away": 0}, "source": "test", "confidence": 0.7, "raw_ref": "snapshot:live:test:1"},
    )

    ledger = BettingLedger(db_path=str(tmp_path / "ledger.db"))
    monitor = LiveMatchMonitor()
    engine = SimulatedExecutionEngine(ledger=ledger, live_monitor=monitor)
    wf = BeidanWorkflow(
        fetcher=fetcher,
        live_monitor=monitor,
        ledger=ledger,
        execution_engine=engine,
        odds_analyzer=OddsAnalyzer(use_historical=False),
        memory_manager=MemoryManager(db_path=str(tmp_path / "chroma_db")),
    )

    buf = io.StringIO()
    res = mentor_cli.run(["--date", "2026-04-15", "--lottery-type", "BEIDAN", "--auto-trade"], workflow=wf, stdout=buf)

    assert isinstance(res.get("historical_impact"), dict)
    assert any(isinstance(x, dict) and x.get("type") == "historical_impact" for x in (res.get("audit") or {}).get("explain") or [])

    assert isinstance(res.get("ticket"), dict)
    assert isinstance(res["ticket"].get("validation"), dict)
    assert (res["ticket"]["validation"].get("router") or {}).get("status") in {"SUCCESS", "VALIDATED"}

    assert isinstance(res.get("execution"), dict)
    assert res["execution"]["ok"] is True
    assert res["execution"]["ledger"]["status"] == "success"

    ticket = res["ticket"]["ticket"]
    leg_mid = str((ticket.get("legs") or [{}])[0].get("match_id") or "")
    assert leg_mid in monitor.active_bets

    conn = sqlite3.connect(str(tmp_path / "ledger.db"))
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*), SUM(CASE WHEN pnl IS NULL THEN 1 ELSE 0 END) FROM bets")
    total, pnl_null = cur.fetchone()
    cur.execute("SELECT pnl FROM bets WHERE match_id=? ORDER BY id DESC LIMIT 1", (ticket["ticket_id"],))
    pnl_row = cur.fetchone()
    conn.close()

    assert int(total) == 1
    assert int(pnl_null) == 0
    assert pnl_row is not None
    assert abs(float(pnl_row[0]) - float(res["post_match_review"]["pnl"])) < 1e-9


def test_closed_loop_trade_zucai_offline_mentor_cli(monkeypatch, tmp_path):
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

    fixtures = [
        {"match_id": f"M{i}", "league_code": "E0", "home_team": f"H{i}", "away_team": f"A{i}", "kickoff_time_utc": "2026-04-15 20:00", "confidence": 0.9, "raw_ref": f"fixture_ref:{i}"}
        for i in range(14)
    ]
    results = [{"match_id": f"M{i}", "status": "FINISHED", "score_ft": "1-0", "raw_ref": f"result_ref:{i}", "source": "test"} for i in range(14)]

    store = SnapshotStore(db_path=str(tmp_path / "snapshots.db"))
    fetcher = MultiSourceFetcher(store=store)
    monkeypatch.setattr(fetcher, "get_fixtures_normalized", lambda date: list(fixtures))
    monkeypatch.setattr(fetcher, "get_results_normalized", lambda date: list(results))

    import core.zucai_workflow as mod

    monkeypatch.setattr(mod, "get_historical_database", lambda lazy_load=True: _DummyDB(draw_rate=0.25))

    wf = ZucaiWorkflow(fetcher=fetcher)
    buf = io.StringIO()
    res = mentor_cli.run(
        ["--date", "2026-04-15", "--lottery-type", "ZUCAI", "--zucai-play-type", "14_match"],
        workflow=wf,
        stdout=buf,
    )

    assert isinstance(res.get("historical_impact"), dict)
    assert "similar_odds_not_applicable:zucai_no_fixed_odds" in (res["historical_impact"].get("degradations") or [])
    assert any(isinstance(x, dict) and x.get("type") == "historical_impact" for x in (res.get("audit") or {}).get("explain") or [])

    assert isinstance(res.get("ticket"), dict)
    assert isinstance(res["ticket"].get("validation"), dict)
    assert (res["ticket"]["validation"].get("router") or {}).get("status") in {"SUCCESS", "VALIDATED"}

    assert isinstance(res.get("post_match_review"), dict)
    assert res["post_match_review"].get("pnl") is not None
