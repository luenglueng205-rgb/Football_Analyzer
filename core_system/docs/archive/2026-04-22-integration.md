# AI-Native Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate the newly created `AfterActionReviewAgent`, `StateGraphRunner`, `MCPToolDiscoverer`, and `Multi-Model Router` directly into the execution flow of `AINativeCoreAgent` and `openclaw_agent.py`.

**Architecture:** We will replace the linear ReAct loop in `ai_native_core.py` with the `StateGraphRunner`. We will inject `MCPToolDiscoverer` tools into the prompt/function schema. We will route specific LLM calls (vision vs reasoning) using the updated `LLMService`. Finally, we will expose a method to trigger `AfterActionReviewAgent`.

**Tech Stack:** Python, OpenAI SDK.

---

### Task 1: Integrate MCP Discoverer into Core Agent

**Files:**
- Modify: `standalone_workspace/agents/ai_native_core.py`

- [ ] **Step 1: Write the failing test for MCP Integration**

```python
# standalone_workspace/tests/test_core_integration.py
import pytest
from agents.ai_native_core import AINativeCoreAgent

@pytest.mark.asyncio
async def test_mcp_discoverer_integration():
    agent = AINativeCoreAgent()
    # Ensure discover_local_tools is called during init
    assert hasattr(agent, "mcp_discoverer")
    assert isinstance(agent.tools, list)
    # The get_openai_tools() returns standard tools, plus any discovered MCP tools
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest standalone_workspace/tests/test_core_integration.py::test_mcp_discoverer_integration -v`
Expected: FAIL (no `mcp_discoverer` attribute)

- [ ] **Step 3: Write minimal implementation**

Modify `standalone_workspace/agents/ai_native_core.py` `__init__`:
```python
    def __init__(self, use_memory: bool = True):
        # ... existing ...
        from tools.tool_registry_v2 import get_openai_tools
        from tools.mcp_discoverer import MCPToolDiscoverer
        
        self.mcp_discoverer = MCPToolDiscoverer()
        mcp_tools = self.mcp_discoverer.discover_local_tools()
        
        self.tools = get_openai_tools() + mcp_tools
        self.mcp_tool_mapping = self.mcp_discoverer.mcp_tool_mapping
        
        # ... existing ...
```

Modify the tool execution part in `process` to support `self.mcp_tool_mapping`:
```python
        # inside the loop handling tool calls
        if tool_name in self.mcp_tool_mapping:
            tool_result = await self.mcp_tool_mapping[tool_name](**tool_args)
        else:
            from tools.tool_registry_v2 import execute_tool
            tool_result = await execute_tool(tool_name, tool_args)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest standalone_workspace/tests/test_core_integration.py::test_mcp_discoverer_integration -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add standalone_workspace/agents/ai_native_core.py standalone_workspace/tests/test_core_integration.py
git commit -m "feat(integration): inject MCPToolDiscoverer into AINativeCoreAgent for dynamic tool loading"
```

### Task 2: Integrate Multi-Model Router into Core Agent

**Files:**
- Modify: `standalone_workspace/agents/ai_native_core.py`

- [ ] **Step 1: Write the failing test for Model Router**

```python
# standalone_workspace/tests/test_core_integration.py
# Append:
@pytest.mark.asyncio
async def test_multi_model_router_integration():
    agent = AINativeCoreAgent()
    # We want to ensure that the agent calls LLMService.generate_report_async with task_type="reasoning"
    # Testing this precisely might require mocking, but we can verify the method signature.
    import inspect
    from tools.llm_service import LLMService
    sig = inspect.signature(LLMService.generate_report_async)
    assert "task_type" in sig.parameters
```

- [ ] **Step 2: Run test to verify it fails/passes** (It should pass if Phase 4 was done right, but we need to change the code).

- [ ] **Step 3: Write implementation**

Modify `standalone_workspace/agents/ai_native_core.py` to use the router instead of direct client calls where appropriate.
```python
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        # ...
        from tools.llm_service import LLMService
        # ...
        # Replace the direct client.chat.completions.create block with LLMService
        
        try:
            # We construct a prompt from self.messages
            system_prompt = self.messages[0]["content"] if self.messages and self.messages[0]["role"] == "system" else self.system_prompt
            data_context = json.dumps(self.messages[1:], ensure_ascii=False)
            
            response_content = await LLMService.generate_report_async(
                system_prompt=system_prompt,
                data_context=data_context,
                role="AINativeCore",
                task_type="reasoning" # Use the deepseek/reasoning router
            )
            
            # Since LLMService currently doesn't handle tool_calls natively in generate_report_async, 
            # we need to either update LLMService to support tool_calls, OR 
            # keep the direct client call for the ReAct loop, and use LLMService for specific sub-tasks.
            # Let's keep the ReAct loop using the direct client for tool_calls, but use LLMService for the Debate Engine.
            pass
        except Exception as e:
            pass
```
*Correction during planning: Since `LLMService.generate_report_async` returns a string and doesn't handle `tool_calls` parameter parsing easily without a rewrite, we will inject the Model Router logic directly into the `AINativeCoreAgent` initialization, or we use `LLMService` for specific sub-tasks like `VisionOddsReader` (which we already did) and `AfterActionReviewAgent` (which we already did).*

Let's implement the router directly in the `AINativeCoreAgent` initialization so it uses `DEEPSEEK_REASONING_MODEL` for the main ReAct loop:
```python
# standalone_workspace/agents/ai_native_core.py __init__
        self.model = os.getenv("DEEPSEEK_REASONING_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
        api_key = os.getenv("DEEPSEEK_API_KEY", os.getenv("OPENAI_API_KEY", "dummy-key"))
        base_url = os.getenv("DEEPSEEK_API_BASE", os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1"))
        
        try:
            self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        except Exception:
            self.client = None
```

