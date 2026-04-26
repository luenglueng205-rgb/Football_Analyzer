import json

from scripts import self_audit_cli


def test_self_audit_drift_bloat_diagnosis_has_expected_keys_and_lists():
    payload = self_audit_cli.collect_self_audit(offline=True)
    diag = payload["drift_diagnosis"]

    assert diag["schema_version"] == "1.0"
    assert diag["status"] in {"ok", "warning", "risk"}
    assert isinstance(diag["signal_definitions"], list)
    assert isinstance(diag["signals"], list)
    assert diag["signals"]

    ids = {s.get("id") for s in diag["signals"]}
    assert {"dup_modules", "multiple_data_paths", "dual_registries", "mock_in_critical_chain"} <= ids

    kcm = diag["keep_cut_merge"]
    assert set(kcm.keys()) == {"keep", "cut", "merge"}
    assert isinstance(kcm["keep"], list) and kcm["keep"]
    assert isinstance(kcm["cut"], list) and kcm["cut"]
    assert isinstance(kcm["merge"], list) and kcm["merge"]

    assert isinstance(diag["slimming_plan"], list)
    assert diag["slimming_plan"]

    json.dumps(payload, ensure_ascii=False)

