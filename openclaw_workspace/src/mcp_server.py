"""
OpenClaw 2026.4 MCP Server Adapter
This script exposes our quant tools via stdio MCP bridge so OpenClaw can discover and call them natively.
"""
import os
import sys
import json
import contextlib
from pathlib import Path
from typing import Dict, Any

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PKG_DIR = WORKSPACE_ROOT / "runtime" / "football_analyzer"
if str(RUNTIME_PKG_DIR) not in sys.path:
    sys.path.insert(0, str(RUNTIME_PKG_DIR))

os.environ.setdefault("OPENCLAW_FOOTBALL_DATA_DIR", str(WORKSPACE_ROOT / "data"))

from smart_money import detect_sharp_money
from bayesian_xg import calculate_bayesian_xg
from quant_math import calculate_poisson_probabilities, calculate_kelly_and_ev
from asian_handicap_analyzer import AsianHandicapAnalyzer
from parlay_filter_matrix import ParlayFilterMatrix

from tools.tool_registry_v2 import get_mcp_tools, execute_tool
import runtime_bridge
import asyncio

from tools.smart_money_tracker import SmartMoneyTracker
from tools.player_xg_adjuster import PlayerXgAdjuster
from tools.monte_carlo_simulator import TimeSliceMonteCarlo
from tools.environment_analyzer import EnvironmentAnalyzer
from tools.memory_manager import MemoryManager
from tools.multisource_fetcher import MultiSourceFetcher
from tools.pre_match_sentinel import PreMatchSentinel
from tools.live_match_monitor import LiveMatchMonitor
from tools.settlement_engine import SettlementEngine
from tools.parlay_rules_engine import ParlayRulesEngine
from tools.anomaly_detector import AnomalyDetector
from tools.daily_reporter import DailyReporter
from tools.lottery_router import LotteryRouter


def handle_request_sync(req: Dict[str, Any]) -> Dict[str, Any]:
    # Use a basic event loop to run the async execute_tool
    return asyncio.run(handle_request(req))

