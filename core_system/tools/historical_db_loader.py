from __future__ import annotations

from importlib import import_module, util
from pathlib import Path
from typing import Any, Callable, Optional

from tools.paths import data_dir

_FACTORY: Optional[Callable[..., Any]] = None


def _load_factory() -> Callable[..., Any]:
    try:
        module = import_module("data.historical_database")
        factory = getattr(module, "get_historical_database", None)
        if callable(factory):
            return factory
    except ModuleNotFoundError:
        pass

    module_path = Path(data_dir("historical_database.py"))
    if not module_path.exists():
        raise ModuleNotFoundError(f"historical_database.py not found at {module_path}")

    spec = util.spec_from_file_location("_core_system_historical_database", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"failed to build import spec for {module_path}")

    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    factory = getattr(module, "get_historical_database", None)
    if not callable(factory):
        raise ImportError("historical_database module does not expose get_historical_database")
    return factory


def get_historical_database(*, lazy_load: bool = True):
    global _FACTORY
    if _FACTORY is None:
        _FACTORY = _load_factory()
    return _FACTORY(lazy_load=lazy_load)
