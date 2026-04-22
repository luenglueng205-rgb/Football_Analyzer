from pathlib import Path


def test_capability_matrix_smoke_tests_pass_offline_with_repo_fixtures():
    from tools.capability_matrix_smoke import run_capability_smoke_tests

    ws_root = Path(__file__).resolve().parents[1]
    report = run_capability_smoke_tests(offline=True, workspace_root=ws_root)
    assert report["overall_status"] == "PASS"

    items = report["items"]
    assert items
    assert not any(i["status"] == "FAIL" for i in items)

    by_id = {i["id"]: i for i in items}
    assert by_id["JINGCAI.fetch_sp.offline_fixture"]["status"] == "PASS"
    assert by_id["BEIDAN.fetch_sp.offline_fixture"]["status"] == "PASS"
    assert by_id["ZUCAI.parlay_combinatorics"]["status"] == "PASS"

