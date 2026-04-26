import asyncio

import pytest

from core.event_bus import EventBus
from tools.multisource_fetcher import MultiSourceFetcher
from tools.snapshot_store import SnapshotStore
from agents.daemon_monitor import RealTimeOddsDaemon


async def _ticks(payloads):
    for p in payloads:
        yield {"payload": p, "meta": {"mock": True, "source": "sim", "confidence": 1.0, "stale": False}}


@pytest.mark.asyncio
async def test_realtime_odds_daemon_offline_ticks_trigger_alert(tmp_path):
    db_path = str(tmp_path / "snapshots.db")
    store = SnapshotStore(db_path=db_path)
    fetcher = MultiSourceFetcher(store=store)
    bus = EventBus()

    alerts = []
    ticks = []

    async def on_alert(evt):
        alerts.append(evt)

    async def on_tick(evt):
        ticks.append(evt)

    await bus.subscribe("ODDS_TICK", on_tick)
    await bus.subscribe("ODDS_ALERT", on_alert)

    daemon = RealTimeOddsDaemon(
        match_id="m1",
        home_team="Arsenal",
        away_team="Tottenham",
        store=store,
        fetcher=fetcher,
        bus=bus,
        online=False,
        polling_interval_s=0.0,
        water_drop_threshold=0.08,
    )

    payloads = [
        {"eu_odds": {"home": 1.95, "draw": 3.5, "away": 3.8}},
        {"eu_odds": {"home": 1.93, "draw": 3.5, "away": 3.9}},
        {"eu_odds": {"home": 1.84, "draw": 3.6, "away": 4.1}},
    ]
    res = await daemon.run(tick_source=_ticks(payloads), max_ticks=3, max_idle_polls=1)

    assert res["running"] is False
    assert len(ticks) == 3
    assert len(alerts) == 1

    odds_match_id = res["odds_match_id"]
    latest_tick = store.get_latest_snapshot(category="odds_tick", match_id=odds_match_id)
    assert latest_tick["ok"] is True
    latest_alert = store.get_latest_snapshot(category="odds_alert", match_id=odds_match_id)
    assert latest_alert["ok"] is True


@pytest.mark.asyncio
async def test_realtime_odds_daemon_offline_does_not_call_fetcher(tmp_path, monkeypatch):
    db_path = str(tmp_path / "snapshots.db")
    store = SnapshotStore(db_path=db_path)
    fetcher = MultiSourceFetcher(store=store)

    async def _boom(*args, **kwargs):
        raise AssertionError("fetch_odds should not be called when online=False")

    monkeypatch.setattr(fetcher, "fetch_odds", _boom)

    bus = EventBus()
    seen = []

    async def on_unavailable(evt):
        seen.append(evt)

    await bus.subscribe("ODDS_UNAVAILABLE", on_unavailable)

    daemon = RealTimeOddsDaemon(
        match_id="m2",
        home_team="Arsenal",
        away_team="Tottenham",
        store=store,
        fetcher=fetcher,
        bus=bus,
        online=False,
        polling_interval_s=0.0,
    )

    await daemon.run(max_ticks=None, max_idle_polls=1)
    await asyncio.sleep(0)
    assert seen
