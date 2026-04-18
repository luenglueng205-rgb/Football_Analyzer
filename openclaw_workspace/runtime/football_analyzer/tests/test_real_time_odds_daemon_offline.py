import pytest

from core.event_bus import EventBus
from tools.snapshot_store import SnapshotStore
from tools.multisource_fetcher import MultiSourceFetcher
from agents.daemon_monitor import RealTimeOddsDaemon


async def _ticks(payloads):
    for p in payloads:
        yield {"payload": p, "meta": {"mock": True, "source": "sim", "confidence": 1.0, "stale": False}}


@pytest.mark.asyncio
async def test_openclaw_realtime_odds_daemon_offline_ticks(tmp_path):
    db_path = str(tmp_path / "snapshots.db")
    store = SnapshotStore(db_path=db_path)
    fetcher = MultiSourceFetcher(store=store)
    bus = EventBus()

    alerts = []

    async def on_alert(evt):
        alerts.append(evt)

    bus.subscribe("ODDS_ALERT", on_alert)

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
        {"eu_odds": {"home": 1.84, "draw": 3.6, "away": 4.1}},
    ]
    res = await daemon.run(tick_source=_ticks(payloads), max_ticks=2, max_idle_polls=1)
    assert res["alert_count"] == 1
    assert alerts

