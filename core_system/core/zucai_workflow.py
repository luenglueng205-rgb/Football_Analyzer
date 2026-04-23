from __future__ import annotations

from collections import Counter
import contextlib
from datetime import datetime, timezone
import io
from typing import Any, Dict, List, Optional

from core.recommendation_schema import AuditTrail, RecommendationSchema, RecommendedBet
from data.historical_database import get_historical_database
from tools.historical_impact import build_historical_impact, to_explain_item
from tools.multisource_fetcher import MultiSourceFetcher
from tools.paths import datasets_dir
from tools.settlement_engine import SettlementEngine
from tools.ticket_builder import LotteryTicketBuilder


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _rotate(items: List[Dict[str, Any]], start_index: int) -> List[Dict[str, Any]]:
    if not items:
        return []
    idx = start_index % len(items)
    return list(items[idx:]) + list(items[:idx])


def _max_matches_for_play_type(play_type: str) -> int:
    pt = str(play_type or "").strip().lower()
    if pt == "renjiu":
        return 9
    return 14


def _selection_from_league_stats(stats: Dict[str, Any]) -> str:
    try:
        draw_rate = float(stats.get("draw_rate") or 0.0)
    except Exception:
        draw_rate = 0.0
    if draw_rate >= 0.30:
        return "1"
    return "3"


def _load_league_stats(primary_league_code: str) -> Dict[str, Any]:
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            db = get_historical_database(lazy_load=True)
            stats = db.get_league_stats(primary_league_code)
            return stats if isinstance(stats, dict) else {}
    except Exception:
        return {}


