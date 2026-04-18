import asyncio
import json
import os
import sys


SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from mcp_server import handle_request


def _call_tool(name: str, arguments: dict):
    req = {"method": "call_tool", "params": {"name": name, "arguments": arguments}}
    return asyncio.run(handle_request(req))


def _extract_json_payload(resp):
    assert "result" in resp
    assert isinstance(resp["result"], list)
    assert resp["result"]
    text = resp["result"][0]["text"]
    return json.loads(text)


def test_openclaw_self_audit_drift_bloat_diagnosis_has_expected_keys_and_lists():
    payload = _extract_json_payload(_call_tool("self_audit", {}))
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

