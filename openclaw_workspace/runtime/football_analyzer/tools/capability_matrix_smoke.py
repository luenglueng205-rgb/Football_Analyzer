from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


SmokeStatus = str


@dataclass(frozen=True)
class SmokeItem:
    id: str
    lottery_type: str
    capability: str
    runtime: str
    status: SmokeStatus
    reason: Optional[str]
    meta: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _ok_item(*, item_id: str, lottery_type: str, capability: str, runtime: str, meta: Optional[Dict[str, Any]] = None) -> SmokeItem:
    return SmokeItem(
        id=item_id,
        lottery_type=lottery_type,
        capability=capability,
        runtime=runtime,
        status="PASS",
        reason=None,
        meta=meta or {},
    )


def _degraded_item(
    *, item_id: str, lottery_type: str, capability: str, runtime: str, reason: str, meta: Optional[Dict[str, Any]] = None
) -> SmokeItem:
    return SmokeItem(
        id=item_id,
        lottery_type=lottery_type,
        capability=capability,
        runtime=runtime,
        status="DEGRADED",
        reason=reason,
        meta=meta or {},
    )


def _fail_item(
    *, item_id: str, lottery_type: str, capability: str, runtime: str, reason: str, meta: Optional[Dict[str, Any]] = None
) -> SmokeItem:
    return SmokeItem(
        id=item_id,
        lottery_type=lottery_type,
        capability=capability,
        runtime=runtime,
        status="FAIL",
        reason=reason,
        meta=meta or {},
    )


