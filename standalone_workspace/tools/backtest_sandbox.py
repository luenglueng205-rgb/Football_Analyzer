from __future__ import annotations

import hashlib
import json
import logging
import os
import random
from datetime import datetime, timezone
from json import JSONDecoder
from typing import Any, Dict, Iterator, List, Optional, Tuple

from core.recommendation_schema import AuditTrail, RecommendedBet, RecommendationSchema
from tools.paths import datasets_dir
from tools.settlement_engine import SettlementEngine
from tools.ticket_builder import LotteryTicketBuilder

logger = logging.getLogger(__name__)


def _now_utc_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _safe_float(v: Any) -> Optional[float]:
    if isinstance(v, (int, float)):
        return float(v)
    try:
        if v is None:
            return None
        return float(str(v))
    except Exception:
        return None


def _wdl_from_min_odds(*, home_odds: float, draw_odds: float, away_odds: float) -> Tuple[str, float]:
    odds = [float(home_odds), float(draw_odds), float(away_odds)]
    idx = min(range(3), key=lambda i: odds[i])
    if idx == 0:
        return "3", odds[0]
    if idx == 1:
        return "1", odds[1]
    return "0", odds[2]


def _make_match_id(*, date: str, league: str, home_team: str, away_team: str) -> str:
    base = f"{date}|{league}|{home_team}|{away_team}"
    digest = hashlib.sha1(base.encode("utf-8")).hexdigest()[:10]
    d = str(date or "").replace("-", "")
    lg = str(league or "UNK").strip()
    h = str(home_team or "H").strip().replace(" ", "_")[:12]
    a = str(away_team or "A").strip().replace(" ", "_")[:12]
    return f"{d}_{lg}_{h}_{a}_{digest}"


def _iter_dataset_matches_streaming(filepath: str) -> Iterator[Dict[str, Any]]:
    decoder = JSONDecoder()
    buf = ""
    in_matches = False
    in_array = False
    pos = 0
    with open(filepath, "r", encoding="utf-8") as f:
        while True:
            if pos >= len(buf) - 1024:
                chunk = f.read(1024 * 256)
                if not chunk:
                    break
                buf = buf[pos:] + chunk
                pos = 0

            if not in_matches:
                idx = buf.find('"matches"', pos)
                if idx < 0:
                    pos = max(0, len(buf) - 16)
                    continue
                pos = idx + len('"matches"')
                in_matches = True

            if in_matches and not in_array:
                lb = buf.find("[", pos)
                if lb < 0:
                    pos = max(0, len(buf) - 16)
                    continue
                pos = lb + 1
                in_array = True

            if not in_array:
                continue

            while True:
                while pos < len(buf) and buf[pos] in " \r\n\t,":
                    pos += 1
                if pos >= len(buf):
                    break
                if buf[pos] == "]":
                    return
                try:
                    obj, end = decoder.raw_decode(buf, pos)
                except json.JSONDecodeError:
                    break
                pos = end
                if isinstance(obj, dict):
                    yield obj


def iter_dataset_matches(
    *,
    filepath: str,
    max_matches: Optional[int] = None,
    seed: int = 7,
    mode: str = "stream",
    sample_strategy: str = "first",
) -> Iterator[Dict[str, Any]]:
    md = str(mode or "stream").strip().lower()
    strategy = str(sample_strategy or "first").strip().lower()

    if md == "load_all":
        with open(filepath, "r", encoding="utf-8") as f:
            raw = json.load(f)
        matches = raw.get("matches", [])
        if not isinstance(matches, list):
            matches = []
        for i, m in enumerate(matches):
            if max_matches is not None and i >= int(max_matches):
                return
            if isinstance(m, dict):
                yield m
        return

    source = _iter_dataset_matches_streaming(filepath)
    if max_matches is None or strategy == "first":
        n = 0
        for m in source:
            yield m
            n += 1
            if max_matches is not None and n >= int(max_matches):
                return
        return

    k = int(max_matches)
    rng = random.Random(int(seed))
    sample: List[Dict[str, Any]] = []
    seen = 0
    for m in source:
        if not isinstance(m, dict):
            continue
        if len(sample) < k:
            sample.append(m)
        else:
            j = rng.randint(0, seen)
            if j < k:
                sample[j] = m
        seen += 1

    for m in sample:
        yield m


