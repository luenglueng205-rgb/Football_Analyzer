"""
OpenClaw 2026.4 MCP Server Adapter
This script exposes our quant tools via stdio MCP bridge so OpenClaw can discover and call them natively.
"""
import sys
import json
from typing import Dict, Any

from smart_money import detect_sharp_money
from bayesian_xg import calculate_bayesian_xg
from quant_math import calculate_poisson_probabilities, calculate_kelly_and_ev
from asian_handicap_analyzer import AsianHandicapAnalyzer
from parlay_filter_matrix import ParlayFilterMatrix

_ah_analyzer = AsianHandicapAnalyzer()
_parlay_matrix = ParlayFilterMatrix()

TOOLS = {
    "detect_smart_money": {
        "description": "对比初盘和即时盘，剥离庄家抽水，检测聪明资金的砸盘方向",
        "parameters": {
            "type": "object",
            "properties": {
                "opening_odds": {"type": "object"},
                "live_odds": {"type": "object"}
            },
            "required": ["opening_odds", "live_odds"]
        }
    },
    "calculate_bayesian_xg": {
        "description": "计算贝叶斯平滑后的 xG 并根据伤停衰减",
        "parameters": {
            "type": "object",
            "properties": {
                "team_stats": {"type": "object"},
                "league_avg": {"type": "number"},
                "injuries": {"type": "array"}
            },
            "required": ["team_stats", "league_avg"]
        }
    },
    "calculate_poisson_probabilities": {
        "description": "计算泊松分布下的胜平负概率",
        "parameters": {
            "type": "object",
            "properties": {
                "home_xg": {"type": "number"},
                "away_xg": {"type": "number"}
            },
            "required": ["home_xg", "away_xg"]
        }
    },
    "calculate_kelly_and_ev": {
        "description": "计算期望值(EV)与凯利仓位，自动处理北单机制",
        "parameters": {
            "type": "object",
            "properties": {
                "odds": {"type": "number"},
                "probability": {"type": "number"},
                "lottery_type": {"type": "string"}
            },
            "required": ["odds", "probability"]
        }
    },
    "analyze_asian_handicap_divergence": {
        "description": "分析欧亚转换偏差。如果实际开出的亚盘比理论盘深或浅，系统将识别出这是诱盘还是真实看好。",
        "parameters": {
            "type": "object",
            "properties": {
                "euro_home_odds": {"type": "number"},
                "actual_asian_handicap": {"type": "number"},
                "home_water": {"type": "number"}
            },
            "required": ["euro_home_odds", "actual_asian_handicap", "home_water"]
        }
    },
    "analyze_water_drop": {
        "description": "计算从初盘到临场的水位下降幅度，判断庄家是真实降赔防范，还是高水阻筹。",
        "parameters": {
            "type": "object",
            "properties": {
                "opening_water": {"type": "number"},
                "live_water": {"type": "number"}
            },
            "required": ["opening_water", "live_water"]
        }
    },
    "calculate_parlay": {
        "description": "计算多场比赛串关的容错组合与资金分配。支持的 parlay_type: '2x1', '3x1', '3x4'。",
        "parameters": {
            "type": "object",
            "properties": {
                "matches": {"type": "array"},
                "parlay_type": {"type": "string"},
                "total_stake": {"type": "number"}
            },
            "required": ["matches", "parlay_type", "total_stake"]
        }
    }
}

def handle_request(req: Dict[str, Any]) -> Dict[str, Any]:
    method = req.get("method")
    if method == "list_tools":
        return {"tools": [{"name": k, **v} for k, v in TOOLS.items()]}
        
    elif method == "call_tool":
        params = req.get("params", {})
        name = params.get("name")
        args = params.get("arguments", {})
        
        try:
            if name == "detect_smart_money":
                res = detect_sharp_money(**args)
            elif name == "calculate_bayesian_xg":
                res = calculate_bayesian_xg(**args)
            elif name == "calculate_poisson_probabilities":
                res = calculate_poisson_probabilities(**args)
            elif name == "calculate_kelly_and_ev":
                res = calculate_kelly_and_ev(**args)
            elif name == "analyze_asian_handicap_divergence":
                res = _ah_analyzer.analyze_divergence(**args)
            elif name == "analyze_water_drop":
                res = _ah_analyzer.analyze_water_drop(**args)
            elif name == "calculate_parlay":
                res = _parlay_matrix.calculate_parlay(**args)
            else:
                return {"error": "Tool not found"}
            return {"result": res}
        except Exception as e:
            return {"error": str(e)}
            
    return {"error": "Method not supported"}

def main():
    # Simple JSON-RPC over stdio for OpenClaw MCP Bridge
    for line in sys.stdin:
        try:
            req = json.loads(line)
            res = handle_request(req)
            sys.stdout.write(json.dumps({"id": req.get("id"), **res}) + "\n")
            sys.stdout.flush()
        except Exception as e:
            sys.stderr.write(f"Error processing line: {e}\n")

if __name__ == "__main__":
    main()
