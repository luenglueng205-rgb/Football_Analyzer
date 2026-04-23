from tools.analyzer_api import AnalyzerAPI


def test_live_odds_protocol_format():
    res = AnalyzerAPI.get_live_odds_protocol(home_team="皇家马德里", away_team="曼城")
    assert "ok" in res
    assert "meta" in res
    assert res["meta"]["mock"] is False


def test_live_injuries_protocol_format():
    res = AnalyzerAPI.get_live_injuries_protocol(team_name="皇家马德里")
    assert "ok" in res
    assert "meta" in res
    assert res["meta"]["mock"] is False


def test_live_news_protocol_format():
    res = AnalyzerAPI.get_live_news_protocol(team_name="皇家马德里", limit=3)
    assert "ok" in res
    assert "meta" in res
    assert res["meta"]["mock"] is False


if __name__ == "__main__":
    test_live_odds_protocol_format()
    test_live_injuries_protocol_format()
    test_live_news_protocol_format()
    print("AnalyzerAPI multisource tests PASSED")

