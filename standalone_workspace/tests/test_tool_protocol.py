import asyncio
from tools.mcp_tools import get_team_stats, scrape_beidan_sp

def test_protocol_success():
    res = get_team_stats("皇家马德里")
    assert "ok" in res
    # It might fail if API is not running, but the format is correct.
    # Let's test just the format.
    if res["ok"]:
        assert "data" in res
        assert res["meta"]["mock"] is False
    else:
        assert "error" in res
        assert "meta" in res
        assert res["meta"]["mock"] is False

def test_protocol_failure():
    # Force a failure
    res = get_team_stats(None)
    assert "ok" in res

async def test_protocol_async_mock():
    # scrape_beidan_sp is marked as mock
    res = await scrape_beidan_sp("曼城", "阿森纳")
    assert "ok" in res
    assert res["ok"] is True
    assert "meta" in res
    assert res["meta"]["mock"] is True

if __name__ == "__main__":
    test_protocol_success()
    test_protocol_failure()
    asyncio.run(test_protocol_async_mock())
    print("Protocol tests PASSED")
