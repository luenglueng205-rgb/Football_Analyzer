# AI-Native Evolution Phase 4: Model Flow (Multi-Model Router) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement an intelligent routing layer that dispatches specific tasks to the most suitable LLM based on task type.

**Architecture:** Modify `LLMService` to accept a `task_type` parameter (e.g., `vision`, `reasoning`, `summarization`). Based on this parameter, the service will pick the correct API Key and Base URL (e.g., `OPENAI_VISION_MODEL`, `DEEPSEEK_REASONING_MODEL`) to optimize performance and cost.

**Tech Stack:** Python, OpenAI API SDK.

---

### Task 1: Enhance the LLM Service

**Files:**
- Modify: `standalone_workspace/tools/llm_service.py`
- Test: `standalone_workspace/tests/test_llm_router.py`

- [ ] **Step 1: Write the failing test**

```python
# standalone_workspace/tests/test_llm_router.py
import pytest
import os
from tools.llm_service import LLMService

@pytest.mark.asyncio
async def test_llm_routing_logic():
    os.environ["OPENAI_API_KEY"] = "dummy-key-for-test"
    os.environ["DEEPSEEK_API_KEY"] = "deepseek-dummy-key"
    os.environ["OPENAI_VISION_MODEL"] = "gpt-4o"
    os.environ["DEEPSEEK_REASONING_MODEL"] = "deepseek-reasoner"
    
    # Mock routing
    # This shouldn't actually call the API since the keys are dummy, 
    # but we can check if it raises the correct error or returns a specific mock
    
    with pytest.raises(ValueError) as excinfo:
        await LLMService.generate_report_async("Prompt", "Context", role="Analyst", task_type="reasoning")
        
    assert "DEEPSEEK_API_KEY" in str(excinfo.value) or "dummy" in str(excinfo.value)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest standalone_workspace/tests/test_llm_router.py -v`
Expected: FAIL (method signature does not accept `task_type`)

- [ ] **Step 3: Write implementation**

```python
# Modify standalone_workspace/tools/llm_service.py
# Add task_type parameter to generate_report and generate_report_async
# Example update in LLMService class:

    @classmethod
    async def generate_report_async(cls, system_prompt: str, data_context: str, role: str = "Analyst", task_type: str = "general") -> str:
        """
        基于任务类型路由到最佳模型 (Model Router)
        task_type: 'general', 'vision', 'reasoning', 'summarization'
        """
        import os
        from openai import AsyncOpenAI
        import json
        
        # Router logic
        if task_type == "vision":
            api_key = os.getenv("OPENAI_API_KEY", "dummy_key")
            base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
            model = os.getenv("OPENAI_VISION_MODEL", "gpt-4o")
        elif task_type == "reasoning":
            api_key = os.getenv("DEEPSEEK_API_KEY", "dummy_key")
            base_url = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com")
            model = os.getenv("DEEPSEEK_REASONING_MODEL", "deepseek-reasoner")
        else:
            api_key = os.getenv("OPENAI_API_KEY", "dummy_key")
            base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini") # default cheap model
            
        if api_key == "dummy_key" or api_key == "your_api_key_here":
            if role == "AAR Analyst":
                return json.dumps({"success": False, "reflection": "Mock reflection.", "lesson": "Mock lesson."})
            raise ValueError(f"请在环境变量中配置有效的 API_KEY ({task_type} 需要) 以启动真实的 AI 推理。")
            
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": data_context}
            ],
            temperature=0.3,
            max_tokens=800
        )
        return response.choices[0].message.content
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest standalone_workspace/tests/test_llm_router.py -v`
Expected: PASS

- [ ] **Step 5: Sync and Commit**

```bash
cp standalone_workspace/tools/llm_service.py openclaw_workspace/runtime/football_analyzer/tools/
git add .
git commit -m "feat(model): implement Multi-Model Router to dispatch reasoning, vision, and general tasks to optimized LLMs"
```
