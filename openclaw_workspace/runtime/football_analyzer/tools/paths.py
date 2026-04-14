import os
from pathlib import Path


def _default_data_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "data"


def data_dir(*parts: str) -> str:
    base = os.getenv("OPENCLAW_FOOTBALL_DATA_DIR")
    base_path = Path(base).expanduser() if base else _default_data_dir()
    path = base_path.joinpath(*parts) if parts else base_path
    return str(path)
