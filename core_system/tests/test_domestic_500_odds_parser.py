from pathlib import Path

from tools.domestic_odds_500 import parse_500_eu_odds_from_ouzhi_html


def test_parse_500_ouzhi_avg_eu_odds_from_saved_html():
    html = (Path(__file__).parent / "fixtures" / "500_ouzhi_sample.html").read_text(encoding="utf-8")
    eu = parse_500_eu_odds_from_ouzhi_html(html)
    assert eu == {"home": 2.10, "draw": 3.35, "away": 3.40}


def test_parse_500_ouzhi_refuses_on_failure():
    assert parse_500_eu_odds_from_ouzhi_html("<html>no odds</html>") is None

