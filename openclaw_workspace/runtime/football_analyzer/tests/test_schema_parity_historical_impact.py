import importlib.util
from pathlib import Path


def _load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module: {module_name} from {file_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_historical_impact_schema_parity_with_standalone():
    repo_root = Path(__file__).resolve().parents[4]
    standalone_path = repo_root / "standalone_workspace" / "tools" / "historical_impact.py"
    runtime_path = repo_root / "openclaw_workspace" / "runtime" / "football_analyzer" / "tools" / "historical_impact.py"

    standalone = _load_module("standalone_historical_impact", standalone_path)
    runtime = _load_module("runtime_historical_impact", runtime_path)

    hi_standalone = standalone.build_historical_impact(
        lottery_type="JINGCAI",
        league_code="E0",
        odds={"home": 2.1, "draw": 3.4, "away": 3.2},
        analysis={},
        similar_odds_result={"ok": True, "data": []},
        data_source={"raw_json_path": "x", "chroma_db_path": "y"},
    )
    hi_runtime = runtime.build_historical_impact(
        lottery_type="JINGCAI",
        league_code="E0",
        odds={"home": 2.1, "draw": 3.4, "away": 3.2},
        analysis={},
        similar_odds_result={"ok": True, "data": []},
        data_source={"raw_json_path": "x", "chroma_db_path": "y"},
    )

    assert hi_runtime.keys() == hi_standalone.keys()
    assert set(hi_runtime["market_calibration"].keys()) == set(hi_standalone["market_calibration"].keys())
    assert set(hi_runtime["similar_odds"].keys()) == set(hi_standalone["similar_odds"].keys())

    item_standalone = standalone.to_explain_item(hi_standalone)
    item_runtime = runtime.to_explain_item(hi_runtime)
    assert item_runtime.keys() == item_standalone.keys()
    assert item_runtime["type"] == "historical_impact"
    assert set(item_runtime["summary"].keys()) == set(item_standalone["summary"].keys())

