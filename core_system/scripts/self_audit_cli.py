from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO, Tuple


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

try:
    from scripts import __version__ as scripts_version
except Exception:
    scripts_version = "unknown"

from tools.capability_matrix_smoke import run_capability_smoke_tests


def _safe_rel(path: Path, root: Optional[Path]) -> str:
    if root is None:
        return str(path)
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except Exception:
        return str(path)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _list_py_files(dir_path: Path) -> List[Path]:
    if not dir_path.is_dir():
        return []
    return [p for p in dir_path.rglob("*.py") if p.is_file()]


def _detect_duplicate_modules(*, repo_root: Optional[Path]) -> Dict[str, Any]:
    if not repo_root:
        return {"available": False, "count": 0, "samples": [], "reason": "repo_root_not_found"}
    standalone_root = (repo_root / "standalone_workspace").resolve()
    openclaw_root = (repo_root / "openclaw_workspace" / "runtime" / "football_analyzer").resolve()
    if not standalone_root.is_dir() or not openclaw_root.is_dir():
        return {"available": False, "count": 0, "samples": [], "reason": "one_side_missing"}

    samples: List[Dict[str, Any]] = []
    count = 0
    for rel_dir in ["agents", "tools", "core", "scripts"]:
        a_dir = standalone_root / rel_dir
        b_dir = openclaw_root / rel_dir
        a_files = {p.relative_to(a_dir): p for p in _list_py_files(a_dir)} if a_dir.is_dir() else {}
        b_files = {p.relative_to(b_dir): p for p in _list_py_files(b_dir)} if b_dir.is_dir() else {}
        overlap = sorted(set(a_files.keys()) & set(b_files.keys()))
        count += len(overlap)
        if len(samples) < 20:
            for rel in overlap[: max(0, 20 - len(samples))]:
                samples.append(
                    {
                        "relative": str(Path(rel_dir) / rel),
                        "standalone": str(a_files[rel]),
                        "openclaw": str(b_files[rel]),
                    }
                )

    return {"available": True, "count": count, "samples": samples}


def _detect_dual_registries(*, ws_root: Path, repo_root: Optional[Path]) -> Dict[str, Any]:
    tools_dir = (ws_root / "tools").resolve()
    candidates = [
        tools_dir / "tool_registry.py",
        tools_dir / "tool_registry_v2.py",
        tools_dir / "tool_registry_v3.py",
    ]
    present = [p for p in candidates if p.is_file()]
    used_by = []
    agents_dir = (ws_root / "agents").resolve()
    if agents_dir.is_dir():
        for p in sorted(_list_py_files(agents_dir)):
            txt = _read_text(p)
            if "tool_registry_v2" in txt or "tool_registry" in txt:
                used_by.append(_safe_rel(p, repo_root))
                if len(used_by) >= 20:
                    break
    return {
        "present": [_safe_rel(p, repo_root) for p in present],
        "has_tool_registry": (tools_dir / "tool_registry.py").is_file(),
        "has_tool_registry_v2": (tools_dir / "tool_registry_v2.py").is_file(),
        "used_by_samples": used_by,
    }


def _detect_mock_in_critical_chain(*, ws_root: Path, repo_root: Optional[Path]) -> Dict[str, Any]:
    markers = ["mock", "dummy", "fake", "simulate", "live_mock"]
    critical_rel = [
        Path("agents/orchestrator.py"),
        Path("agents/scout.py"),
        Path("agents/analyst.py"),
        Path("agents/strategist.py"),
        Path("agents/risk_manager.py"),
        Path("agents/async_scout.py"),
        Path("agents/async_analyst.py"),
        Path("agents/async_risk_manager.py"),
        Path("agents/syndicate_os.py"),
        Path("tools/multisource_fetcher.py"),
        Path("tools/analyzer_api.py"),
        Path("tools/llm_service.py"),
        Path("tools/paths.py"),
        Path("tools/tool_registry.py"),
        Path("tools/tool_registry_v2.py"),
    ]
    hits: List[Dict[str, Any]] = []
    for rel in critical_rel:
        path = (ws_root / rel).resolve()
        if not path.is_file():
            continue
        txt = _read_text(path).lower()
        found = [m for m in markers if m in txt]
        if found:
            hits.append({"file": _safe_rel(path, repo_root), "markers": found[:5]})
    return {"hit_count": len(hits), "hits": hits[:20]}


