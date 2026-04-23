import pytest
import sys
from pathlib import Path

# Add standalone_workspace to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.state_graph_core import compile_football_graph

@pytest.mark.asyncio
async def test_football_graph_compiles():
    graph = compile_football_graph()
    assert graph is not None
    
    # Mock state
    initial_state = {
        "match": "TeamA vs TeamB",
        "data": {},
        "hypothesis": "",
        "math_verified": False,
        "debate_passed": False,
        "final_decision": "",
        "messages": []
    }
    
    # Run graph (mocked)
    final_state = await graph.ainvoke(initial_state)
    assert final_state["final_decision"] != ""
