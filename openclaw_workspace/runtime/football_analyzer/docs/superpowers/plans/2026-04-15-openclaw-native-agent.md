# OpenClaw 架构重构与能力同步 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将独立版 (Standalone) 中最新开发的四大领域精通数学模型、长效记忆中枢及视觉能力同步至 OpenClaw 适配版。同时重构 OpenClaw 配置，将系统升格为 Native Agent 并在 MCP Server 中暴露底层核武器为标准 Tools。

**Architecture:** 
1. **代码物理同步**：使用 `cp` 将 `standalone_workspace` 中更新的文件覆盖到 `openclaw_workspace/runtime/football_analyzer` 中。
2. **MCP 工具暴露**：重构 `openclaw_workspace/src/mcp_server.py`，注册 `detect_smart_money`, `calculate_bayesian_xg`, `query_historical_odds` 等新工具。
3. **主权宣告**：重写 `openclaw_workspace/openclaw.json`，设置 `"workspace_type": "native_agent"` 并定义最高级别的 `Digital Betting Syndicate` 主导角色。

**Tech Stack:** Python 3.10+, OpenClaw (JSON-RPC), ChromaDB, Scipy

---

### Task 1: 物理代码同步 (Code Synchronization)

**Files:**
- Command Line Operations Only

- [ ] **Step 1: 同步 `tools` 和 `skills` 目录的新文件**

将独立版中新增和修改的核心模型文件拷贝至 OpenClaw 的运行时目录中。

```bash
# 拷贝四大领域精通模型
cp standalone_workspace/tools/player_xg_adjuster.py openclaw_workspace/runtime/football_analyzer/tools/
cp standalone_workspace/tools/monte_carlo_simulator.py openclaw_workspace/runtime/football_analyzer/tools/
cp standalone_workspace/tools/smart_money_tracker.py openclaw_workspace/runtime/football_analyzer/tools/
cp standalone_workspace/tools/environment_analyzer.py openclaw_workspace/runtime/football_analyzer/tools/

# 覆盖更新过的核心工具 (带有天气API、精确Metadata过滤等)
cp standalone_workspace/tools/multisource_fetcher.py openclaw_workspace/runtime/football_analyzer/tools/
cp standalone_workspace/tools/memory_manager.py openclaw_workspace/runtime/football_analyzer/tools/

# 覆盖 ScoutAgent
cp standalone_workspace/agents/async_scout.py openclaw_workspace/runtime/football_analyzer/agents/
```

- [ ] **Step 2: Commit**

```bash
git add openclaw_workspace/runtime/football_analyzer/
git commit -m "chore: sync domain mastery models and updated core tools to openclaw runtime"
```

### Task 2: 宣告 OpenClaw 主导权 (Manifest Configuration)

**Files:**
- Create/Modify: `openclaw_workspace/openclaw.json`

- [ ] **Step 1: 编写 `openclaw.json` 配置文件**

```json
{
  "name": "digital-betting-syndicate",
  "version": "2.0.0",
  "description": "An AI-Native Football Analysis & Betting Syndicate OS.",
  "workspace_type": "native_agent",
  "sandbox": {
    "mode": "agent",
    "allow_network": true
  },
  "agents": {
    "main": {
      "role": "Digital Betting Syndicate Orchestrator",
      "description": "最高指挥官。负责统筹赛前情报、调动底层数学模型计算预期进球，并综合基本面与风控发出最终投注指令。",
      "system_prompt_file": "runtime/football_analyzer/docs/LOTTERY_RULES.md",
      "tools": [
        "local_mcp.detect_smart_money",
        "local_mcp.calculate_adjusted_xg",
        "local_mcp.run_monte_carlo",
        "local_mcp.query_historical_odds",
        "local_mcp.fetch_weather_impact"
      ]
    }
  },
  "mcpServers": {
    "local_mcp": {
      "command": "python3",
      "args": ["src/mcp_server.py"]
    }
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add openclaw_workspace/openclaw.json
git commit -m "feat: upgrade openclaw workspace to native_agent mode and declare primary orchestrator"
```

### Task 3: 重构 MCP Server 暴露底层“核武器” (Tool Exposing)

**Files:**
- Modify: `openclaw_workspace/src/mcp_server.py`

- [ ] **Step 1: 导入新模型并注册新的 MCP Tools**

在 `mcp_server.py` 的顶部导入新的模型，并在工具列表和 `call_tool` 分发器中注册它们。

```python
# 在顶部导入
from runtime.football_analyzer.tools.smart_money_tracker import SmartMoneyTracker
from runtime.football_analyzer.tools.player_xg_adjuster import PlayerXgAdjuster
from runtime.football_analyzer.tools.monte_carlo_simulator import TimeSliceMonteCarlo
from runtime.football_analyzer.tools.environment_analyzer import EnvironmentAnalyzer
from runtime.football_analyzer.tools.memory_manager import MemoryManager
from runtime.football_analyzer.tools.multisource_fetcher import MultiSourceFetcher

# 在 handle_list_tools() 返回的列表中追加:
            {
                "name": "detect_smart_money",
                "description": "Detect anomalous drops in odds indicating smart money.",
                "inputSchema": {
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
                "inputSchema": {
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
                "inputSchema": {
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
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "league": {"type": "string"},
                        "home_odds": {"type": "number"},
                        "draw_odds": {"type": "number"},
                        "away_odds": {"type": "number"}
                    },
                    "required": ["league", "home_odds", "draw_odds", "away_odds"]
                }
            }

# 在 handle_call_tool() 的调度逻辑中追加:
    if name == "detect_smart_money":
        tracker = SmartMoneyTracker()
        result = tracker.detect_anomaly(arguments.get("odds_history", []))
        return {"content": [{"type": "text", "text": json.dumps(result)}]}
        
    elif name == "calculate_adjusted_xg":
        adjuster = PlayerXgAdjuster()
        result = adjuster.calculate_adjusted_xg(arguments.get("base_xg", 1.0), arguments.get("injuries", []))
        return {"content": [{"type": "text", "text": str(result)}]}
        
    elif name == "run_monte_carlo":
        simulator = TimeSliceMonteCarlo()
        result = simulator.simulate_match(arguments.get("home_xg", 1.0), arguments.get("away_xg", 1.0))
        return {"content": [{"type": "text", "text": json.dumps(result)}]}
        
    elif name == "query_historical_odds":
        manager = MemoryManager()
        result = manager.query_historical_odds(
            arguments.get("league", ""), 
            arguments.get("home_odds", 2.0),
            arguments.get("draw_odds", 3.0),
            arguments.get("away_odds", 3.0)
        )
        return {"content": [{"type": "text", "text": json.dumps(result)}]}
```

- [ ] **Step 2: Commit**

```bash
git add openclaw_workspace/src/mcp_server.py
git commit -m "feat: expose domain mastery models and memory retrieval as MCP tools"
```