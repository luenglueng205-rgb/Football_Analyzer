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
        return {"tools": tools_list}
        
    elif method == "call_tool":
        params = req.get("params", {})
        name = params.get("name")
        args = params.get("arguments", {})
        
        try:
            with contextlib.redirect_stdout(sys.stderr):
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