def _generate_drift_bloat_diagnosis(*, ws_root: Path, repo_root: Optional[Path], mismatch: Dict[str, Any]) -> Dict[str, Any]:
    defs = [
        {"id": "dup_modules", "title": "重复模块", "description": "standalone 与 openclaw/runtime 存在同名同路径模块，导致双维护与漂移风险"},
        {"id": "multiple_data_paths", "title": "多数据路径", "description": "root/data 与 workspace/data（或 env var）并存，导致数据可见性与一致性漂移"},
        {"id": "dual_registries", "title": "双注册表", "description": "存在 tool_registry 与 tool_registry_v2 等并行注册入口，工具暴露与权限策略易分叉"},
        {"id": "mock_in_critical_chain", "title": "Mock 混入关键链路", "description": "关键链路使用 mock/dummy/fake/live_mock 等标记，可能污染实盘或让回归不可预测"},
    ]

    dup = _detect_duplicate_modules(repo_root=repo_root)
    dual_reg = _detect_dual_registries(ws_root=ws_root, repo_root=repo_root)
    mock = _detect_mock_in_critical_chain(ws_root=ws_root, repo_root=repo_root)

    multi_data_triggered = bool(mismatch.get("root_vs_standalone_path_diff")) or (
        bool(mismatch.get("root_has_raw_json")) and bool(mismatch.get("standalone_has_raw_json"))
    )

    signals: List[Dict[str, Any]] = [
        {
            "id": "dup_modules",
            "triggered": bool(dup.get("available") and dup.get("count")),
            "severity": "warn" if dup.get("available") and dup.get("count") else "info",
            "evidence": dup,
        },
        {
            "id": "multiple_data_paths",
            "triggered": bool(multi_data_triggered),
            "severity": "high" if mismatch.get("root_vs_standalone_path_diff") else ("warn" if multi_data_triggered else "info"),
            "evidence": {
                "repo_data_dir": mismatch.get("repo_data_dir"),
                "standalone_data_dir": mismatch.get("standalone_data_dir"),
                "root_vs_standalone_path_diff": mismatch.get("root_vs_standalone_path_diff"),
                "root_has_raw_json": mismatch.get("root_has_raw_json"),
                "standalone_has_raw_json": mismatch.get("standalone_has_raw_json"),
            },
        },
        {
            "id": "dual_registries",
            "triggered": bool(dual_reg.get("has_tool_registry") and dual_reg.get("has_tool_registry_v2")),
            "severity": "warn" if dual_reg.get("has_tool_registry") and dual_reg.get("has_tool_registry_v2") else "info",
            "evidence": dual_reg,
        },
        {
            "id": "mock_in_critical_chain",
            "triggered": bool(mock.get("hit_count")),
            "severity": "high" if mock.get("hit_count") else "info",
            "evidence": mock,
        },
    ]

    keep = [
        {
            "id": "canonical_tool_registry_v2",
            "title": "保留统一工具注册表（v2）作为唯一对外工具面",
            "files": [
                _safe_rel((ws_root / "tools" / "tool_registry_v2.py").resolve(), repo_root),
            ],
        },
        {
            "id": "self_audit_cli_entrypoint",
            "title": "保留 standalone 自检入口（离线确定性）",
            "files": [
                _safe_rel((ws_root / "scripts" / "self_audit_cli.py").resolve(), repo_root),
            ],
        },
    ]

    cut = [
        {
            "id": "cut_tool_registry_legacy",
            "title": "移除旧版工具注册表（迁移后删除）",
            "files": [
                _safe_rel((ws_root / "tools" / "tool_registry.py").resolve(), repo_root),
            ],
        },
        {
            "id": "cut_root_data_dependency",
            "title": "切断对 repo_root/data 的隐式依赖（只认 STANDALONE_FOOTBALL_DATA_DIR）",
            "files": [
                "workspace/data/",
                "standalone_workspace/tools/paths.py",
            ],
        },
    ]

    merge = [
        {
            "id": "merge_dual_registries",
            "title": "合并 tool_registry -> tool_registry_v2（react_scout 等迁移）",
            "files": [
                _safe_rel((ws_root / "agents" / "react_scout.py").resolve(), repo_root),
                _safe_rel((ws_root / "tools" / "tool_registry.py").resolve(), repo_root),
                _safe_rel((ws_root / "tools" / "tool_registry_v2.py").resolve(), repo_root),
            ],
        },
        {
            "id": "merge_dual_edition_duplicates",
            "title": "收敛双版本重复模块（选定单一 source-of-truth 并同步生成/复制）",
            "files": [s.get("relative") for s in (dup.get("samples") or []) if s.get("relative")],
        },
    ]

    slimming_plan = [
        {
            "phase": 0,
            "title": "止血：先保证能力矩阵与数据可见性不再回退",
            "goals": ["保证自检可稳定输出", "确保历史数据路径唯一且可追踪"],
            "actions": [
                {"id": "freeze_data_dir", "change": "统一 STANDALONE_FOOTBALL_DATA_DIR，禁止隐式读取 repo_root/data", "evidence": "historical_data.root_vs_standalone"},
                {"id": "guard_mocks", "change": "关键链路 mock 必须受 offline/dev 开关保护", "evidence": "drift_diagnosis.signals.mock_in_critical_chain"},
            ],
        },
        {
            "phase": 1,
            "title": "合并：消除双注册表与双入口的分叉点",
            "goals": ["工具暴露面唯一", "入口与 schema 一致"],
            "actions": [
                {"id": "registry_unification", "change": "react_scout 迁移到 tool_registry_v2，逐步删除 tool_registry.py"},
                {"id": "entrypoint_contract", "change": "self_audit 的 drift_diagnosis 作为双版本契约的一部分固化"},
            ],
        },
        {
            "phase": 2,
            "title": "瘦身：收敛重复模块与数据抓取路径",
            "goals": ["减少重复文件维护成本", "减少多路径回退导致的漂移"],
            "actions": [
                {"id": "dedupe_modules", "change": "选定 canonical 目录（推荐 standalone_workspace），openclaw/runtime 通过同步生成"},
                {"id": "prune_fetch_paths", "change": "多数据源抓取只保留 1 条主路径 + 1 条明确降级路径（写入自检证据）"},
            ],
        },
    ]

    severities = [s.get("severity") for s in signals]
    status = "risk" if "high" in severities else ("warning" if "warn" in severities else "ok")

    return {
        "schema_version": "1.0",
        "status": status,
        "signal_definitions": defs,
        "signals": signals,
        "keep_cut_merge": {"keep": keep, "cut": cut, "merge": merge},
        "slimming_plan": slimming_plan,
    }


