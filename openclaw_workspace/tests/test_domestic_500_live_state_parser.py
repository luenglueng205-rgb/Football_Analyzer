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


def test_parse_500_live_detail_html_extracts_minute_score_and_red_cards():
    from tools.domestic_500_live_state import parse_500_live_detail_html

    html = _load_fixture("500_live_detail_1234567890.html")
    parsed = parse_500_live_detail_html(html=html)
    assert parsed["ok"] is True
    assert parsed["data"]["minute"] == 76
    assert parsed["data"]["ft_score"] == "1-0"
    assert parsed["data"]["red_cards"] == {"home": 1, "away": 0}


def test_fetcher_get_live_state_normalized(monkeypatch, tmp_path):
    html = _load_fixture("500_live_detail_1234567890.html")

    import tools.domestic_500_live_state as mod

    def fake_get(url: str, *args, **kwargs):
        assert "live.500.com/detail.php" in url
        return _Resp(html, 200)

    monkeypatch.setattr(mod.requests, "get", fake_get)

    db_path = str(tmp_path / "snapshots.db")
    fetcher = MultiSourceFetcher(store=SnapshotStore(db_path=db_path))
    out = fetcher.get_live_state_normalized(
        match_id="20260415_E0_ARS_TOT",
        league_name="英超",
        home_team="Arsenal",
        away_team="Tottenham",
        kickoff_time="2026-04-15 20:00",
        source_ids={"500.com": {"fid": "1234567890"}},
    )
    assert out["ok"] is True
    assert out["match_id"] == "20260415_E0_ARS_TOT"
    assert out["minute"] == 76
    assert out["score_ft"] == "1-0"
    assert out["red_cards"] == {"home": 1, "away": 0}
    assert out["source"] == "live.500.com"
    assert out["raw_ref"].startswith("snapshot:live_state:")

