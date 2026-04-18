from pathlib import Path


def test_capability_matrix_smoke_tests_no_fail_offline():
    from tools.capability_matrix_smoke import run_capability_smoke_tests

    ws_root = Path(__file__).resolve().parents[1]
    report = run_capability_smoke_tests(offline=True, workspace_root=ws_root)
    assert report["overall_status"] in {"PASS", "DEGRADED"}
    assert not any(i["status"] == "FAIL" for i in report["items"])

