from pathlib import Path

import pytest

from tools.paths import data_dir, datasets_dir


def test_standalone_default_paths_are_isolated(monkeypatch):
    monkeypatch.delenv("STANDALONE_FOOTBALL_DATA_DIR", raising=False)
    monkeypatch.delenv("STANDALONE_FOOTBALL_DATASETS_DIR", raising=False)

    standalone_root = Path(__file__).resolve().parents[1]
    assert Path(data_dir()).resolve() == (standalone_root / "data").resolve()
    assert Path(datasets_dir()).resolve() == (standalone_root / "datasets").resolve()


def test_standalone_rejects_openclaw_data_dir(monkeypatch):
    repo_root = Path(__file__).resolve().parents[2]
    openclaw_root = repo_root / "openclaw_workspace"

    monkeypatch.setenv("STANDALONE_FOOTBALL_DATA_DIR", str(openclaw_root / "data"))
    with pytest.raises(ValueError):
        data_dir()

    monkeypatch.setenv("STANDALONE_FOOTBALL_DATASETS_DIR", str(openclaw_root / "datasets"))
    with pytest.raises(ValueError):
        datasets_dir()


def test_standalone_allows_in_workspace_overrides(monkeypatch):
    standalone_root = Path(__file__).resolve().parents[1]

    target_data = standalone_root / "data" / "tmp_isolation_test"
    monkeypatch.setenv("STANDALONE_FOOTBALL_DATA_DIR", str(target_data))
    assert Path(data_dir()).resolve() == target_data.resolve()

    target_datasets = standalone_root / "datasets" / "tmp_isolation_test"
    monkeypatch.setenv("STANDALONE_FOOTBALL_DATASETS_DIR", str(target_datasets))
    assert Path(datasets_dir()).resolve() == target_datasets.resolve()
