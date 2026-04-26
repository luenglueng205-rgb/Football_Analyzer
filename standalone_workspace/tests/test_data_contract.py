import pytest


def test_normalized_match_requires_audit_fields():
    from core.data_contract import NormalizedMatch

    m = NormalizedMatch(
        match_id="20260415_E0_ARS_TOT",
        league_code="E0",
        home_team_id="ARS",
        away_team_id="TOT",
        kickoff_time_utc="2026-04-15T12:00:00Z",
        status="SCHEDULED",
        source="CN_500",
        confidence=0.9,
        raw_ref="snapshot:fixtures:500:hash",
    )
    assert m.source == "CN_500"


def test_normalized_match_confidence_range():
    from core.data_contract import NormalizedMatch

    with pytest.raises(ValueError):
        NormalizedMatch(
            match_id="20260415_E0_ARS_TOT",
            league_code="E0",
            home_team_id="ARS",
            away_team_id="TOT",
            kickoff_time_utc="2026-04-15T12:00:00Z",
            status="SCHEDULED",
            source="CN_500",
            confidence=1.1,
            raw_ref="snapshot:fixtures:500:hash",
        )


def test_normalized_odds_requires_audit_fields():
    from core.data_contract import NormalizedOdds

    o = NormalizedOdds(
        match_id="20260415_E0_ARS_TOT",
        lottery_type="JINGCAI",
        play_type="JINGCAI_WDL",
        market="WDL",
        handicap=None,
        selections={
            "H": {"odds": 1.95, "last_update": "2026-04-15T10:00:00Z"},
            "D": {"odds": 3.4, "last_update": "2026-04-15T10:00:00Z"},
            "A": {"odds": 3.8, "last_update": "2026-04-15T10:00:00Z"},
        },
        source="CN_500",
        confidence=0.85,
        raw_ref="snapshot:odds:500:hash",
    )
    assert o.market == "WDL"