def _find_repo_root(start: Path) -> Optional[Path]:
    for p in [start, *start.parents]:
        if (p / "standalone_workspace").is_dir() and (p / "openclaw_workspace").is_dir():
            return p
    return None


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _resolve_data_dir(workspace_root: Path, env_var: str) -> Dict[str, Any]:
    base = os.getenv(env_var)
    base_path = Path(base).expanduser() if base else (workspace_root / "data")
    base_path = base_path.resolve()
    root = workspace_root.resolve()
    if not _is_within(base_path, root):
        raise ValueError(f"{env_var} must be inside {root}")
    return {"path": str(base_path), "via_env": bool(base)}


def _stat_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "exists": False, "size_bytes": None}
    try:
        st = path.stat()
        return {"path": str(path), "exists": True, "size_bytes": int(st.st_size)}
    except Exception:
        return {"path": str(path), "exists": True, "size_bytes": None}


def _stat_dir(path: Path) -> Dict[str, Any]:
    exists = path.is_dir()
    out: Dict[str, Any] = {"path": str(path), "exists": bool(exists)}
    if not exists:
        out["entries"] = None
        return out
    try:
        out["entries"] = sorted([p.name for p in path.iterdir()])[:50]
        return out
    except Exception:
        out["entries"] = None
        return out


