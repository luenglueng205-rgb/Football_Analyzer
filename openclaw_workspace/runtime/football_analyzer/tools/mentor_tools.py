import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from tools.betting_ledger import BettingLedger
from tools.daily_reporter import DailyReporter
from tools.live_match_monitor import LiveMatchMonitor
from tools.historical_database import get_historical_database
from tools.historical_impact import build_historical_impact
from tools.memory_manager import MemoryManager
from tools.settlement_engine import SettlementEngine


_LEAGUE_ALIASES: Dict[str, str] = {
    "英超": "E0",
    "premier league": "E0",
    "epl": "E0",
    "西甲": "SP1",
    "laliga": "SP1",
    "la liga": "SP1",
    "意甲": "I1",
    "serie a": "I1",
    "德甲": "D1",
    "bundesliga": "D1",
    "法甲": "F1",
    "ligue 1": "F1",
    "欧冠": "CL",
    "champions league": "CL",
}


def identify_league(league_name: str) -> Dict[str, Any]:
    key = (league_name or "").strip().lower()
    code = _LEAGUE_ALIASES.get(key) or _LEAGUE_ALIASES.get(key.replace("-", " ")) or "UNK"
    candidates = []
    for alias, c in _LEAGUE_ALIASES.items():
        if key and (key in alias or alias in key):
            candidates.append({"league_code": c, "alias": alias})
    if not candidates and code != "UNK":
        candidates.append({"league_code": code, "alias": key})
    return {
        "ok": True,
        "data": {"input": league_name, "league_code": code, "candidates": candidates},
        "error": None,
        "meta": {"source": "mentor_tools"},
    }


def recommend_league(query: str, top_n: int = 3) -> Dict[str, Any]:
    text = (query or "").strip().lower()
    picks: List[Dict[str, Any]] = []
    for alias, code in _LEAGUE_ALIASES.items():
        if text and (alias in text or text in alias):
            picks.append({"league_code": code, "confidence": 0.9, "reason": f"match:{alias}"})
    if not picks:
        picks = [{"league_code": "E0", "confidence": 0.6, "reason": "default"}, {"league_code": "SP1", "confidence": 0.55, "reason": "default"}]
    return {"ok": True, "data": {"query": query, "recommended_leagues": picks[: max(1, int(top_n))]}, "error": None, "meta": {"source": "mentor_tools"}}


