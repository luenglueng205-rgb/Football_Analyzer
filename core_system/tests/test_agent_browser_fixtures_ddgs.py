from tools.agent_browser import AgentBrowser


def test_agent_browser_ddgs_fixture_parse(monkeypatch):
    browser = AgentBrowser()
    browser.visual = None

    import tools.domestic_500_fixtures as mod

    def fake_get(*args, **kwargs):
        raise RuntimeError("network disabled in test")

    monkeypatch.setattr(mod.requests, "get", fake_get)

    def fake_text(query: str, max_results: int = 10):
        return [
            {
                "title": "英超 Arsenal vs Tottenham 20:00",
                "body": "2026-04-15 20:00 英超 Arsenal vs Tottenham",
                "href": "https://zx.500.com/jczq/",
            }
        ]

    monkeypatch.setattr(browser.ddgs, "text", fake_text)

    fixtures = browser.scrape_500_fixtures(date="2026-04-15")
    assert fixtures
    assert fixtures[0]["league"] == "英超"
    assert fixtures[0]["home_team"] == "Arsenal"
    assert fixtures[0]["away_team"] == "Tottenham"
    assert fixtures[0]["kickoff_time"] == "2026-04-15 20:00"
