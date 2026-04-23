def test_match_identity_stable_across_sources():
    from core.match_identity import MatchIdentityBuilder

    b = MatchIdentityBuilder()
    mid1 = b.build("英超", "Arsenal", "Tottenham", "2026-04-15 20:00")
    mid2 = b.build("Premier League", "阿森纳", "热刺", "2026-04-15 20:00")
    assert mid1 == mid2


def test_league_resolver_handles_common_aliases():
    from core.match_identity import LeagueResolver

    r = LeagueResolver()
    assert r.resolve_code("英超") == "E0"
    assert r.resolve_code("英格兰超级联赛") == "E0"
    assert r.resolve_code("Premier League") == "E0"
    assert r.resolve_code("西甲") == "SP1"
    assert r.resolve_code("意甲") == "I1"
    assert r.resolve_code("德甲") == "D1"
    assert r.resolve_code("法甲") == "F1"
    assert r.resolve_code("中超") == "CHN"


def test_team_resolver_handles_aliases():
    from core.match_identity import TeamResolver

    r = TeamResolver()
    assert r.resolve_team_id("阿森纳") == "ARS"
    assert r.resolve_team_id("Arsenal") == "ARS"
    assert r.resolve_team_id("热刺") == "TOT"
    assert r.resolve_team_id("Tottenham") == "TOT"
