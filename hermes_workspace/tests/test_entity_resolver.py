from tools.entity_resolver import EntityResolver


def test_entity_resolver_aliases():
    r = EntityResolver()
    team = r.resolve_team("曼城")
    assert team["ok"] is True
    assert team["data"]["canonical_name"] == "曼城"
    assert isinstance(team["data"]["team_id"], str)

    team2 = r.resolve_team("Manchester City")
    assert team2["ok"] is True
    assert team2["data"]["team_id"] == team["data"]["team_id"]


if __name__ == "__main__":
    test_entity_resolver_aliases()
    print("test_entity_resolver_aliases PASSED")

