# 2026-04-14 Sync OpenClaw Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Synchronize the new pure-math quantitative tools (Asian Handicap, Parlay Filter Matrix) from the Standalone version into the tiny 11KB OpenClaw Native Workspace adapter.

**Architecture:** We will copy the pure-math python scripts into the `openclaw_workspace/src` directory, then expose them through the `openclaw_workspace/src/mcp_server.py` using standard Stdio MCP protocol. We will NOT copy the daemons or ledgers, as OpenClaw handles scheduling and state natively.

**Tech Stack:** Python 3, `mcp`.

---

### Task 1: Copy Pure-Math Tools to OpenClaw Workspace

**Files:**
- Modify: `openclaw_workspace/src/asian_handicap_analyzer.py` (Create from Standalone)
- Modify: `openclaw_workspace/src/parlay_filter_matrix.py` (Create from Standalone)

- [ ] **Step 1: Copy Asian Handicap Analyzer**
Run: `cp tools/asian_handicap_analyzer.py openclaw_workspace/src/`
Expected: File is copied successfully.

- [ ] **Step 2: Copy Parlay Filter Matrix**
Run: `cp tools/parlay_filter_matrix.py openclaw_workspace/src/`
Expected: File is copied successfully.

- [ ] **Step 3: Commit**
Run: `git add openclaw_workspace/src/asian_handicap_analyzer.py openclaw_workspace/src/parlay_filter_matrix.py && git commit -m "feat: sync pure math tools to openclaw workspace"`

---

### Task 2: Expose Tools in OpenClaw MCP Server

**Files:**
- Modify: `openclaw_workspace/src/mcp_server.py`

- [ ] **Step 1: Write the updated MCP Server code**

Modify `openclaw_workspace/src/mcp_server.py` to include the new tools. Replace its contents with:

```python
from typing import Any
import mcp.types as types
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import sys

from bayesian_xg import BayesianXGModel
from quant_math import BivariatePoisson
from smart_money import SmartMoneyTracker
from asian_handicap_analyzer import AsianHandicapAnalyzer
from parlay_filter_matrix import ParlayFilterMatrix

server = Server("football_quant")

xg_model = BayesianXGModel()
poisson_model = BivariatePoisson()
smart_money = SmartMoneyTracker()
ah_analyzer = AsianHandicapAnalyzer()
parlay_matrix = ParlayFilterMatrix()

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="calculate_bivariate_poisson",
            description="基于 xG 计算胜平负概率",
            inputSchema={
                "type": "object",
                "properties": {
                    "home_xg": {"type": "number"},
                    "away_xg": {"type": "number"},
                    "correlation": {"type": "number", "default": 0.2}
                },
                "required": ["home_xg", "away_xg"]
            }
        ),
        types.Tool(
            name="detect_smart_money",
            description="对比初盘和即时盘，剥离抽水，检测聪明资金的砸盘方向",
            inputSchema={
                "type": "object",
                "properties": {
                    "opening_odds": {"type": "object"},
                    "live_odds": {"type": "object"}
                },
                "required": ["opening_odds", "live_odds"]
            }
        ),
        types.Tool(
            name="analyze_asian_handicap_divergence",
            description="分析欧亚转换偏差",
            inputSchema={
                "type": "object",
                "properties": {
                    "euro_home_odds": {"type": "number"},
                    "actual_asian_handicap": {"type": "number"},
                    "home_water": {"type": "number"}
                },
                "required": ["euro_home_odds", "actual_asian_handicap", "home_water"]
            }
        ),
        types.Tool(
            name="calculate_parlay",
            description="计算多场比赛串关的容错组合与资金分配",
            inputSchema={
                "type": "object",
                "properties": {
                    "matches": {"type": "array"},
                    "parlay_type": {"type": "string"},
                    "total_stake": {"type": "number"}
                },
                "required": ["matches", "parlay_type", "total_stake"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent]:
    if not arguments:
        arguments = {}

    try:
        if name == "calculate_bivariate_poisson":
            result = poisson_model.calculate_match_odds(
                arguments["home_xg"], 
                arguments["away_xg"], 
                arguments.get("correlation", 0.2)
            )
            return [types.TextContent(type="text", text=str(result))]
            
        elif name == "detect_smart_money":
            result = smart_money.detect_sharp_money(
                arguments["opening_odds"], 
                arguments["live_odds"]
            )
            return [types.TextContent(type="text", text=str(result))]
            
        elif name == "analyze_asian_handicap_divergence":
            result = ah_analyzer.analyze_divergence(
                arguments["euro_home_odds"],
                arguments["actual_asian_handicap"],
                arguments["home_water"]
            )
            return [types.TextContent(type="text", text=str(result))]
            
        elif name == "calculate_parlay":
            result = parlay_matrix.calculate_parlay(
                arguments["matches"],
                arguments["parlay_type"],
                arguments["total_stake"]
            )
            return [types.TextContent(type="text", text=str(result))]
            
        else:
            raise ValueError(f"Unknown tool: {name}")
            
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]

async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="football_quant",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

- [ ] **Step 2: Commit**
Run: `git add openclaw_workspace/src/mcp_server.py && git commit -m "feat: expose new math tools via MCP in OpenClaw workspace"`
