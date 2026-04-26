from __future__ import annotations

import asyncio
import time
import threading
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, Optional

from core.event_bus import EventBus
from tools.multisource_fetcher import MultiSourceFetcher
from tools.snapshot_store import SnapshotStore


def _now_ts() -> float:
    return time.time()


def _coerce_home_odds(payload: Any) -> Optional[float]:
    if not isinstance(payload, dict):
        return None
    if isinstance(payload.get("eu_odds"), dict) and payload["eu_odds"].get("home") is not None:
        try:
            return float(payload["eu_odds"]["home"])
        except Exception:
            return None
    if isinstance(payload.get("jingcai_sp"), dict) and payload["jingcai_sp"].get("home") is not None:
        try:
            return float(payload["jingcai_sp"]["home"])
        except Exception:
            return None
    if payload.get("home") is not None:
        try:
            return float(payload["home"])
        except Exception:
            return None
    if isinstance(payload.get("selections"), dict):
        sel = payload["selections"].get("H")
        if isinstance(sel, dict) and sel.get("odds") is not None:
            try:
                return float(sel["odds"])
            except Exception:
                return None
    return None


class RealTimeOddsDaemon:
    def __init__(
        self,
        match_id: str,
        home_team: str,
        away_team: str,
        *,
        store: Optional[SnapshotStore] = None,
        fetcher: Optional[MultiSourceFetcher] = None,
        bus: Optional[EventBus] = None,
        online: bool = False,
        polling_interval_s: float = 2.0,
        water_drop_threshold: float = 0.08,
        baseline_home_odds: Optional[float] = None,
    ):
        self.match_id = str(match_id)
        self.home_team = str(home_team)
        self.away_team = str(away_team)
        self.online = bool(online)
        self.polling_interval_s = float(polling_interval_s)
        self.water_drop_threshold = float(water_drop_threshold)
        self.baseline_home_odds = float(baseline_home_odds) if baseline_home_odds is not None else None

        self.store = store or SnapshotStore()
        if fetcher is None:
            try:
                fetcher = MultiSourceFetcher(store=self.store, online=self.online)
            except TypeError:
                fetcher = MultiSourceFetcher(store=self.store)
        self.fetcher = fetcher
        self.bus = bus or EventBus()

        self._running = False
        self._stop_event = asyncio.Event()
        self._started_at: Optional[float] = None
        self._tick_count = 0
        self._alert_count = 0

        self._odds_match_id = self._derive_odds_match_id()
        self.store.upsert_match(
            match_id=self._odds_match_id,
            league="Unknown",
            home_team=self.home_team,
            away_team=self.away_team,
            kickoff_time="Unknown",
            source="RealTimeOddsDaemon",
        )

    def _derive_odds_match_id(self) -> str:
        resolver = getattr(self.fetcher, "resolver", None)
        if resolver is not None:
            try:
                home = resolver.resolve_team(self.home_team)
                away = resolver.resolve_team(self.away_team)
                if isinstance(home, dict) and home.get("ok") and isinstance(away, dict) and away.get("ok"):
                    hid = home.get("data", {}).get("team_id")
                    aid = away.get("data", {}).get("team_id")
                    if hid and aid:
                        return f"ODDS::{hid}::{aid}"
            except Exception:
                pass
        return f"ODDS::{self.match_id}"

    def status(self) -> Dict[str, Any]:
        return {
            "running": bool(self._running),
            "started_at": self._started_at,
            "tick_count": self._tick_count,
            "alert_count": self._alert_count,
            "match_id": self.match_id,
            "odds_match_id": self._odds_match_id,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "online": bool(self.online),
            "polling_interval_s": float(self.polling_interval_s),
            "water_drop_threshold": float(self.water_drop_threshold),
            "baseline_home_odds": self.baseline_home_odds,
        }

    def request_stop(self) -> None:
        try:
            self._stop_event.set()
        except Exception:
            pass

    async def run_forever(self, *, tick_source: Optional[AsyncIterator[Dict[str, Any]]] = None) -> None:
        await self.run(tick_source=tick_source, max_ticks=None)

    async def run(
        self,
        *,
        tick_source: Optional[AsyncIterator[Dict[str, Any]]] = None,
        max_ticks: Optional[int] = None,
        max_idle_polls: Optional[int] = None,
    ) -> Dict[str, Any]:
        self._running = True
        self._started_at = _now_ts()
        self._stop_event = asyncio.Event()
        await self.bus.publish("ODDS_DAEMON_STARTED", self.status())
        self.store.insert_snapshot(
            category="odds_daemon_state",
            match_id=self._odds_match_id,
            source="RealTimeOddsDaemon",
            payload={"event": "started", "status": self.status()},
            confidence=1.0,
            stale=False,
        )

        try:
            idle_polls = 0
            while True:
                if self._stop_event.is_set():
                    break
                if max_ticks is not None and self._tick_count >= int(max_ticks):
                    break

                tick = await self._next_tick(tick_source=tick_source)
                if tick is None:
                    idle_polls += 1
                    if max_idle_polls is not None and idle_polls >= int(max_idle_polls):
                        break
                    await asyncio.sleep(self.polling_interval_s)
                    continue
                idle_polls = 0

                self._tick_count += 1
                home_odds = _coerce_home_odds(tick.get("payload"))
                baseline = self.baseline_home_odds
                if baseline is None and home_odds is not None:
                    self.baseline_home_odds = float(home_odds)
                    baseline = self.baseline_home_odds

                drop_amplitude = None
                if baseline is not None and home_odds is not None:
                    drop_amplitude = float(baseline) - float(home_odds)

                event = {
                    "ts": tick.get("ts"),
                    "match_id": self.match_id,
                    "odds_match_id": self._odds_match_id,
                    "home_team": self.home_team,
                    "away_team": self.away_team,
                    "payload": tick.get("payload"),
                    "meta": tick.get("meta"),
                    "home_odds": home_odds,
                    "baseline_home_odds": baseline,
                    "drop_amplitude": drop_amplitude,
                }

                self.store.insert_snapshot(
                    category="odds_tick",
                    match_id=self._odds_match_id,
                    source=str((tick.get("meta") or {}).get("source") or "unknown"),
                    payload=event,
                    confidence=float((tick.get("meta") or {}).get("confidence") or 0.0),
                    stale=bool((tick.get("meta") or {}).get("stale") or False),
                )
                await self.bus.publish("ODDS_TICK", event)

                if drop_amplitude is not None and drop_amplitude > self.water_drop_threshold:
                    self._alert_count += 1
                    alert = {
                        **event,
                        "alert": {
                            "type": "WATER_DROP",
                            "threshold": float(self.water_drop_threshold),
                            "triggered": True,
                        },
                    }
                    self.store.insert_snapshot(
                        category="odds_alert",
                        match_id=self._odds_match_id,
                        source="RealTimeOddsDaemon",
                        payload=alert,
                        confidence=1.0,
                        stale=False,
                    )
                    await self.bus.publish("ODDS_ALERT", alert)

                await asyncio.sleep(self.polling_interval_s)
        except asyncio.CancelledError:
            pass
        finally:
            self._running = False
            await self.bus.publish("ODDS_DAEMON_STOPPED", self.status())
            self.store.insert_snapshot(
                category="odds_daemon_state",
                match_id=self._odds_match_id,
                source="RealTimeOddsDaemon",
                payload={"event": "stopped", "status": self.status()},
                confidence=1.0,
                stale=False,
            )

        return self.status()

    async def _next_tick(self, *, tick_source: Optional[AsyncIterator[Dict[str, Any]]]) -> Optional[Dict[str, Any]]:
        if tick_source is not None:
            try:
                tick = await tick_source.__anext__()
                if isinstance(tick, dict):
                    tick.setdefault("ts", _now_ts())
                    tick.setdefault("meta", {"mock": True, "source": "tick_source", "confidence": 1.0, "stale": False})
                    return tick
            except StopAsyncIteration:
                self.request_stop()
                return None
            except Exception:
                return None

        if not self.online:
            latest = self.store.get_latest_snapshot(category="odds", match_id=self._odds_match_id)
            if latest.get("ok"):
                data = latest.get("data") or {}
                return {"ts": _now_ts(), "payload": data.get("payload"), "meta": {"source": "snapshot", "stale": True}}
            await self.bus.publish(
                "ODDS_UNAVAILABLE",
                {
                    "ts": _now_ts(),
                    "match_id": self.match_id,
                    "odds_match_id": self._odds_match_id,
                    "reason": "no_snapshot_and_online_disabled",
                },
            )
            return None

        res = await self.fetcher.fetch_odds(self.home_team, self.away_team)
        if isinstance(res, dict) and res.get("ok"):
            return {"ts": _now_ts(), "payload": res.get("data"), "meta": res.get("meta")}
        err = (res or {}).get("error") if isinstance(res, dict) else None
        await self.bus.publish(
            "ODDS_UNAVAILABLE",
            {
                "ts": _now_ts(),
                "match_id": self.match_id,
                "odds_match_id": self._odds_match_id,
                "reason": "fetch_failed",
                "error": err,
            },
        )
        return None


