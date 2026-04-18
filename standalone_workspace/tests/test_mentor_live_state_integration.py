from __future__ import annotations

import io
from pathlib import Path

from core.mentor_workflow import MentorWorkflow
from scripts import mentor_cli
from tools.multisource_fetcher import MultiSourceFetcher
from tools.snapshot_store import SnapshotStore


class _Resp:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code
        self.encoding = "utf-8"
        self.apparent_encoding = "utf-8"


def test_mentor_workflow_includes_live_check_when_live_state_available(monkeypatch, tmp_path):
    here = Path(__file__).resolve().parent
    fixtures_html = (here / "fixtures" / "500_trade_2026-04-15.html").read_text(encoding="utf-8")
    sp_html = (here / "fixtures" / "500_trade_jczq_sp_2026-04-15.html").read_text(encoding="utf-8")
    live_html = (here / "fixtures" / "500_live_detail_1234567890.html").read_text(encoding="utf-8")

    import tools.domestic_500_jczq_sp as sp_mod
    import tools.domestic_sources as src_mod
    import tools.domestic_500_live_state as live_mod

    monkeypatch.setattr(src_mod, "fetch_500_trade_html", lambda date=None, timeout_s=3.0: fixtures_html)
    monkeypatch.setattr(
        sp_mod,
        "fetch_500_jczq_trade_html",
        lambda date=None, timeout_s=4.0: {"ok": True, "html": sp_html, "url": "https://trade.500.com/jczq/", "error": None},
    )

    def fake_get(url: str, *args, **kwargs):
        if "live.500.com/detail.php" in url:
            return _Resp(live_html, 200)
        raise RuntimeError(f"unexpected url in test: {url}")

    monkeypatch.setattr(live_mod.requests, "get", fake_get)

    db_path = str(tmp_path / "snapshots.db")
    store = SnapshotStore(db_path=db_path)
    fetcher = MultiSourceFetcher(store=store)

    monkeypatch.setattr(
        fetcher,
        "fetch_results_sync",
        lambda date: {
            "ok": False,
            "data": None,
            "error": {"code": "NOT_FOUND", "message": "offline test"},
            "meta": {"mock": True, "source": "offline", "confidence": 0.0, "stale": True},
        },
    )

    wf = MentorWorkflow(fetcher=fetcher)
    buf = io.StringIO()
    res = mentor_cli.run(["--date", "2026-04-15"], workflow=wf, stdout=buf)

    assert res["live_check"] is not None
    assert res["live_check"]["match_id"] == "20260415_E0_ARS_TOT"
    assert res["live_check"].get("live_state") is not None
    assert res["live_check"]["live_state"]["minute"] == 76
    assert res["live_check"]["live_state"]["score_ft"] == "1-0"

