from pathlib import Path

import pytest

from tools.paths import data_dir, datasets_dir


def test_openclaw_default_paths_are_isolated(monkeypatch):
    monkeypatch.delenv("OPENCLAW_FOOTBALL_DATA_DIR", raising=False)
    monkeypatch.delenv("OPENCLAW_FOOTBALL_DATASETS_DIR", raising=False)

    openclaw_root = Path(__file__).resolve().parents[3]
    assert Path(data_dir()).resolve() == (openclaw_root / "data").resolve()
    assert Path(datasets_dir()).resolve() == (openclaw_root / "datasets").resolve()


def test_openclaw_rejects_standalone_data_dir(monkeypatch):
    repo_root = Path(__file__).resolve().parents[4]
    standalone_root = repo_root / "standalone_workspace"

    monkeypatch.setenv("OPENCLAW_FOOTBALL_DATA_DIR", str(standalone_root / "data"))
    with pytest.raises(ValueError):
        data_dir()

    monkeypatch.setenv("OPENCLAW_FOOTBALL_DATASETS_DIR", str(standalone_root / "datasets"))
    with pytest.raises(ValueError):
        datasets_dir()


def test_openclaw_allows_in_workspace_overrides(monkeypatch):
    openclaw_root = Path(__file__).resolve().parents[3]

    target_data = openclaw_root / "data" / "tmp_isolation_test"
    monkeypatch.setenv("OPENCLAW_FOOTBALL_DATA_DIR", str(target_data))
    assert Path(data_dir()).resolve() == target_data.resolve()

    target_datasets = openclaw_root / "datasets" / "tmp_isolation_test"
    monkeypatch.setenv("OPENCLAW_FOOTBALL_DATASETS_DIR", str(target_datasets))
    assert Path(datasets_dir()).resolve() == target_datasets.resolve()
