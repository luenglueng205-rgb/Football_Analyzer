import hashlib
import io
import json
from pathlib import Path

from core.mentor_workflow import MentorWorkflow
from scripts import mentor_cli
from tools.multisource_fetcher import MultiSourceFetcher
from tools.snapshot_store import SnapshotStore


def test_mentor_cli_outputs_abcd_and_audit(monkeypatch, tmp_path):
    db_path = str(tmp_path / "snapshots.db")
    store = SnapshotStore(db_path=db_path)
    fetcher = MultiSourceFetcher(store=store)

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

    def fake_fetch_odds_sync(home_team: str, away_team: str):
        return {
            "ok": True,
            "data": {"eu_odds": {"home": 2.1, "draw": 3.4, "away": 3.2}},
            "error": None,
            "meta": {"mock": True, "source": "snapshot", "confidence": 0.88, "stale": False},
        }

    monkeypatch.setattr(fetcher, "fetch_fixtures_sync", fake_fetch_fixtures_sync)
    monkeypatch.setattr(fetcher, "fetch_odds_sync", fake_fetch_odds_sync)

    store.insert_snapshot(
        category="results",
        match_id="RESULTS::2026-04-15",
        source="500.com",
        payload={
            "results": [
                {
                    "match_id": "20260415_E0_ARS_TOT",
                    "status": "FINISHED",
                    "score_ht": "0-1",
                    "score_ft": "2-1",
                    "source": "500.com",
                    "confidence": 0.9,
                    "raw_ref": "snapshot:results:500.com:test",
                }
            ]
        },
        confidence=0.9,
        stale=False,
    )

    wf = MentorWorkflow(fetcher=fetcher)
    buf = io.StringIO()
    res = mentor_cli.run(["--date", "2026-04-15"], workflow=wf, stdout=buf)

    assert isinstance(res, dict)
    assert "recommended_leagues" in res
    assert "recommended_bets" in res
    assert "recommended_parlays" in res
    assert "live_check" in res
    assert "post_match_review" in res
    assert "audit" in res
    assert "historical_impact" in res
    assert "ticket" in res
    assert "execution" in res

    assert res["recommended_leagues"][0]["league_code"] == "E0"
    assert len(res["recommended_bets"]) >= 1
    assert res["audit"]["sources"]
    assert any("LotteryRouter" == s for s in res["audit"]["sources"])
    assert any(str(x).startswith("router:") for x in res["audit"]["degradations"])
    assert any(isinstance(x, dict) and x.get("type") == "historical_impact" for x in (res["audit"].get("explain") or []))
    assert res["live_check"]["match_id"] == "20260415_E0_ARS_TOT"
    assert "memory_injection" in res["post_match_review"]
    assert res["ticket"] is not None
    assert isinstance(res["ticket"].get("ticket"), dict)
    assert isinstance(res["ticket"].get("validation"), dict)
    assert res["execution"] is None


