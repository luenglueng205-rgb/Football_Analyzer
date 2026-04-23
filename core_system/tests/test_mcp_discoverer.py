import pytest
import sys
from pathlib import Path

# Add standalone_workspace to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.mcp_discoverer import MCPToolDiscoverer

def test_discover_tools():
    discoverer = MCPToolDiscoverer()
    # Mocking discovery
    tools = discoverer.discover_local_tools("tests/mock_mcp_servers")
    
    assert isinstance(tools, list)
    if len(tools) > 0:
        assert "type" in tools[0]
        assert tools[0]["type"] == "function"