def _normalize_lottery_type(lt: str) -> str:
    up = str(lt or "").strip().upper()
    if up in {"JINGCAI", "JC"}:
        return "JINGCAI"
    if up in {"BEIDAN", "BD"}:
        return "BEIDAN"
    if up in {"ZUCAI", "ZC", "TRADITIONAL"}:
        return "ZUCAI"
    return "JINGCAI"


def _default_play_type(lottery_type: str) -> str:
    lt = _normalize_lottery_type(lottery_type)
    if lt == "ZUCAI":
        return "14_match"
    return "WDL"


def _normalize_play_type(lottery_type: str, play_type: str) -> str:
    lt = _normalize_lottery_type(lottery_type)
    pt = str(play_type or "").strip()
    if not pt:
        return _default_play_type(lt)
    up = pt.upper()
    if lt == "ZUCAI":
        low = pt.lower()
        if low in {"14_match", "renjiu", "6_htft", "4_goals"}:
            return low
        if up in {"ZUCAI_14_MATCH", "14_MATCH"}:
            return "14_match"
        if up in {"ZUCAI_RENJIU", "RENJIU", "RX9"}:
            return "renjiu"
        if up in {"ZUCAI_6_HTFT", "6_HTFT"}:
            return "6_htft"
        if up in {"ZUCAI_4_GOALS", "4_GOALS"}:
            return "4_goals"
        return "14_match"

    if up.startswith("JINGCAI_"):
        return up.replace("JINGCAI_", "", 1)
    if up.startswith("BEIDAN_"):
        return up.replace("BEIDAN_", "", 1)
    return up


def _ticket_batch_size(lottery_type: str, play_type: str) -> int:
    lt = _normalize_lottery_type(lottery_type)
    pt = _normalize_play_type(lt, play_type)
    if lt == "ZUCAI":
        if pt == "renjiu":
            return 9
        if pt == "6_htft":
            return 6
        if pt == "4_goals":
            return 4
        return 14
    if lt == "BEIDAN":
        return 15 if pt in {"MIXED_PARLAY"} else 1
    return 8 if pt in {"MIXED_PARLAY"} else 1


