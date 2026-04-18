import asyncio
import json
import os
import sys
import math


SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from mcp_server import handle_request


def _list_tool_names(tools):
    names = []
    for t in tools:
        if isinstance(t, dict) and "name" in t:
            names.append(t["name"])
    return names


def test_mcp_mentor_tools_listed():
    resp = asyncio.run(handle_request({"method": "list_tools"}))
    assert "tools" in resp
    names = _list_tool_names(resp["tools"])
    assert "identify_league" in names
    assert "recommend_league" in names
    assert "recommend_bets" in names
    assert "live_check" in names
    assert "post_match_review" in names


def _call_tool(name: str, arguments: dict):
    req = {"method": "call_tool", "params": {"name": name, "arguments": arguments}}
    return asyncio.run(handle_request(req))


def _extract_json_payload(resp):
    assert "result" in resp
    assert isinstance(resp["result"], list)
    assert resp["result"]
    text = resp["result"][0]["text"]
    return json.loads(text)


def test_mcp_identify_league_call():
    payload = _extract_json_payload(_call_tool("identify_league", {"league_name": "英超"}))
    assert payload["ok"] is True
    assert payload["data"]["league_code"] == "E0"


def test_mcp_recommend_league_call():
    payload = _extract_json_payload(_call_tool("recommend_league", {"query": "英超 串关", "top_n": 2}))
    assert payload["ok"] is True
    assert isinstance(payload["data"]["recommended_leagues"], list)
    assert payload["data"]["recommended_leagues"]


def test_mcp_recommend_bets_call():
    payload = _extract_json_payload(
        _call_tool(
            "recommend_bets",
            {
                "league_code": "E0",
                "home_team": "Arsenal",
                "away_team": "Tottenham",
                "odds": {"home": 2.05, "draw": 3.4, "away": 3.6},
                "stake": 100,
            },
        )
    )
    assert payload["ok"] is True
    assert payload["data"]["league_code"] == "E0"
    assert payload["data"]["recommended_bets"][0]["match_id"]
    assert "historical_impact" in payload["data"]


def test_mcp_recommend_bets_beidan_call():
    odds = {"home": 2.05, "draw": 3.4, "away": 3.6}
    payload = _extract_json_payload(
        _call_tool(
            "recommend_bets",
            {
                "league_code": "E0",
                "home_team": "Arsenal",
                "away_team": "Tottenham",
                "odds": odds,
                "lottery_type": "beidan",
                "stake": 100,
            },
        )
    )
    assert payload["ok"] is True
    assert payload["data"]["historical_impact"]["lottery_type"] == "BEIDAN"
    bet0 = payload["data"]["recommended_bets"][0]
    assert bet0["lottery_type"] == "beidan"

    inv = {k: 1.0 / float(v) for k, v in odds.items()}
    total = sum(inv.values())
    probs = {k: v / total for k, v in inv.items()}
    best = max(("home", "draw", "away"), key=lambda k: probs.get(k, 0.0))
    expected_ev = (float(odds[best]) * float(probs[best]) * 0.65) - 1.0
    assert bet0["selection"] == best
    assert bet0["ev"] is not None
    assert math.isclose(float(bet0["ev"]), round(expected_ev, 4), rel_tol=0, abs_tol=1e-9)


def test_mcp_recommend_bets_zucai_call_allows_missing_odds():
    payload = _extract_json_payload(
        _call_tool(
            "recommend_bets",
            {
                "league_code": "E0",
                "home_team": "Arsenal",
                "away_team": "Tottenham",
                "lottery_type": "zucai",
                "stake": 100,
            },
        )
    )
    assert payload["ok"] is True
    assert payload["data"]["odds"] is None
    hi = payload["data"]["historical_impact"]
    assert hi["lottery_type"] == "ZUCAI"
    assert hi["similar_odds"]["enabled"] is False
    assert "similar_odds_not_applicable:zucai_no_fixed_odds" in hi["degradations"]
    bet0 = payload["data"]["recommended_bets"][0]
    assert bet0["lottery_type"] == "zucai"
    assert bet0["odds"] is None
    assert bet0["ev"] is None


def test_mcp_live_check_call():
    payload = _extract_json_payload(
        _call_tool(
            "live_check",
            {
                "match_id": "E0:Arsenal:Tottenham",
                "selection": "home",
                "original_stake": 100.0,
                "original_odds": 2.1,
                "current_score": "1-0",
                "live_odds_against": 4.5,
                "current_minute": 76,
            },
        )
    )
    assert payload["ok"] is True
    assert payload["data"]["match_id"] == "E0:Arsenal:Tottenham"


def test_mcp_post_match_review_call():
    payload = _extract_json_payload(
        _call_tool(
            "post_match_review",
            {
                "match_id": "E0:Arsenal:Tottenham",
                "ft_score": "2-1",
                "selection": "home",
                "stake": 100.0,
                "odds": 2.1,
                "status": "FINISHED",
                "date_str": "2026-04-15",
            },
        )
    )
    assert payload["ok"] is True
    assert "settlement" in payload["data"]
    assert "daily_report" in payload["data"]
