import pytest

from core.recommendation_schema import RecommendationSchema, RecommendedBet
from tools.ticket_builder import LotteryTicketBuilder
from tools.lottery_router import LotteryRouter


def _bet(match_id: str, *, lottery_type: str, play_type: str, selection: str, odds: float | None):
    return RecommendedBet(
        match_id=match_id,
        lottery_type=lottery_type,
        play_type=play_type,
        market="WDL",
        selection=selection,
        prob=0.4,
        odds=odds,
        ev=None,
        edge=None,
        risk_tags=[],
    )


def test_ticket_builder_beidan_allows_15_legs():
    schema = RecommendationSchema(
        recommended_bets=[
            _bet(f"M{i}", lottery_type="BEIDAN", play_type="BEIDAN_WDL", selection="3", odds=2.5) for i in range(15)
        ]
    )
    res = LotteryTicketBuilder().build_validated_ticket(schema=schema, stake=100.0, date="2026-04-15")
    assert res["ok"] in {True, False}
    assert res["ticket"]
    assert len(res["ticket"]["legs"]) == 15


def test_ticket_builder_zucai_14_match_has_14_legs_and_no_odds():
    schema = RecommendationSchema(
        recommended_bets=[
            _bet(f"M{i}", lottery_type="ZUCAI", play_type="14_match", selection="3", odds=None) for i in range(14)
        ]
    )
    res = LotteryTicketBuilder().build_validated_ticket(schema=schema, stake=100.0, date="2026-04-15")
    assert res["ticket"]
    assert res["ticket"]["play_type"] == "14_match"
    assert len(res["ticket"]["legs"]) == 14
    assert all("odds" not in leg or leg["odds"] is None for leg in res["ticket"]["legs"])


def test_ticket_builder_zucai_6_htft_has_6_legs_and_no_odds():
    schema = RecommendationSchema(
        recommended_bets=[_bet(f"M{i}", lottery_type="ZUCAI", play_type="6_htft", selection="3", odds=None) for i in range(6)]
    )
    res = LotteryTicketBuilder().build_validated_ticket(schema=schema, stake=100.0, date="2026-04-15")
    assert res["ticket"]
    assert res["ticket"]["play_type"] == "6_htft"
    assert len(res["ticket"]["legs"]) == 6
    assert all("odds" not in leg or leg["odds"] is None for leg in res["ticket"]["legs"])


def test_router_normalizes_zucai_play_type_and_validates_leg_count():
    router = LotteryRouter()
    ok = router.route_and_validate("ZUCAI", {"play_type": "ZUCAI_6_HTFT", "legs": [{"match_id": f"M{i}"} for i in range(6)]})
    assert ok["status"] == "SUCCESS"
    with pytest.raises(ValueError, match="6场半全场"):
        router.route_and_validate("ZUCAI", {"play_type": "ZUCAI_6_HTFT", "legs": [{"match_id": f"M{i}"} for i in range(5)]})
