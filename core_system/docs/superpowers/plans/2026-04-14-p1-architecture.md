# P1 - Architecture Maturation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Elevate the architecture's maturity by creating a Single Source of Truth (SSOT) for Tool Registry (shared by Standalone and OpenClaw) and implementing Pydantic/JSONSchema validation for tool arguments.

**Architecture:** 
1. **Tool Registry SSOT**: Move `AVAILABLE_TOOLS` and `TOOL_MAPPING` into a centralized `tool_registry.py` that generates both OpenAI format (for Standalone) and MCP format (for OpenClaw).
2. **Pydantic Validation**: Define Pydantic models for each tool's arguments. When LLM passes JSON, we validate it through Pydantic. If it fails, we catch the `ValidationError` and return it clearly.

**Tech Stack:** Python 3, `pydantic`.

---

### Task 1: Install Pydantic

**Files:**
- Modify: `requirements.txt` (or similar)

- [ ] **Step 1: Install Pydantic**
Run: `python3 -m pip install "pydantic>=2.0.0" --user --break-system-packages`
Expected: Installs pydantic successfully.

- [ ] **Step 2: Commit**
Run: `git commit --allow-empty -m "chore: add pydantic dependency"`

---

### Task 2: Create Tool Schemas and Validation

**Files:**
- Create: `tools/tool_registry_v2.py`
- Test: `tests/test_tool_registry.py`

- [ ] **Step 1: Write the failing test**

```python
import asyncio
from tools.tool_registry_v2 import execute_tool, get_openai_tools, get_mcp_tools

async def test_registry():
    # Test valid args
    res = await execute_tool("analyze_water_drop", {"opening_water": 1.05, "live_water": 0.85})
    assert res["ok"] is True
    
    # Test invalid args
    res = await execute_tool("analyze_water_drop", {"opening_water": "high", "live_water": 0.85})
    assert res["ok"] is False
    assert res["error"]["code"] == "VALIDATION_ERROR"
    
    # Test schemas
    openai_tools = get_openai_tools()
    assert len(openai_tools) > 0
    assert openai_tools[0]["type"] == "function"
    
    mcp_tools = get_mcp_tools()
    assert len(mcp_tools) > 0
    assert hasattr(mcp_tools[0], "name") # mcp.types.Tool

if __name__ == "__main__":
    asyncio.run(test_registry())
    print("test_registry PASSED")
```

- [ ] **Step 2: Run test to verify it fails**
Run: `PYTHONPATH=. python3 tests/test_tool_registry.py`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Write minimal implementation**

```python
from pydantic import BaseModel, Field, ValidationError
from typing import Dict, Any, List, Optional
import mcp.types as types
import inspect
from tools.mcp_tools import TOOL_MAPPING

class ToolDefinition:
    def __init__(self, name: str, description: str, model: type[BaseModel], func: callable):
        self.name = name
        self.description = description
        self.model = model
        self.func = func

    def to_openai(self) -> dict:
        schema = self.model.model_json_schema()
        # Remove title to make it cleaner
        if "title" in schema:
            del schema["title"]
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": schema
            }
        }

    def to_mcp(self) -> types.Tool:
        schema = self.model.model_json_schema()
        if "title" in schema:
            del schema["title"]
        return types.Tool(
            name=self.name,
            description=self.description,
            inputSchema=schema
        )

# Define Pydantic Models for validation
class WaterDropArgs(BaseModel):
    opening_water: float
    live_water: float

class TeamStatsArgs(BaseModel):
    team_name: str
    league: Optional[str] = None

class BankrollArgs(BaseModel):
    pass

# We map existing TOOL_MAPPING to definitions.
# For brevity in this step, we just define a few to prove the concept.
_TOOLS = [
    ToolDefinition(
        name="analyze_water_drop",
        description="计算从初盘到临场的水位下降幅度",
        model=WaterDropArgs,
        func=TOOL_MAPPING["analyze_water_drop"]
    ),
    ToolDefinition(
        name="get_team_stats",
        description="获取球队历史统计数据",
        model=TeamStatsArgs,
        func=TOOL_MAPPING["get_team_stats"]
    ),
    ToolDefinition(
        name="check_bankroll",
        description="查看当前真实可用资金",
        model=BankrollArgs,
        func=TOOL_MAPPING["check_bankroll"]
    )
]

REGISTRY = {t.name: t for t in _TOOLS}

def get_openai_tools() -> list:
    return [t.to_openai() for t in _TOOLS]

def get_mcp_tools() -> list:
    return [t.to_mcp() for t in _TOOLS]

async def execute_tool(name: str, args_dict: dict) -> dict:
    if name not in REGISTRY:
        return {"ok": False, "error": {"code": "UNKNOWN_TOOL", "message": f"Tool {name} not found"}, "meta": {}}
        
    tool_def = REGISTRY[name]
    try:
        validated_args = tool_def.model(**args_dict)
    except ValidationError as e:
        return {
            "ok": False,
            "error": {"code": "VALIDATION_ERROR", "message": str(e)},
            "meta": {"mock": False}
        }
        
    # Execute
    if inspect.iscoroutinefunction(tool_def.func):
        return await tool_def.func(**validated_args.model_dump())
    else:
        return tool_def.func(**validated_args.model_dump())
```

- [ ] **Step 4: Run test to verify it passes**
Run: `PYTHONPATH=. python3 tests/test_tool_registry.py`
Expected: PASS

- [ ] **Step 5: Commit**
Run: `git add tools/tool_registry_v2.py tests/test_tool_registry.py && git commit -m "feat: add pydantic tool registry and validation"`

---

### Task 3: Migrate all tools to Registry SSOT

**Files:**
- Modify: `tools/tool_registry_v2.py`
- Modify: `agents/ai_native_core.py`
- Modify: `openclaw_workspace/src/mcp_server.py`

- [ ] **Step 1: Write full implementation in `tools/tool_registry_v2.py`**
Define Pydantic models for all 15 tools in `TOOL_MAPPING` and add them to `_TOOLS`.
(e.g., `ExecuteBetArgs`, `AsianHandicapArgs`, `PoissonArgs`, `VisionArgs`, `ParlayArgs`, etc.)

- [ ] **Step 2: Update Standalone Core**
In `agents/ai_native_core.py`:
Replace `AVAILABLE_TOOLS` import with `from tools.tool_registry_v2 import get_openai_tools, execute_tool`.
Replace `self._execute_tool(function_name, arguments)` with `await execute_tool(function_name, arguments)`.
Pass `tools=get_openai_tools()` to OpenAI.

- [ ] **Step 3: Update OpenClaw MCP Server**
In `openclaw_workspace/src/mcp_server.py`:
Replace manual schema definitions with `get_mcp_tools()`.
Replace the giant `if/elif` block in `handle_call_tool` with `res = await execute_tool(name, arguments)`.

- [ ] **Step 4: Run existing tests to ensure no breakage**
Run: `PYTHONPATH=. python3 tests/test_param_validation.py`
Run: `PYTHONPATH=. python3 tests/test_tool_protocol.py`

- [ ] **Step 5: Commit**
Run: `git add tools/tool_registry_v2.py agents/ai_native_core.py openclaw_workspace/src/mcp_server.py && git commit -m "refactor: migrate standalone and openclaw to SSOT tool registry"`
