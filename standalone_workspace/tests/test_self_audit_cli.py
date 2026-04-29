import io
import json
from pathlib import Path

import pytest

from scripts import self_audit_cli


def test_collect_self_audit_reports_root_vs_standalone_mismatch(tmp_path: Path):
    repo_root = tmp_path / "repo"
    ws_root = repo_root / "standalone_workspace"
    (repo_root / "data" / "chroma_db" / "dummy").mkdir(parents=True, exist_ok=True)
    (repo_root / "data" / "raw").mkdir(parents=True, exist_ok=True)
    (repo_root / "data" / "raw" / "COMPLETE_FOOTBALL_DATA_FINAL_UPDATED.json").write_text("{}", encoding="utf-8")
    (ws_root / "data").mkdir(parents=True, exist_ok=True)

    payload = self_audit_cli.collect_self_audit(offline=True, repo_root=repo_root, workspace_root=ws_root)
    assert payload["schema_version"] == "1.0"
    assert payload["edition"]["id"] == "standalone"
    assert payload["network"]["enabled"] is False

    mismatch = payload["historical_data"]["root_vs_standalone"]
    assert mismatch["root_vs_standalone_path_diff"] is True
    assert mismatch["root_has_chroma_db"] is True
    assert mismatch["standalone_has_chroma_db"] is False
    assert mismatch["root_has_raw_json"] is True
    assert mismatch["standalone_has_raw_json"] is False


def test_collect_self_audit_deep_reports_record_count_and_chroma_counts(tmp_path: Path):
    chromadb = pytest.importorskip("chromadb")

    repo_root = tmp_path / "repo"
    ws_root = repo_root / "standalone_workspace"

    root_raw_dir = repo_root / "data" / "raw"
    root_raw_dir.mkdir(parents=True, exist_ok=True)
    (root_raw_dir / "COMPLETE_FOOTBALL_DATA_FINAL_UPDATED.json").write_text(
        json.dumps({"matches": [{"id": 1}, {"id": 2}, {"id": 3}]}), encoding="utf-8"
    )

    ws_raw_dir = ws_root / "data" / "raw"
    ws_raw_dir.mkdir(parents=True, exist_ok=True)
    (ws_raw_dir / "COMPLETE_FOOTBALL_DATA_FINAL_UPDATED.json").write_text(
        json.dumps({"matches": [{"id": "a"}, {"id": "b"}]}), encoding="utf-8"
    )

    root_chroma = repo_root / "data" / "chroma_db"
    ws_chroma = ws_root / "data" / "chroma_db"
    root_chroma.mkdir(parents=True, exist_ok=True)
    ws_chroma.mkdir(parents=True, exist_ok=True)

    root_client = chromadb.PersistentClient(path=str(root_chroma))
    root_col = root_client.get_or_create_collection(name="football_insights_local")
    root_col.add(ids=["r1", "r2"], documents=["x", "y"], embeddings=[[0.0, 0.0], [1.0, 1.0]])

    ws_client = chromadb.PersistentClient(path=str(ws_chroma))
    ws_col = ws_client.get_or_create_collection(name="football_insights_local")
    ws_col.add(ids=["s1"], documents=["z"], embeddings=[[0.5, 0.5]])

    payload = self_audit_cli.collect_self_audit(offline=True, deep=True, repo_root=repo_root, workspace_root=ws_root)
    root_raw = payload["historical_data"]["root_data"]["raw_json"]
    ws_raw = payload["historical_data"]["standalone_data"]["raw_json"]

    assert root_raw["record_count_estimate"] == 3
    assert ws_raw["record_count_estimate"] == 2

    root_chroma_stats = payload["historical_data"]["root_data"]["chroma_db_dir"]
    ws_chroma_stats = payload["historical_data"]["standalone_data"]["chroma_db_dir"]

    assert root_chroma_stats["total_docs_estimate"] == 2
    assert ws_chroma_stats["total_docs_estimate"] == 1


def test_self_audit_cli_run_outputs_json(tmp_path: Path):
    repo_root = tmp_path / "repo"
    ws_root = repo_root / "standalone_workspace"
    (repo_root / "data").mkdir(parents=True, exist_ok=True)
    (ws_root / "data").mkdir(parents=True, exist_ok=True)

    buf = io.StringIO()
    self_audit_cli.run(["--pretty"], stdout=buf, repo_root=repo_root, workspace_root=ws_root)
    out = json.loads(buf.getvalue())
    assert out["schema_version"] == "1.0"