def recommend_bets(
    league_code: str,
    home_team: str,
    away_team: str,
    odds: Optional[Dict[str, float]] = None,
    lottery_type: str = "jingcai",
    stake: float = 100.0,
) -> Dict[str, Any]:
    lt = (lottery_type or "jingcai").strip().lower()
    lt_upper = lt.upper()

    odds_in = odds if isinstance(odds, dict) else None
    odds_for_calc = odds_in
    if lt != "zucai":
        odds_for_calc = odds_for_calc or {"home": 2.2, "draw": 3.2, "away": 3.4}

    if isinstance(odds_for_calc, dict) and odds_for_calc:
        inv = {k: (1.0 / float(v)) if v else 0.0 for k, v in odds_for_calc.items()}
        total = sum(inv.values()) or 1.0
        probs = {k: (v / total) for k, v in inv.items()}
        best = max(("home", "draw", "away"), key=lambda k: probs.get(k, 0.0))
        best_odds_raw = odds_for_calc.get(best)
        best_odds = float(best_odds_raw) if isinstance(best_odds_raw, (int, float)) and float(best_odds_raw) > 0 else None
        best_prob = float(probs.get(best) or 0.0)
    else:
        probs = {"home": 1.0 / 3.0, "draw": 1.0 / 3.0, "away": 1.0 / 3.0}
        best = "home"
        best_odds = None
        best_prob = 1.0 / 3.0

    if lt == "zucai":
        ev = None
    else:
        factor = 0.65 if lt == "beidan" else 1.0
        ev = (best_odds * best_prob * factor) - 1.0 if best_odds and best_prob else None

    match_id = f"{league_code}:{home_team}:{away_team}".replace(" ", "_")
    analysis: Dict[str, Any] = {}
    try:
        db = get_historical_database(lazy_load=True)
        stats = db.get_league_stats(str(league_code))
        if isinstance(stats, dict) and int(stats.get("sample_size", 0) or 0) > 0:
            league_stats = {
                "sample_size": int(stats.get("sample_size") or 0),
                "avg_goals": stats.get("avg_total_goals"),
                "over_2_5_rate": stats.get("over_2_5_rate"),
                "btts_rate": stats.get("btts_yes_rate"),
                "draw_rate": stats.get("draw_rate"),
            }
            calibration_info = {
                "calibrated": True,
                "historical_weight": 0.0,
                "sample_size": int(stats.get("sample_size") or 0),
                "hist_distribution": {
                    "home": stats.get("home_win_rate"),
                    "draw": stats.get("draw_rate"),
                    "away": stats.get("away_win_rate"),
                },
            }
            analysis = {"league_stats": league_stats, "calibration_info": calibration_info}
    except Exception:
        analysis = {}

    similar_odds_result: Optional[Dict[str, Any]] = None
    data_source = {"raw_json_path": None, "chroma_db_path": None}
    if lt != "zucai":
        try:
            mm = MemoryManager()
            data_source = {"raw_json_path": None, "chroma_db_path": getattr(mm, "db_path", None)}
            if league_code and str(league_code) != "UNK" and isinstance(odds_for_calc, dict):
                similar_odds_result = mm.query_historical_odds(
                    league=str(league_code),
                    home_odds=float(odds_for_calc.get("home") or 0.0),
                    draw_odds=float(odds_for_calc.get("draw") or 0.0),
                    away_odds=float(odds_for_calc.get("away") or 0.0),
                    tolerance=0.10,
                    limit=20,
                )
        except Exception:
            similar_odds_result = {"_exception": True}

    odds_for_hi = odds_for_calc if lt != "zucai" else None
    historical_impact = build_historical_impact(
        lottery_type=lt_upper,
        league_code=league_code,
        odds=odds_for_hi,
        analysis=analysis,
        similar_odds_result=similar_odds_result,
        data_source=data_source,
    )

    return {
        "ok": True,
        "data": {
            "match_id": match_id,
            "league_code": league_code,
            "home_team": home_team,
            "away_team": away_team,
            "odds": odds_for_calc if lt != "zucai" else odds_in,
            "historical_impact": historical_impact,
            "recommended_bets": [
                {
                    "match_id": match_id,
                    "lottery_type": lt,
                    "market": "WDL",
                    "selection": best,
                    "prob": round(best_prob, 4),
                    "odds": best_odds,
                    "ev": round(ev, 4) if isinstance(ev, float) else ev,
                    "stake": float(stake),
                }
            ],
        },
        "error": None,
        "meta": {"source": "mentor_tools"},
    }


def live_check(
    match_id: str,
    selection: str,
    original_stake: float,
    original_odds: float,
    current_score: str,
    live_odds_against: float,
    current_minute: int,
) -> Dict[str, Any]:
    monitor = LiveMatchMonitor()
    monitor.register_live_bet(match_id, selection, float(original_stake), float(original_odds))
    return {
        "ok": True,
        "data": monitor.evaluate_hedge_opportunity(match_id, current_score, float(live_odds_against), int(current_minute)),
        "error": None,
        "meta": {"source": "mentor_tools"},
    }


