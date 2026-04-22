from __future__ import annotations

from typing import Any, Dict, Optional

from tools.betting_ledger import BettingLedger
from tools.live_match_monitor import LiveMatchMonitor


class SimulatedExecutionEngine:
    def __init__(self, *, ledger: BettingLedger, live_monitor: LiveMatchMonitor):
        self.ledger = ledger
        self.live_monitor = live_monitor

    def execute(self, *, ticket: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(ticket, dict) or not ticket.get("ticket_id"):
            return {"ok": False, "error": {"code": "BAD_TICKET", "message": "ticket_id required"}}

        lottery_type = str(ticket.get("lottery_type") or "").lower() or "jingcai"
        stake = float(ticket.get("stake") or 0.0)
        legs = ticket.get("legs") or []
        if stake <= 0 or not isinstance(legs, list) or not legs:
            return {"ok": False, "error": {"code": "BAD_TICKET", "message": "stake/legs invalid"}}

        per_leg_stake = stake / float(len(legs))
        registered = []
        for leg in legs:
            if not isinstance(leg, dict):
                continue
            mid = str(leg.get("match_id") or "")
            if not mid:
                continue
            odds = leg.get("odds")
            odds_f = float(odds) if isinstance(odds, (int, float)) else 0.0
            selection = str(leg.get("selection") or "")
            if odds_f > 0:
                self.live_monitor.register_live_bet(mid, selection, float(per_leg_stake), float(odds_f))
                registered.append(mid)

        leg0 = legs[0] if isinstance(legs[0], dict) else {}
        odds0 = leg0.get("odds")
        odds0_f = float(odds0) if isinstance(odds0, (int, float)) else 0.0
        selection0 = str(leg0.get("selection") or "")

        ledger_res = self.ledger.execute_bet(
            match_id=str(ticket.get("ticket_id")),
            lottery_type=lottery_type,
            selection=selection0,
            odds=odds0_f if odds0_f else 1.01,
            stake=float(stake),
        )
        ok = ledger_res.get("status") == "success"
        return {"ok": bool(ok), "ticket_id": str(ticket.get("ticket_id")), "ledger": ledger_res, "registered_matches": registered}

    def settle(self, *, ticket: Dict[str, Any], settlement: Dict[str, Any]) -> Dict[str, Any]:
        ticket_id = str(ticket.get("ticket_id") or "")
        if not ticket_id:
            return {"ok": False, "error": {"code": "BAD_TICKET", "message": "ticket_id required"}}

        legs = ticket.get("legs") or []
        if not isinstance(legs, list) or not legs:
            return {"ok": False, "error": {"code": "BAD_TICKET", "message": "legs required"}}

        leg0 = legs[0] if isinstance(legs[0], dict) else {}
        odds0 = leg0.get("odds")
        odds0_f = float(odds0) if isinstance(odds0, (int, float)) else 1.0
        selection0 = str(leg0.get("selection") or "")
        stake = float(ticket.get("stake") or 0.0)

        status = str(settlement.get("status") or "").upper()
        official = str(settlement.get("official_result") or "")
        if status == "VOID" or official == "REFUND":
            pnl = 0.0
            result = "VOID"
        elif selection0 and official and selection0 == official:
            pnl = stake * (odds0_f - 1.0)
            result = "WON"
        else:
            pnl = -stake
            result = "LOST"

        ledger_res = self.ledger.record_result(match_id=ticket_id, result=result, pnl=float(pnl))
        ok = ledger_res.get("status") == "success"
        out: Dict[str, Any] = {"ok": bool(ok), "ticket_id": ticket_id, "result": result, "pnl": float(pnl), "ledger": ledger_res}
        ft_score = settlement.get("ft_score")
        if ft_score is not None:
            out["ft_score"] = str(ft_score)
        return out

