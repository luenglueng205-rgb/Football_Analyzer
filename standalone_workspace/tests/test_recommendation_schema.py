import pytest

from agents.analyst import AnalystAgent
from core.recommendation_schema import RecommendationSchemaAdapter
from tools.odds_analyzer import OddsAnalyzer
from tools.smart_bet_selector import SmartBetSelector


def test_analyst_output_contains_recommendation_schema():
    agent = AnalystAgent()
    res = agent.process(
        {
            "action": "analyze_odds",
            "params": {"match_id": "M1", "odds": {"home": 2.0, "draw": 3.4, "away": 3.8}},
        }
    )
    schema = res["recommendation_schema"]
    assert isinstance(schema, dict)
    assert "recommended_bets" in schema
    assert len(schema["recommended_bets"]) == 1
    assert schema["recommended_bets"][0]["match_id"] == "M1"


def test_odds_analyzer_output_contains_recommendation_schema():
    analyzer = OddsAnalyzer(use_historical=False)
    res = analyzer.analyze({"home": 2.0, "draw": 3.4, "away": 3.8}, league=None, calibrate=False)
    schema = res["recommendation_schema"]
    assert isinstance(schema, dict)
    assert "recommended_bets" in schema
    assert "audit" in schema


def test_smart_bet_selector_can_export_schema():
    selector = SmartBetSelector()
    match_1 = {
        "match_id": "M1",
        "home_team": "Man City",
        "markets": {
            "1x2": {"home": {"odds": 1.10, "prob": 0.85}, "draw": {"odds": 9.0, "prob": 0.10}},
            "handicap_-2": {"home": {"odds": 2.5, "prob": 0.45}},
        },
    }
    match_2 = {
        "match_id": "M2",
        "home_team": "Chelsea",
        "markets": {
            "1x2": {"home": {"odds": 2.5, "prob": 0.35}},
            "total": {"under_2.5": {"odds": 1.9, "prob": 0.60}},
        },
    }
    schema = selector.extract_value_bets_schema([match_1, match_2])
    assert "recommended_bets" in schema
    assert len(schema["recommended_bets"]) == 2
    assert schema["recommended_bets"][0]["match_id"] in {"M1", "M2"}


def test_recommendation_schema_calibrated_prob_within_bounds_and_ev_uses_calibrated_prob():
    out = {
        "recommendation": {"primary": "home"},
        "probabilities": {"home": 0.9, "draw": 0.2, "away": -0.1},
        "odds": {"home": 2.0, "draw": 3.0, "away": 4.0},
        "anomalies": [],
    }
    schema = RecommendationSchemaAdapter.from_analyst_output(out, match_id="M1").to_dict()
    bet = schema["recommended_bets"][0]
    assert 0.0 <= bet["prob"] <= 1.0
    assert bet["ev"] == pytest.approx(bet["prob"] * bet["odds"], rel=1e-9, abs=1e-12)


def test_recommendation_schema_calibration_handles_invalid_model_prob():
    out = {
        "recommendation": {"primary": "draw"},
        "probabilities": {"home": 10.0, "draw": 2.0, "away": 1.0},
        "odds": {"home": 2.2, "draw": 3.1, "away": 3.4},
        "anomalies": [],
    }
    schema = RecommendationSchemaAdapter.from_analyst_output(out, match_id="M1").to_dict()
    bet = schema["recommended_bets"][0]
    assert 0.0 <= bet["prob"] <= 1.0
