from __future__ import annotations

import hashlib
from typing import Any, Dict, Optional, Tuple

from standalone_workspace.core.recommendation_schema import RecommendationSchema
from standalone_workspace.core.ticket_schema import LotteryTicket, TicketLeg
from standalone_workspace.tools.lottery_router import LotteryRouter
from standalone_workspace.tools.parlay_rules_engine import ParlayRulesEngine


def _selection_to_code(selection: str) -> str:
    m = {
        "home": "3",
        "draw": "1",
        "away": "0",
        "h": "3",
        "d": "1",
        "a": "0",
        "3": "3",
        "1": "1",
        "0": "0",
    }
    return m.get(str(selection or "").strip().lower(), str(selection or "").strip())


def _normalize_market(market: str) -> str:
    s = str(market or "").strip().upper()
    # WDL: 胜平负
    if s in {"1X2", "WDL", "JINGCAI_WDL", "BEIDAN_WDL"}:
        return "WDL"
    # HANDICAP: 让球胜平负
    if s in {"HANDICAP_WDL", "HANDICAP", "RQ", "JINGCAI_HANDICAP_WDL", "BEIDAN_HANDICAP_WDL"}:
        return "HANDICAP"
    # GOALS: 总进球
    if s in {"TOTAL_GOALS", "GOALS", "JINGCAI_GOALS", "BEIDAN_GOALS"}:
        return "GOALS"
    # CS: 比分
    if s in {"CORRECT_SCORE", "CS", "JINGCAI_CS", "BEIDAN_CS"}:
        return "CS"
    # HTFT: 半全场
    if s in {"HTFT", "JINGCAI_HTFT", "BEIDAN_HTFT"}:
        return "HTFT"
    # 修复：北单特有玩法被剥夺真身的严重漏洞
    if s in {"UP_DOWN_ODD_EVEN", "BEIDAN_UP_DOWN_ODD_EVEN", "SXDS"}:
        return "UP_DOWN_ODD_EVEN"
    if s in {"SFGG", "BEIDAN_SFGG"}:
        return "SFGG"
    # 修复：竞彩混合过关
    if s in {"MIXED_PARLAY", "JINGCAI_MIXED_PARLAY", "MIXED"}:
        return "MIXED_PARLAY"
        
    return s or "WDL"


def _normalize_zucai_play_type(play_type: str) -> str:
    s = str(play_type or "").strip()
    if not s:
        return "renjiu"
    up = s.upper()
    if up in {"ZUCAI_14_MATCH", "14_MATCH", "14MATCH"}:
        return "14_match"
    if up in {"ZUCAI_RENJIU", "RENJIU", "RX9"}:
        return "renjiu"
    if up in {"ZUCAI_6_HTFT", "6_HTFT", "6HTFT"}:
        return "6_htft"
    if up in {"ZUCAI_4_GOALS", "4_GOALS", "4GOALS"}:
        return "4_goals"
    low = s.lower()
    if low in {"14_match", "renjiu", "6_htft", "4_goals"}:
        return low
    return low


def _max_legs_for_lottery(lottery_type: str) -> int:
    lt = str(lottery_type or "").upper()
    if lt == "BEIDAN":
        return 15
    if lt == "ZUCAI":
        return 14
    return 8



def _ticket_id(*, date: str, lottery_type: str, play_type: str, seed: str) -> str:
    base = f"{date}|{lottery_type}|{play_type}|{seed}"
    digest = hashlib.sha1(base.encode("utf-8")).hexdigest()[:12]
    return f"TICKET::{date}::{lottery_type}::{play_type}::{digest}"


