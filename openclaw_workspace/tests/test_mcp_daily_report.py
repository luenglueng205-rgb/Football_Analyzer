import asyncio
import json
import os
import sys
from typing import Dict, Any

# Mock the context object that OpenClaw would pass
class MockContext:
    pass

# Import the MCP server handle_request method
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from mcp_server import handle_request

async def test_mcp_daily_report():
    print("🚀 [OpenClaw MCP Test] Calling 'generate_daily_report' tool...")
    
    # Construct the JSON-RPC request exactly as OpenClaw would send it
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "call_tool",
        "params": {
            "name": "generate_daily_report",
            "arguments": {
                "date_str": "2026-04-16",
                "pnl": 1500.50,
                "evolution_reason": "系统成功规避了皇马客场诱盘陷阱，基本面派权重已上调。"
            }
        }
    }
    
    # Execute the request through the OpenClaw MCP interface
    response = await handle_request(request)
    
    print("\n✅ MCP Response Received:")
    if "result" in response and "content" in response["result"]:
        content = response["result"]["content"][0]["text"]
        print(content)
    else:
        print("❌ Error in response:", json.dumps(response, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(test_mcp_daily_report())