def post_match_review(
    match_id: str,
    ft_score: str,
    selection: str,
    stake: float,
    odds: float,
    status: str = "FINISHED",
    date_str: Optional[str] = None,
) -> Dict[str, Any]:
    date_str = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    settlement = SettlementEngine().determine_match_result(ft_score=ft_score, status=status)
    selection_to_code = {"home": "3", "draw": "1", "away": "0", "3": "3", "1": "1", "0": "0"}
    picked = selection_to_code.get(str(selection).lower(), str(selection))
    pnl = -float(stake)
    if settlement.get("status") == "SETTLED" and picked == str(settlement.get("official_result")):
        pnl = float(stake) * (float(odds) - 1.0)
    report = DailyReporter().generate_report(date_str=date_str, pnl=pnl, evolution_reason="post_match_review")
    return {
        "ok": True,
        "data": {
            "match_id": match_id,
            "settlement": settlement,
            "pnl": pnl,
            "daily_report": report,
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
        "error": None,
        "meta": {"source": "mentor_tools"},
    }

_LEDGER: Optional[BettingLedger] = None
_LIVE_MONITOR: Optional[LiveMatchMonitor] = None


def _get_ledger(db_path: Optional[str] = None) -> BettingLedger:
    if db_path:
        return BettingLedger(db_path=db_path)
    global _LEDGER
    if _LEDGER is None:
        _LEDGER = BettingLedger()
    return _LEDGER


def _get_live_monitor(reset: bool = False) -> LiveMatchMonitor:
    global _LIVE_MONITOR
    if _LIVE_MONITOR is None:
        _LIVE_MONITOR = LiveMatchMonitor()
    if reset:
        _LIVE_MONITOR.active_bets = {}
    return _LIVE_MONITOR


def _extract_ticket_request(
    recommendation_schema: Optional[Dict[str, Any]],
    ticket_request: Optional[Dict[str, Any]],
    match_id: Optional[str],
    lottery_type: Optional[str],
    selection: Optional[str],
    odds: Optional[float],
    stake: Optional[float],
) -> Dict[str, Any]:
    if isinstance(recommendation_schema, dict):
        bets = recommendation_schema.get("recommended_bets")
        if isinstance(bets, list) and bets:
            b0 = bets[0] if isinstance(bets[0], dict) else None
            if isinstance(b0, dict):
                match_id = match_id or b0.get("match_id")
                lottery_type = lottery_type or b0.get("lottery_type") or b0.get("lottery") or b0.get("type")
                selection = selection or b0.get("selection")
                odds = odds if odds is not None else b0.get("odds")
                stake = stake if stake is not None else b0.get("stake")

    if isinstance(ticket_request, dict):
        match_id = match_id or ticket_request.get("match_id")
        lottery_type = lottery_type or ticket_request.get("lottery_type") or ticket_request.get("lottery")
        selection = selection or ticket_request.get("selection")
        odds = odds if odds is not None else ticket_request.get("odds")
        stake = stake if stake is not None else ticket_request.get("stake")

    return {
        "match_id": match_id,
        "lottery_type": lottery_type,
        "selection": selection,
        "odds": odds,
        "stake": stake,
    }


def place_ticket(
    recommendation_schema: Any = None,
    ticket_request: Any = None,
    match_id: Optional[str] = None,
    lottery_type: Optional[str] = None,
    selection: Optional[str] = None,
    odds: Optional[float] = None,
    stake: Optional[float] = None,
    db_path: Optional[str] = None,
    reset_live_monitor: bool = False,
) -> Dict[str, Any]:
    schema_dict = _loads_args(recommendation_schema)
    ticket_dict = _loads_args(ticket_request)

    req = _extract_ticket_request(
        recommendation_schema=schema_dict,
        ticket_request=ticket_dict,
        match_id=match_id,
        lottery_type=lottery_type,
        selection=selection,
        odds=odds,
        stake=stake,
    )

    m_id = req.get("match_id")
    lt = (req.get("lottery_type") or "jingcai").lower()
    sel = req.get("selection")
    o = req.get("odds")
    s = req.get("stake")

    if not m_id or not sel or o is None or s is None:
        return {
            "ok": False,
            "data": None,
            "error": {
                "code": "INVALID_TICKET_REQUEST",
                "message": "place_ticket requires match_id, selection, odds, stake (or a RecommendationSchema with recommended_bets[0]).",
            },
            "meta": {"source": "mentor_tools", "simulated": True},
        }

    try:
        o_f = float(o)
        s_f = float(s)
    except Exception:
        return {
            "ok": False,
            "data": None,
            "error": {"code": "INVALID_NUMBER", "message": "odds/stake must be numeric."},
            "meta": {"source": "mentor_tools", "simulated": True},
        }

    ledger = _get_ledger(db_path=db_path)
    ledger_res = ledger.execute_bet(match_id=str(m_id), lottery_type=str(lt), selection=str(sel), odds=o_f, stake=s_f)
    if ledger_res.get("status") != "success":
        return {
            "ok": False,
            "data": {"ledger": ledger_res},
            "error": {"code": "BET_REJECTED", "message": str(ledger_res.get("message") or "execute_bet failed")},
            "meta": {"source": "mentor_tools", "simulated": True},
        }

    monitor = _get_live_monitor(reset=bool(reset_live_monitor))
    monitor.register_live_bet(str(m_id), str(sel), s_f, o_f)
    active_bet = monitor.active_bets.get(str(m_id))

    return {
        "ok": True,
        "data": {
            "match_id": str(m_id),
            "lottery_type": str(lt),
            "selection": str(sel),
            "odds": o_f,
            "stake": s_f,
            "ledger": ledger_res,
            "live_monitor": active_bet,
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
        "error": None,
        "meta": {"source": "mentor_tools", "simulated": True},
    }


def _loads_args(args: Any) -> Dict[str, Any]:
    if args is None:
        return {}
    if isinstance(args, dict):
        return args
    if isinstance(args, str):
        try:
            parsed = json.loads(args)
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, dict):
            return parsed
    return {}