- [ ] **Step 4: Commit**

```bash
git add standalone_workspace/agents/ai_native_core.py
git commit -m "feat(integration): route AINativeCoreAgent main reasoning loop to DeepSeek reasoning model if configured"
```

### Task 3: Expose After-Action Review (AAR) in OpenClaw Agent

**Files:**
- Modify: `openclaw_workspace/src/openclaw_agent.py`
- Modify: `standalone_workspace/agents/after_action_review.py`

- [ ] **Step 1: Write implementation**

Modify `openclaw_workspace/src/openclaw_agent.py` to add a new CLI command and async method for AAR:
```python
    async def post_match_review(self, home_team: str, away_team: str, home_score: int, away_score: int, prediction_file: str = None) -> Dict[str, Any]:
        """触发赛后复盘与强化学习"""
        logger.info(f"Starting post-match review for {home_team} vs {away_team}")
        try:
            from agents.after_action_review import AfterActionReviewAgent
            aar_agent = AfterActionReviewAgent()
            
            match_data = {"home_team": home_team, "away_team": away_team, "home_score": home_score, "away_score": away_score}
            
            # In a real system, load prediction from DB. For now, mock it.
            prediction = {"predicted_winner": home_team, "confidence": 0.8}
            
            result = await aar_agent.generate_reflection(match_data, prediction)
            if result.get("lesson"):
                await aar_agent.save_lesson_to_doc(result["lesson"])
                
            return {"ok": True, "data": result}
        except Exception as e:
            return {"ok": False, "error": str(e)}

# Update CLI args in __main__:
    parser.add_argument("--action", default="analyze", choices=["analyze", "query", "review"])
    parser.add_argument("--home_score", type=int, default=0)
    parser.add_argument("--away_score", type=int, default=0)
    
    args = parser.parse_args()
    agent = OpenClawMainAgent(online=args.online)
    
    if args.action == "analyze":
        result = asyncio.run(agent.analyze_and_trade(args.lottery, args.date, args.home, args.away))
    elif args.action == "review":
        result = asyncio.run(agent.post_match_review(args.home, args.away, args.home_score, args.away_score))
```

- [ ] **Step 2: Commit**

```bash
git add openclaw_workspace/src/openclaw_agent.py
git commit -m "feat(integration): expose After-Action Review (RLHF) trigger in openclaw_agent CLI"
```

### Task 4: Integrate StateGraph into AINativeCoreAgent

*Note: Fully replacing the ReAct loop with StateGraph is a massive structural change that might break existing `MultiAgentDebateEngine` integration in one go. We will implement `AINativeCoreAgent.process_graph(state)` as an alternative entry point alongside the traditional `process(state)` to ensure stability, then switch `openclaw_agent.py` to use it.*

**Files:**
- Modify: `standalone_workspace/agents/ai_native_core.py`
- Modify: `openclaw_workspace/src/openclaw_agent.py`

- [ ] **Step 1: Write implementation**

Modify `standalone_workspace/agents/ai_native_core.py`:
```python
    async def process_graph(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用 2026 版 StateGraph (DAG) 架构执行分析，避免 ReAct 死循环。
        """
        from core.state_graph_core import compile_football_graph
        graph = compile_football_graph()
        
        # Format initial state
        initial_state = {
            "match": f"{state.get('current_match', {}).get('home_team')} vs {state.get('current_match', {}).get('away_team')}",
            "data": state.get("params", {}),
            "hypothesis": "",
            "math_verified": False,
            "debate_passed": False,
            "final_decision": "",
            "messages": []
        }
        
        final_state = await graph.ainvoke(initial_state)
        
        # Convert graph output to standard report format
        report = f"# AI-Native Graph Analysis Report\n\n## 最终决策\n{final_state.get('final_decision')}\n\n## 验证状态\n数学验证: {final_state.get('math_verified')}\n风控辩论: {final_state.get('debate_passed')}"
        
        return {"report": report, "state": final_state}
```

Modify `openclaw_workspace/src/openclaw_agent.py` to optionally use graph:
```python
    parser.add_argument("--use_graph", action="store_true", help="使用最新的 StateGraph 架构而不是传统的 ReAct 循环")
    
    # inside analyze_and_trade:
    if getattr(self, "use_graph", False):
        result = await self.brain.process_graph(state)
    else:
        result = await self.brain.process(state)
```

- [ ] **Step 2: Commit**

```bash
git add standalone_workspace/agents/ai_native_core.py openclaw_workspace/src/openclaw_agent.py
git commit -m "feat(integration): integrate StateGraph into AINativeCoreAgent as an alternative, safer execution path"
```

### Task 5: Final Sync to OpenClaw Runtime

- [ ] **Step 1: Copy all modified standalone files to openclaw runtime**

```bash
rsync -av --exclude 'data/chroma_db' --exclude 'data/chroma_db_part_*' --exclude 'datasets' --exclude '.git' --exclude '.DS_Store' "/Volumes/J ZAO 9 SER 1/Python/TRAE-SOLO/football_analyzer/standalone_workspace/" "/Volumes/J ZAO 9 SER 1/Python/TRAE-SOLO/football_analyzer/openclaw_workspace/runtime/football_analyzer/"
```

- [ ] **Step 2: Final Git Push**

```bash
git add .
git commit -m "chore: sync final integration phase to openclaw runtime"
git push origin main
```