@dataclass
class _DaemonState:
    thread: Optional[threading.Thread] = None
    loop: Optional[asyncio.AbstractEventLoop] = None
    task: Optional[asyncio.Task] = None
    daemon: Optional[RealTimeOddsDaemon] = None
    started_at: Optional[float] = None
    last_error: Optional[str] = None


_STATE = _DaemonState()
_STATE_LOCK = threading.Lock()


def _daemon_runner(kwargs: Dict[str, Any]) -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    daemon = RealTimeOddsDaemon(**kwargs)
    with _STATE_LOCK:
        _STATE.loop = loop
        _STATE.daemon = daemon
        _STATE.started_at = _now_ts()
        _STATE.last_error = None
    try:
        task = loop.create_task(daemon.run_forever())
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
                _STATE.daemon = None


def start_daemon(
    *,
    match_id: str,
    home_team: str,
    away_team: str,
    online: bool = False,
    polling_interval_s: float = 2.0,
    water_drop_threshold: float = 0.08,
    baseline_home_odds: Optional[float] = None,
) -> Dict[str, Any]:
    cfg = {
        "match_id": match_id,
        "home_team": home_team,
        "away_team": away_team,
        "online": bool(online),
        "polling_interval_s": float(polling_interval_s),
        "water_drop_threshold": float(water_drop_threshold),
        "baseline_home_odds": baseline_home_odds,
    }
    with _STATE_LOCK:
        if _STATE.thread and _STATE.thread.is_alive():
            return daemon_status()
        t = threading.Thread(target=_daemon_runner, args=(cfg,), daemon=True, name="realtime-odds-daemon")
        _STATE.thread = t
    t.start()
    return daemon_status()


