import os
import tempfile
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.publisher_agent import PublisherAgent
from tools.betting_ledger import BettingLedger
from tools.memory_manager import MemoryManager
from tools.paths import data_dir
from tools.snapshot_store import SnapshotStore


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def main() -> None:
    os.environ.pop("OPENCLAW_FOOTBALL_DATA_DIR", None)
    default_dir = Path(data_dir()).resolve()
    _assert(str(default_dir).endswith("openclaw_workspace/data"), f"default data_dir unexpected: {default_dir}")

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["OPENCLAW_FOOTBALL_DATA_DIR"] = tmp
        os.environ.pop("OPENAI_API_KEY", None)

        store = SnapshotStore()
        _assert(store.db_path.startswith(tmp), f"SnapshotStore path not in env dir: {store.db_path}")
        store.upsert_match("m1", "L", "H", "A", "2099-01-01T00:00:00Z", "test")
        store.insert_snapshot("odds", "m1", "test", {"x": 1}, 0.9, False)
        latest = store.get_latest_snapshot("odds", "m1")
        _assert(latest["ok"] is True, f"SnapshotStore read failed: {latest}")

        ledger = BettingLedger()
        _assert(ledger.db_path.startswith(tmp), f"BettingLedger path not in env dir: {ledger.db_path}")
        bankroll = ledger.check_bankroll()
        _assert("current_bankroll" in bankroll, f"BettingLedger check_bankroll failed: {bankroll}")

        memory = MemoryManager()
        _assert(memory.db_path.startswith(tmp), f"MemoryManager path not in env dir: {memory.db_path}")

        publisher = PublisherAgent()
        report_dir = os.path.join(tmp, "reports")
        os.makedirs(report_dir, exist_ok=True)
        report_path = os.path.join(report_dir, "test_report.md")
        with open(report_path, "w") as f:
            f.write("hello")
        _assert(report_path.startswith(tmp), f"Publisher report not in env dir: {report_path}")
        _assert(Path(report_path).exists(), f"Publisher report file not created: {report_path}")

    print("Task2 paths smoke test: OK")


if __name__ == "__main__":
    main()
