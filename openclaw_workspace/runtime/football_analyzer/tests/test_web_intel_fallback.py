from tools.multisource_fetcher import MultiSourceFetcher


def test_openclaw_web_intel_odds_before_foreign(monkeypatch):
    f = MultiSourceFetcher()

    monkeypatch.setattr(
        f.web_intel,
        "extract_odds",
        lambda **kwargs: {
            "ok": True,
            "data": {"eu_odds": {"home": 2.2, "draw": 3.3, "away": 3.1}},
            "error": None,
            "meta": {"mock": True, "source": "web_intel", "confidence": 0.25, "stale": False},
        },
    )
    monkeypatch.setattr(f.foreign_api, "get_odds", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("foreign api should not be called")))
    res = f.fetch_odds_sync(home_team="Arsenal", away_team="Tottenham")
    assert res["ok"] is True
    assert res["meta"]["source"] == "web_intel"


def test_openclaw_web_intel_fixtures_fallback(monkeypatch):
    f = MultiSourceFetcher()
    monkeypatch.setattr(f.browser, "scrape_500_fixtures", lambda date=None: [])
    monkeypatch.setattr(
        f.web_intel,
        "extract_fixtures",
        lambda **kwargs: [
            {
                "league": "UNK",
                "home_team": "Arsenal",
                "away_team": "Tottenham",
                "kickoff_time": "2026-04-15 20:00",
                "status": "upcoming",
            }
        ],
    )
    res = f.fetch_fixtures_sync(date="2026-04-15")
    assert res["ok"] is True
    assert res["meta"]["source"] == "web_intel"

