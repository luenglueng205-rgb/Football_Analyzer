import pytest
import sys
from pathlib import Path

# Add standalone_workspace to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.ai_native_core import AINativeCoreAgent

@pytest.mark.asyncio
async def test_mcp_discoverer_integration():
    agent = AINativeCoreAgent()
    # Ensure discover_local_tools is called during init
    assert hasattr(agent, "mcp_discoverer")
    assert isinstance(agent.tools, list)
    # The get_openai_tools() returns standard tools, plus any discovered MCP tools
