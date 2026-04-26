from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class TicketLeg:
    match_id: str
    play_type: str
    selection: str
    odds: Optional[float] = None
    handicap: Optional[float] = None

    def __post_init__(self) -> None:
        if not str(self.match_id or "").strip():
            raise ValueError("match_id required")
        if not str(self.play_type or "").strip():
            raise ValueError("play_type required")
        if not str(self.selection or "").strip():
            raise ValueError("selection required")
        if self.odds is not None:
            if not isinstance(self.odds, (int, float)):
                raise ValueError("odds must be number")
            if float(self.odds) <= 1.0 or float(self.odds) == float("inf"):
                raise ValueError("odds must be > 1.0 and finite")


@dataclass(frozen=True)
class LotteryTicket:
    ticket_id: str
    lottery_type: str
    play_type: str
    stake: float
    legs: List[TicketLeg]
    created_at: str = ""
    meta: Dict[str, Any] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if not str(self.ticket_id or "").strip():
            raise ValueError("ticket_id required")
        if str(self.lottery_type or "").upper() not in {"JINGCAI", "BEIDAN", "ZUCAI"}:
            raise ValueError("lottery_type must be JINGCAI/BEIDAN/ZUCAI")
        if not str(self.play_type or "").strip():
            raise ValueError("play_type required")
        if not isinstance(self.stake, (int, float)) or float(self.stake) <= 0:
            raise ValueError("stake must be > 0")
        if not isinstance(self.legs, list) or not self.legs:
            raise ValueError("legs required")
        if self.created_at:
            if not isinstance(self.created_at, str):
                raise ValueError("created_at must be string")
        if self.meta is None:
            object.__setattr__(self, "meta", {})
        if not self.created_at:
            object.__setattr__(self, "created_at", _now_utc())

        lt = str(self.lottery_type or "").upper()
        if lt in {"JINGCAI", "BEIDAN"}:
            for leg in self.legs:
                if leg.odds is None:
                    raise ValueError("odds required for jingcai/beidan legs")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

