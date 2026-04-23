import math


def calculate_clv(placed_odds: float, closing_odds: float) -> dict:
    if placed_odds <= 0 or closing_odds <= 0:
        return {"ok": False, "data": None, "error": {"code": "BAD_INPUT", "message": "odds must be > 0"}, "meta": {"mock": False, "source": "clv"}}
    return {
        "ok": True,
        "data": {"clv": math.log(closing_odds / placed_odds), "placed_odds": placed_odds, "closing_odds": closing_odds},
        "error": None,
        "meta": {"mock": False, "source": "clv"},
    }

