from __future__ import annotations

import time


def test_agent_browser_offline_by_default():
    from tools.agent_browser import AgentBrowser

    b = AgentBrowser()
    assert b.online is False
    assert b.ddgs is None
    assert b.visual is None
    assert b.search_web("test") == []


def test_agent_browser_ddgs_is_bounded_by_timeout(monkeypatch):
    from tools.agent_browser import AgentBrowser

    monkeypatch.setenv("AGENT_BROWSER_DDGS_TIMEOUT_S", "0.05")
    b = AgentBrowser(online=True)

    class _SlowDDGS:
        def text(self, query: str, max_results: int = 5):
            time.sleep(0.2)
            return iter([{"title": "t", "body": "b", "href": "u"}])

    b.ddgs = _SlowDDGS()

    start = time.monotonic()
    out = b.search_web("x", max_results=3)
    elapsed = time.monotonic() - start

    assert out == []
    assert elapsed < 0.2
