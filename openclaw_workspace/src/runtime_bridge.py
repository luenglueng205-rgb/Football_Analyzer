import asyncio
import os
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PKG_DIR = WORKSPACE_ROOT / "runtime" / "football_analyzer"
if str(RUNTIME_PKG_DIR) not in sys.path:
    sys.path.insert(0, str(RUNTIME_PKG_DIR))

os.environ.setdefault("OPENCLAW_FOOTBALL_DATA_DIR", str(WORKSPACE_ROOT / "data"))

from agents.publisher_agent import PublisherAgent
from agents.syndicate_os import SyndicateOS
from market_sentinel import MarketSentinel


def _ok(data: Any, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {"ok": True, "data": data, "error": None, "meta": meta or {}}


def _err(code: str, message: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {"ok": False, "data": None, "error": {"code": code, "message": message}, "meta": meta or {}}


async def run_once_match(home_team: str, away_team: str, lottery_desc: str = "竞彩足球") -> Dict[str, Any]:
    try:
        os_system = SyndicateOS()
        publisher = PublisherAgent()
        os_result = await os_system.process_match(home_team, away_team, lottery_desc)

        date_str = datetime.now().strftime("%Y%m%d")
        report_path = publisher.report_path(home_team, away_team, date_str)
        report = await publisher.publish(home_team, away_team, os_result)

        if report == "研报生成失败":
            return _err(
                "PUBLISH_FAILED",
                "研报生成失败",
                meta={"publisher_report_path": report_path, "os_result": os_result},
            )

        return _ok({
            "match": os_result.get("match"),
            "scout_report": os_result.get("scout_report"),
            "debates": os_result.get("debates"),
            "final_decision": os_result.get("final_decision"),
            "publisher_report_path": report_path,
            "publisher_report": report,
            "os_result": os_result,
        })
    except Exception as e:
        return _err("WORKFLOW_ERROR", str(e))


async def run_once_market_scan(max_workers: int = 3) -> Dict[str, Any]:
    try:
        sentinel = MarketSentinel(max_workers=max_workers)
        summary = await sentinel.run_once()
        return _ok(summary)
    except Exception as e:
        return _err("WORKFLOW_ERROR", str(e))


@dataclass
class _DaemonState:
    thread: Optional[threading.Thread] = None
    loop: Optional[asyncio.AbstractEventLoop] = None
    task: Optional[asyncio.Task] = None
    started_at: Optional[float] = None
    max_workers: int = 3
    polling_interval: int = 3600
    last_error: Optional[str] = None


_STATE = _DaemonState()
_STATE_LOCK = threading.Lock()


def _daemon_runner(max_workers: int, polling_interval: int) -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    with _STATE_LOCK:
        _STATE.loop = loop
        _STATE.started_at = time.time()
        _STATE.max_workers = max_workers
        _STATE.polling_interval = polling_interval
        _STATE.last_error = None

    try:
        if os.getenv("OPENCLAW_DAEMON_MODE") == "noop":
            async def _noop() -> None:
                while True:
                    await asyncio.sleep(polling_interval)

            task = loop.create_task(_noop())
        else:
            sentinel = MarketSentinel(max_workers=max_workers)
            sentinel.polling_interval = polling_interval
            task = loop.create_task(sentinel.run_forever())

        with _STATE_LOCK:
            _STATE.task = task

        loop.run_until_complete(task)
    except BaseException as e:
        if not isinstance(e, asyncio.CancelledError):
            with _STATE_LOCK:
                _STATE.last_error = str(e)
    finally:
        try:
            pending = [t for t in asyncio.all_tasks(loop) if not t.done()]
            for t in pending:
                t.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        finally:
            loop.close()
            with _STATE_LOCK:
                _STATE.loop = None
                _STATE.task = None
                _STATE.thread = None


def daemon_start(max_workers: int = 3, polling_interval: int = 3600) -> Dict[str, Any]:
    with _STATE_LOCK:
        if _STATE.thread and _STATE.thread.is_alive():
            return daemon_status()

        t = threading.Thread(
            target=_daemon_runner,
            args=(max_workers, polling_interval),
            daemon=True,
            name="market-sentinel-daemon",
        )
        _STATE.thread = t

    t.start()
    return daemon_status()


def daemon_stop(timeout_s: float = 10.0) -> Dict[str, Any]:
    with _STATE_LOCK:
        thread = _STATE.thread
        loop = _STATE.loop
        task = _STATE.task

    if not thread or not thread.is_alive():
        return daemon_status()

    if loop and task:
        loop.call_soon_threadsafe(task.cancel)

    thread.join(timeout=timeout_s)
    return daemon_status()


def daemon_status() -> Dict[str, Any]:
    with _STATE_LOCK:
        running = bool(_STATE.thread and _STATE.thread.is_alive())
        return _ok(
            {
                "running": running,
                "started_at": _STATE.started_at,
                "max_workers": _STATE.max_workers,
                "polling_interval": _STATE.polling_interval,
                "last_error": _STATE.last_error,
            }
        )
