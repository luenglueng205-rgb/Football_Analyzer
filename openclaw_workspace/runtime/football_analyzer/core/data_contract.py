from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional

MatchStatus = Literal[
    "SCHEDULED",
    "LIVE",
    "FINISHED",
    "CANCELLED",
    "POSTPONED",
    "ABANDONED",
]

ResultStatus = Literal["FINISHED", "CANCELLED", "POSTPONED", "ABANDONED"]

LotteryType = Literal["JINGCAI", "BEIDAN", "ZUCAI"]

PlayType = Literal[
    "JINGCAI_WDL",
    "JINGCAI_HANDICAP_WDL",
    "JINGCAI_GOALS",
    "JINGCAI_CS",
    "JINGCAI_HTFT",
    "JINGCAI_MIXED_PARLAY",
    "BEIDAN_WDL",
    "BEIDAN_SFGG",
    "BEIDAN_UP_DOWN_ODD_EVEN",
    "BEIDAN_GOALS",
    "BEIDAN_CS",
    "BEIDAN_HTFT",
    "ZUCAI_14_MATCH",
    "ZUCAI_RENJIU",
    "ZUCAI_6_HTFT",
    "ZUCAI_4_GOALS",
]


def _validate_confidence(confidence: float) -> None:
    if confidence < 0.0 or confidence > 1.0:
        raise ValueError("confidence must be in [0.0, 1.0]")


@dataclass(frozen=True)
class NormalizedMatch:
    match_id: str
    league_code: str
    home_team_id: str
    away_team_id: str
    kickoff_time_utc: str
    status: MatchStatus
    source: str
    confidence: float
    raw_ref: str

    def __post_init__(self) -> None:
        _validate_confidence(self.confidence)


@dataclass(frozen=True)
class NormalizedOdds:
    match_id: str
    lottery_type: LotteryType
    play_type: PlayType
    market: str
    handicap: Optional[float]
    selections: Dict[str, Dict[str, Any]]
    source: str
    confidence: float
    raw_ref: str

    def __post_init__(self) -> None:
        _validate_confidence(self.confidence)
        if not self.selections:
            raise ValueError("selections cannot be empty")


@dataclass(frozen=True)
class NormalizedLiveState:
    match_id: str
    minute: int
    score_ft: str
    red_cards: Dict[str, int]
    lineups: Optional[Dict[str, Any]]
    injuries_suspensions: Optional[Dict[str, Any]]
    key_events: Optional[list[Dict[str, Any]]]
    source: str
    confidence: float
    raw_ref: str

    def __post_init__(self) -> None:
        _validate_confidence(self.confidence)
        if self.minute < 0:
            raise ValueError("minute must be >= 0")


@dataclass(frozen=True)
class NormalizedResult:
    match_id: str
    status: ResultStatus
    score_ht: Optional[str]
    score_ft: Optional[str]
    source: str
    confidence: float
    raw_ref: str

    def __post_init__(self) -> None:
        _validate_confidence(self.confidence)

