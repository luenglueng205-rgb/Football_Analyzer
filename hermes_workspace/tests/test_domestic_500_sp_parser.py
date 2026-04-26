from __future__ import annotations

from pathlib import Path

from tools.multisource_fetcher import MultiSourceFetcher
from tools.snapshot_store import SnapshotStore


class _Resp:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code


def _load_fixture(name: str) -> str:
    here = Path(__file__).resolve().parent
    p = here / "fixtures" / name
    return p.read_text(encoding="utf-8")


def test_parse_500_jczq_trade_sp_html_extracts_wdl_and_handicap_wdl():
    from tools.domestic_500_jczq_sp import parse_500_jczq_trade_sp_html

    html = _load_fixture("500_trade_jczq_sp_2026-04-15.html")
    res = parse_500_jczq_trade_sp_html(
        html=html,
        home_team="Arsenal",
        away_team="Tottenham",
        kickoff_time="2026-04-15 20:00",
    )
    assert res["ok"] is True
    markets = res["data"]["jingcai_sp"]
    assert markets["WDL"]["handicap"] == 0.0
    assert markets["WDL"]["home"] == 2.10
    assert markets["HANDICAP_WDL"]["handicap"] == -1.0
    assert markets["HANDICAP_WDL"]["away"] == 4.10


def test_parse_500_jczq_trade_sp_html_can_locate_row_by_fid_even_if_teams_differ():
    from tools.domestic_500_jczq_sp import parse_500_jczq_trade_sp_html

    html = _load_fixture("500_trade_jczq_sp_2026-04-15.html")
    res = parse_500_jczq_trade_sp_html(
        html=html,
        home_team="Arsenal FC",
        away_team="Tottenham Hotspur FC",
        kickoff_time="2026-04-15 20:00",
        fid="1234567890",
    )
    assert res["ok"] is True
    markets = res["data"]["jingcai_sp"]
    assert markets["WDL"]["home"] == 2.10


def test_fetcher_get_odds_normalized_prefers_jingcai_sp(monkeypatch, tmp_path):
    html = _load_fixture("500_trade_jczq_sp_2026-04-15.html")

    import tools.domestic_500_jczq_sp as mod

    def fake_get(*args, **kwargs):
        return _Resp(html, 200)

    monkeypatch.setattr(mod.requests, "get", fake_get)

    db_path = str(tmp_path / "snapshots.db")
    f = MultiSourceFetcher(store=SnapshotStore(db_path=db_path))

    res = f.get_odds_normalized(
        league_name="英超",
        home_team="Arsenal",
        away_team="Tottenham",
        kickoff_time="2026-04-15 20:00",
        lottery_type="JINGCAI",
        play_type="JINGCAI_WDL",
        market="WDL",
        handicap=None,
    )
    assert res["ok"] is True
    assert res["selections"]["H"]["odds"] == 2.10
    assert res["selections"]["H"]["sp"] == 2.10
    assert res["handicap"] == 0.0
    assert res["source"] == "500.com"
    assert "raw_ref" in res

    res2 = f.get_odds_normalized(
        league_name="英超",
        home_team="Arsenal",
        away_team="Tottenham",
        kickoff_time="2026-04-15 20:00",
        lottery_type="JINGCAI",
        play_type="JINGCAI_HANDICAP_WDL",
        market="HANDICAP_WDL",
        handicap=None,
    )
    assert res2["ok"] is True
    assert res2["selections"]["H"]["odds"] == 1.75
    assert res2["handicap"] == -1.0


def test_parse_500_beidan_sp_html_extracts_handicap_wdl():
    from tools.domestic_500_beidan_sp import parse_500_beidan_sp_html

    html = _load_fixture("500_trade_beidan_sp_2026-04-15.html")
    res = parse_500_beidan_sp_html(html=html, home_team="Arsenal", away_team="Tottenham")
    assert res["ok"] is True
    markets = res["data"]["beidan_sp"]
    assert markets["HANDICAP_WDL"]["handicap"] == -1.0
    assert markets["HANDICAP_WDL"]["home"] == 2.73


def test_parse_500_beidan_sp_html_can_locate_row_by_fid_even_if_teams_differ():
    from tools.domestic_500_beidan_sp import parse_500_beidan_sp_html

    html = _load_fixture("500_trade_beidan_sp_2026-04-15.html")
    res = parse_500_beidan_sp_html(html=html, home_team="Arsenal FC", away_team="Tottenham FC", fid="1234567890")
    assert res["ok"] is True
    markets = res["data"]["beidan_sp"]
    assert markets["HANDICAP_WDL"]["home"] == 2.73


def test_fetcher_get_odds_normalized_beidan_sp(monkeypatch, tmp_path):
    html = _load_fixture("500_trade_beidan_sp_2026-04-15.html")

    import tools.domestic_500_beidan_sp as mod

    def fake_get(*args, **kwargs):
        return _Resp(html, 200)

    monkeypatch.setattr(mod.requests, "get", fake_get)

    db_path = str(tmp_path / "snapshots.db")
    f = MultiSourceFetcher(store=SnapshotStore(db_path=db_path))

    res = f.get_odds_normalized(
        league_name="欧冠",
        home_team="Arsenal",
        away_team="Tottenham",
        kickoff_time="2026-04-15 20:00",
        lottery_type="BEIDAN",
        play_type="BEIDAN_WDL",
        market="HANDICAP_WDL",
        handicap=None,
    )
    assert res["ok"] is True
    assert res["selections"]["H"]["odds"] == 2.73
    assert res["handicap"] == -1.0