class ZucaiWorkflow:
    def __init__(
        self,
        *,
        fetcher: Optional[MultiSourceFetcher] = None,
        ticket_builder: Optional[LotteryTicketBuilder] = None,
        settlement_engine: Optional[SettlementEngine] = None,
    ):
        self.fetcher = fetcher or MultiSourceFetcher()
        self.ticket_builder = ticket_builder or LotteryTicketBuilder()
        self.settlement_engine = settlement_engine or SettlementEngine()

    def run(
        self,
        *,
        date: str,
        stake: float = 100.0,
        play_type: str = "14_match",
        match_index: int = 0,
    ) -> Dict[str, Any]:
        pt = str(play_type or "14_match").strip().lower()
        need = _max_matches_for_play_type(pt)
        fixtures = self.fetcher.get_fixtures_normalized(date=date)
        if not fixtures:
            schema = RecommendationSchema(audit=AuditTrail(degradations=["no_fixtures"]))
            out = schema.to_dict()
            out["historical_impact"] = build_historical_impact(
                lottery_type="ZUCAI",
                league_code="UNK",
                odds=None,
                analysis={},
                similar_odds_result=None,
                data_source={
                    "raw_json_path": datasets_dir("raw", "COMPLETE_FOOTBALL_DATA_FINAL_UPDATED.json"),
                    "chroma_db_path": None,
                },
            )
            out["ticket"] = None
            return out

        rotated = _rotate(list(fixtures), int(match_index))
        picked = rotated[:need]
        if len(picked) < need:
            schema = RecommendationSchema(audit=AuditTrail(degradations=["insufficient_fixtures"]))
            out = schema.to_dict()
            out["historical_impact"] = build_historical_impact(
                lottery_type="ZUCAI",
                league_code="UNK",
                odds=None,
                analysis={},
                similar_odds_result=None,
                data_source={
                    "raw_json_path": datasets_dir("raw", "COMPLETE_FOOTBALL_DATA_FINAL_UPDATED.json"),
                    "chroma_db_path": None,
                },
            )
            out["ticket"] = None
            return out

        league_codes = [str(m.get("league_code") or "UNK") for m in picked if isinstance(m, dict)]
        primary_league_code = (Counter([c for c in league_codes if c and c != "UNK"]).most_common(1) or [("UNK", 0)])[0][
            0
        ]

        stats = _load_league_stats(primary_league_code)
        selection = _selection_from_league_stats(stats)

        prob = None
        if selection == "1" and isinstance(stats.get("draw_rate"), (int, float)):
            prob = float(stats.get("draw_rate"))
        elif selection == "3" and isinstance(stats.get("home_win_rate"), (int, float)):
            prob = float(stats.get("home_win_rate"))
        elif selection == "0" and isinstance(stats.get("away_win_rate"), (int, float)):
            prob = float(stats.get("away_win_rate"))

        recommended_bets: List[RecommendedBet] = []
        raw_refs: List[str] = []
        for m in picked:
            if not isinstance(m, dict):
                continue
            mid = str(m.get("match_id") or "").strip()
            if not mid:
                continue
            if m.get("raw_ref"):
                raw_refs.append(str(m.get("raw_ref")))
            recommended_bets.append(
                RecommendedBet(
                    match_id=mid,
                    lottery_type="ZUCAI",
                    play_type=pt,
                    market="WDL",
                    selection=selection,
                    prob=prob,
                    odds=None,
                    ev=None,
                    edge=None,
                    risk_tags=["heuristic"],
                )
            )

        recommended_leagues = [
            {"league_code": str(code), "confidence": float(picked[0].get("confidence") or 0.0), "reason": "fixtures_normalized"}
            for code in sorted(set(league_codes))
            if code
        ]

        analysis = {
            "league_stats": {
                "draw_rate": stats.get("draw_rate"),
                "avg_goals": stats.get("avg_total_goals") if stats.get("avg_total_goals") is not None else stats.get("avg_goals"),
                "over_2_5_rate": stats.get("over_2_5_rate"),
                "btts_rate": stats.get("btts_rate") if stats.get("btts_rate") is not None else stats.get("btts_yes_rate"),
                "sample_size": stats.get("sample_size"),
            }
        }

        historical_impact = build_historical_impact(
            lottery_type="ZUCAI",
            league_code=primary_league_code,
            odds=None,
            analysis=analysis,
            similar_odds_result=None,
            data_source={
                "raw_json_path": datasets_dir("raw", "COMPLETE_FOOTBALL_DATA_FINAL_UPDATED.json"),
                "chroma_db_path": None,
            },
        )

        base_schema = RecommendationSchema(
            recommended_leagues=recommended_leagues,
            recommended_bets=recommended_bets,
            recommended_parlays=[],
            live_check=None,
            post_match_review=None,
            audit=AuditTrail(sources=["ZucaiWorkflow"], raw_refs=raw_refs, degradations=[], conflicts=[]),
        )

        ticket_out: Optional[Dict[str, Any]] = None
        ticket_validation: Optional[Dict[str, Any]] = None
        router_events: List[str] = []
        router_conflicts: List[str] = []
        try:
            built = self.ticket_builder.build_validated_ticket(schema=base_schema, stake=float(stake), date=date)
            if isinstance(built, dict):
                ticket_out = built.get("ticket") if isinstance(built.get("ticket"), dict) else None
                ticket_validation = built.get("validation") if isinstance(built.get("validation"), dict) else None
                if built.get("ok") is True and ticket_out and ticket_validation:
                    router_status = (ticket_validation.get("router") or {}).get("status")
                    router_events.append(f"router:{ticket_out.get('lottery_type')}:{router_status}")
                else:
                    err = built.get("error") if isinstance(built.get("error"), dict) else None
                    code = (err or {}).get("code") if isinstance(err, dict) else "UNKNOWN"
                    msg = (err or {}).get("message") if isinstance(err, dict) else "ticket rejected"
                    router_conflicts.append(f"ticket_reject:{code}:{msg}")
        except Exception as e:
            router_conflicts.append(f"ticket_build_error:{type(e).__name__}:{e}")

        results = self.fetcher.get_results_normalized(date=date)
        results_by_match_id: Dict[str, Dict[str, Any]] = {}
        for r in results:
            if isinstance(r, dict) and r.get("match_id"):
                results_by_match_id[str(r.get("match_id"))] = r

        settlement_summary: Dict[str, Any] = {
            "status": "PENDING",
            "legs_total": len(recommended_bets),
            "legs_settled": 0,
            "legs_correct": 0,
            "legs_void": 0,
            "legs_missing": 0,
            "per_leg": [],
        }
        all_ok = True
        any_missing = False
        for b in recommended_bets:
            mid = str(b.match_id or "")
            res = results_by_match_id.get(mid)
            if not res or not res.get("score_ft"):
                any_missing = True
                settlement_summary["legs_missing"] += 1
                settlement_summary["per_leg"].append({"match_id": mid, "status": "PENDING"})
                continue
            score_ft = str(res.get("score_ft") or "")
            status = str(res.get("status") or "FINISHED")
            det = self.settlement_engine.determine_all_play_types_results(score_ft, status=status)
            if str(det.get("status") or "").upper() == "VOID":
                settlement_summary["legs_void"] += 1
                settlement_summary["legs_settled"] += 1
                settlement_summary["per_leg"].append({"match_id": mid, "status": "VOID", "ft_score": score_ft})
                continue
            official = str(det.get("WDL") or det.get("official_result") or "")
            ok = str(b.selection) == official
            settlement_summary["legs_settled"] += 1
            if ok:
                settlement_summary["legs_correct"] += 1
            else:
                all_ok = False
            settlement_summary["per_leg"].append(
                {
                    "match_id": mid,
                    "status": "SETTLED",
                    "ft_score": score_ft,
                    "official_result": official,
                    "picked": str(b.selection),
                    "hit": ok,
                }
            )

        pnl = 0.0
        if any_missing:
            settlement_summary["status"] = "PENDING"
            pnl = 0.0
        else:
            settlement_summary["status"] = "WON" if all_ok else "LOST"
            payout = float(stake) if all_ok else 0.0
            settlement_summary["payout"] = payout
            pnl = payout - float(stake)

        post_match_review = {
            "play_type": pt,
            "stake": float(stake),
            "selection_heuristic": {"primary_league_code": primary_league_code, "picked": selection, "draw_rate": stats.get("draw_rate")},
            "settlement": settlement_summary,
            "pnl": pnl,
            "ts": _now_utc(),
        }

        audit_sources = list(base_schema.audit.sources)
        if router_events or router_conflicts:
            audit_sources.append("LotteryRouter")
        if ticket_out:
            audit_sources.append("TicketBuilder")

        degradations = list(base_schema.audit.degradations)
        degradations.extend(router_events)
        conflicts = list(base_schema.audit.conflicts)
        conflicts.extend(router_conflicts)

        explain = list(getattr(base_schema.audit, "explain", []))
        explain.append(to_explain_item(historical_impact))

        audit = AuditTrail(
            sources=[s for s in audit_sources if s],
            raw_refs=[r for r in base_schema.audit.raw_refs if r],
            degradations=[d for d in degradations if d],
            conflicts=[c for c in conflicts if c],
            explain=explain,
        )

        final_schema = RecommendationSchema(
            recommended_leagues=recommended_leagues,
            recommended_bets=recommended_bets,
            recommended_parlays=[],
            live_check=None,
            post_match_review=post_match_review,
            audit=audit,
        )
        out = final_schema.to_dict()
        out["historical_impact"] = historical_impact
        out["ticket"] = {"ticket": ticket_out, "validation": ticket_validation} if ticket_out else None
        return out
