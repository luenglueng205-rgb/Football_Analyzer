# AI-Native Football Analyzer Evolution Spec

## Goal
Evolve the existing pure AI-Native codebase into its ultimate 2026 form by implementing four critical architectural upgrades:
1. **Self-Reflection & RLHF (After-Action Review)**: Automate post-match evaluation and update the system's memory and dynamic experience rules.
2. **Graph-based Reasoning (StateGraph)**: Migrate the `AINativeCoreAgent` from a simple `while` ReAct loop to a robust Directed Acyclic Graph (DAG) state machine to prevent infinite loops and ensure logical step progression.
3. **MCP Dynamic Discovery**: Allow the core agent to dynamically discover and use external Model Context Protocol (MCP) tools at runtime instead of relying solely on hardcoded Python functions.
4. **Multi-Model Router**: Implement an intelligent routing layer that dispatches specific tasks to the most suitable LLM (e.g., Vision tasks to GPT-4o, complex reasoning to DeepSeek, simple summarization to cheaper models).

## Architecture

**Phase 1: Memory Flow (AAR Agent)**
Create an `AfterActionReviewAgent` that takes match results and previous AI predictions, uses an LLM to extract key insights (why the prediction succeeded or failed), and writes these back into `DYNAMIC_EXPERIENCE.md` and ChromaDB.

**Phase 2: Control Flow (StateGraph)**
Replace the linear `for i in range(15)` ReAct loop in `ai_native_core.py` with a StateGraph (using `langgraph` or a custom lightweight state machine). The nodes will be: `Initialize`, `Data_Gathering`, `Hypothesis_Generation`, `Math_Verification`, `Debate`, `Execution`, `End`.

**Phase 3: Tool Flow (MCP Discovery)**
Enhance the `tool_registry_v2.py` and `ai_native_core.py` to scan a predefined local directory or port range for MCP servers, fetch their schemas, and dynamically append them to the LLM's available tools.

**Phase 4: Model Flow (Multi-Model Router)**
Modify `llm_service.py` to accept a `task_type` parameter. Based on this parameter, it will select different clients/models from environment variables (e.g., `OPENAI_VISION_MODEL`, `DEEPSEEK_REASONING_MODEL`).

## Tech Stack
- Python 3.10+
- OpenAI SDK (for LLM calls)
- LangGraph (or custom async state machine)
- MCP SDK (Model Context Protocol)
- ChromaDB (Vector Store)

## Implementation Order
We will tackle these one by one, ensuring each is fully tested and integrated into both `standalone_workspace` and `openclaw_workspace`.
