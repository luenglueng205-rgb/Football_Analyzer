from tools.market_probability_engine import MarketProbabilityEngine


def test_market_probability_engine_goals_distribution_sums_to_one():
    eng = MarketProbabilityEngine(max_goals=7)
    dist = eng.goals_distribution(home_xg=1.2, away_xg=0.8)
    assert abs(sum(dist.values()) - 1.0) < 1e-6
    assert "7+" in dist


def test_market_probability_engine_wdl_probs_sums_to_one():
    eng = MarketProbabilityEngine()
    p = eng.wdl_from_xg(home_xg=1.4, away_xg=1.0)
    assert abs(sum(p.values()) - 1.0) < 1e-6
    assert set(p.keys()) == {"3", "1", "0"}


def test_market_probability_engine_handicap_wdl_probs_sums_to_one():
    eng = MarketProbabilityEngine()
    p = eng.handicap_wdl_from_xg(home_xg=1.2, away_xg=1.2, handicap=-1.0)
    assert abs(sum(p.values()) - 1.0) < 1e-6
    assert set(p.keys()) == {"3", "1", "0"}


def test_market_probability_engine_cs_topk_probs_sums_to_one():
    eng = MarketProbabilityEngine()
    top = eng.cs_topk(home_xg=1.3, away_xg=0.9, k=12)
    assert abs(sum(top.values()) - 1.0) < 1e-6
    assert len(top) == 12
