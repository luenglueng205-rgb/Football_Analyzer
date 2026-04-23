import pytest
import sys
import inspect
from pathlib import Path

# Add standalone_workspace to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.llm_service import LLMService

@pytest.mark.asyncio
async def test_multi_model_router_integration():
    sig = inspect.signature(LLMService.generate_report_async)
    assert "task_type" in sig.parameters
