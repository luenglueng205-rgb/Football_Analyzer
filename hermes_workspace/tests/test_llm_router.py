import pytest
import os
import sys
from pathlib import Path

# Add standalone_workspace to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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
    
    try:
        await LLMService.generate_report_async("Prompt", "Context", role="Analyst", task_type="reasoning")
        assert False, "Expected Exception to be raised for dummy key"
    except Exception as e:
        # Either ValueError or openai.AuthenticationError is fine
        assert "API_KEY" in str(e) or "Authentication" in str(e) or "401" in str(e)
