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


def _fixture_text(*, workspace_root: Path, name: str) -> Optional[str]:
    p = (workspace_root / "tests" / "fixtures" / name).resolve()
    if not p.exists():
        return None
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return None


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
    runtime = "standalone"
    items: List[SmokeItem] = []

    jingcai_sp_html = _fixture_text(workspace_root=ws_root, name="500_trade_jczq_sp_2026-04-15.html")
    if not jingcai_sp_html:
        items.append(
            _degraded_item(
                item_id="JINGCAI.fetch_sp.offline_fixture",
                lottery_type="JINGCAI",
                capability="fetch_sp",
                runtime=runtime,
                reason="fixture_missing:500_trade_jczq_sp_2026-04-15.html",
            )
        )
    else:
        try:
            from tools.domestic_500_jczq_sp import parse_500_jczq_trade_sp_html

            res = parse_500_jczq_trade_sp_html(
                html=jingcai_sp_html,
                home_team="Arsenal",
                away_team="Tottenham",
                kickoff_time="2026-04-15 20:00",
            )
            if res.get("ok") and isinstance(res.get("data"), dict) and (res["data"].get("jingcai_sp") or {}).get("WDL"):
                items.append(
                    _ok_item(
                        item_id="JINGCAI.fetch_sp.offline_fixture",
                        lottery_type="JINGCAI",
                        capability="fetch_sp",
                        runtime=runtime,
                        meta={"provider": (res.get("data") or {}).get("provider")},
                    )
                )
            else:
                items.append(
                    _fail_item(
                        item_id="JINGCAI.fetch_sp.offline_fixture",
                        lottery_type="JINGCAI",
                        capability="fetch_sp",
                        runtime=runtime,
                        reason=f"parse_failed:{(res.get('error') or {}).get('code') or 'unknown'}",
                        meta={"error": res.get("error")},
                    )
                )
        except Exception as e:
            items.append(
                _fail_item(
                    item_id="JINGCAI.fetch_sp.offline_fixture",
                    lottery_type="JINGCAI",
                    capability="fetch_sp",
                    runtime=runtime,
                    reason=f"exception:{type(e).__name__}:{str(e)}",
                )
            )

    live_html = _fixture_text(workspace_root=ws_root, name="500_live_detail_1234567890.html")
    if not live_html:
        items.append(
            _degraded_item(
                item_id="JINGCAI.live_state.offline_fixture",
                lottery_type="JINGCAI",
                capability="live_state",
                runtime=runtime,
                reason="fixture_missing:500_live_detail_1234567890.html",
            )
        )
    else:
        try:
            from tools.domestic_500_live_state import parse_500_live_detail_html

            res = parse_500_live_detail_html(html=live_html)
            if res.get("ok") and isinstance(res.get("data"), dict) and res["data"].get("ft_score"):
                items.append(
                    _ok_item(
                        item_id="JINGCAI.live_state.offline_fixture",
                        lottery_type="JINGCAI",
                        capability="live_state",
                        runtime=runtime,
                        meta={"ft_score": res["data"].get("ft_score"), "minute": res["data"].get("minute")},
                    )
                )
            else:
                items.append(
                    _fail_item(
                        item_id="JINGCAI.live_state.offline_fixture",
                        lottery_type="JINGCAI",
                        capability="live_state",
                        runtime=runtime,
                        reason=f"parse_failed:{(res.get('error') or {}).get('code') or 'unknown'}",
                        meta={"error": res.get("error")},
                    )
                )
        except Exception as e:
            items.append(
                _fail_item(
                    item_id="JINGCAI.live_state.offline_fixture",
                    lottery_type="JINGCAI",
                    capability="live_state",
                    runtime=runtime,
                    reason=f"exception:{type(e).__name__}:{str(e)}",
                )
            )

    results_html = _fixture_text(workspace_root=ws_root, name="500_trade_results_2026-04-15.html")
    if not results_html:
        items.append(
            _degraded_item(
                item_id="JINGCAI.results.offline_fixture",
                lottery_type="JINGCAI",
                capability="results",
                runtime=runtime,
                reason="fixture_missing:500_trade_results_2026-04-15.html",
            )
        )
    else:
        try:
            from tools.domestic_500_results import parse_500_trade_results_html

            parsed = parse_500_trade_results_html(html=results_html, date="2026-04-15")
            if parsed:
                items.append(
                    _ok_item(
                        item_id="JINGCAI.results.offline_fixture",
                        lottery_type="JINGCAI",
                        capability="results",
                        runtime=runtime,
                        meta={"count": len(parsed)},
                    )
                )
            else:
                items.append(
                    _fail_item(
                        item_id="JINGCAI.results.offline_fixture",
                        lottery_type="JINGCAI",
                        capability="results",
                        runtime=runtime,
                        reason="parse_failed:no_rows",
                    )
                )
        except Exception as e:
            items.append(
                _fail_item(
                    item_id="JINGCAI.results.offline_fixture",
                    lottery_type="JINGCAI",
                    capability="results",
                    runtime=runtime,
                    reason=f"exception:{type(e).__name__}:{str(e)}",
                )
            )

    try:
        from tools.lottery_router import LotteryRouter

        router = LotteryRouter()
        ticket = {"play_type": "WDL", "legs": [{"match_id": "M1", "odds": 2.0}]}
        out = router.route_and_validate("JINGCAI", ticket)
        if out.get("status") == "SUCCESS":
            items.append(_ok_item(item_id="JINGCAI.ticket_validation", lottery_type="JINGCAI", capability="ticket_validation", runtime=runtime))
        else:
            items.append(
                _fail_item(
                    item_id="JINGCAI.ticket_validation",
                    lottery_type="JINGCAI",
                    capability="ticket_validation",
                    runtime=runtime,
                    reason=f"unexpected_status:{out.get('status')}",
                )
            )
    except Exception as e:
        items.append(
            _fail_item(
                item_id="JINGCAI.ticket_validation",
                lottery_type="JINGCAI",
                capability="ticket_validation",
                runtime=runtime,
                reason=f"exception:{type(e).__name__}:{str(e)}",
            )
        )

    beidan_html = _fixture_text(workspace_root=ws_root, name="500_trade_beidan_sp_2026-04-15.html")
    if not beidan_html:
        items.append(
            _degraded_item(
                item_id="BEIDAN.fetch_sp.offline_fixture",
                lottery_type="BEIDAN",
                capability="fetch_sp",
                runtime=runtime,
                reason="fixture_missing:500_trade_beidan_sp_2026-04-15.html",
            )
        )
    else:
        try:
            from tools.domestic_500_beidan_sp import parse_500_beidan_sp_html

            res = parse_500_beidan_sp_html(html=beidan_html, home_team="Arsenal", away_team="Tottenham", fid="1234567890")
            sp = (res.get("data") or {}).get("beidan_sp") if isinstance(res.get("data"), dict) else None
            if res.get("ok") and isinstance(sp, dict) and sp.get("HANDICAP_WDL"):
                items.append(_ok_item(item_id="BEIDAN.fetch_sp.offline_fixture", lottery_type="BEIDAN", capability="fetch_sp", runtime=runtime))
            else:
                items.append(
                    _fail_item(
                        item_id="BEIDAN.fetch_sp.offline_fixture",
                        lottery_type="BEIDAN",
                        capability="fetch_sp",
                        runtime=runtime,
                        reason=f"parse_failed:{(res.get('error') or {}).get('code') or 'unknown'}",
                        meta={"error": res.get("error")},
                    )
                )
        except Exception as e:
            items.append(
                _fail_item(
                    item_id="BEIDAN.fetch_sp.offline_fixture",
                    lottery_type="BEIDAN",
                    capability="fetch_sp",
                    runtime=runtime,
                    reason=f"exception:{type(e).__name__}:{str(e)}",
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
            items.append(
                _fail_item(
                    item_id="BEIDAN.ticket_validation",
                    lottery_type="BEIDAN",
                    capability="ticket_validation",
                    runtime=runtime,
                    reason=f"unexpected_status:{out.get('status')}",
                )
            )
    except Exception as e:
        items.append(
            _fail_item(
                item_id="BEIDAN.ticket_validation",
                lottery_type="BEIDAN",
                capability="ticket_validation",
                runtime=runtime,
                reason=f"exception:{type(e).__name__}:{str(e)}",
            )
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
            items.append(
                _fail_item(
                    item_id="ZUCAI.ticket_validation",
                    lottery_type="ZUCAI",
                    capability="ticket_validation",
                    runtime=runtime,
                    reason=f"unexpected_status:{out.get('status')}",
                )
            )
    except Exception as e:
        items.append(
            _fail_item(
                item_id="ZUCAI.ticket_validation",
                lottery_type="ZUCAI",
                capability="ticket_validation",
                runtime=runtime,
                reason=f"exception:{type(e).__name__}:{str(e)}",
            )
        )

    try:
        from tools.parlay_rules_engine import ParlayRulesEngine

        engine = ParlayRulesEngine()
        c = engine.calculate_chuantong_combinations([1] * 10, "renjiu")
        if c == 10:
            items.append(_ok_item(item_id="ZUCAI.parlay_combinatorics", lottery_type="ZUCAI", capability="parlay_combinatorics", runtime=runtime))
        else:
            items.append(
                _fail_item(
                    item_id="ZUCAI.parlay_combinatorics",
                    lottery_type="ZUCAI",
                    capability="parlay_combinatorics",
                    runtime=runtime,
                    reason=f"unexpected_count:{c}",
                )
            )
    except Exception as e:
        items.append(
            _fail_item(
                item_id="ZUCAI.parlay_combinatorics",
                lottery_type="ZUCAI",
                capability="parlay_combinatorics",
                runtime=runtime,
                reason=f"exception:{type(e).__name__}:{str(e)}",
            )
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
            items.append(
                _fail_item(
                    item_id="ZUCAI.selection_edge",
                    lottery_type="ZUCAI",
                    capability="selection_edge",
                    runtime=runtime,
                    reason="no_value_bets",
                )
            )
    except Exception as e:
        items.append(
            _fail_item(
                item_id="ZUCAI.selection_edge",
                lottery_type="ZUCAI",
                capability="selection_edge",
                runtime=runtime,
                reason=f"exception:{type(e).__name__}:{str(e)}",
            )
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

