# AI-Native Integration Spec

## Goal
Integrate the newly created architectural components (`AfterActionReviewAgent`, `StateGraphRunner`, `MCPToolDiscoverer`, and `Multi-Model Router`) directly into the main execution flows of both `standalone_workspace` and `openclaw_workspace`.

## Architecture
1. **Tool Discovery**: Update `AINativeCoreAgent` to instantiate `MCPToolDiscoverer` on startup and merge discovered tools into its `self.tools` list.
2. **Model Routing**: Refactor the inner ReAct loop inside `AINativeCoreAgent` to use `LLMService.generate_report_async(..., task_type="reasoning")` instead of directly calling `client.chat.completions.create` with a hardcoded model.
3. **Graph Integration**: Replace the `for i in range(self.max_loops):` in `AINativeCoreAgent.process()` with an invocation of `compile_football_graph().ainvoke(state)`.
4. **AAR Agent Hook**: In `openclaw_agent.py` and `AINativeCoreAgent`'s final step, add a background task to trigger `AfterActionReviewAgent.generate_reflection()` after a prediction is finalized (simulating a post-match trigger for now, or exposing a specific endpoint for it).

## Tech Stack
- Python 3.10+
- Existing project files (`ai_native_core.py`, `openclaw_agent.py`)

## Implementation Plan
See `docs/superpowers/plans/2026-04-22-integration.md`
