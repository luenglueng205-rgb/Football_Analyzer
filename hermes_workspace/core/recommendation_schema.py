from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from hermes_workspace.tools.market_probability_engine import MarketProbabilityEngine

_MODEL_MARKET_BLEND = 0.7


@dataclass(frozen=True)
class RecommendedBet:
    match_id: Optional[str]
    lottery_type: str
    play_type: Optional[str]
    market: str
    selection: str
    prob: Optional[float]
    odds: Optional[float]
    ev: Optional[float]
    edge: Optional[float]
    risk_tags: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class AuditTrail:
    sources: List[str] = field(default_factory=list)
    raw_refs: List[str] = field(default_factory=list)
    degradations: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    explain: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class RecommendationSchema:
    recommended_leagues: List[Dict[str, Any]] = field(default_factory=list)
    recommended_bets: List[RecommendedBet] = field(default_factory=list)
    recommended_parlays: List[Dict[str, Any]] = field(default_factory=list)
    live_check: Optional[Dict[str, Any]] = None
    post_match_review: Optional[Dict[str, Any]] = None
    audit: AuditTrail = field(default_factory=AuditTrail)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RecommendationSchemaAdapter:
    @staticmethod
    def _calibrate_probabilities_with_market(probs: Dict[str, Any], odds: Dict[str, Any]) -> Dict[str, float]:
        engine = MarketProbabilityEngine()
        implied = engine.implied_probabilities_from_odds(odds if isinstance(odds, dict) else {})

        if not implied:
            model_raw: Dict[str, float] = {}
            if isinstance(probs, dict):
                for k, v in probs.items():
                    try:
                        fv = float(v)
                    except Exception:
                        continue
                    if fv < 0.0:
                        fv = 0.0
                    if fv > 1.0:
                        fv = 1.0
                    model_raw[str(k)] = fv
            s = sum(model_raw.values())
            if s <= 0:
                return {}
            return {k: v / s for k, v in model_raw.items()}

        model_raw: Dict[str, float] = {}
        for k in implied.keys():
            v = probs.get(k) if isinstance(probs, dict) else None
            try:
                fv = float(v)
            except Exception:
                fv = 0.0
            if fv < 0.0:
                fv = 0.0
            if fv > 1.0:
                fv = 1.0
            model_raw[str(k)] = fv

        model_sum = sum(model_raw.values())
        if model_sum <= 0:
            return dict(implied)
        model = {k: v / model_sum for k, v in model_raw.items()}

        calibrated = {
            k: (_MODEL_MARKET_BLEND * model.get(k, 0.0)) + ((1.0 - _MODEL_MARKET_BLEND) * implied.get(k, 0.0))
            for k in implied.keys()
        }
        cal_sum = sum(calibrated.values())
        if cal_sum <= 0:
            return dict(implied)
        return {k: v / cal_sum for k, v in calibrated.items()}

    @staticmethod
    def from_analyst_output(
        output: Dict[str, Any],
        match_id: Optional[str] = None,
        *,
        memories: Optional[List[Dict[str, Any]]] = None,
    ) -> RecommendationSchema:
        rec = output.get("recommendation", {}) if isinstance(output, dict) else {}
        probs = output.get("probabilities", {}) if isinstance(output, dict) else {}
        odds = output.get("odds", {}) if isinstance(output, dict) else {}
        anomalies = output.get("anomalies", []) if isinstance(output, dict) else []

        selection = rec.get("primary")
        calibrated_probs = RecommendationSchemaAdapter._calibrate_probabilities_with_market(probs, odds)
        if selection:
            prob = calibrated_probs.get(selection)
            if prob is None and isinstance(probs, dict):
                prob = probs.get(selection)
        else:
            prob = None
        selection_odds = odds.get(selection) if selection else None
        ev = None
        if prob is not None and selection_odds is not None:
            try:
                ev = float(prob) * float(selection_odds)
            except Exception:
                ev = None

        risk_tags: List[str] = []
        if isinstance(anomalies, list):
            for a in anomalies:
                if isinstance(a, dict) and a.get("type"):
                    risk_tags.append(f"anomaly:{a['type']}")

        recommended_bets: List[RecommendedBet] = []
        if selection:
            recommended_bets.append(
                RecommendedBet(
                    match_id=match_id,
                    lottery_type="JINGCAI",
                    play_type="JINGCAI_WDL",
                    market="WDL",
                    selection=selection,
                    prob=float(prob) if isinstance(prob, (int, float)) else None,
                    odds=float(selection_odds) if isinstance(selection_odds, (int, float)) else None,
                    ev=ev,
                    edge=None,
                    risk_tags=risk_tags,
                )
            )

        tips = rec.get("additional_tips", [])
        explain: List[Dict[str, Any]] = []
        if isinstance(memories, list) and memories:
            explain.append({"type": "memory", "count": len(memories), "items": list(memories)[:5]})
        audit = AuditTrail(
            sources=[output.get("data_source")] if output.get("data_source") else [],
            raw_refs=[],
            degradations=[t for t in tips if isinstance(t, str)],
            conflicts=[],
            explain=explain,
        )

        return RecommendationSchema(recommended_bets=recommended_bets, audit=audit)

    @staticmethod
    def from_odds_analyzer_output(
        output: Dict[str, Any],
        match_id: Optional[str] = None,
        *,
        memories: Optional[List[Dict[str, Any]]] = None,
    ) -> RecommendationSchema:
        rec = output.get("recommendation", {}) if isinstance(output, dict) else {}
        value_analysis = output.get("value_analysis", {}) if isinstance(output, dict) else {}

        action = rec.get("action")
        if action != "bet":
            explain: List[Dict[str, Any]] = []
            if isinstance(memories, list) and memories:
                explain.append({"type": "memory", "count": len(memories), "items": list(memories)[:5]})
            return RecommendationSchema(
                recommended_bets=[],
                audit=AuditTrail(
                    sources=["OddsAnalyzer"],
                    raw_refs=[],
                    degradations=[rec.get("reason")] if rec.get("reason") else [],
                    explain=explain,
                ),
            )

        outcomes = rec.get("outcomes", [])
        recommended_bets: List[RecommendedBet] = []
        for outcome in outcomes:
            d = value_analysis.get(outcome, {}) if isinstance(value_analysis, dict) else {}
            prob = d.get("implied_probability")
            odds = d.get("bookmaker_odds")
            ev = None
            if prob is not None and odds is not None:
                try:
                    ev = float(prob) * float(odds)
                except Exception:
                    ev = None
            edge = None
            if d.get("value_percent") is not None:
                try:
                    edge = float(d.get("value_percent")) / 100.0
                except Exception:
                    edge = None

            recommended_bets.append(
                RecommendedBet(
                    match_id=match_id,
                    lottery_type="JINGCAI",
                    play_type="JINGCAI_WDL",
                    market="WDL",
                    selection=str(outcome),
                    prob=float(prob) if isinstance(prob, (int, float)) else None,
                    odds=float(odds) if isinstance(odds, (int, float)) else None,
                    ev=ev,
                    edge=edge,
                    risk_tags=["value_bet"],
                )
            )

        recommended_bets.sort(key=lambda b: b.ev if isinstance(b.ev, (int, float)) else 0.0, reverse=True)

        explain: List[Dict[str, Any]] = []
        if isinstance(memories, list) and memories:
            explain.append({"type": "memory", "count": len(memories), "items": list(memories)[:5]})
        audit = AuditTrail(
            sources=["OddsAnalyzer"],
            raw_refs=[],
            degradations=[t for t in rec.get("additional_tips", []) if isinstance(t, str)],
            conflicts=[],
            explain=explain,
        )
        return RecommendationSchema(recommended_bets=recommended_bets, audit=audit)

    @staticmethod
    def from_smart_bet_selector_output(value_bets: List[Dict[str, Any]]) -> RecommendationSchema:
        recommended_bets: List[RecommendedBet] = []
        for b in value_bets:
            if not isinstance(b, dict):
                continue
            lt = (b.get("lottery_type") or "JINGCAI").upper()
            market = str(b.get("market") or "UNKNOWN")
            play_type = None
            if lt == "JINGCAI":
                if market == "1x2" or market == "WDL":
                    play_type = "JINGCAI_WDL"
                elif market.startswith("handicap") or market == "HANDICAP_WDL":
                    play_type = "JINGCAI_HANDICAP_WDL"
                elif market == "total" or market == "GOALS":
                    play_type = "JINGCAI_GOALS"
                elif market == "cs" or market == "CS":
                    play_type = "JINGCAI_CS"
                elif market == "htft" or market == "HTFT":
                    play_type = "JINGCAI_HTFT"
                elif market == "mixed" or market == "MIXED_PARLAY":
                    play_type = "JINGCAI_MIXED_PARLAY"
                else:
                    play_type = f"JINGCAI_{market.upper()}"
            elif lt == "BEIDAN":
                if market == "1x2" or market == "WDL":
                    play_type = "BEIDAN_WDL"
                elif market == "sfgg" or market == "SFGG":
                    play_type = "BEIDAN_SFGG"
                elif market == "sxds" or market == "UP_DOWN_ODD_EVEN":
                    play_type = "BEIDAN_UP_DOWN_ODD_EVEN"
                elif market == "total" or market == "GOALS":
                    play_type = "BEIDAN_GOALS"
                elif market == "cs" or market == "CS":
                    play_type = "BEIDAN_CS"
                elif market == "htft" or market == "HTFT":
                    play_type = "BEIDAN_HTFT"
                else:
                    play_type = f"BEIDAN_{market.upper()}"
            elif lt == "ZUCAI":
                if market == "14_match" or market == "14_MATCH":
                    play_type = "ZUCAI_14_MATCH"
                elif market == "renjiu" or market == "RENJIU":
                    play_type = "ZUCAI_RENJIU"
                elif market == "6_htft" or market == "6_HTFT":
                    play_type = "ZUCAI_6_HTFT"
                elif market == "4_goals" or market == "4_GOALS":
                    play_type = "ZUCAI_4_GOALS"
                else:
                    play_type = f"ZUCAI_{market.upper()}"

            recommended_bets.append(
                RecommendedBet(
                    match_id=b.get("match_id"),
                    lottery_type=lt,
                    play_type=play_type,
                    market=market,
                    selection=str(b.get("selection") or "UNKNOWN"),
                    prob=float(b.get("prob")) if isinstance(b.get("prob"), (int, float)) else None,
                    odds=float(b.get("odds")) if isinstance(b.get("odds"), (int, float)) else None,
                    ev=float(b.get("ev")) if isinstance(b.get("ev"), (int, float)) else None,
                    edge=float(b.get("probability_edge")) if isinstance(b.get("probability_edge"), (int, float)) else None,
                    risk_tags=[],
                )
            )

        recommended_bets.sort(
            key=lambda x: x.edge if isinstance(x.edge, (int, float)) else (x.ev if isinstance(x.ev, (int, float)) else 0.0),
            reverse=True,
        )

        return RecommendationSchema(recommended_bets=recommended_bets, audit=AuditTrail(sources=["SmartBetSelector"]))
