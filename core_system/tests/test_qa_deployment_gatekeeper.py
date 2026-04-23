import os

import pytest


def _dummy_complete_report():
    return {
        "coverage_percentage": 100.0,
        "covered_nodes": 96,
        "total_nodes": 96,
        "is_complete": True,
        "missing_nodes": [],
        "matrix_data": {},
    }


def test_gatekeeper_runs_matrix_then_core_tests(monkeypatch, tmp_path):
    from scripts import qa_deployment_gatekeeper as gatekeeper

    calls = []
    subprocess_calls = []

    def fake_pytest_main(args):
        calls.append(list(args))
        return 0

    class DummyTracker:
        def get_coverage_report(self):
            return _dummy_complete_report()

    monkeypatch.setattr(gatekeeper.pytest, "main", fake_pytest_main)
    monkeypatch.setattr(gatekeeper, "get_global_tracker", lambda: DummyTracker())
    monkeypatch.setenv("QA_GATEKEEPER_REPORT_DIR", str(tmp_path))

    class _Proc:
        def __init__(self, returncode: int):
            self.returncode = returncode

    def fake_subprocess_run(args, cwd=None):
        subprocess_calls.append({"args": list(args), "cwd": cwd})
        return _Proc(0)

    monkeypatch.setattr(gatekeeper.subprocess, "run", fake_subprocess_run)

    with pytest.raises(SystemExit) as ex:
        gatekeeper.run_gatekeeper()

    assert ex.value.code == 0
    assert len(calls) == 1
    assert len(subprocess_calls) == 1

    assert any("qa_matrix_tests" in str(x) for x in calls[0])

    core_call = subprocess_calls[0]["args"]
    for name in gatekeeper.CORE_CLOSED_LOOP_TESTS:
        assert any(str(x).endswith(os.path.join("tests", name)) for x in core_call)


def test_gatekeeper_fails_when_core_tests_fail(monkeypatch, tmp_path):
    from scripts import qa_deployment_gatekeeper as gatekeeper

    calls = []

    def fake_pytest_main(args):
        calls.append(list(args))
        return 0

    class DummyTracker:
        def get_coverage_report(self):
            return _dummy_complete_report()

    monkeypatch.setattr(gatekeeper.pytest, "main", fake_pytest_main)
    monkeypatch.setattr(gatekeeper, "get_global_tracker", lambda: DummyTracker())
    monkeypatch.setenv("QA_GATEKEEPER_REPORT_DIR", str(tmp_path))

    class _Proc:
        def __init__(self, returncode: int):
            self.returncode = returncode

    monkeypatch.setattr(gatekeeper.subprocess, "run", lambda *a, **k: _Proc(2))

    with pytest.raises(SystemExit) as ex:
        gatekeeper.run_gatekeeper()

    assert ex.value.code == 1
    assert len(calls) == 1