def _inspect_json_dataset(path: Path, *, deep: bool) -> Dict[str, Any]:
    base = _stat_file(path)
    out: Dict[str, Any] = dict(base)
    out["record_count_estimate"] = None
    out["record_count_method"] = "none"
    out["format"] = None
    out["error"] = None

    if not deep or not out.get("exists") or not out.get("size_bytes"):
        return out

    size_bytes = int(out["size_bytes"] or 0)
    max_exact_parse_bytes = 5_000_000

    try:
        if size_bytes <= max_exact_parse_bytes:
            with path.open("r", encoding="utf-8") as f:
                obj = json.load(f)
            if isinstance(obj, dict) and isinstance(obj.get("matches"), list):
                out["format"] = "object.matches_array"
                out["record_count_estimate"] = len(obj["matches"])
                out["record_count_method"] = "json_load.matches_len"
                return out
            if isinstance(obj, list):
                out["format"] = "array"
                out["record_count_estimate"] = len(obj)
                out["record_count_method"] = "json_load.len"
                return out
            if isinstance(obj, dict):
                out["format"] = "object"
                out["record_count_estimate"] = None
                out["record_count_method"] = "json_load.object_unknown"
                return out
            out["format"] = "scalar"
            out["record_count_estimate"] = 1
            out["record_count_method"] = "json_load.scalar"
            return out

        count, method, fmt = _stream_count_json_records(path)
        out["format"] = fmt
        out["record_count_estimate"] = count
        out["record_count_method"] = method
        return out
    except Exception as e:
        out["error"] = str(e)
        return out


def _stream_count_json_records(path: Path) -> Tuple[Optional[int], str, Optional[str]]:
    first_non_ws = _peek_first_non_ws_char(path)
    if first_non_ws == "{":
        count = _stream_count_objects_in_matches_array(path)
        if count is not None:
            return count, "stream.matches_array_object_count", "object.matches_array"
        if _looks_like_ndjson(path):
            return _stream_count_ndjson_lines(path), "stream.ndjson_line_count", "ndjson"
        return None, "stream.unknown_object", "object"
    if first_non_ws == "[":
        count = _stream_count_objects_in_top_level_array(path)
        return count, "stream.top_level_array_object_count", "array"
    if _looks_like_ndjson(path):
        return _stream_count_ndjson_lines(path), "stream.ndjson_line_count", "ndjson"
    return None, "stream.unknown", None


def _peek_first_non_ws_char(path: Path) -> Optional[str]:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            chunk = f.read(65536)
        for ch in chunk:
            if not ch.isspace():
                return ch
        return None
    except Exception:
        return None


def _looks_like_ndjson(path: Path) -> bool:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            sample_lines: List[str] = []
            for _ in range(5):
                line = f.readline()
                if not line:
                    break
                line = line.strip()
                if line:
                    sample_lines.append(line)
        if len(sample_lines) < 2:
            return False
        ok = 0
        for ln in sample_lines[:3]:
            try:
                json.loads(ln)
                ok += 1
            except Exception:
                break
        return ok >= 2
    except Exception:
        return False


def _stream_count_ndjson_lines(path: Path) -> int:
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        return sum(1 for line in f if line.strip())


def _stream_count_objects_in_top_level_array(path: Path) -> Optional[int]:
    try:
        in_string = False
        escape = False
        bracket_depth = 0
        brace_depth = 0
        started = False
        count = 0
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                for ch in chunk:
                    if in_string:
                        if escape:
                            escape = False
                        elif ch == "\\":
                            escape = True
                        elif ch == '"':
                            in_string = False
                        continue
                    if ch == '"':
                        in_string = True
                        continue
                    if ch == "[":
                        bracket_depth += 1
                        started = True
                        continue
                    if ch == "]":
                        bracket_depth -= 1
                        if started and bracket_depth == 0:
                            return count
                        continue
                    if ch == "{":
                        if started and bracket_depth == 1 and brace_depth == 0:
                            count += 1
                        brace_depth += 1
                        continue
                    if ch == "}":
                        if brace_depth > 0:
                            brace_depth -= 1
                        continue
        return count if started else None
    except Exception:
        return None