def test_mentor_cli_selects_first_fixture_with_usable_odds(monkeypatch, tmp_path):
    db_path = str(tmp_path / "snapshots.db")
    store = SnapshotStore(db_path=db_path)
    fetcher = MultiSourceFetcher(store=store)

    fixtures = [
        {
            "league": "英超",
            "home_team": "Arsenal",
            "away_team": "Tottenham",
            "kickoff_time": "2026-04-15 20:00",
            "status": "upcoming",
        },
        {
            "league": "英超",
            "home_team": "Chelsea",
            "away_team": "Liverpool",
            "kickoff_time": "2026-04-15 22:00",
            "status": "upcoming",
        },
    ]

    def fake_fetch_fixtures_sync(date=None):
        return {
            "ok": True,
            "data": {"fixtures": list(fixtures)},
            "error": None,
            "meta": {"mock": True, "source": "test_fixtures", "confidence": 0.9, "stale": False},
        }

    def fake_fetch_odds_sync(home_team: str, away_team: str):
        if home_team == "Arsenal" and away_team == "Tottenham":
            return {
                "ok": True,
                "data": {},
                "error": None,
                "meta": {"mock": True, "source": "test_odds", "confidence": 0.88, "stale": False},
            }
        return {
            "ok": True,
            "data": {"eu_odds": {"home": 2.05, "draw": 3.4, "away": 3.6}},
            "error": None,
            "meta": {"mock": True, "source": "test_odds", "confidence": 0.88, "stale": False},
        }

    monkeypatch.setattr(fetcher, "fetch_fixtures_sync", fake_fetch_fixtures_sync)
    monkeypatch.setattr(fetcher, "fetch_odds_sync", fake_fetch_odds_sync)

    selected_match_id = fetcher.identity.build("英超", "Chelsea", "Liverpool", "2026-04-15 22:00")
    store.insert_snapshot(
        category="results",
        match_id="RESULTS::2026-04-15",
        source="test_results",
        payload={
            "results": [
                {
                    "match_id": selected_match_id,
                    "status": "FINISHED",
                    "score_ft": "1-1",
                    "league": "英超",
                    "home_team": "Chelsea",
                    "away_team": "Liverpool",
                    "kickoff_time": "2026-04-15 22:00",
                }
            ]
        },
        confidence=0.9,
        stale=False,
    )

    wf = MentorWorkflow(fetcher=fetcher)
    buf = io.StringIO()
    res = mentor_cli.run(["--date", "2026-04-15"], workflow=wf, stdout=buf)

    assert res["recommended_bets"]
    assert res["live_check"]["match_id"] == selected_match_id

    fixtures_payload = {"date": "2026-04-15", "fixtures": fixtures}
    fixtures_digest = hashlib.sha1(json.dumps(fixtures_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    expected_fixtures_ref = f"snapshot:fixtures:test_fixtures:{fixtures_digest}"

    odds_payload = {"eu_odds": {"home": 2.05, "draw": 3.4, "away": 3.6}}
    odds_meta = {"mock": True, "source": "test_odds", "confidence": 0.88, "stale": False}
    odds_snapshot_payload = {"match_id": selected_match_id, "market": "WDL", "payload": odds_payload, "meta": odds_meta}
    odds_digest = hashlib.sha1(json.dumps(odds_snapshot_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    expected_odds_ref = f"snapshot:odds_raw:test_odds:{odds_digest}"

    first_match_id = fetcher.identity.build("英超", "Arsenal", "Tottenham", "2026-04-15 20:00")
    first_odds_payload = {}
    first_odds_snapshot_payload = {"match_id": first_match_id, "market": "WDL", "payload": first_odds_payload, "meta": odds_meta}
    first_odds_digest = hashlib.sha1(json.dumps(first_odds_snapshot_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    unexpected_odds_ref = f"snapshot:odds_raw:test_odds:{first_odds_digest}"

    results_payload = {
        "date": "2026-04-15",
        "results": [
            {
                "match_id": selected_match_id,
                "status": "FINISHED",
                "score_ft": "1-1",
                "league": "英超",
                "home_team": "Chelsea",
                "away_team": "Liverpool",
                "kickoff_time": "2026-04-15 22:00",
            }
        ],
    }
    results_digest = hashlib.sha1(json.dumps(results_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    expected_results_ref = f"snapshot:results:test_results:{results_digest}"

    assert expected_fixtures_ref in res["audit"]["raw_refs"]
    assert expected_odds_ref in res["audit"]["raw_refs"]
    assert expected_results_ref in res["audit"]["raw_refs"]
    assert unexpected_odds_ref not in res["audit"]["raw_refs"]


def test_mentor_cli_matches_results_by_fid_and_clears_results_not_found(monkeypatch, tmp_path):
    here = Path(__file__).resolve().parent
    fixtures_html = (here / "fixtures" / "500_trade_2026-04-15.html").read_text(encoding="utf-8")
    results_html = (here / "fixtures" / "500_trade_results_fid_mismatch_2026-04-15.html").read_text(encoding="utf-8")

    import tools.domestic_500_results as res_mod
    import tools.domestic_sources as src_mod

    monkeypatch.setattr(src_mod, "fetch_500_trade_html", lambda date=None, timeout_s=3.0: fixtures_html)
    monkeypatch.setattr(
        res_mod,
        "fetch_500_trade_results_html",
        lambda date=None, timeout_s=4.0: {"ok": True, "html": results_html, "url": "https://trade.500.com/jczq/", "error": None},
    )

    db_path = str(tmp_path / "snapshots.db")
    store = SnapshotStore(db_path=db_path)
    fetcher = MultiSourceFetcher(store=store)

    def fake_fetch_odds_sync(home_team: str, away_team: str):
        return {
            "ok": True,
            "data": {"eu_odds": {"home": 2.1, "draw": 3.4, "away": 3.2}},
            "error": None,
            "meta": {"mock": True, "source": "snapshot", "confidence": 0.88, "stale": False},
        }

    monkeypatch.setattr(fetcher, "fetch_odds_sync", fake_fetch_odds_sync)

    wf = MentorWorkflow(fetcher=fetcher)
    buf = io.StringIO()
    res = mentor_cli.run(["--date", "2026-04-15", "--ft-score-fallback", "0-0"], workflow=wf, stdout=buf)

    assert "results_not_found" not in res["audit"]["degradations"]
    assert "results_ft_fallback" not in res["audit"]["degradations"]
    assert res["post_match_review"]["settlement"]["ft_score"] == "2-1"


def test_mentor_cli_uses_cached_fixtures_snapshot_when_available(monkeypatch, tmp_path):
    db_path = str(tmp_path / "snapshots.db")
    store = SnapshotStore(db_path=db_path)
    store.insert_snapshot(
        category="fixtures",
        match_id="FIXTURES::2026-04-15",
        source="500.com",
        payload={
            "date": "2026-04-15",
            "fixtures": [
                {
                    "league": "英超",
                    "home_team": "Arsenal",
                    "away_team": "Tottenham",
                    "kickoff_time": "2026-04-15 20:00",
                    "status": "upcoming",
                }
            ],
        },
        confidence=0.9,
        stale=False,
    )

    fetcher = MultiSourceFetcher(store=store)

    def should_not_call_fetch_fixtures_sync(date=None):
        raise AssertionError("fetch_fixtures_sync should not be called when fixtures snapshot exists")

    def fake_fetch_odds_sync(home_team: str, away_team: str):
        return {
            "ok": True,
            "data": {"eu_odds": {"home": 2.1, "draw": 3.4, "away": 3.2}},
            "error": None,
            "meta": {"mock": True, "source": "snapshot", "confidence": 0.88, "stale": False},
        }

    monkeypatch.setattr(fetcher, "fetch_fixtures_sync", should_not_call_fetch_fixtures_sync)
    monkeypatch.setattr(fetcher, "fetch_odds_sync", fake_fetch_odds_sync)

    wf = MentorWorkflow(fetcher=fetcher)
    buf = io.StringIO()
    res = mentor_cli.run(["--date", "2026-04-15"], workflow=wf, stdout=buf)

    assert res["recommended_leagues"]
    assert "no_fixtures" not in res["audit"]["degradations"]


def test_mentor_cli_offline_html_fixtures_and_sp_have_odds_and_prob(monkeypatch, tmp_path):
    here = Path(__file__).resolve().parent
    fixtures_html = (here / "fixtures" / "500_trade_2026-04-15.html").read_text(encoding="utf-8")
    sp_html = (here / "fixtures" / "500_trade_jczq_sp_2026-04-15.html").read_text(encoding="utf-8")

    import tools.domestic_500_jczq_sp as sp_mod
    import tools.domestic_sources as src_mod

    monkeypatch.setattr(src_mod, "fetch_500_trade_html", lambda date=None, timeout_s=3.0: fixtures_html)
    monkeypatch.setattr(
        sp_mod,
        "fetch_500_jczq_trade_html",
        lambda date=None, timeout_s=4.0: {"ok": True, "html": sp_html, "url": "https://trade.500.com/jczq/", "error": None},
    )

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

    assert res["recommended_leagues"]
    assert res["recommended_leagues"][0]["league_code"] != "UNK"
    assert res["recommended_bets"]
    b0 = res["recommended_bets"][0]
    assert b0.get("odds") is not None and float(b0["odds"]) > 0
    assert b0.get("prob") is not None and float(b0["prob"]) > 0


def test_mentor_cli_parses_lottery_type_and_online_flag():
    parser = mentor_cli.build_parser()
    args = parser.parse_args([])
    assert args.lottery_type == "JINGCAI"
    assert args.zucai_play_type == "14_match"
    assert args.online is False

    args2 = parser.parse_args(["--lottery-type", "ZUCAI", "--zucai-play-type", "renjiu", "--online"])
    assert args2.lottery_type == "ZUCAI"
    assert args2.zucai_play_type == "renjiu"
    assert args2.online is True


def test_mentor_cli_offline_does_not_call_web_intel_fallbacks(monkeypatch, tmp_path):
    import tools.web_intel_extractor as intel_mod
    import tools.api_clients as api_mod
    from tools.snapshot_store import SnapshotStore

    monkeypatch.setattr(intel_mod.WebIntelExtractor, "extract_odds_normalized", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("web_intel should not be called in offline mode")))
    monkeypatch.setattr(api_mod.ForeignAPIClient, "get_odds", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("foreign_api should not be called in offline mode")))

    real_cls = mentor_cli.MultiSourceFetcher

    def _factory(*, online: bool = False):
        store = SnapshotStore(db_path=str(tmp_path / "snapshots.db"))
        return real_cls(store=store, online=online)

    monkeypatch.setattr(mentor_cli, "MultiSourceFetcher", lambda *args, **kwargs: _factory(online=bool(kwargs.get("online", False))))

    class DummyWorkflow:
        def __init__(self, *, fetcher):
            self.fetcher = fetcher

        def run(self, *, date: str, stake: float = 100.0, **kwargs):
            monkeypatch.setattr(
                self.fetcher,
                "fetch_odds_sync",
                lambda home_team, away_team: {
                    "ok": True,
                    "data": {},
                    "error": None,
                    "meta": {"mock": False, "source": "test_odds", "confidence": 0.1, "stale": True},
                },
            )
            odds = self.fetcher.get_odds_normalized(
                league_name="英超",
                home_team="Arsenal",
                away_team="Tottenham",
                kickoff_time=f"{date} 20:00",
                lottery_type="JINGCAI",
                play_type="JINGCAI_WDL",
                market="WDL",
            )
            return {"ok": True, "odds_ok": odds.get("ok"), "odds_source": odds.get("source")}

    monkeypatch.setattr(mentor_cli, "MentorWorkflow", DummyWorkflow)

    out = mentor_cli.run(["--date", "2026-04-15"], stdout=io.StringIO())
    assert out["ok"] is True
    assert out["odds_source"] != "web_intel"


def test_mentor_cli_routes_by_lottery_type(monkeypatch, tmp_path):
    import types
    import sys
    from tools.snapshot_store import SnapshotStore

    called = {"beidan": False, "zucai": False}

    class DummyBeidanWorkflow:
        def __init__(self, *, fetcher=None):
            self.fetcher = fetcher

        def run(self, *, date: str, stake: float = 100.0, **kwargs):
            called["beidan"] = True
            return {"ok": True, "lottery_type": "BEIDAN"}

    class DummyZucaiWorkflow:
        def __init__(self, *, fetcher=None):
            self.fetcher = fetcher

        def run(self, *, date: str, stake: float = 100.0, play_type: str = "14_match", **kwargs):
            called["zucai"] = True
            return {"ok": True, "lottery_type": "ZUCAI", "play_type": play_type}

    m_bd = types.ModuleType("core.beidan_workflow")
    m_bd.BeidanWorkflow = DummyBeidanWorkflow
    m_zc = types.ModuleType("core.zucai_workflow")
    m_zc.ZucaiWorkflow = DummyZucaiWorkflow
    sys.modules["core.beidan_workflow"] = m_bd
    sys.modules["core.zucai_workflow"] = m_zc

    real_cls = mentor_cli.MultiSourceFetcher
    monkeypatch.setattr(
        mentor_cli,
        "MultiSourceFetcher",
        lambda *args, **kwargs: real_cls(store=SnapshotStore(db_path=str(tmp_path / "snapshots.db")), online=bool(kwargs.get("online", False))),
    )

    out_bd = mentor_cli.run(["--date", "2026-04-15", "--lottery-type", "BEIDAN"], stdout=io.StringIO())
    assert out_bd["lottery_type"] == "BEIDAN"
    assert called["beidan"] is True

    out_zc = mentor_cli.run(
        ["--date", "2026-04-15", "--lottery-type", "ZUCAI", "--zucai-play-type", "renjiu"],
        stdout=io.StringIO(),
    )
    assert out_zc["lottery_type"] == "ZUCAI"
    assert out_zc["play_type"] == "renjiu"
    assert called["zucai"] is True
