from tools.historical_impact import build_historical_impact, to_explain_item


def test_historical_impact_schema_has_required_keys():
    hi = build_historical_impact(
        lottery_type="JINGCAI",
        league_code="E0",
        odds={"home": 2.1, "draw": 3.4, "away": 3.2},
        analysis={
            "calibration_info": {
                "calibrated": True,
                "historical_weight": 0.25,
                "sample_size": 1000,
                "hist_distribution": {"home": 0.45, "draw": 0.26, "away": 0.29},
            },
            "league_stats": {
                "avg_goals": 2.7,
                "over_2_5_rate": 0.52,
                "btts_rate": 0.47,
                "draw_rate": 0.26,
                "sample_size": 1000,
            },
        },
        similar_odds_result={"ok": True, "data": []},
        data_source={"raw_json_path": "x", "chroma_db_path": "y"},
    )
    assert hi["enabled"] is True
    assert hi["lottery_type"] == "JINGCAI"
    assert "league_stats" in hi
    assert "market_calibration" in hi
    assert "similar_odds" in hi
    assert "data_source" in hi
    assert isinstance(hi["degradations"], list)


def test_historical_explain_item_contains_summary_and_samples():
    hi = build_historical_impact(
        lottery_type="ZUCAI",
        league_code="E0",
        odds=None,
        analysis={},
        similar_odds_result=None,
        data_source={"raw_json_path": "x", "chroma_db_path": "y"},
    )
    item = to_explain_item(hi)
    assert item["type"] == "historical_impact"
    assert "summary" in item
    assert "samples" in item

