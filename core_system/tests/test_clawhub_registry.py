import asyncio
import json

from tools.mcp_tools import call_clawhub_tool, list_clawhub_tools
from tools.tool_registry_v2 import REGISTRY


def _schema_for(tool_name: str) -> dict:
    schema = REGISTRY[tool_name].model.model_json_schema()
    schema.pop("title", None)
    return schema


def test_clawhub_registry_list_and_proxy_call(tmp_path, monkeypatch):
    registry_path = tmp_path / "clawhub_registry.json"
    tool_name = "clawhub_analyze_water_drop"
    payload = {
        "schema_version": "clawhub_registry_v1",
        "tools": [
            {
                "name": tool_name,
                "description": "ClawHub alias for analyze_water_drop",
                "input_schema": _schema_for("analyze_water_drop"),
                "call_target": {"kind": "tool_registry_v2", "name": "analyze_water_drop"},
            }
        ],
    }
    registry_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("CLAWHUB_REGISTRY_PATH", str(registry_path))

    listed = list_clawhub_tools()
    assert listed["ok"] is True
    names = [t["name"] for t in listed["data"]["tools"]]
    assert tool_name in names

    res = asyncio.run(call_clawhub_tool(tool_name, {"opening_water": 1.05, "live_water": 0.85}))
    assert res["ok"] is True
    assert res.get("meta", {}).get("clawhub") is True


def test_clawhub_registry_rejects_duplicate_name_with_internal(tmp_path, monkeypatch):
    registry_path = tmp_path / "clawhub_registry.json"
    payload = {
        "schema_version": "clawhub_registry_v1",
        "tools": [
            {
                "name": "analyze_water_drop",
                "description": "conflict",
                "input_schema": _schema_for("analyze_water_drop"),
                "call_target": {"kind": "tool_registry_v2", "name": "analyze_water_drop"},
            }
        ],
    }
    registry_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("CLAWHUB_REGISTRY_PATH", str(registry_path))

    listed = list_clawhub_tools()
    assert listed["ok"] is False
    assert listed["error"]["code"] == "REGISTRY_LOAD_FAILED"


def test_clawhub_registry_schema_mismatch(tmp_path, monkeypatch):
    registry_path = tmp_path / "clawhub_registry.json"
    tool_name = "clawhub_bad_schema"
    payload = {
        "schema_version": "clawhub_registry_v1",
        "tools": [
            {
                "name": tool_name,
                "description": "bad schema",
                "input_schema": {"type": "object", "properties": {}},
                "call_target": {"kind": "tool_registry_v2", "name": "analyze_water_drop"},
            }
        ],
    }
    registry_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("CLAWHUB_REGISTRY_PATH", str(registry_path))

    res = asyncio.run(call_clawhub_tool(tool_name, {"opening_water": 1.05, "live_water": 0.85}))
    assert res["ok"] is False
    assert res["error"]["code"] == "SCHEMA_MISMATCH"
