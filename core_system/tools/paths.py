import os
from pathlib import Path


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _default_data_dir() -> Path:
    return _workspace_root() / "data"


def _default_datasets_dir() -> Path:
    return _workspace_root() / "datasets"


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def data_dir(*parts: str) -> str:
    base = os.getenv("STANDALONE_FOOTBALL_DATA_DIR")
    base_path = Path(base).expanduser() if base else _default_data_dir()
    base_path = base_path.resolve()
    root = _workspace_root().resolve()
    if not _is_within(base_path, root):
        raise ValueError(f"STANDALONE_FOOTBALL_DATA_DIR must be inside {root}")
    path = base_path.joinpath(*parts) if parts else base_path
    return str(path)


def datasets_dir(*parts: str) -> str:
    base = os.getenv("STANDALONE_FOOTBALL_DATASETS_DIR")
    base_path = Path(base).expanduser() if base else _default_datasets_dir()
    base_path = base_path.resolve()
    root = _workspace_root().resolve()
    if not _is_within(base_path, root):
        raise ValueError(f"STANDALONE_FOOTBALL_DATASETS_DIR must be inside {root}")
    path = base_path.joinpath(*parts) if parts else base_path
    return str(path)