def _stream_count_objects_in_matches_array(path: Path) -> Optional[int]:
    try:
        in_string = False
        escape = False
        bracket_depth = 0
        brace_depth = 0
        matched_key = False
        key_buf = ""
        after_key = False
        in_matches_array = False
        matches_array_depth = 0
        count = 0

        def push_key_char(c: str) -> None:
            nonlocal key_buf, matched_key
            key_buf = (key_buf + c)[-16:]
            if key_buf.endswith('"matches"'):
                matched_key = True

        with path.open("r", encoding="utf-8", errors="ignore") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                for ch in chunk:
                    if in_string:
                        push_key_char(ch)
                        if escape:
                            escape = False
                        elif ch == "\\":
                            escape = True
                        elif ch == '"':
                            in_string = False
                        continue

                    if ch == '"':
                        in_string = True
                        push_key_char(ch)
                        continue

                    if in_matches_array:
                        if ch == "[":
                            matches_array_depth += 1
                            continue
                        if ch == "]":
                            matches_array_depth -= 1
                            if matches_array_depth == 0:
                                return count
                            continue
                        if ch == "{":
                            if matches_array_depth == 1 and brace_depth == 0:
                                count += 1
                            brace_depth += 1
                            continue
                        if ch == "}":
                            if brace_depth > 0:
                                brace_depth -= 1
                            continue
                        continue

                    if ch == "{":
                        brace_depth += 1
                        continue
                    if ch == "}":
                        if brace_depth > 0:
                            brace_depth -= 1
                        continue
                    if ch == "[":
                        bracket_depth += 1
                        continue
                    if ch == "]":
                        if bracket_depth > 0:
                            bracket_depth -= 1
                        continue

                    if matched_key and not after_key:
                        if ch == ":":
                            after_key = True
                        continue

                    if after_key:
                        if ch.isspace():
                            continue
                        if ch == "[":
                            in_matches_array = True
                            matches_array_depth = 1
                            continue
                        after_key = False
                        matched_key = False
                        continue

        return None
    except Exception:
        return None


def _inspect_chroma_dir(path: Path, *, deep: bool) -> Dict[str, Any]:
    base = _stat_dir(path)
    out: Dict[str, Any] = dict(base)
    out["collections"] = None
    out["total_docs_estimate"] = None
    out["doc_count_method"] = "none"
    out["error"] = None

    if not deep or not out.get("exists"):
        return out

    try:
        import chromadb

        client = chromadb.PersistentClient(path=str(path))
        collections = client.list_collections()
        items = []
        total = 0
        for c in collections:
            name = getattr(c, "name", None) or str(c)
            try:
                cnt = client.get_collection(name=name).count()
            except Exception:
                cnt = None
            items.append({"name": name, "count": cnt})
            if isinstance(cnt, int):
                total += cnt
        out["collections"] = items
        out["total_docs_estimate"] = total
        out["doc_count_method"] = "chromadb.collection.count"
        return out
    except Exception as e:
        out["error"] = str(e)
        out["doc_count_method"] = "chromadb.error"
        return out


