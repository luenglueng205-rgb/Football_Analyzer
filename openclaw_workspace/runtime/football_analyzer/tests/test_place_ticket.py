from tools.betting_ledger import BettingLedger
from tools.mentor_tools import place_ticket


def test_place_ticket_minimal_request(tmp_path):
    db_path = str(tmp_path / "ledger.db")
    ledger = BettingLedger(db_path=db_path)
    before = ledger.check_bankroll()

    res = place_ticket(
        ticket_request={
            "match_id": "E0:Arsenal:Tottenham",
            "lottery_type": "jingcai",
            "selection": "home",
            "odds": 2.1,
            "stake": 250.0,
        },
        db_path=db_path,
        reset_live_monitor=True,
    )

    assert res["ok"] is True
    assert res["data"]["ledger"]["status"] == "success"
    assert res["data"]["live_monitor"]["status"] == "active"

    after = BettingLedger(db_path=db_path).check_bankroll()
    assert after["current_bankroll"] == before["current_bankroll"] - 250.0


def test_place_ticket_from_recommendation_schema(tmp_path):
    db_path = str(tmp_path / "ledger.db")
    schema = {
        "recommended_bets": [
            {
                "match_id": "SP1:Real_Madrid:Barcelona",
                "lottery_type": "JINGCAI",
                "market": "WDL",
                "selection": "home",
                "odds": 1.95,
                "stake": 100.0,
            }
        ],
        "audit": {"sources": ["unit_test"], "raw_refs": [], "degradations": [], "conflicts": []},
    }

    res = place_ticket(recommendation_schema=schema, db_path=db_path, reset_live_monitor=True)
    assert res["ok"] is True
    assert res["data"]["match_id"] == "SP1:Real_Madrid:Barcelona"
    assert "ticket_code" in res["data"]["ledger"]


def test_place_ticket_rejects_missing_fields(tmp_path):
    db_path = str(tmp_path / "ledger.db")
    res = place_ticket(ticket_request={"match_id": "M1"}, db_path=db_path, reset_live_monitor=True)
    assert res["ok"] is False
    assert res["error"]["code"] == "INVALID_TICKET_REQUEST"

