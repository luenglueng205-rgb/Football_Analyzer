import asyncio

from tools.multisource_fetcher import MultiSourceFetcher


def test_fallback_never_crash():
    f = MultiSourceFetcher()
    res = asyncio.run(f.fetch_odds(home_team="皇家马德里", away_team="曼城"))
    assert "ok" in res and "meta" in res
    if res["ok"]:
        assert "confidence" in res["meta"]
    else:
        assert res["error"]["code"] in ["CAPTCHA_REQUIRED", "NOT_FOUND", "FETCH_FAILED", "BAD_INPUT"]


if __name__ == "__main__":
    asyncio.run(test_fallback_never_crash())
    print("test_fallback_never_crash PASSED")