def collect_self_audit(
    *,
    offline: bool = True,
    deep: bool = False,
    repo_root: Optional[Path] = None,
    workspace_root: Optional[Path] = None,
) -> Dict[str, Any]:
    ws_root = (workspace_root or WORKSPACE_ROOT).resolve()
    rp_root = (repo_root.resolve() if repo_root else _find_repo_root(ws_root))
    rp_root = rp_root.resolve() if rp_root else None

    data_dir_info = _resolve_data_dir(ws_root, "STANDALONE_FOOTBALL_DATA_DIR")
    standalone_data_dir = Path(data_dir_info["path"]).resolve()

    repo_data_dir = (rp_root / "data").resolve() if rp_root else None

    raw_rel = Path("workspace") / "data" / "raw" / "COMPLETE_FOOTBALL_DATA_FINAL_UPDATED.json"
    raw_repo_root_rel = Path("COMPLETE_FOOTBALL_DATA_FINAL_UPDATED.json")
    chinese_rel = Path("workspace") / "data" / "chinese_mapped"
    chroma_rel = Path("chroma_db")

    root_stats: Dict[str, Any] = {"available": False}
    if repo_data_dir:
        root_expected_raw = (rp_root / raw_rel).resolve()
        root_repo_root_raw = (rp_root / raw_repo_root_rel).resolve()
        root_stats = {
            "available": True,
            "data_dir": _stat_dir(repo_data_dir),
            "raw_json": _inspect_json_dataset(root_expected_raw, deep=deep),
            "raw_json_candidates": [
                {"label": "repo_root_expected", **_inspect_json_dataset(root_expected_raw, deep=deep)},
                {"label": "repo_root_repo_level", **_inspect_json_dataset(root_repo_root_raw, deep=deep)},
            ],
            "chinese_mapped_dir": _stat_dir((rp_root / chinese_rel).resolve()),
            "chroma_db_dir": _inspect_chroma_dir((repo_data_dir / chroma_rel).resolve(), deep=deep),
        }

    standalone_expected_raw = (standalone_data_dir / "raw" / "COMPLETE_FOOTBALL_DATA_FINAL_UPDATED.json").resolve()
    standalone_workspace_raw = (ws_root / raw_rel).resolve()
    standalone_stats = {
        "data_dir": _stat_dir(standalone_data_dir),
        "raw_json": _inspect_json_dataset(standalone_workspace_raw, deep=deep),
        "raw_json_expected": _inspect_json_dataset(standalone_expected_raw, deep=deep),
        "raw_json_candidates": [
            {"label": "workspace_expected", **_inspect_json_dataset(standalone_expected_raw, deep=deep)},
            {"label": "workspace_default_rel", **_inspect_json_dataset(standalone_workspace_raw, deep=deep)},
        ],
        "chinese_mapped_dir": _stat_dir((ws_root / chinese_rel).resolve()),
        "chroma_db_dir": _inspect_chroma_dir((standalone_data_dir / chroma_rel).resolve(), deep=deep),
        "resolver": data_dir_info,
    }

    mismatch = {
        "repo_root_found": bool(rp_root),
        "repo_data_dir": str(repo_data_dir) if repo_data_dir else None,
        "standalone_data_dir": str(standalone_data_dir),
        "root_vs_standalone_path_diff": bool(repo_data_dir and repo_data_dir != standalone_data_dir),
        "root_has_chroma_db": bool(root_stats.get("chroma_db_dir", {}).get("exists")) if root_stats.get("available") else False,
        "standalone_has_chroma_db": bool(standalone_stats.get("chroma_db_dir", {}).get("exists")),
        "root_has_raw_json": bool(root_stats.get("raw_json", {}).get("exists")) if root_stats.get("available") else False,
        "standalone_has_raw_json": bool(standalone_stats.get("raw_json", {}).get("exists")),
        "standalone_has_raw_json_expected": bool(standalone_stats.get("raw_json_expected", {}).get("exists")),
    }
    mismatch["status"] = "mismatch" if mismatch["root_vs_standalone_path_diff"] else "aligned"

    suggestions: List[Dict[str, Any]] = []
    if mismatch["root_has_chroma_db"] and not mismatch["standalone_has_chroma_db"]:
        suggestions.append(
            {
                "id": "migrate_chroma_db",
                "title": "将根目录 data/chroma_db 迁移到 standalone_workspace/data/chroma_db 或重建",
                "from": str(repo_data_dir / chroma_rel) if repo_data_dir else None,
                "to": str(standalone_data_dir / chroma_rel),
            }
        )
    if mismatch["root_has_raw_json"] and not mismatch["standalone_has_raw_json"]:
        suggestions.append(
            {
                "id": "migrate_raw_dataset",
                "title": "将根目录 data/raw 数据包迁移到 standalone_workspace/data/raw 或调整引用路径",
                "from": str((rp_root / raw_rel).resolve()) if rp_root else None,
                "to": str((ws_root / raw_rel).resolve()),
            }
        )
    if mismatch.get("root_has_raw_json") and not mismatch.get("standalone_has_raw_json_expected"):
        suggestions.append(
            {
                "id": "align_data_dir_or_copy_dataset",
                "title": "确保数据包位于 STANDALONE_FOOTBALL_DATA_DIR/raw 下（推荐复制/rsync，而不是引用 root/data）",
                "expected": str(standalone_expected_raw),
                "current_examples": [c.get("path") for c in standalone_stats.get("raw_json_candidates", []) if c.get("exists")],
            }
        )

    suggestions.append(
        {
            "id": "historical_query_metadata_alignment",
            "title": "让 22 万场历史数据对 query_historical_odds “可见可用”：写入正确 metadata 或放宽 where/type 条件",
            "query_entrypoint": "agents/async_scout.py -> MemoryManager.query_historical_odds()",
            "query_where_requires": {
                "type": "historical_match",
                "league": "E0 (example)",
                "home_odds": "float",
                "draw_odds": "float",
                "away_odds": "float",
            },
            "current_ingestion_issue": {
                "script": "scripts/data_ingestion_pipeline.py",
                "built_metadata_unused": True,
                "stored_metadata_actual": {"type": "episodic", "tags": "comma-separated"},
            },
            "minimal_fixes": [
                {
                    "kind": "ingestion_change",
                    "change": "MemoryManager.add_episodic_memory 支持传入 metadatas 并原样写入；pipeline 调用时传入 metadata",
                    "files": ["tools/memory_manager.py", "scripts/data_ingestion_pipeline.py"],
                },
                {
                    "kind": "query_change",
                    "change": "query_historical_odds where_clause 放宽为 type in ['historical_match','episodic']，并避免依赖 league/odds metadata（或改为从文档文本解析）",
                    "files": ["tools/memory_manager.py"],
                },
            ],
        }
    )

    payload: Dict[str, Any] = {
        "schema_version": "1.0",
        "edition": {
            "id": "standalone",
            "version": scripts_version,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "workspace_root": str(ws_root),
            "repo_root": str(rp_root) if rp_root else None,
        },
        "network": {"enabled": False, "mode": "offline"},
        "capability_matrix": run_capability_smoke_tests(offline=offline, workspace_root=ws_root),
        "historical_data": {
            "deep": bool(deep),
            "root_data": root_stats,
            "standalone_data": standalone_stats,
            "root_vs_standalone": mismatch,
            "suggestions": suggestions,
        },
        "drift_diagnosis": _generate_drift_bloat_diagnosis(ws_root=ws_root, repo_root=rp_root, mismatch=mismatch),
    }

    if not offline:
        payload["network"] = {"enabled": True, "mode": "online", "status": "placeholder"}
    return payload


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="self_audit")
    p.add_argument("--pretty", action="store_true")
    p.add_argument("--online", action="store_true")
    p.add_argument("--deep", action="store_true")
    return p


def run(
    argv: Optional[List[str]] = None,
    *,
    stdout: Optional[TextIO] = None,
    repo_root: Optional[Path] = None,
    workspace_root: Optional[Path] = None,
) -> Dict[str, Any]:
    args = build_parser().parse_args(argv)
    payload = collect_self_audit(
        offline=not bool(args.online),
        deep=bool(args.deep),
        repo_root=repo_root,
        workspace_root=workspace_root,
    )

    out = stdout or sys.stdout
    if args.pretty:
        out.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    else:
        out.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return payload


def main(argv: Optional[List[str]] = None) -> int:
    run(argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
