import asyncio
import json
import os
import sys


SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from mcp_server import handle_request


def _list_tools():
    resp = asyncio.run(handle_request({"method": "list_tools"}))
    assert "tools" in resp
    assert isinstance(resp["tools"], list)
    return resp["tools"]


def _find_tool(tools, name: str):
    for t in tools:
        if isinstance(t, dict) and t.get("name") == name:
            return t
    return None


def _call_tool(name: str, arguments: dict):
    req = {"method": "call_tool", "params": {"name": name, "arguments": arguments}}
    return asyncio.run(handle_request(req))


def _extract_json_payload(resp):
    assert "result" in resp
    assert isinstance(resp["result"], list)
    assert resp["result"]
    text = resp["result"][0]["text"]
    return json.loads(text)


def test_mcp_self_audit_tool_listed_and_schema_present():
    tool = _find_tool(_list_tools(), "self_audit")
    assert tool is not None
    assert "parameters" in tool
    params = tool["parameters"]
    assert params.get("type") == "object"
    assert "properties" in params
    assert "online" in params["properties"]
    assert "deep" in params["properties"]


def test_mcp_self_audit_callable_and_output_schema_present():
    payload = _extract_json_payload(_call_tool("self_audit", {}))
    assert payload["schema_version"] == "1.0"
    assert "edition" in payload
    assert "network" in payload
    assert "capability_matrix" in payload
    assert "historical_data" in payload
    assert "drift_diagnosis" in payload
    assert payload["network"]["enabled"] is False
    assert "root_data" in payload["historical_data"]
    assert "standalone_data" in payload["historical_data"]
    assert "root_vs_standalone" in payload["historical_data"]

    deep_payload = _extract_json_payload(_call_tool("self_audit", {"deep": True}))
    assert deep_payload["historical_data"]["deep"] is True
