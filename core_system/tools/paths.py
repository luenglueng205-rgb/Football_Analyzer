import os
from pathlib import Path


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _repo_root() -> Path:
    return _workspace_root().parent


def _knowledge_base_root() -> Path:
    return _workspace_root() / "global_knowledge_base"


def _default_data_dir() -> Path:
    return _knowledge_base_root() / "data"


def _default_datasets_dir() -> Path:
    return _knowledge_base_root() / "datasets"


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _is_allowed_base(path: Path) -> bool:
    roots = (_workspace_root().resolve(), _repo_root().resolve())
    return any(_is_within(path, root) for root in roots)


def knowledge_base_dir(*parts: str) -> str:
    base_path = _knowledge_base_root().resolve(strict=False)
    path = base_path.joinpath(*parts) if parts else base_path
    return str(path)


def data_dir(*parts: str) -> str:
    base = os.getenv("STANDALONE_FOOTBALL_DATA_DIR")
    base_path = Path(base).expanduser() if base else _default_data_dir()
    base_path = base_path.resolve(strict=False)
    if not _is_allowed_base(base_path):
        raise ValueError(
            f"STANDALONE_FOOTBALL_DATA_DIR must be inside {_workspace_root().resolve()} "
            f"or {_repo_root().resolve()}"
        )
    path = base_path.joinpath(*parts) if parts else base_path
    return str(path)


def datasets_dir(*parts: str) -> str:
    base = os.getenv("STANDALONE_FOOTBALL_DATASETS_DIR")
    base_path = Path(base).expanduser() if base else _default_datasets_dir()
    base_path = base_path.resolve(strict=False)
    if not _is_allowed_base(base_path):
        raise ValueError(
            f"STANDALONE_FOOTBALL_DATASETS_DIR must be inside {_workspace_root().resolve()} "
            f"or {_repo_root().resolve()}"
        )
    path = base_path.joinpath(*parts) if parts else base_path
    return str(path)


def chroma_db_dir(*parts: str) -> str:
    """
    返回 ChromaDB 数据库目录路径。
    默认位于 global_knowledge_base/chroma_db，
    可通过环境变量 STANDALONE_FOOTBALL_CHROMA_DB_DIR 覆盖。
    """
    base = os.getenv("STANDALONE_FOOTBALL_CHROMA_DB_DIR")
    base_path = Path(base).expanduser() if base else _knowledge_base_root() / "chroma_db"
    base_path = base_path.resolve(strict=False)
    if not _is_allowed_base(base_path):
        raise ValueError(
            f"STANDALONE_FOOTBALL_CHROMA_DB_DIR must be inside {_workspace_root().resolve()} "
            f"or {_repo_root().resolve()}"
        )
    path = base_path.joinpath(*parts) if parts else base_path
    return str(path)


# 历史数据 JSON 文件的规范名称（避免各处硬编码文件名）
HISTORICAL_DATA_FILENAME = "COMPLETE_FOOTBALL_DATA_FINAL_UPDATED.json"
