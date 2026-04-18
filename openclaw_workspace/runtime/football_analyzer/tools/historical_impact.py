from __future__ import annotations

from typing import Any, Dict, Optional

from tools.paths import datasets_dir


def build_historical_impact(
    *,
    lottery_type: str,
    league_code: str,
    odds: Optional[Dict[str, float]],
    analysis: Dict[str, Any],
    similar_odds_result: Optional[Dict[str, Any]] = None,
    data_source: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "enabled": True,
        "lottery_type": str(lottery_type).upper(),
        "league_code": str(league_code or "UNK"),
        "league_stats": None,
        "market_calibration": {
            "enabled": False,
            "method": "league_distribution_blend",
            "historical_weight": None,
            "calibrated": False,
        },
        "similar_odds": {"enabled": False, "tolerance": 0.10, "matched_count": 0, "sample": []},
        "data_source": data_source
        or {
            "raw_json_path": datasets_dir("raw", "COMPLETE_FOOTBALL_DATA_FINAL_UPDATED.json"),
            "chroma_db_path": None,
        },
        "degradations": [],
    }

    try:
        cal = analysis.get("calibration_info") if isinstance(analysis.get("calibration_info"), dict) else {}
        hist_dist = cal.get("hist_distribution") if isinstance(cal.get("hist_distribution"), dict) else {}
        ls = analysis.get("league_stats") if isinstance(analysis.get("league_stats"), dict) else {}
        sample_size = cal.get("sample_size") if isinstance(cal.get("sample_size"), int) else ls.get("sample_size")
        league_stats_out = {
            "sample_size": int(sample_size) if isinstance(sample_size, (int, float)) else 0,
            "home_win_rate": float(hist_dist.get("home")) if isinstance(hist_dist.get("home"), (int, float)) else None,
            "draw_rate": float(ls.get("draw_rate"))
            if isinstance(ls.get("draw_rate"), (int, float))
            else (float(hist_dist.get("draw")) if isinstance(hist_dist.get("draw"), (int, float)) else None),
            "away_win_rate": float(hist_dist.get("away")) if isinstance(hist_dist.get("away"), (int, float)) else None,
            "avg_total_goals": float(ls.get("avg_goals")) if isinstance(ls.get("avg_goals"), (int, float)) else None,
            "over_2_5_rate": float(ls.get("over_2_5_rate")) if isinstance(ls.get("over_2_5_rate"), (int, float)) else None,
            "btts_yes_rate": float(ls.get("btts_rate")) if isinstance(ls.get("btts_rate"), (int, float)) else None,
        }
        out["league_stats"] = league_stats_out
        calibrated = bool(cal.get("calibrated")) if isinstance(cal, dict) else False
        out["market_calibration"] = {
            "enabled": bool(cal),
            "method": "league_distribution_blend",
            "historical_weight": cal.get("historical_weight"),
            "calibrated": calibrated,
        }
        if isinstance(league_stats_out.get("sample_size"), int) and league_stats_out["sample_size"] <= 0:
            out["degradations"].append("league_stats_unavailable")
        if not calibrated and isinstance(cal.get("reason"), str) and cal.get("reason"):
            out["degradations"].append(f"market_calibration:{cal.get('reason')}")
    except Exception:
        out["degradations"].append("historical_impact_parse_error")

    if out.get("lottery_type") == "ZUCAI" and odds is None:
        out["degradations"].append("similar_odds_not_applicable:zucai_no_fixed_odds")
        return out

    try:
        if isinstance(similar_odds_result, dict) and similar_odds_result.get("_exception") is True:
            out["degradations"].append("similar_odds_error")
        elif isinstance(similar_odds_result, dict):
            data = similar_odds_result.get("data")
            if similar_odds_result.get("ok") is True and isinstance(data, list) and data:
                sample = []
                for item in data[:3]:
                    meta = item.get("metadata") if isinstance(item, dict) else None
                    meta = meta if isinstance(meta, dict) else {}
                    sample.append(
                        {
                            "match_id": meta.get("match_id") or meta.get("id") or None,
                            "date": meta.get("date"),
                            "result": meta.get("result"),
                            "home_team": meta.get("home_team"),
                            "away_team": meta.get("away_team"),
                            "home_odds": meta.get("home_odds"),
                            "draw_odds": meta.get("draw_odds"),
                            "away_odds": meta.get("away_odds"),
                        }
                    )
                out["similar_odds"] = {
                    "enabled": True,
                    "tolerance": float(out["similar_odds"].get("tolerance") or 0.10),
                    "matched_count": len(data),
                    "sample": sample,
                }
            else:
                out["degradations"].append("similar_odds_unavailable")
    except Exception:
        out["degradations"].append("similar_odds_error")

    _ = odds
    return out


def to_explain_item(historical_impact: Dict[str, Any]) -> Dict[str, Any]:
    sim = historical_impact.get("similar_odds") if isinstance(historical_impact.get("similar_odds"), dict) else {}
    return {
        "type": "historical_impact",
        "summary": {
            "enabled": historical_impact.get("enabled"),
            "lottery_type": historical_impact.get("lottery_type"),
            "league_code": historical_impact.get("league_code"),
            "league_stats": historical_impact.get("league_stats"),
            "market_calibration": historical_impact.get("market_calibration"),
            "similar_odds": {k: v for k, v in sim.items() if k != "sample"},
            "data_source": historical_impact.get("data_source"),
            "degradations": historical_impact.get("degradations"),
        },
        "samples": sim.get("sample", []),
    }

