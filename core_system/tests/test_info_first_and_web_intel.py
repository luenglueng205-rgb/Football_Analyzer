from tools.domestic_sources import DomesticSources
from tools.multisource_fetcher import MultiSourceFetcher
from tools.snapshot_store import SnapshotStore


def test_info_first_skips_visual_on_captcha_jingcai(monkeypatch):
    monkeypatch.setenv("INFO_FIRST_MODE", "1")

    class DummyBrowser:
        def scrape_500_jingcai_sp_visual(self, *args, **kwargs):
            raise AssertionError("should not fight captcha in info-first mode")

    import tools.domestic_sources as ds

    def fake_fetch(*, home_team: str, away_team: str, kickoff_time=None, fid=None):
        return {
            "ok": False,
            "data": None,
            "error": {"code": "CAPTCHA_REQUIRED", "message": "blocked"},
            "meta": {"mock": True, "source": "500.com", "confidence": 0.0, "stale": True},
        }

    monkeypatch.setattr(ds, "fetch_500_jczq_sp_by_teams", fake_fetch)
    d = DomesticSources(browser=DummyBrowser())
    res = d.get_jingcai_sp(home_team="A", away_team="B", kickoff_time="2026-04-15 20:00", fid=None)
    assert res["ok"] is False
    assert res["error"]["code"] == "CAPTCHA_REQUIRED"


def test_info_first_skips_browser_fixtures_on_captcha(monkeypatch):
    monkeypatch.setenv("INFO_FIRST_MODE", "1")

    class DummyBrowser:
        def scrape_500_fixtures(self, *args, **kwargs):
            raise AssertionError("should not fight captcha in info-first mode")

    import tools.domestic_sources as ds

    monkeypatch.setattr(ds, "fetch_500_trade_html", lambda date=None: "<html>验证码</html>")
    d = DomesticSources(browser=DummyBrowser())
    out = d.get_fixtures(date="2026-04-15")
    assert out == []


def test_web_intel_fixtures_fallback(monkeypatch, tmp_path):
    db_path = str(tmp_path / "snapshots.db")
    f = MultiSourceFetcher(store=SnapshotStore(db_path=db_path), online=True)

    monkeypatch.setattr(
        f,
        "fetch_fixtures_sync",
        lambda date=None: {
            "ok": False,
            "data": None,
            "error": {"code": "NOT_FOUND", "message": "no fixtures"},
            "meta": {"mock": True, "source": "multisource", "confidence": 0.0, "stale": True},
        },
    )

    def fake_intel(*, date: str):
        return [
            {
                "match_id": "20260415_E0_ARS_TOT",
                "league_code": "E0",
                "home_team_id": "ARS",
                "away_team_id": "TOT",
                "kickoff_time_utc": "2026-04-15 20:00",
                "status": "SCHEDULED",
                "source": "web_intel",
                "confidence": 0.25,
                "raw_ref": "web_intel:fixtures:deadbeef",
                "degradations": ["low_confidence:web_intel"],
                "source_ids": {},
                "league_name": "英超",
                "home_team": "Arsenal",
                "away_team": "Tottenham",
            }
        ]

    monkeypatch.setattr(f.web_intel, "extract_fixtures_normalized", fake_intel)

    matches = f.get_fixtures_normalized(date="2026-04-15")
    assert matches and matches[0]["source"] == "web_intel"


def test_web_intel_odds_used_before_foreign_api(monkeypatch, tmp_path):
    db_path = str(tmp_path / "snapshots.db")
    f = MultiSourceFetcher(store=SnapshotStore(db_path=db_path), online=True)

    monkeypatch.setattr(
        f,
        "fetch_odds_sync",
        lambda home_team, away_team: {
            "ok": False,
            "data": None,
            "error": {"code": "NOT_FOUND", "message": "no odds"},
            "meta": {"mock": True, "source": "multisource", "confidence": 0.0, "stale": True, "degradations": []},
        },
    )

    def fake_intel(**kwargs):
        return {
            "ok": True,
            "match_id": "20260415_E0_ARS_TOT",
            "lottery_type": "JINGCAI",
            "play_type": "JINGCAI_WDL",
            "market": "WDL",
            "handicap": None,
            "selections": {
                "H": {"odds": 2.2, "last_update": "2026-04-15T00:00:00Z"},
                "D": {"odds": 3.3, "last_update": "2026-04-15T00:00:00Z"},
                "A": {"odds": 3.1, "last_update": "2026-04-15T00:00:00Z"},
            },
            "source": "web_intel",
            "confidence": 0.25,
            "raw_ref": "web_intel:odds:deadbeef",
            "degradations": ["low_confidence:web_intel"],
        }

    monkeypatch.setattr(f.web_intel, "extract_odds_normalized", fake_intel)
    monkeypatch.setattr(f.foreign_api, "get_odds", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("foreign api should not be called")))

    odds = f.get_odds_normalized(
        league_name="英超",
        home_team="Arsenal",
        away_team="Tottenham",
        kickoff_time="2026-04-15 20:00",
        lottery_type="JINGCAI",
        play_type="JINGCAI_WDL",
        market="WDL",
    )
    assert odds["ok"] is True
    assert odds["source"] == "web_intel"
    assert odds["selections"]["H"]["odds"] == 2.2


def test_web_intel_results_fallback(monkeypatch, tmp_path):
    db_path = str(tmp_path / "snapshots.db")
    f = MultiSourceFetcher(store=SnapshotStore(db_path=db_path), online=True)

    monkeypatch.setattr(
        f,
        "fetch_results_sync",
        lambda date: {
            "ok": False,
            "data": None,
            "error": {"code": "NOT_FOUND", "message": "no results"},
            "meta": {"mock": True, "source": "multisource", "confidence": 0.0, "stale": True},
        },
    )

    def fake_results(*, date: str):
        return [
            {
                "match_id": "20260415_E0_ARS_TOT",
                "status": "FINISHED",
                "score_ft": "2-1",
                "source": "web_intel",
                "confidence": 0.2,
                "raw_ref": "web_intel:results:deadbeef",
                "degradations": ["low_confidence:web_intel"],
                "source_ids": {},
                "league": "英超",
                "kickoff_time": "2026-04-15 20:00",
                "home_team": "Arsenal",
                "away_team": "Tottenham",
            }
        ]

    monkeypatch.setattr(f.web_intel, "extract_results_normalized", fake_results)
    results = f.get_results_normalized("2026-04-15")
    assert results and results[0]["score_ft"] == "2-1"