def _render_backtest_markdown(report: Dict[str, Any]) -> str:
    s = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    hi = report.get("historical_impact_aggregates") if isinstance(report.get("historical_impact_aggregates"), dict) else {}
    by_league = hi.get("by_league") if isinstance(hi.get("by_league"), list) else []
    lines: List[str] = []
    lines.append("# Grand Blind Backtest Report")
    lines.append("")
    lines.append(f"- run_id: {report.get('run_id')}")
    lines.append(f"- lottery_type: {report.get('lottery_type')}")
    lines.append(f"- play_type: {report.get('play_type')}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- tickets_total: {s.get('tickets_total')}")
    lines.append(f"- tickets_validated: {s.get('tickets_validated')}")
    lines.append(f"- tickets_rejected: {s.get('tickets_rejected')}")
    lines.append(f"- stake_total: {s.get('stake_total')}")
    lines.append(f"- payout_total: {s.get('payout_total')}")
    lines.append(f"- pnl_total: {s.get('pnl_total')}")
    lines.append(f"- roi: {s.get('roi')}")
    lines.append(f"- win_rate: {s.get('win_rate')}")
    lines.append("")
    lines.append("## Historical Impact Aggregates")
    lines.append("")
    lines.append(f"- matches_total: {hi.get('matches_total')}")
    lines.append(f"- date_range: {hi.get('date_range')}")
    lines.append("")
    if by_league:
        lines.append("### Top Leagues")
        lines.append("")
        lines.append("| league | n | home% | draw% | away% | avg_goals |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for rec in by_league[:10]:
            if not isinstance(rec, dict):
                continue
            lines.append(
                f"| {rec.get('league')} | {rec.get('n')} | {rec.get('home_win_rate')} | {rec.get('draw_rate')} | {rec.get('away_win_rate')} | {rec.get('avg_goals')} |"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


class BacktestSandbox:
    def __init__(self):
        self.hyperparams_path = os.path.join(os.path.dirname(__file__), "..", "configs", "hyperparams.json")
        self._load_hyperparams()
        self.ticket_builder = LotteryTicketBuilder()
        self.settlement_engine = SettlementEngine()

    def _load_hyperparams(self):
        try:
            with open(self.hyperparams_path, "r", encoding="utf-8") as f:
                self.params = json.load(f)
        except Exception as e:
            logger.error(f"加载超参数失败: {e}")
            self.params = {}

    def simulate_match(self, match_data: dict) -> dict:
        home = match_data["home"]
        away = match_data["away"]
        odds = match_data["pre_match_odds"]
        true_result = match_data["actual_result"]

        w_fun = self.params.get("weights", {}).get("fundamental_quant", 0.33)
        w_con = self.params.get("weights", {}).get("contrarian_quant", 0.33)
        w_smt = self.params.get("weights", {}).get("smart_money_quant", 0.33)

        if odds[0] < 1.5:
            ai_score_home = w_fun * 0.9 + w_con * 0.1 + w_smt * 0.5
            ai_score_draw = w_fun * 0.05 + w_con * 0.6 + w_smt * 0.3
        else:
            ai_score_home = w_fun * 0.4 + w_con * 0.4 + w_smt * 0.4
            ai_score_draw = w_fun * 0.3 + w_con * 0.3 + w_smt * 0.3

        ai_decision = "3" if ai_score_home > ai_score_draw else "1"

        stake = 100.0
        if ai_decision == true_result:
            hit_odds = odds[0] if true_result == "3" else (odds[1] if true_result == "1" else odds[2])
            profit = (stake * hit_odds) - stake
            status = "WIN"
        else:
            profit = -stake
            status = "LOSS"

        return {
            "match": f"{home} vs {away}",
            "decision": ai_decision,
            "actual": true_result,
            "odds": odds,
            "status": status,
            "profit": profit,
            "ai_confidence_home": ai_score_home,
        }

    def run_batch_simulation(self, historical_matches: list) -> dict:
        logger.info(f"⏳ 启动时光机，开始回测 {len(historical_matches)} 场历史赛事...")
        results = []
        total_profit = 0
        wins = 0

        for match in historical_matches:
            res = self.simulate_match(match)
            results.append(res)
            total_profit += res["profit"]
            if res["status"] == "WIN":
                wins += 1

        total_matches = len(historical_matches)
        win_rate = wins / total_matches if total_matches > 0 else 0
        roi = total_profit / (total_matches * 100) if total_matches > 0 else 0

        report = {
            "total_simulated": total_matches,
            "wins": wins,
            "win_rate": round(win_rate, 3),
            "total_profit": round(total_profit, 2),
            "roi": round(roi, 3),
            "details": results,
        }

        logger.info(f"📊 时光机报告: 胜率 {win_rate*100:.1f}%, ROI {roi*100:.1f}%, 净利 {total_profit}")
        return report

    def run_grand_blind_backtest(
        self,
        *,
        dataset_path: Optional[str] = None,
        lottery_type: str = "JINGCAI",
        play_type: str = "",
        stake: float = 100.0,
        max_matches: Optional[int] = None,
        seed: int = 7,
        dataset_mode: str = "stream",
        sample_strategy: str = "first",
        output_dir: Optional[str] = None,
        keep_examples: int = 20,
    ) -> Dict[str, Any]:
        lt = _normalize_lottery_type(lottery_type)
        pt = _normalize_play_type(lt, play_type)
        path = dataset_path or datasets_dir("raw", "COMPLETE_FOOTBALL_DATA_FINAL_UPDATED.json")
        run_id = f"grand_blind::{_now_utc_compact()}::{lt}::{pt}"

        out_dir = output_dir or os.path.join(os.path.dirname(__file__), "..", "reports", "backtests")
        os.makedirs(out_dir, exist_ok=True)

        batch_size = _ticket_batch_size(lt, pt)

        tickets_total = 0
        tickets_validated = 0
        tickets_rejected = 0
        stake_total = 0.0
        payout_total = 0.0
        pnl_total = 0.0
        tickets_won = 0

        examples: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []

        league_stats: Dict[str, Dict[str, Any]] = {}
        date_min: Optional[str] = None
        date_max: Optional[str] = None
        matches_total = 0

        def update_hist_agg(m: Dict[str, Any]) -> None:
            nonlocal matches_total, date_min, date_max
            league = str(m.get("league") or m.get("league_code") or "UNK")
            d = str(m.get("date") or "")
            if d:
                if date_min is None or d < date_min:
                    date_min = d
                if date_max is None or d > date_max:
                    date_max = d
            home_goals = _safe_float(m.get("home_goals"))
            away_goals = _safe_float(m.get("away_goals"))
            rec = league_stats.get(league)
            if rec is None:
                rec = {"n": 0, "home": 0, "draw": 0, "away": 0, "goals_sum": 0.0}
                league_stats[league] = rec
            if isinstance(home_goals, (int, float)) and isinstance(away_goals, (int, float)):
                if home_goals > away_goals:
                    rec["home"] += 1
                elif home_goals == away_goals:
                    rec["draw"] += 1
                else:
                    rec["away"] += 1
                rec["goals_sum"] += float(home_goals) + float(away_goals)
            rec["n"] += 1
            matches_total += 1

        def settle_ticket_fixed_odds(ticket: Dict[str, Any], results_by_mid: Dict[str, Dict[str, Any]]) -> Tuple[float, Dict[str, Any]]:
            settlement = self.settlement_engine.settle_ticket(ticket, results_by_mid)
            payout = float(settlement.get("payout") or 0.0)
            pnl = payout - float(ticket.get("stake") or 0.0)
            return pnl, settlement

        def build_results_for_ticket(ticket: Dict[str, Any], match_map: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
            res: Dict[str, Dict[str, Any]] = {}
            for leg in ticket.get("legs") or []:
                mid = str(leg.get("match_id") or "")
                if not mid:
                    continue
                m = match_map.get(mid)
                if not isinstance(m, dict):
                    continue
                ft = str(m.get("result") or "")
                det = self.settlement_engine.determine_all_play_types_results(ft, status="FINISHED")
                if str(det.get("status") or "").upper() == "VOID":
                    res[mid] = {"status": "VOID", "official_result": "REFUND", "ft_score": ft}
                    continue
                leg_pt = str(leg.get("play_type") or "WDL").strip().upper()
                key = leg_pt
                if key in {"HANDICAP"}:
                    key = f"{lt}_HANDICAP_WDL"
                elif key == "SFGG":
                    key = "BEIDAN_SFGG"
                else:
                    key = f"{lt}_{key}"
                official = det.get(key)
                if official is None:
                    official = det.get(leg_pt) or det.get("WDL") or det.get("official_result")
                res[mid] = {"status": "SETTLED", "official_result": str(official), "ft_score": ft}
            return res

        current_date: Optional[str] = None
        bucket: List[Dict[str, Any]] = []

        def flush_bucket() -> None:
            nonlocal tickets_total, tickets_validated, tickets_rejected, stake_total, payout_total, pnl_total, tickets_won
            nonlocal bucket, current_date

            if not bucket:
                return

            date = current_date or (bucket[0].get("date") or "")
            legs_bets: List[RecommendedBet] = []
            match_map: Dict[str, Dict[str, Any]] = {}
            degradations: List[str] = []

            for m in bucket:
                if not isinstance(m, dict):
                    continue
                league = str(m.get("league") or "UNK")
                dt = str(m.get("date") or date or "")
                home = str(m.get("home_team") or "")
                away = str(m.get("away_team") or "")
                mid = _make_match_id(date=dt, league=league, home_team=home, away_team=away)
                match_map[mid] = dict(m)

                home_odds = _safe_float(m.get("home_odds"))
                draw_odds = _safe_float(m.get("draw_odds"))
                away_odds = _safe_float(m.get("away_odds"))
                if lt != "ZUCAI" and (home_odds is None or draw_odds is None or away_odds is None):
                    degradations.append("missing_odds")
                    continue

                if lt == "ZUCAI":
                    selection, odds_used = "3", None
                    if home_odds is not None and draw_odds is not None and away_odds is not None:
                        selection, _ = _wdl_from_min_odds(home_odds=float(home_odds), draw_odds=float(draw_odds), away_odds=float(away_odds))
                else:
                    selection, odds_used = _wdl_from_min_odds(home_odds=float(home_odds), draw_odds=float(draw_odds), away_odds=float(away_odds))

                market = "WDL"
                odds_out = float(odds_used) if isinstance(odds_used, (int, float)) else None
                if lt == "BEIDAN" and pt == "SFGG":
                    odds_out = odds_out if odds_out is not None else 2.0
                    market = "HANDICAP"
                if lt == "BEIDAN" and pt in {"GOALS", "CS", "HTFT", "UP_DOWN_ODD_EVEN"}:
                    odds_out = odds_out if odds_out is not None else 2.0
                    degradations.append("synthetic_odds_for_beidan_non_fixed_market")
                bet_play_type = f"{lt}_{pt}" if lt != "ZUCAI" else f"ZUCAI_{pt.upper()}"
                legs_bets.append(
                    RecommendedBet(
                        match_id=mid,
                        lottery_type=lt,
                        play_type=bet_play_type,
                        market=market,
                        selection=selection,
                        prob=None,
                        odds=odds_out,
                        ev=None,
                        edge=None,
                        risk_tags=[],
                    )
                )

            tickets_total += 1
            stake_total += float(stake)

            schema = RecommendationSchema(
                recommended_leagues=[],
                recommended_bets=legs_bets,
                recommended_parlays=[],
                live_check=None,
                post_match_review=None,
                audit=AuditTrail(sources=["GrandBlindBacktest"], raw_refs=[], degradations=degradations, conflicts=[], explain=[]),
            )

            built = self.ticket_builder.build_validated_ticket(schema=schema, stake=float(stake), date=str(date))
            if built.get("ok") is not True:
                tickets_rejected += 1
                if len(errors) < 50:
                    errors.append({"type": "ticket_rejected", "date": str(date), "error": built.get("error"), "degradations": degradations})
                bucket = []
                current_date = None
                return

            ticket = built.get("ticket") if isinstance(built.get("ticket"), dict) else None
            if ticket is None:
                tickets_rejected += 1
                if len(errors) < 50:
                    errors.append({"type": "ticket_missing", "date": str(date)})
                bucket = []
                current_date = None
                return

            tickets_validated += 1

            pnl = 0.0
            settlement: Dict[str, Any] = {}
            if lt == "ZUCAI":
                all_ok = True
                legs = ticket.get("legs") or []
                per_leg: List[Dict[str, Any]] = []
                for leg in legs:
                    mid = str(leg.get("match_id") or "")
                    m = match_map.get(mid)
                    ft = str((m or {}).get("result") or "")
                    det = self.settlement_engine.determine_all_play_types_results(ft, status="FINISHED")
                    if str(det.get("status") or "").upper() == "VOID":
                        all_ok = False
                        per_leg.append({"match_id": mid, "status": "VOID", "ft_score": ft})
                        continue
                    official = str(det.get("WDL") or det.get("official_result") or "")
                    picked = str(leg.get("selection") or "")
                    hit = picked == official
                    if not hit:
                        all_ok = False
                    per_leg.append({"match_id": mid, "status": "SETTLED", "ft_score": ft, "official_result": official, "picked": picked, "hit": hit})
                payout = float(stake) if all_ok else 0.0
                pnl = payout - float(stake)
                settlement = {"status": "WON" if all_ok else "LOST", "payout": payout, "per_leg": per_leg}
            else:
                res_map = build_results_for_ticket(ticket, match_map)
                pnl, settlement = settle_ticket_fixed_odds(ticket, res_map)

            pnl_total += float(pnl)
            payout = float(settlement.get("payout") or 0.0)
            payout_total += payout
            if float(pnl) > 0:
                tickets_won += 1

            if len(examples) < int(keep_examples):
                examples.append(
                    {
                        "date": str(date),
                        "ticket": ticket,
                        "validation": built.get("validation"),
                        "settlement": settlement,
                        "pnl": float(pnl),
                        "degradations": degradations,
                    }
                )

            bucket = []
            current_date = None

        it = iter_dataset_matches(
            filepath=path,
            max_matches=max_matches,
            seed=seed,
            mode=dataset_mode,
            sample_strategy=sample_strategy,
        )

        if lt != "ZUCAI" and pt not in {"WDL", "MIXED_PARLAY", "SFGG", "GOALS", "CS", "HTFT", "UP_DOWN_ODD_EVEN"}:
            pt = "WDL"

        for m in it:
            if not isinstance(m, dict):
                continue
            update_hist_agg(m)
            d = str(m.get("date") or "")
            if batch_size == 1:
                current_date = d
                bucket = [m]
                flush_bucket()
                continue
            if current_date is None:
                current_date = d
            if d != current_date or len(bucket) >= batch_size:
                flush_bucket()
                current_date = d
            bucket.append(m)
            if len(bucket) >= batch_size:
                flush_bucket()

        flush_bucket()

        roi = (pnl_total / stake_total) if stake_total > 0 else 0.0
        win_rate = (tickets_won / tickets_validated) if tickets_validated > 0 else 0.0

        league_rows: List[Dict[str, Any]] = []
        for lg, rec in league_stats.items():
            n = int(rec.get("n") or 0)
            if n <= 0:
                continue
            home = int(rec.get("home") or 0)
            draw = int(rec.get("draw") or 0)
            away = int(rec.get("away") or 0)
            goals_sum = float(rec.get("goals_sum") or 0.0)
            league_rows.append(
                {
                    "league": lg,
                    "n": n,
                    "home_win_rate": round(home / n, 4),
                    "draw_rate": round(draw / n, 4),
                    "away_win_rate": round(away / n, 4),
                    "avg_goals": round(goals_sum / n, 4) if n > 0 else 0.0,
                }
            )
        league_rows.sort(key=lambda r: int(r.get("n") or 0), reverse=True)

        report: Dict[str, Any] = {
            "run_id": run_id,
            "ts_utc": datetime.now(timezone.utc).isoformat(),
            "dataset_path": path,
            "dataset_mode": dataset_mode,
            "sample_strategy": sample_strategy,
            "seed": int(seed),
            "lottery_type": lt,
            "play_type": pt,
            "summary": {
                "tickets_total": tickets_total,
                "tickets_validated": tickets_validated,
                "tickets_rejected": tickets_rejected,
                "stake_total": round(stake_total, 2),
                "payout_total": round(payout_total, 2),
                "pnl_total": round(pnl_total, 2),
                "roi": round(roi, 6),
                "win_rate": round(win_rate, 6),
            },
            "historical_impact_aggregates": {
                "matches_total": matches_total,
                "date_range": f"{date_min or 'N/A'}..{date_max or 'N/A'}",
                "by_league": league_rows[:50],
            },
            "examples": examples,
            "errors": errors,
        }

        report_path = os.path.join(out_dir, f"{run_id.replace('::', '_')}.json")
        md_path = os.path.join(out_dir, f"{run_id.replace('::', '_')}.md")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(_render_backtest_markdown(report))

        report["report_path"] = report_path
        report["report_md_path"] = md_path
        return report
