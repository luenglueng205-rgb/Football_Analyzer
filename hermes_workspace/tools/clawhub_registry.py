from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Literal

from pydantic import BaseModel, Field


def _normalize_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(schema, dict):
        return {}
    out = dict(schema)
    out.pop("title", None)
    return out


class ClawHubCallTarget(BaseModel):
    kind: Literal["tool_registry_v2"] = "tool_registry_v2"
    name: str


class ClawHubToolEntry(BaseModel):
    name: str
    description: str = ""
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    call_target: ClawHubCallTarget


class ClawHubRegistrySpec(BaseModel):
    schema_version: str = "clawhub_registry_v1"
    tools: List[ClawHubToolEntry] = Field(default_factory=list)


def clawhub_registry_json_schema() -> Dict[str, Any]:
    schema = ClawHubRegistrySpec.model_json_schema()
    schema.pop("title", None)
    return schema


class ClawHubRegistry:
    def __init__(self, path: Optional[Path], spec: ClawHubRegistrySpec):
        self.path = path
        self.spec = spec
        self._by_name = {t.name: t for t in self.spec.tools}

    @classmethod
    def load_from_env(cls, *, existing_tool_names: Optional[Set[str]] = None) -> "ClawHubRegistry":
        existing = set(existing_tool_names or set())
        path_str = os.getenv("CLAWHUB_REGISTRY_PATH")
        if not path_str:
            reg = cls(None, ClawHubRegistrySpec())
            reg._validate(existing_tool_names=existing)
            return reg

        path = Path(path_str)
        if not path.exists():
            reg = cls(path, ClawHubRegistrySpec())
            reg._validate(existing_tool_names=existing)
            return reg

        raw = json.loads(path.read_text(encoding="utf-8"))
        spec = ClawHubRegistrySpec.model_validate(raw)
        reg = cls(path, spec)
        reg._validate(existing_tool_names=existing)
        return reg

    def _validate(self, *, existing_tool_names: Set[str]) -> None:
        names = [t.name for t in self.spec.tools]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate tool names inside ClawHub registry")

        dup = set(names) & set(existing_tool_names)
        if dup:
            raise ValueError(f"ClawHub tool names conflict with existing registry: {sorted(dup)}")

    def export_tools(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for t in self.spec.tools:
            out.append(
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.input_schema,
                    "call_target": t.call_target.model_dump(),
                }
            )
        return out

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        tool = self._by_name.get(name)
        if tool is None:
            return {
                "ok": False,
                "data": None,
                "error": {"code": "UNKNOWN_CLAWHUB_TOOL", "message": f"Tool {name} not found in ClawHub registry"},
                "meta": {"mock": False, "source": "clawhub"},
            }

        if tool.call_target.kind != "tool_registry_v2":
            return {
                "ok": False,
                "data": None,
                "error": {"code": "UNSUPPORTED_CALL_TARGET", "message": f"Unsupported call target: {tool.call_target.kind}"},
                "meta": {"mock": False, "source": "clawhub"},
            }

        from tools import tool_registry_v2

        target = tool_registry_v2.REGISTRY.get(tool.call_target.name)
        if target is None:
            return {
                "ok": False,
                "data": None,
                "error": {"code": "UNKNOWN_CALL_TARGET", "message": f"Call target {tool.call_target.name} not found"},
                "meta": {"mock": False, "source": "clawhub"},
            }

        expected_schema = _normalize_schema(target.model.model_json_schema())
        actual_schema = _normalize_schema(tool.input_schema)
        if expected_schema != actual_schema:
            return {
                "ok": False,
                "data": None,
                "error": {
                    "code": "SCHEMA_MISMATCH",
                    "message": "ClawHub input_schema does not match call_target schema",
                },
                "meta": {
                    "mock": False,
                    "source": "clawhub",
                    "clawhub_tool": tool.name,
                    "call_target": tool.call_target.model_dump(),
                },
            }

        res = await tool_registry_v2.execute_tool(tool.call_target.name, arguments)
        if isinstance(res, dict):
            meta = dict(res.get("meta") or {})
            meta.update(
                {
                    "clawhub": True,
                    "clawhub_tool": tool.name,
                    "call_target": tool.call_target.model_dump(),
                }
            )
            res["meta"] = meta
        return res
