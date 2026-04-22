# AI-Native Evolution Phase 2: Control Flow (StateGraph) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the `AINativeCoreAgent` from a simple `while` ReAct loop to a robust Directed Acyclic Graph (DAG) state machine using `langgraph` or a custom asynchronous state machine.

**Architecture:** Create an `AgentState` TypedDict. Define nodes: `gather_data`, `generate_hypothesis`, `verify_math`, `debate_risk`, `execute`. Define edges connecting them sequentially or conditionally based on the state. Compile the graph and run it.

**Tech Stack:** Python, LangGraph (if available) or `asyncio` state machine.

---

### Task 1: Create the StateGraph Core

**Files:**
- Create: `standalone_workspace/core/state_graph_core.py`
- Modify: `standalone_workspace/agents/ai_native_core.py` (to import the new graph)
- Test: `standalone_workspace/tests/test_state_graph_core.py`

- [ ] **Step 1: Write the failing test**

```python
# standalone_workspace/tests/test_state_graph_core.py
import pytest
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
        "final_decision": ""
    }
    
    # Run graph (mocked)
    final_state = await graph.ainvoke(initial_state)
    assert final_state["final_decision"] != ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest standalone_workspace/tests/test_state_graph_core.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Write minimal implementation**

```python
# standalone_workspace/core/state_graph_core.py
import asyncio
from typing import TypedDict, Dict, Any, List

class FootballAgentState(TypedDict):
    match: str
    data: Dict[str, Any]
    hypothesis: str
    math_verified: bool
    debate_passed: bool
    final_decision: str
    messages: List[Dict[str, str]]

class StateGraphRunner:
    def __init__(self):
        self.nodes = {}
        self.edges = {}
        self.entry_point = None
        
    def add_node(self, name, func):
        self.nodes[name] = func
        
    def add_edge(self, start, end):
        if start not in self.edges:
            self.edges[start] = []
        self.edges[start].append(end)
        
    def set_entry_point(self, name):
        self.entry_point = name
        
    async def ainvoke(self, state: FootballAgentState) -> FootballAgentState:
        current_node = self.entry_point
        while current_node:
            print(f"Executing node: {current_node}")
            state = await self.nodes[current_node](state)
            
            # Simple linear progression for now
            next_nodes = self.edges.get(current_node, [])
            if not next_nodes:
                break
            current_node = next_nodes[0]
        return state

async def node_gather_data(state: FootballAgentState) -> FootballAgentState:
    state["data"] = {"home_xg": 1.5, "away_xg": 1.0}
    return state

async def node_generate_hypothesis(state: FootballAgentState) -> FootballAgentState:
    state["hypothesis"] = "Home team likely to win."
    return state

async def node_verify_math(state: FootballAgentState) -> FootballAgentState:
    state["math_verified"] = True
    return state

async def node_debate_risk(state: FootballAgentState) -> FootballAgentState:
    state["debate_passed"] = True
    return state

async def node_execute(state: FootballAgentState) -> FootballAgentState:
    state["final_decision"] = "Bet placed on Home Win."
    return state

def compile_football_graph():
    graph = StateGraphRunner()
    graph.add_node("gather_data", node_gather_data)
    graph.add_node("generate_hypothesis", node_generate_hypothesis)
    graph.add_node("verify_math", node_verify_math)
    graph.add_node("debate_risk", node_debate_risk)
    graph.add_node("execute", node_execute)
    
    graph.add_edge("gather_data", "generate_hypothesis")
    graph.add_edge("generate_hypothesis", "verify_math")
    graph.add_edge("verify_math", "debate_risk")
    graph.add_edge("debate_risk", "execute")
    
    graph.set_entry_point("gather_data")
    return graph
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest standalone_workspace/tests/test_state_graph_core.py -v`
Expected: PASS

- [ ] **Step 5: Sync and Commit**

```bash
cp standalone_workspace/core/state_graph_core.py openclaw_workspace/runtime/football_analyzer/core/
git add .
git commit -m "feat(control-flow): implement lightweight StateGraph for structured agent reasoning"
```