async def handle_request(req: Dict[str, Any]) -> Dict[str, Any]:
    method = req.get("method")
    if method == "list_tools":
        # get_mcp_tools returns mcp.types.Tool objects, we need to serialize them for this custom JSON-RPC
        # Wait, the previous implementation returned a simple dict. 
        # Let's keep it compatible with OpenClaw's custom JSON-RPC bridge for now.
        tools_list = []
        for t in get_mcp_tools():
            # t is mcp.types.Tool
            tools_list.append({
                "name": t.name,
                "description": t.description,
                "parameters": t.inputSchema
            })
            
        tools_list.extend([
            {
                "name": "detect_smart_money",
                "description": "Detect anomalous drops in odds indicating smart money.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "odds_history": {"type": "array", "description": "List of odds dicts with home, draw, away"}
                    },
                    "required": ["odds_history"]
                }
            },
            {
                "name": "calculate_adjusted_xg",
                "description": "Adjust base xG based on player injuries and importance.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "base_xg": {"type": "number"},
                        "injuries": {"type": "array"}
                    },
                    "required": ["base_xg", "injuries"]
                }
            },
            {
                "name": "run_monte_carlo",
                "description": "Run 90-min time-slice Monte Carlo simulation for half/full time probabilities.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "home_xg": {"type": "number"},
                        "away_xg": {"type": "number"}
                    },
                    "required": ["home_xg", "away_xg"]
                }
            },
            {
                "name": "query_historical_odds",
                "description": "Query ChromaDB for historical match outcomes with similar odds.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "league": {"type": "string"},
                        "home_odds": {"type": "number"},
                        "draw_odds": {"type": "number"},
                        "away_odds": {"type": "number"}
                    },
                    "required": ["league", "home_odds", "draw_odds", "away_odds"]
                }
            },
            {
                "name": "check_lineups_t30",
                "description": "Proactively check T-30 mins lineups to see if key players are missing, returning EV adjustment and actions.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "match_id": {"type": "string"},
                        "key_players": {"type": "array", "items": {"type": "string"}},
                        "actual_starting_xi": {"type": "array", "items": {"type": "string"}},
                        "original_ev": {"type": "number"}
                    },
                    "required": ["match_id", "key_players", "actual_starting_xi", "original_ev"]
                }
            },
            {
                "name": "evaluate_hedge_opportunity",
                "description": "Calculate if hedging an active live bet guarantees a profit.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "match_id": {"type": "string"},
                        "original_stake": {"type": "number"},
                        "original_odds": {"type": "number"},
                        "current_score": {"type": "string"},
                        "live_odds_against": {"type": "number"},
                        "current_minute": {"type": "integer"}
                    },
                    "required": ["match_id", "original_stake", "original_odds", "current_score", "live_odds_against", "current_minute"]
                }
            },
            {
                 "name": "calculate_fuzzy_banker_combinations",
                 "description": "Calculate combinations for Beidan fuzzy bankers and Jingcai banker-tuo parlay tickets.",
                 "parameters": {
                     "type": "object",
                     "properties": {
                         "banker_selections": {"type": "array", "items": {"type": "integer"}},
                         "tuo_selections": {"type": "array", "items": {"type": "integer"}},
                         "parlay_size": {"type": "integer"},
                         "min_bankers": {"type": "integer"}
                     },
                     "required": ["banker_selections", "tuo_selections", "parlay_size"]
                 }
             },
             {
                 "name": "calculate_chuantong_combinations",
                 "description": "Calculate combinations for Traditional Football Lottery (14-match, Renjiu, etc.).",
                 "parameters": {
                     "type": "object",
                     "properties": {
                         "match_selections": {"type": "array", "items": {"type": "integer"}},
                         "play_type": {"type": "string", "enum": ["14_match", "renjiu", "6_htft", "4_goals"]}
                     },
                     "required": ["match_selections", "play_type"]
                 }
             },
             {
                 "name": "settle_official_match",
                "description": "Settle a match according to official Jingcai/Beidan 90-min rules and cancellations.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ft_score": {"type": "string"},
                        "aet_score": {"type": "string"},
                        "status": {"type": "string"}
                    },
                    "required": ["ft_score", "status"]
                }
            },
            {
                "name": "detect_bookmaker_anomaly",
                "description": "Detect classic bookmaker traps based on odds and odds movement.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "home_odds": {"type": "number"},
                        "draw_odds": {"type": "number"},
                        "away_odds": {"type": "number"},
                        "odds_drop_ratio": {"type": "number"}
                    },
                    "required": ["home_odds", "draw_odds", "away_odds"]
                }
            },
            {
                "name": "generate_daily_report",
                "description": "Generate a Markdown daily report summarizing PnL and evolution reasons.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date_str": {"type": "string"},
                        "pnl": {"type": "number"},
                        "evolution_reason": {"type": "string"}
                    },
                    "required": ["date_str", "pnl", "evolution_reason"]
                }
            }
        ])
        
        return {"tools": tools_list}
        
    elif method == "call_tool":
        params = req.get("params", {})
        name = params.get("name")
        args = params.get("arguments", {})
        
        try:
            with contextlib.redirect_stdout(sys.stderr):
                if name == "detect_smart_money":
                    tracker = SmartMoneyTracker()
                    result = tracker.detect_anomaly(args.get("odds_history", []))
                    res = [{"type": "text", "text": json.dumps(result)}]
                elif name == "calculate_adjusted_xg":
                    adjuster = PlayerXgAdjuster()
                    result = adjuster.calculate_adjusted_xg(args.get("base_xg", 1.0), args.get("injuries", []))
                    res = [{"type": "text", "text": str(result)}]
                elif name == "run_monte_carlo":
                    simulator = TimeSliceMonteCarlo()
                    result = simulator.simulate_match(args.get("home_xg", 1.0), args.get("away_xg", 1.0))
                    res = [{"type": "text", "text": json.dumps(result)}]
                elif name == "query_historical_odds":
                    manager = MemoryManager()
                    result = manager.query_historical_odds(
                        args.get("league", ""), 
                        args.get("home_odds", 2.0),
                        args.get("draw_odds", 3.0),
                        args.get("away_odds", 3.0)
                    )
                    res = [{"type": "text", "text": json.dumps(result)}]
                elif name == "check_lineups_t30":
                    sentinel = PreMatchSentinel()
                    sentinel.register_match(args["match_id"], args["key_players"], args["original_ev"])
                    result = sentinel.check_lineups_t30(args["match_id"], args["actual_starting_xi"])
                    res = [{"type": "text", "text": json.dumps(result)}]
                elif name == "evaluate_hedge_opportunity":
                    monitor = LiveMatchMonitor()
                    monitor.register_live_bet(args["match_id"], "Home Win", args["original_stake"], args["original_odds"])
                    result = monitor.evaluate_hedge_opportunity(args["match_id"], args["current_score"], args["live_odds_against"], args["current_minute"])
                    res = [{"type": "text", "text": json.dumps(result)}]
                elif name == "calculate_fuzzy_banker_combinations":
                    engine = ParlayRulesEngine()
                    result = engine.calculate_fuzzy_banker_combinations(
                        args["banker_selections"], 
                        args["tuo_selections"], 
                        args["parlay_size"], 
                        args.get("min_bankers")
                    )
                    res = [{"type": "text", "text": str(result)}]
                elif name == "calculate_chuantong_combinations":
                    engine = ParlayRulesEngine()
                    result = engine.calculate_chuantong_combinations(
                        args["match_selections"],
                        args.get("play_type", "renjiu")
                    )
                    res = [{"type": "text", "text": str(result)}]
                elif name == "settle_official_match":
                    engine = SettlementEngine()
                    result = engine.determine_match_result(args.get("ft_score", ""), args.get("aet_score"), args.get("status", "FINISHED"))
                    res = [{"type": "text", "text": json.dumps(result)}]
                elif name == "detect_bookmaker_anomaly":
                    detector = AnomalyDetector()
                    result = detector.detect_anomaly(
                        home_odds=args.get("home_odds", 2.0),
                        draw_odds=args.get("draw_odds", 3.0),
                        away_odds=args.get("away_odds", 3.0),
                        odds_drop_ratio=args.get("odds_drop_ratio", 0.0),
                    )
                    res = [{"type": "text", "text": json.dumps(result)}]
                elif name == "generate_daily_report":
                    reporter = DailyReporter()
                    result = reporter.generate_report(
                        date_str=args.get("date_str", ""),
                        pnl=args.get("pnl", 0.0),
                        evolution_reason=args.get("evolution_reason", ""),
                    )
                    res = [{"type": "text", "text": result}]
                elif name == "validate_ticket_physics":
                    router = LotteryRouter()
                    try:
                        result = router.route_and_validate(args["lottery_type"], args["ticket_data"])
                        res = [{"type": "text", "text": json.dumps(result)}]
                    except ValueError as e:
                        # Return validation failure as a normal response text, not an MCP protocol error, 
                        # so the LLM can see the rejection reason and correct itself.
                        res = [{"type": "text", "text": json.dumps({"isError": True, "error": str(e)})}]
                else:
                    res = await execute_tool(name, args)
            return {"result": res}
        except Exception as e:
            return {"error": str(e)}

    elif method == "run_workflow":
        params = req.get("params", {})
        name = params.get("name")
        args = params.get("arguments", {})
        try:
            workflow = getattr(runtime_bridge, name, None)
            if workflow is None:
                return {"error": f"Unknown workflow: {name}"}
            if asyncio.iscoroutinefunction(workflow):
                with contextlib.redirect_stdout(sys.stderr):
                    return {"result": await workflow(**args)}
            with contextlib.redirect_stdout(sys.stderr):
                return {"result": workflow(**args)}
        except Exception as e:
            return {"error": str(e)}

    elif method == "daemon_start":
        params = req.get("params", {})
        args = params.get("arguments", {})
        try:
            with contextlib.redirect_stdout(sys.stderr):
                return {"result": runtime_bridge.daemon_start(**args)}
        except Exception as e:
            return {"error": str(e)}

    elif method == "daemon_stop":
        try:
            with contextlib.redirect_stdout(sys.stderr):
                return {"result": runtime_bridge.daemon_stop()}
        except Exception as e:
            return {"error": str(e)}

    elif method == "daemon_status":
        try:
            with contextlib.redirect_stdout(sys.stderr):
                return {"result": runtime_bridge.daemon_status()}
        except Exception as e:
            return {"error": str(e)}
            
    return {"error": "Method not supported"}

def main():
    # Simple JSON-RPC over stdio for OpenClaw MCP Bridge
    for line in sys.stdin:
        try:
            req = json.loads(line)
            res = handle_request_sync(req)
            sys.stdout.write(json.dumps({"id": req.get("id"), **res}) + "\n")
            sys.stdout.flush()
        except Exception as e:
            sys.stderr.write(f"Error processing line: {e}\n")

if __name__ == "__main__":
    main()