class LotteryTicketBuilder:
    def __init__(
        self,
        *,
        router: Optional[LotteryRouter] = None,
        parlay_engine: Optional[ParlayRulesEngine] = None,
    ):
        self.router = router or LotteryRouter()
        self.parlay_engine = parlay_engine or ParlayRulesEngine()

    def build_validated_ticket(self, *, schema: RecommendationSchema, stake: float, date: str) -> Dict[str, Any]:
        if not schema.recommended_bets:
            return {"ok": False, "ticket": None, "validation": None, "error": {"code": "NO_BETS", "message": "no recommended bets"}}

        b0 = schema.recommended_bets[0]
        lottery_type = str(getattr(b0, "lottery_type", "") or "JINGCAI").upper()
        raw_market = str(getattr(b0, "market", "") or "")
        raw_play_type = str(getattr(b0, "play_type", "") or "")
        market = _normalize_market(raw_market or raw_play_type or "WDL")
        if lottery_type == "ZUCAI":
            play_type = _normalize_zucai_play_type(raw_play_type or "renjiu")
        else:
            up_pt = raw_play_type.strip().upper()
            if up_pt.startswith("JINGCAI_"):
                play_type = up_pt.replace("JINGCAI_", "", 1)
            elif up_pt.startswith("BEIDAN_"):
                play_type = up_pt.replace("BEIDAN_", "", 1)
            else:
                play_type = market
            if play_type == "HANDICAP_WDL":
                play_type = "HANDICAP"

        if lottery_type == "JINGCAI" and len(schema.recommended_bets) >= 2:
            play_type = "MIXED_PARLAY"

        max_legs = _max_legs_for_lottery(lottery_type)
        legs = []
        for b in schema.recommended_bets[:max_legs]:
            mid = str(getattr(b, "match_id", "") or "").strip()
            if not mid:
                continue
            leg_market = _normalize_market(str(getattr(b, "market", "") or market))
            odds_f = None
            if lottery_type != "ZUCAI":
                odds = getattr(b, "odds", None)
                odds_f = float(odds) if isinstance(odds, (int, float)) else None
            legs.append(
                TicketLeg(
                    match_id=mid,
                    play_type=leg_market,
                    selection=_selection_to_code(str(getattr(b, "selection", "") or "")),
                    odds=odds_f,
                )
            )

        if not legs:
            return {"ok": False, "ticket": None, "validation": None, "error": {"code": "BAD_BETS", "message": "no usable match_id in bets"}}

        ticket = LotteryTicket(
            ticket_id=_ticket_id(date=date, lottery_type=lottery_type, play_type=play_type, seed=str(legs[0].match_id)),
            lottery_type=lottery_type,
            play_type=play_type,
            stake=float(stake),
            legs=legs,
            meta={"source": "RecommendationSchema"},
        )

        validation, status = self._validate(ticket=ticket)
        if status != "VALIDATED":
            return {"ok": False, "ticket": ticket.to_dict(), "validation": validation, "error": {"code": "VALIDATION_FAILED", "message": "ticket rejected"}}
        return {"ok": True, "ticket": ticket.to_dict(), "validation": validation, "status": status}

    def _validate(self, *, ticket: LotteryTicket) -> Tuple[Dict[str, Any], str]:
        router_res: Dict[str, Any] = {}
        parlay_res: Optional[Dict[str, Any]] = None

        legs_payload = []
        for leg in ticket.legs:
            rec: Dict[str, Any] = {"match_id": leg.match_id, "play_type": leg.play_type, "selection": leg.selection}
            if leg.odds is not None:
                rec["odds"] = float(leg.odds)
            if leg.handicap is not None:
                rec["handicap"] = float(leg.handicap)
            legs_payload.append(rec)

        if len(ticket.legs) > 1:
            lt_cn = "竞彩足球" if ticket.lottery_type == "JINGCAI" else "北京单场" if ticket.lottery_type == "BEIDAN" else "传统足彩"
            parlay_res = self.parlay_engine.validate_ticket_legs(lt_cn, legs_payload)
            if not parlay_res.get("is_valid"):
                return {"router": router_res, "parlay": parlay_res}, "REJECTED"

        try:
            router_res = self.router.route_and_validate(ticket.lottery_type, {"play_type": ticket.play_type, "legs": legs_payload})
        except Exception as e:
            return {"router": {"status": "ERROR", "message": str(e)}, "parlay": parlay_res}, "REJECTED"

        st = str(router_res.get("status") or "").upper()
        if st not in {"SUCCESS", "VALIDATED"}:
            return {"router": router_res, "parlay": parlay_res}, "REJECTED"
        return {"router": router_res, "parlay": parlay_res}, "VALIDATED"
