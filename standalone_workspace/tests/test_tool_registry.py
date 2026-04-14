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
    names = [t["function"]["name"] for t in openai_tools]
    assert "get_live_odds" in names
    
    mcp_tools = get_mcp_tools()
    assert len(mcp_tools) > 0
    assert hasattr(mcp_tools[0], "name") # mcp.types.Tool

if __name__ == "__main__":
    asyncio.run(test_registry())
    print("test_registry PASSED")