def stop_daemon(*, timeout_s: float = 10.0) -> Dict[str, Any]:
    with _STATE_LOCK:
        thread = _STATE.thread
        loop = _STATE.loop
        task = _STATE.task
        daemon = _STATE.daemon

    if not thread or not thread.is_alive():
        return daemon_status()

    if daemon is not None:
        try:
            daemon.request_stop()
        except Exception:
            pass
    if loop and task:
        loop.call_soon_threadsafe(task.cancel)
    thread.join(timeout=timeout_s)
    return daemon_status()


def daemon_status() -> Dict[str, Any]:
    with _STATE_LOCK:
        running = bool(_STATE.thread and _STATE.thread.is_alive())
        return {
            "ok": True,
            "data": {
                "running": running,
                "started_at": _STATE.started_at,
                "last_error": _STATE.last_error,
                "daemon": _STATE.daemon.status() if _STATE.daemon is not None else None,
            },
            "error": None,
            "meta": {},
        }


async def _cli_printer(event: Dict[str, Any]) -> None:
    import json
    import sys

    sys.stdout.write(json.dumps(event, ensure_ascii=False) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    async def _main() -> None:
        bus = EventBus()
        await bus.subscribe("ODDS_TICK", _cli_printer)
        await bus.subscribe("ODDS_ALERT", _cli_printer)
        await bus.subscribe("ODDS_UNAVAILABLE", _cli_printer)
        d = RealTimeOddsDaemon("match_1024", "曼城", "切尔西", bus=bus)
        try:
            await d.run_forever()
        except KeyboardInterrupt:
            d.request_stop()

    asyncio.run(_main())
