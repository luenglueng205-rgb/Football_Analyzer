import os

from tools.snapshot_store import SnapshotStore


def test_snapshot_store_roundtrip():
    db_path = "test_snapshots.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    store = SnapshotStore(db_path=db_path)
    match_id = "UCL_RM_MCI_20260414"

    store.upsert_match(
        match_id=match_id,
        league="欧冠",
        home_team="皇家马德里",
        away_team="曼城",
        kickoff_time="2026-04-14T20:00:00+08:00",
        source="500.com",
    )

    store.insert_snapshot(
        category="odds",
        match_id=match_id,
        source="500.com",
        payload={"eu_odds": {"home": 2.3, "draw": 3.4, "away": 2.8}},
        confidence=0.85,
        stale=False,
    )

    latest = store.get_latest_snapshot(category="odds", match_id=match_id)
    assert latest["ok"] is True
    assert latest["data"]["payload"]["eu_odds"]["home"] == 2.3
    assert latest["data"]["meta"]["confidence"] == 0.85

    if os.path.exists(db_path):
        os.remove(db_path)


if __name__ == "__main__":
    test_snapshot_store_roundtrip()
    print("test_snapshot_store_roundtrip PASSED")

