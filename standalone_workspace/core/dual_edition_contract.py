from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple


_PYTHON_ROOT = Path(__file__).resolve().parents[1]
if str(_PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(_PYTHON_ROOT))


EditionId = Literal["standalone", "openclaw"]
ContractDimension = Literal["isolation", "schema_parity", "capability_matrix_parity"]
Severity = Literal["blocker", "warning"]


@dataclass(frozen=True)
class ContractCheckSpec:
    id: str
    dimension: ContractDimension
    severity: Severity
    title: str
    evaluator: str
    inputs: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CheckResult:
    ok: bool
    check_id: str
    dimension: ContractDimension
    severity: Severity
    title: str
    skipped: bool
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EditionSpec:
    edition: EditionId
    python_root_relpath: str
    data_dir_relpath: str
    datasets_dir_relpath: str
    data_env_var: str
    datasets_env_var: str


EDITIONS: Dict[EditionId, EditionSpec] = {
    "standalone": EditionSpec(
        edition="standalone",
        python_root_relpath="standalone_workspace",
        data_dir_relpath="standalone_workspace/data",
        datasets_dir_relpath="standalone_workspace/datasets",
        data_env_var="STANDALONE_FOOTBALL_DATA_DIR",
        datasets_env_var="STANDALONE_FOOTBALL_DATASETS_DIR",
    ),
    "openclaw": EditionSpec(
        edition="openclaw",
        python_root_relpath="openclaw_workspace/runtime/football_analyzer",
        data_dir_relpath="openclaw_workspace/data",
        datasets_dir_relpath="openclaw_workspace/datasets",
        data_env_var="OPENCLAW_FOOTBALL_DATA_DIR",
        datasets_env_var="OPENCLAW_FOOTBALL_DATASETS_DIR",
    ),
}


CONTRACT_CHECKS: List[ContractCheckSpec] = [
    ContractCheckSpec(
        id="physical_isolation",
        dimension="isolation",
        severity="blocker",
        title="双版本数据目录物理隔离",
        evaluator="core.dual_edition_contract.check_physical_isolation",
        inputs={"a": "standalone", "b": "openclaw"},
    ),
    ContractCheckSpec(
        id="capability_matrix_parity",
        dimension="capability_matrix_parity",
        severity="blocker",
        title="双版本能力矩阵（tool name）一致",
        evaluator="core.dual_edition_contract.check_capability_matrix_parity",
        inputs={"a": "standalone", "b": "openclaw", "source": "tools.tool_registry_v2.get_mcp_tools"},
    ),
    ContractCheckSpec(
        id="tool_schema_parity",
        dimension="schema_parity",
        severity="warning",
        title="双版本工具 schema（inputSchema）一致",
        evaluator="core.dual_edition_contract.check_tool_schema_parity",
        inputs={"a": "standalone", "b": "openclaw", "source": "tools.tool_registry_v2.get_mcp_tools"},
    ),
]


def _find_repo_root(start: Path) -> Optional[Path]:
    for p in [start, *start.parents]:
        if (p / "standalone_workspace").is_dir() and (p / "openclaw_workspace").is_dir():
            return p
    return None


def _tool_registry_dump(python_root: Path) -> Tuple[bool, Dict[str, Any]]:
    code = "\n".join(
        [
            "import json, sys",
            f"sys.path.insert(0, {json.dumps(str(python_root))})",
            "from tools.tool_registry_v2 import get_mcp_tools",
            "tools = get_mcp_tools()",
            "out = []",
            "for t in tools:",
            "    out.append({'name': getattr(t, 'name', None), 'description': getattr(t, 'description', None), 'inputSchema': getattr(t, 'inputSchema', None)})",
            "print(json.dumps(out, ensure_ascii=False, sort_keys=True))",
        ]
    )
    try:
        raw = subprocess.check_output([sys.executable, "-c", code], stderr=subprocess.STDOUT, text=True)
        payload = json.loads(raw.strip() or "[]")
        if not isinstance(payload, list):
            return False, {"error": "unexpected_payload", "raw": raw}
        return True, {"tools": payload}
    except Exception as e:
        return False, {"error": "subprocess_failed", "message": str(e)}