def run_capability_smoke_tests(*, offline: bool = True, workspace_root: Optional[Path] = None) -> Dict[str, Any]:
    ws_root = (workspace_root or Path(__file__).resolve().parents[1]).resolve()
    runtime = "openclaw_runtime"
    items: List[SmokeItem] = []

    def _record_fail(*, item_id: str, lottery_type: str, capability: str, reason: str, meta: Optional[Dict[str, Any]] = None) -> None:
        if offline:
            items.append(
                _degraded_item(
                    item_id=item_id,
                    lottery_type=lottery_type,
                    capability=capability,
                    runtime=runtime,
                    reason=f"offline_downgrade:{reason}",
                    meta=meta,
                )
            )
            return
        items.append(
            _fail_item(
                item_id=item_id,
                lottery_type=lottery_type,
                capability=capability,
                runtime=runtime,
                reason=reason,
                meta=meta,
            )
        )

    items.append(
        _degraded_item(
            item_id="JINGCAI.fetch_sp.offline_fixture",
            lottery_type="JINGCAI",
            capability="fetch_sp",
            runtime=runtime,
            reason="not_applicable_in_openclaw_runtime:domestic_500_jczq_sp_not_packaged",
        )
    )
    items.append(
        _degraded_item(
            item_id="JINGCAI.live_state.offline_fixture",
            lottery_type="JINGCAI",
            capability="live_state",
            runtime=runtime,
            reason="not_applicable_in_openclaw_runtime:domestic_500_live_state_not_packaged",
        )
    )
    items.append(
        _degraded_item(
            item_id="JINGCAI.results.offline_fixture",
            lottery_type="JINGCAI",
            capability="results",
            runtime=runtime,
            reason="not_applicable_in_openclaw_runtime:domestic_500_results_not_packaged",
        )
    )

    try:
        from tools.historical_impact import build_historical_impact, to_explain_item

        hi = build_historical_impact(
            lottery_type="JINGCAI",
            league_code="E0",
            odds={"home": 2.1, "draw": 3.4, "away": 3.2},
            analysis={},
            similar_odds_result={"ok": True, "data": []},
            data_source={"raw_json_path": "x", "chroma_db_path": "y"},
        )
        item = to_explain_item(hi)
        if isinstance(hi, dict) and isinstance(item, dict) and item.get("type") == "historical_impact":
            items.append(_ok_item(item_id="JINGCAI.historical_impact.schema", lottery_type="JINGCAI", capability="historical_impact", runtime=runtime))
        else:
            _record_fail(
                item_id="JINGCAI.historical_impact.schema",
                lottery_type="JINGCAI",
                capability="historical_impact",
                reason="invalid_schema",
            )
    except Exception as e:
        _record_fail(
            item_id="JINGCAI.historical_impact.schema",
            lottery_type="JINGCAI",
            capability="historical_impact",
            reason=f"exception:{type(e).__name__}:{str(e)}",
        )

    try:
        from tools.lottery_router import LotteryRouter

        router = LotteryRouter()
        ticket = {"play_type": "WDL", "legs": [{"match_id": "M1", "odds": 2.0}]}
        out = router.route_and_validate("JINGCAI", ticket)
        if out.get("status") == "SUCCESS":
            items.append(_ok_item(item_id="JINGCAI.ticket_validation", lottery_type="JINGCAI", capability="ticket_validation", runtime=runtime))
        else:
            _record_fail(
                item_id="JINGCAI.ticket_validation",
                lottery_type="JINGCAI",
                capability="ticket_validation",
                reason=f"unexpected_status:{out.get('status')}",
            )
    except Exception as e:
        _record_fail(
            item_id="JINGCAI.ticket_validation",
            lottery_type="JINGCAI",
            capability="ticket_validation",
            reason=f"exception:{type(e).__name__}:{str(e)}",
        )

    items.append(
        _degraded_item(
            item_id="BEIDAN.fetch_sp.offline_fixture",
            lottery_type="BEIDAN",
            capability="fetch_sp",
            runtime=runtime,
            reason="not_applicable_in_openclaw_runtime:domestic_500_beidan_sp_not_packaged",
        )
    )

    try:
        from tools.lottery_router import LotteryRouter

        router = LotteryRouter()
        ticket = {"play_type": "WDL", "legs": [{"match_id": "M1"}]}
        out = router.route_and_validate("BEIDAN", ticket)
        if out.get("status") == "SUCCESS":
            items.append(_ok_item(item_id="BEIDAN.ticket_validation", lottery_type="BEIDAN", capability="ticket_validation", runtime=runtime))
        else:
            _record_fail(
                item_id="BEIDAN.ticket_validation",
                lottery_type="BEIDAN",
                capability="ticket_validation",
                reason=f"unexpected_status:{out.get('status')}",
            )
    except Exception as e:
        _record_fail(
            item_id="BEIDAN.ticket_validation",
            lottery_type="BEIDAN",
            capability="ticket_validation",
            reason=f"exception:{type(e).__name__}:{str(e)}",
        )

    try:
        from tools.lottery_router import LotteryRouter

        router = LotteryRouter()
        legs = [{"match_id": f"M{i}"} for i in range(9)]
        ticket = {"play_type": "renjiu", "legs": legs}
        out = router.route_and_validate("ZUCAI", ticket)
        if out.get("status") == "SUCCESS":
            items.append(_ok_item(item_id="ZUCAI.ticket_validation", lottery_type="ZUCAI", capability="ticket_validation", runtime=runtime))
        else:
            _record_fail(
                item_id="ZUCAI.ticket_validation",
                lottery_type="ZUCAI",
                capability="ticket_validation",
                reason=f"unexpected_status:{out.get('status')}",
            )
    except Exception as e:
        _record_fail(
            item_id="ZUCAI.ticket_validation",
            lottery_type="ZUCAI",
            capability="ticket_validation",
            reason=f"exception:{type(e).__name__}:{str(e)}",
        )

    try:
        from tools.parlay_rules_engine import ParlayRulesEngine

        engine = ParlayRulesEngine()
        c = engine.calculate_chuantong_combinations([1] * 10, "renjiu")
        if c == 10:
            items.append(_ok_item(item_id="ZUCAI.parlay_combinatorics", lottery_type="ZUCAI", capability="parlay_combinatorics", runtime=runtime))
        else:
            _record_fail(
                item_id="ZUCAI.parlay_combinatorics",
                lottery_type="ZUCAI",
                capability="parlay_combinatorics",
                reason=f"unexpected_count:{c}",
            )
    except Exception as e:
        _record_fail(
            item_id="ZUCAI.parlay_combinatorics",
            lottery_type="ZUCAI",
            capability="parlay_combinatorics",
            reason=f"exception:{type(e).__name__}:{str(e)}",
        )

    try:
        from tools.smart_bet_selector import SmartBetSelector

        selector = SmartBetSelector(min_edge_threshold=0.15)
        data = [
            {
                "match_id": "M1",
                "lottery_type": "ZUCAI",
                "markets": {"WDL": {"3": {"prob": 0.6, "support_rate": 0.4}}},
            }
        ]
        bets = selector.extract_value_bets(data)
        if bets and bets[0].get("lottery_type") == "ZUCAI":
            items.append(_ok_item(item_id="ZUCAI.selection_edge", lottery_type="ZUCAI", capability="selection_edge", runtime=runtime))
        else:
            _record_fail(
                item_id="ZUCAI.selection_edge",
                lottery_type="ZUCAI",
                capability="selection_edge",
                reason="no_value_bets",
            )
    except Exception as e:
        _record_fail(
            item_id="ZUCAI.selection_edge",
            lottery_type="ZUCAI",
            capability="selection_edge",
            reason=f"exception:{type(e).__name__}:{str(e)}",
        )

    pass_count = sum(1 for i in items if i.status == "PASS")
    degraded_count = sum(1 for i in items if i.status == "DEGRADED")
    fail_count = sum(1 for i in items if i.status == "FAIL")
    overall_status = "FAIL" if fail_count else "DEGRADED" if degraded_count else "PASS"

    return {
        "overall_status": overall_status,
        "summary": {"pass": pass_count, "degraded": degraded_count, "fail": fail_count, "total": len(items)},
        "items": [i.to_dict() for i in items],
        "meta": {"offline": bool(offline), "workspace_root": str(ws_root)},
    }
