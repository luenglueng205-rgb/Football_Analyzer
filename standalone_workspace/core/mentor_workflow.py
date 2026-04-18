from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from core.recommendation_schema import AuditTrail, RecommendedBet, RecommendationSchema, RecommendationSchemaAdapter
from tools.daily_reporter import DailyReporter
from tools.betting_ledger import BettingLedger
from tools.live_match_monitor import LiveMatchMonitor
from tools.lottery_router import LotteryRouter
from tools.multisource_fetcher import MultiSourceFetcher
from tools.odds_analyzer import OddsAnalyzer
from tools.simulated_execution_engine import SimulatedExecutionEngine
from tools.settlement_engine import SettlementEngine
from tools.ticket_builder import LotteryTicketBuilder
from tools.memory_manager import MemoryManager
from tools.memory_retriever import MemoryRetriever
from tools.memory_writer import MemoryWriter
from tools.historical_impact import build_historical_impact, to_explain_item
from tools.paths import datasets_dir


MemoryHook = Callable[[Dict[str, Any]], Dict[str, Any]]


def _noop_memory_hook(_: Dict[str, Any]) -> Dict[str, Any]:
    return {"ok": True, "hook": "noop"}


class MentorWorkflow:
    def __init__(
        self,
        *,
        fetcher: Optional[MultiSourceFetcher] = None,
        odds_analyzer: Optional[OddsAnalyzer] = None,
        router: Optional[LotteryRouter] = None,
        live_monitor: Optional[LiveMatchMonitor] = None,
        settlement_engine: Optional[SettlementEngine] = None,
        daily_reporter: Optional[DailyReporter] = None,
        ledger: Optional[BettingLedger] = None,
        ticket_builder: Optional[LotteryTicketBuilder] = None,
        execution_engine: Optional[SimulatedExecutionEngine] = None,
        pre_match_memory_hook: Optional[MemoryHook] = None,
        post_match_memory_hook: Optional[MemoryHook] = None,
        memory_manager: Optional[MemoryManager] = None,
        memory_retriever: Optional[MemoryRetriever] = None,
        memory_writer: Optional[MemoryWriter] = None,
    ):
        self.fetcher = fetcher or MultiSourceFetcher()
        self.odds_analyzer = odds_analyzer or OddsAnalyzer(use_historical=True)
        self.router = router or LotteryRouter()
        self.live_monitor = live_monitor or LiveMatchMonitor()
        self.settlement_engine = settlement_engine or SettlementEngine()
        self.daily_reporter = daily_reporter or DailyReporter()
        self.ledger = ledger
        self.ticket_builder = ticket_builder or LotteryTicketBuilder(router=self.router)
        self.execution_engine = execution_engine
        self.memory_manager = memory_manager or MemoryManager()
        self.memory_retriever = memory_retriever or MemoryRetriever(manager=self.memory_manager)
        self.memory_writer = memory_writer or MemoryWriter(manager=self.memory_manager)

        if pre_match_memory_hook is not None:
            self.pre_match_memory_hook = pre_match_memory_hook
        else:
            def _default_pre_hook(payload: Dict[str, Any]) -> Dict[str, Any]:
                match = payload.get("match") if isinstance(payload, dict) else None
                match = match if isinstance(match, dict) else {}
                return self.memory_retriever.retrieve_for_match(match=match, top_k=5)
            self.pre_match_memory_hook = _default_pre_hook

        if post_match_memory_hook is not None:
            self.post_match_memory_hook = post_match_memory_hook
        else:
            def _default_post_hook(payload: Dict[str, Any]) -> Dict[str, Any]:
                match = payload.get("match") if isinstance(payload, dict) else None
                match = match if isinstance(match, dict) else {}
                settlement = payload.get("settlement") if isinstance(payload, dict) else None
                pnl = payload.get("pnl") if isinstance(payload, dict) else None
                summary = f"post_match: match_id={match.get('match_id')} league={match.get('league_code')} ft={getattr(settlement, 'get', lambda _k, _d=None: None)('ft_score')} pnl={pnl}"
                tags = ["mentor_workflow", "post_match"]
                if isinstance(settlement, dict) and settlement.get("official_result") is not None:
                    tags.append(f"result:{settlement.get('official_result')}")
                if isinstance(pnl, (int, float)):
                    tags.append("pnl:win" if float(pnl) > 0 else ("pnl:push" if float(pnl) == 0 else "pnl:lose"))
                return self.memory_writer.write_post_match(
                    match=match,
                    summary=summary,
                    tags=tags,
                    metadata={"settlement": settlement, "pnl": pnl} if isinstance(settlement, dict) else {"pnl": pnl},
                )
            self.post_match_memory_hook = _default_post_hook

    def run(
        self,
        *,
        date: str,
        match_id: Optional[str] = None,
        match_index: int = 0,
        stake: float = 100.0,
        auto_trade: bool = False,
        current_score: str = "1-0",
        current_minute: int = 76,
        live_odds_against: float = 4.5,
        ft_score_fallback: str = "2-1",
    ) -> Dict[str, Any]:
        fixtures = self.fetcher.get_fixtures_normalized(date=date)
        if not fixtures:
            empty = RecommendationSchema(
                recommended_leagues=[],
                recommended_bets=[],
                recommended_parlays=[],
                live_check=None,
                post_match_review=None,
                audit=AuditTrail(degradations=["no_fixtures"]),
            )
            return empty.to_dict()

        def odds_inputs(match: Dict[str, Any]) -> Dict[str, Any]:
            league_name = str(match.get("league_name") or match.get("league") or match.get("league_code") or "UNK")
            home_team = str(match.get("home_team") or "") or str(match.get("home_team_id") or "")
            away_team = str(match.get("away_team") or "") or str(match.get("away_team_id") or "")
            kickoff_time = str(match.get("kickoff_time_utc") or "")
            return {
                "league_name": league_name,
                "home_team": home_team,
                "away_team": away_team,
                "kickoff_time": kickoff_time,
                "source_ids": match.get("source_ids") if isinstance(match, dict) else None,
            }

        def fetch_odds(match: Dict[str, Any]) -> Dict[str, Any]:
            inp = odds_inputs(match)
            return self.fetcher.get_odds_normalized(
                league_name=inp["league_name"],
                home_team=inp["home_team"],
                away_team=inp["away_team"],
                kickoff_time=inp["kickoff_time"],
                source_ids=inp["source_ids"],
                lottery_type="JINGCAI",
                play_type="JINGCAI_WDL",
                market="WDL",
            )

        def odds_usable(odds_norm: Dict[str, Any]) -> bool:
            if odds_norm.get("ok") is not True:
                return False
            selections = odds_norm.get("selections") or {}
            odds_for_analyzer: Dict[str, float] = {
                "home": float(selections.get("H", {}).get("odds") or 0.0),
                "draw": float(selections.get("D", {}).get("odds") or 0.0),
                "away": float(selections.get("A", {}).get("odds") or 0.0),
            }
            return all(odds_for_analyzer.get(k, 0.0) > 0 for k in ("home", "draw", "away"))

        start_index = match_index % len(fixtures)
        selected = fixtures[start_index]
        odds_norm: Dict[str, Any]
        matched_match_id = False
        if match_id:
            for m in fixtures:
                if m.get("match_id") == match_id:
                    selected = m
                    matched_match_id = True
                    break

        if matched_match_id:
            odds_norm = fetch_odds(selected)
        else:
            odds_norm = fetch_odds(selected)
            if not odds_usable(odds_norm):
                for offset in range(1, len(fixtures)):
                    cand = fixtures[(start_index + offset) % len(fixtures)]
                    cand_odds = fetch_odds(cand)
                    if odds_usable(cand_odds):
                        selected = cand
                        odds_norm = cand_odds
                        break

        league_code = str(selected.get("league_code") or "UNK")
        recommended_leagues = [
            {
                "league_code": league_code,
                "confidence": float(selected.get("confidence") or 0.0),
                "reason": "fixtures_normalized",
            }
        ]

        pre_match_memory = self.pre_match_memory_hook({"stage": "A", "match": selected, "date": date})
        retrieved_memories: List[Dict[str, Any]] = []
        if isinstance(pre_match_memory, dict) and isinstance(pre_match_memory.get("data"), list):
            retrieved_memories = [m for m in pre_match_memory["data"] if isinstance(m, dict)]

        selections = odds_norm.get("selections") or {}
        odds_for_analyzer: Dict[str, float] = {
            "home": float(selections.get("H", {}).get("odds") or 0.0),
            "draw": float(selections.get("D", {}).get("odds") or 0.0),
            "away": float(selections.get("A", {}).get("odds") or 0.0),
        }
        complete_odds = all(odds_for_analyzer.get(k, 0.0) > 0 for k in ("home", "draw", "away"))
        fallback_events: List[str] = []
        analysis: Dict[str, Any] = {}
        if odds_norm.get("ok") is True and complete_odds:
            analysis = self.odds_analyzer.analyze(
                odds_for_analyzer, league=league_code, calibrate=True, memories=retrieved_memories
            )
            base_schema = RecommendationSchemaAdapter.from_odds_analyzer_output(
                analysis, match_id=selected.get("match_id"), memories=retrieved_memories
            )
            if not base_schema.recommended_bets:
                probs = analysis.get("implied_probabilities") if isinstance(analysis, dict) else None
                if isinstance(probs, dict):
                    best = max(
                        ("home", "draw", "away"),
                        key=lambda k: float(probs.get(k) or 0.0),
                    )
                    prob = float(probs.get(best) or 0.0)
                    odds = float(odds_for_analyzer.get(best) or 0.0)
                    if prob > 0 and odds > 0:
                        ev = (prob * odds) if prob and odds else None
                        base_schema = RecommendationSchema(
                            recommended_leagues=list(base_schema.recommended_leagues),
                            recommended_bets=[
                                RecommendedBet(
                                    match_id=selected.get("match_id"),
                                    lottery_type="JINGCAI",
                                    play_type="JINGCAI_WDL",
                                    market="WDL",
                                    selection=best,
                                    prob=prob,
                                    odds=odds,
                                    ev=ev,
                                    edge=None,
                                    risk_tags=["fallback"],
                                )
                            ],
                            recommended_parlays=list(base_schema.recommended_parlays),
                            live_check=base_schema.live_check,
                            post_match_review=base_schema.post_match_review,
                            audit=base_schema.audit,
                        )
                        fallback_events.append("fallback_bet_generated")
        else:
            err = odds_norm.get("error") if isinstance(odds_norm, dict) else None
            err_code = (err or {}).get("code") if isinstance(err, dict) else None
            degradations = [f"odds_unavailable:{err_code}"] if err_code else ["odds_unavailable"]
            base_schema = RecommendationSchema(
                recommended_leagues=[],
                recommended_bets=[],
                recommended_parlays=[],
                live_check=None,
                post_match_review=None,
                audit=AuditTrail(sources=["OddsNormalizer"], raw_refs=[], degradations=degradations, conflicts=[]),
            )

        similar_odds_result: Optional[Dict[str, Any]] = None
        try:
            if league_code != "UNK" and complete_odds:
                similar_odds_result = self.memory_manager.query_historical_odds(
                    league=league_code,
                    home_odds=float(odds_for_analyzer.get("home") or 0.0),
                    draw_odds=float(odds_for_analyzer.get("draw") or 0.0),
                    away_odds=float(odds_for_analyzer.get("away") or 0.0),
                    tolerance=0.10,
                    limit=20,
                )
        except Exception:
            similar_odds_result = {"_exception": True}

        historical_impact = build_historical_impact(
            lottery_type="JINGCAI",
            league_code=league_code,
            odds=odds_for_analyzer if complete_odds else None,
            analysis=analysis if isinstance(analysis, dict) else {},
            similar_odds_result=similar_odds_result,
            data_source={
                "raw_json_path": datasets_dir("raw", "COMPLETE_FOOTBALL_DATA_FINAL_UPDATED.json"),
                "chroma_db_path": getattr(self.memory_manager, "db_path", None),
            },
        )

        try:
            action = "bet" if base_schema.recommended_bets else "skip"
            primary = None
            if base_schema.recommended_bets:
                primary = str(base_schema.recommended_bets[0].selection)
            summary = (
                f"pre_match: match_id={selected.get('match_id')} league={league_code} "
                f"{selected.get('home_team')} vs {selected.get('away_team')} kickoff={selected.get('kickoff_time')} "
                f"odds={odds_for_analyzer} action={action} primary={primary} retrieved_memories={len(retrieved_memories)}"
            )
            tags = ["mentor_workflow", "pre_match", f"league:{league_code}", f"action:{action}"]
            if primary:
                tags.append(f"pick:{primary}")
            if fallback_events:
                tags.append("fallback")
            stored = self.memory_writer.write_pre_match(match=selected, summary=summary, tags=tags)
            if isinstance(pre_match_memory, dict):
                pre_match_memory = {**pre_match_memory, "stored": stored}
        except Exception:
            if isinstance(pre_match_memory, dict):
                pre_match_memory = {**pre_match_memory, "stored": {"ok": False}}

        router_events: List[str] = []
        router_conflicts: List[str] = []
        ticket_out: Optional[Dict[str, Any]] = None
        ticket_validation: Optional[Dict[str, Any]] = None
        execution_out: Optional[Dict[str, Any]] = None
        engine: Optional[SimulatedExecutionEngine] = self.execution_engine
        if base_schema.recommended_bets:
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

        if auto_trade and ticket_out and ticket_validation and ((ticket_validation.get("router") or {}).get("status") in {"SUCCESS", "VALIDATED"}):
            if engine is None:
                ledger = self.ledger or BettingLedger()
                engine = SimulatedExecutionEngine(ledger=ledger, live_monitor=self.live_monitor)
            execution_out = engine.execute(ticket=ticket_out)

        live_check: Optional[Dict[str, Any]] = None
        live_state_norm: Optional[Dict[str, Any]] = None
        try:
            live_state_norm = self.fetcher.get_live_state_normalized(
                match_id=selected.get("match_id"),
                league_name=str(selected.get("league") or selected.get("league_name") or "UNK"),
                home_team=str(selected.get("home_team") or ""),
                away_team=str(selected.get("away_team") or ""),
                kickoff_time=str(selected.get("kickoff_time") or ""),
                source_ids=selected.get("source_ids") if isinstance(selected.get("source_ids"), dict) else None,
            )
        except Exception:
            live_state_norm = None

        live_score = current_score
        live_minute = int(current_minute)
        if isinstance(live_state_norm, dict) and live_state_norm.get("ok"):
            if live_state_norm.get("score_ft"):
                live_score = str(live_state_norm.get("score_ft"))
            if live_state_norm.get("minute") is not None:
                try:
                    live_minute = int(live_state_norm.get("minute"))
                except Exception:
                    live_minute = int(current_minute)
        monitor_selection: Optional[str] = None
        monitor_odds: Optional[float] = None
        if ticket_out and isinstance(ticket_out.get("legs"), list) and ticket_out.get("legs"):
            leg0 = ticket_out["legs"][0]
            if isinstance(leg0, dict):
                monitor_selection = str(leg0.get("selection") or "")
                o0 = leg0.get("odds")
                monitor_odds = float(o0) if isinstance(o0, (int, float)) else None
        elif base_schema.recommended_bets:
            b0 = base_schema.recommended_bets[0]
            monitor_selection = str(b0.selection)
            monitor_odds = float(b0.odds) if isinstance(b0.odds, (int, float)) else None

        if monitor_odds and monitor_odds > 1.0 and monitor_selection:
            if not (auto_trade and execution_out and execution_out.get("ok")):
                self.live_monitor.register_live_bet(selected["match_id"], monitor_selection, float(stake), float(monitor_odds))
            live_check = self.live_monitor.evaluate_hedge_opportunity(selected["match_id"], live_score, float(live_odds_against), live_minute)
            if isinstance(live_check, dict) and isinstance(live_state_norm, dict) and live_state_norm.get("ok"):
                live_check["live_state"] = {k: v for k, v in live_state_norm.items() if k != "ok"}

        if live_check is None and isinstance(live_state_norm, dict) and live_state_norm.get("ok"):
            live_check = {
                "match_id": selected.get("match_id"),
                "current_score": live_score,
                "minute": live_minute,
                "recommended_action": "LIVE_STATE_ONLY",
                "live_state": {k: v for k, v in live_state_norm.items() if k != "ok"},
            }

        results = self.fetcher.get_results_normalized(date=date)
        ft_score = ft_score_fallback
        result_status = "FINISHED"
        result_hit: Optional[Dict[str, Any]] = None
        selected_fid: Optional[str] = None
        if isinstance(selected, dict):
            sids = selected.get("source_ids")
            if isinstance(sids, dict):
                if isinstance(sids.get("500.com"), dict) and sids["500.com"].get("fid"):
                    selected_fid = str(sids["500.com"]["fid"])
                elif sids.get("fid"):
                    selected_fid = str(sids.get("fid"))
        for r in results:
            if selected_fid and isinstance(r, dict):
                rids = r.get("source_ids")
                rfid = None
                if isinstance(rids, dict):
                    if isinstance(rids.get("500.com"), dict) and rids["500.com"].get("fid"):
                        rfid = str(rids["500.com"]["fid"])
                    elif rids.get("fid"):
                        rfid = str(rids.get("fid"))
                if rfid and rfid == selected_fid and r.get("score_ft"):
                    ft_score = str(r.get("score_ft"))
                    result_status = str(r.get("status") or "FINISHED")
                    result_hit = r
                    break
                if rfid and rfid == selected_fid:
                    result_status = str(r.get("status") or "FINISHED")
                    result_hit = r
            if r.get("match_id") == selected.get("match_id") and r.get("score_ft"):
                ft_score = str(r.get("score_ft"))
                result_status = str(r.get("status") or "FINISHED")
                result_hit = r
                break
            if r.get("match_id") == selected.get("match_id"):
                result_status = str(r.get("status") or "FINISHED")
                result_hit = r

        if hasattr(self.settlement_engine, "determine_match_result"):
            settlement = getattr(self.settlement_engine, "determine_match_result")(ft_score, status=result_status)
        else:
            all_results = self.settlement_engine.determine_all_play_types_results(ft_score, status=result_status)
            settlement = {
                "status": all_results.get("status"),
                "official_result": all_results.get("WDL"),
                "ft_score": ft_score,
            }

        pnl = 0.0
        if ticket_out and isinstance(ticket_out.get("legs"), list) and ticket_out.get("legs"):
            leg0 = ticket_out["legs"][0]
            if isinstance(leg0, dict):
                selection0 = str(leg0.get("selection") or "")
                odds0 = leg0.get("odds")
                odds0_f = float(odds0) if isinstance(odds0, (int, float)) else 1.0
                pnl = -float(stake)
                if str(settlement.get("status") or "").upper() == "VOID":
                    pnl = 0.0
                elif selection0 and selection0 == str(settlement.get("official_result")):
                    pnl = float(stake) * (odds0_f - 1.0)
        elif base_schema.recommended_bets:
            pnl = -float(stake)
            b0 = base_schema.recommended_bets[0]
            selection_to_code = {"home": "3", "draw": "1", "away": "0", "H": "3", "D": "1", "A": "0", "3": "3", "1": "1", "0": "0"}
            picked = selection_to_code.get(str(b0.selection), None)
            if picked is not None and picked == str(settlement.get("official_result")):
                pnl = float(stake) * (float(b0.odds or 1.0) - 1.0)

        if auto_trade and engine and ticket_out and execution_out and execution_out.get("ok"):
            settled = engine.settle(ticket=ticket_out, settlement=settlement)
            execution_out = {**execution_out, "settlement": settled, "pnl": settled.get("pnl")}
            if settled.get("ok") and isinstance(settled.get("pnl"), (int, float)):
                pnl = float(settled.get("pnl"))
        report = self.daily_reporter.generate_report(date_str=date, pnl=pnl, evolution_reason="mentor_workflow_demo")

        post_match_memory = self.post_match_memory_hook(
            {
                "stage": "D",
                "match_id": selected.get("match_id"),
                "match": selected,
                "recommendation_schema": base_schema.to_dict() if hasattr(base_schema, "to_dict") else None,
                "settlement": settlement,
                "pnl": pnl,
                "date": date,
            }
        )

        post_match_review = {
            "match_id": selected.get("match_id"),
            "settlement": settlement,
            "pnl": pnl,
            "daily_report": report,
            "memory_injection": {"pre_match": pre_match_memory, "post_match": post_match_memory},
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }

        audit_sources = list(base_schema.audit.sources)
        if selected.get("source"):
            audit_sources.append(str(selected.get("source")))
        if odds_norm.get("source"):
            audit_sources.append(str(odds_norm.get("source")))
        if result_hit and result_hit.get("source"):
            audit_sources.append(str(result_hit.get("source")))
        if isinstance(live_state_norm, dict) and live_state_norm.get("ok") and live_state_norm.get("source"):
            audit_sources.append(str(live_state_norm.get("source")))
        if router_events or router_conflicts:
            audit_sources.append("LotteryRouter")
        if ticket_out:
            audit_sources.append("TicketBuilder")
        if execution_out and execution_out.get("ok"):
            audit_sources.append("SimulatedExecutionEngine")
        raw_refs = list(base_schema.audit.raw_refs)
        if selected.get("raw_ref"):
            raw_refs.append(str(selected.get("raw_ref")))
        if odds_norm.get("raw_ref"):
            raw_refs.append(str(odds_norm.get("raw_ref")))
        if result_hit and result_hit.get("raw_ref"):
            raw_refs.append(str(result_hit.get("raw_ref")))
        if isinstance(live_state_norm, dict) and live_state_norm.get("ok") and live_state_norm.get("raw_ref"):
            raw_refs.append(str(live_state_norm.get("raw_ref")))

        degradations = list(base_schema.audit.degradations)
        odds_degradations = odds_norm.get("degradations") if isinstance(odds_norm, dict) else None
        if isinstance(odds_degradations, list):
            degradations.extend([str(x) for x in odds_degradations if x])
        degradations.extend(fallback_events)
        if isinstance(live_state_norm, dict) and not live_state_norm.get("ok") and isinstance(live_state_norm.get("error"), dict):
            degradations.append(f"live_state_unavailable:{live_state_norm['error'].get('code')}")
        if not result_hit:
            degradations.append("results_not_found")
        elif (result_hit.get("status") == "FINISHED" and not result_hit.get("score_ft")) or ft_score == ft_score_fallback:
            degradations.append("results_ft_fallback")
        degradations.extend(router_events)
        conflicts = list(base_schema.audit.conflicts)
        conflicts.extend(router_conflicts)
        explain = list(getattr(base_schema.audit, "explain", []))
        if not explain and retrieved_memories:
            explain.append({"type": "memory", "count": len(retrieved_memories), "items": list(retrieved_memories)[:5]})
        explain.append(to_explain_item(historical_impact))

        audit = AuditTrail(
            sources=[s for s in audit_sources if s],
            raw_refs=[r for r in raw_refs if r],
            degradations=[d for d in degradations if d],
            conflicts=[c for c in conflicts if c],
            explain=explain,
        )

        final_schema = RecommendationSchema(
            recommended_leagues=recommended_leagues,
            recommended_bets=list(base_schema.recommended_bets),
            recommended_parlays=list(base_schema.recommended_parlays),
            live_check=live_check,
            post_match_review=post_match_review,
            audit=audit,
        )
        out = final_schema.to_dict()
        out["historical_impact"] = historical_impact
        out["ticket"] = {"ticket": ticket_out, "validation": ticket_validation} if ticket_out else None
        out["execution"] = execution_out
        return out