def _normalize_tool_schemas(payload: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for t in payload:
        if not isinstance(t, dict):
            continue
        name = t.get("name")
        if not isinstance(name, str) or not name:
            continue
        schema = t.get("inputSchema") if isinstance(t.get("inputSchema"), dict) else {}
        out[name] = {"name": name, "inputSchema": schema}
    return out


def check_physical_isolation(*, a: EditionId, b: EditionId) -> CheckResult:
    repo_root = _find_repo_root(Path(__file__).resolve())
    if repo_root is None:
        return CheckResult(
            ok=False,
            check_id="physical_isolation",
            dimension="isolation",
            severity="blocker",
            title="双版本数据目录物理隔离",
            skipped=True,
            details={"reason": "repo_root_not_found"},
        )

    a_spec = EDITIONS[a]
    b_spec = EDITIONS[b]

    a_data_other = str((repo_root / b_spec.data_dir_relpath).resolve())
    a_datasets_other = str((repo_root / b_spec.datasets_dir_relpath).resolve())

    ok = True
    details: Dict[str, Any] = {"a": a, "b": b, "checks": []}

    try:
        from tools.paths import data_dir as a_data_dir, datasets_dir as a_datasets_dir

        os.environ[a_spec.data_env_var] = a_data_other
        try:
            a_data_dir()
            ok = False
            details["checks"].append({"target": "data_dir", "ok": False, "reason": "did_not_reject_other_workspace"})
        except Exception:
            details["checks"].append({"target": "data_dir", "ok": True})

        os.environ[a_spec.datasets_env_var] = a_datasets_other
        try:
            a_datasets_dir()
            ok = False
            details["checks"].append({"target": "datasets_dir", "ok": False, "reason": "did_not_reject_other_workspace"})
        except Exception:
            details["checks"].append({"target": "datasets_dir", "ok": True})
    finally:
        os.environ.pop(a_spec.data_env_var, None)
        os.environ.pop(a_spec.datasets_env_var, None)

    return CheckResult(
        ok=ok,
        check_id="physical_isolation",
        dimension="isolation",
        severity="blocker",
        title="双版本数据目录物理隔离",
        skipped=False,
        details=details,
    )


def check_capability_matrix_parity(*, a: EditionId, b: EditionId, source: str) -> CheckResult:
    repo_root = _find_repo_root(Path(__file__).resolve())
    if repo_root is None:
        return CheckResult(
            ok=False,
            check_id="capability_matrix_parity",
            dimension="capability_matrix_parity",
            severity="blocker",
            title="双版本能力矩阵（tool name）一致",
            skipped=True,
            details={"reason": "repo_root_not_found"},
        )

    a_root = repo_root / EDITIONS[a].python_root_relpath
    b_root = repo_root / EDITIONS[b].python_root_relpath
    if not a_root.is_dir() or not b_root.is_dir():
        return CheckResult(
            ok=False,
            check_id="capability_matrix_parity",
            dimension="capability_matrix_parity",
            severity="blocker",
            title="双版本能力矩阵（tool name）一致",
            skipped=True,
            details={"reason": "python_root_missing", "a_root": str(a_root), "b_root": str(b_root)},
        )

    ok_a, dump_a = _tool_registry_dump(a_root)
    ok_b, dump_b = _tool_registry_dump(b_root)
    if not ok_a or not ok_b:
        return CheckResult(
            ok=False,
            check_id="capability_matrix_parity",
            dimension="capability_matrix_parity",
            severity="blocker",
            title="双版本能力矩阵（tool name）一致",
            skipped=True,
            details={"reason": "tool_registry_dump_failed", "a": dump_a, "b": dump_b, "source": source},
        )

    a_tools = _normalize_tool_schemas(dump_a.get("tools") or [])
    b_tools = _normalize_tool_schemas(dump_b.get("tools") or [])
    a_names = set(a_tools.keys())
    b_names = set(b_tools.keys())
    missing_in_b = sorted(a_names - b_names)
    missing_in_a = sorted(b_names - a_names)
    ok = not missing_in_b and not missing_in_a

    return CheckResult(
        ok=ok,
        check_id="capability_matrix_parity",
        dimension="capability_matrix_parity",
        severity="blocker",
        title="双版本能力矩阵（tool name）一致",
        skipped=False,
        details={
            "source": source,
            "a": a,
            "b": b,
            "a_count": len(a_names),
            "b_count": len(b_names),
            "missing_in_b": missing_in_b,
            "missing_in_a": missing_in_a,
        },
    )


def check_tool_schema_parity(*, a: EditionId, b: EditionId, source: str) -> CheckResult:
    repo_root = _find_repo_root(Path(__file__).resolve())
    if repo_root is None:
        return CheckResult(
            ok=False,
            check_id="tool_schema_parity",
            dimension="schema_parity",
            severity="warning",
            title="双版本工具 schema（inputSchema）一致",
            skipped=True,
            details={"reason": "repo_root_not_found"},
        )

    a_root = repo_root / EDITIONS[a].python_root_relpath
    b_root = repo_root / EDITIONS[b].python_root_relpath
    if not a_root.is_dir() or not b_root.is_dir():
        return CheckResult(
            ok=False,
            check_id="tool_schema_parity",
            dimension="schema_parity",
            severity="warning",
            title="双版本工具 schema（inputSchema）一致",
            skipped=True,
            details={"reason": "python_root_missing", "a_root": str(a_root), "b_root": str(b_root)},
        )

    ok_a, dump_a = _tool_registry_dump(a_root)
    ok_b, dump_b = _tool_registry_dump(b_root)
    if not ok_a or not ok_b:
        return CheckResult(
            ok=False,
            check_id="tool_schema_parity",
            dimension="schema_parity",
            severity="warning",
            title="双版本工具 schema（inputSchema）一致",
            skipped=True,
            details={"reason": "tool_registry_dump_failed", "a": dump_a, "b": dump_b, "source": source},
        )

    a_tools = _normalize_tool_schemas(dump_a.get("tools") or [])
    b_tools = _normalize_tool_schemas(dump_b.get("tools") or [])
    common = sorted(set(a_tools.keys()) & set(b_tools.keys()))
    diffs: List[Dict[str, Any]] = []
    for name in common:
        if a_tools[name].get("inputSchema") != b_tools[name].get("inputSchema"):
            diffs.append({"tool": name})

    ok = not diffs
    return CheckResult(
        ok=ok,
        check_id="tool_schema_parity",
        dimension="schema_parity",
        severity="warning",
        title="双版本工具 schema（inputSchema）一致",
        skipped=False,
        details={
            "source": source,
            "a": a,
            "b": b,
            "common": len(common),
            "diff_count": len(diffs),
            "diff_tools": [d["tool"] for d in diffs],
        },
    )


def run_contract_checks() -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    for spec in CONTRACT_CHECKS:
        if spec.id == "physical_isolation":
            res = check_physical_isolation(a=spec.inputs["a"], b=spec.inputs["b"])
        elif spec.id == "capability_matrix_parity":
            res = check_capability_matrix_parity(a=spec.inputs["a"], b=spec.inputs["b"], source=spec.inputs["source"])
        elif spec.id == "tool_schema_parity":
            res = check_tool_schema_parity(a=spec.inputs["a"], b=spec.inputs["b"], source=spec.inputs["source"])
        else:
            res = CheckResult(
                ok=False,
                check_id=spec.id,
                dimension=spec.dimension,
                severity=spec.severity,
                title=spec.title,
                skipped=True,
                details={"reason": "unknown_check"},
            )
        results.append(res.to_dict())

    blockers_failed = [r for r in results if r.get("severity") == "blocker" and r.get("skipped") is False and r.get("ok") is False]
    return {
        "ok": len(blockers_failed) == 0,
        "results": results,
        "meta": {"blockers_failed": len(blockers_failed)},
    }
