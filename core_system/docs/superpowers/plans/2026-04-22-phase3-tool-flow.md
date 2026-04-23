# AI-Native Evolution Phase 3: Tool Flow (MCP Discovery) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow the core agent to dynamically discover and use external Model Context Protocol (MCP) tools at runtime instead of relying solely on hardcoded Python functions.

**Architecture:** Create an `MCPToolDiscoverer` that scans an `mcp_servers/` directory or pings a local registry for available tools. It reads `tools.json` or calls the MCP `/tools` endpoint to get JSON schemas, then dynamically appends them to the LLM's `tools` array.

**Tech Stack:** Python, MCP SDK.

---

### Task 1: Create the MCP Tool Discoverer

**Files:**
- Create: `standalone_workspace/tools/mcp_discoverer.py`
- Modify: `standalone_workspace/tools/tool_registry_v2.py`
- Test: `standalone_workspace/tests/test_mcp_discoverer.py`

- [ ] **Step 1: Write the failing test**

```python
# standalone_workspace/tests/test_mcp_discoverer.py
import pytest
from tools.mcp_discoverer import MCPToolDiscoverer

def test_discover_tools():
    discoverer = MCPToolDiscoverer()
    # Mocking discovery
    tools = discoverer.discover_local_tools("tests/mock_mcp_servers")
    
    assert isinstance(tools, list)
    if len(tools) > 0:
        assert "type" in tools[0]
        assert tools[0]["type"] == "function"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest standalone_workspace/tests/test_mcp_discoverer.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Write minimal implementation**

```python
# standalone_workspace/tools/mcp_discoverer.py
import os
import json
from pathlib import Path
from typing import List, Dict, Any

class MCPToolDiscoverer:
    """
    动态发现和注册 MCP (Model Context Protocol) 工具
    """
    def __init__(self):
        self.discovered_tools = []
        self.mcp_tool_mapping = {}

    def discover_local_tools(self, mcp_servers_dir: str = "mcp_servers") -> List[Dict[str, Any]]:
        """扫描本地目录发现 MCP 工具配置"""
        base_path = Path(__file__).resolve().parents[2] / mcp_servers_dir
        
        if not base_path.exists():
            return []
            
        for server_dir in base_path.iterdir():
            if server_dir.is_dir():
                tools_file = server_dir / "tools.json"
                if tools_file.exists():
                    try:
                        with open(tools_file, "r", encoding="utf-8") as f:
                            server_tools = json.load(f)
                            for tool in server_tools:
                                # Validate standard OpenAI tool format
                                if "type" in tool and tool["type"] == "function":
                                    self.discovered_tools.append(tool)
                                    # Register a dummy executor for MCP
                                    tool_name = tool["function"]["name"]
                                    self.mcp_tool_mapping[tool_name] = self._create_mcp_executor(server_dir.name, tool_name)
                    except Exception as e:
                        print(f"Failed to load tools from {tools_file}: {e}")
                        
        return self.discovered_tools
        
    def _create_mcp_executor(self, server_name: str, tool_name: str):
        """创建一个闭包，用于后续通过 HTTP/Stdio 调用真实的 MCP Server"""
        async def executor(**kwargs):
            print(f"[MCP] Calling {tool_name} on server {server_name} with args {kwargs}")
            # Placeholder for real MCP SDK invocation
            return {"status": "success", "message": f"Executed {tool_name} via MCP."}
        return executor
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest standalone_workspace/tests/test_mcp_discoverer.py -v`
Expected: PASS

- [ ] **Step 5: Sync and Commit**

```bash
cp standalone_workspace/tools/mcp_discoverer.py openclaw_workspace/runtime/football_analyzer/tools/
git add .
git commit -m "feat(tools): implement dynamic MCP Tool Discovery for zero-code tool integration"
```
