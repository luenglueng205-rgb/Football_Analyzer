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
