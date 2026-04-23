import pytest
import os
import sys
from pathlib import Path

# Add standalone_workspace to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.after_action_review import AfterActionReviewAgent

@pytest.mark.asyncio
async def test_aar_agent_reflection():
    os.environ["OPENAI_API_KEY"] = "dummy-key-for-test"
    agent = AfterActionReviewAgent()
    
    # Mock data
    match_data = {"home_team": "TeamA", "away_team": "TeamB", "home_score": 1, "away_score": 0}
    prediction = {"predicted_winner": "TeamB", "confidence": 0.8, "reasoning": "TeamA is weak."}
    
    try:
        result = await agent.generate_reflection(match_data, prediction)
    except ValueError as e:
        # Expected ValueError when dummy-key is used
        assert "OPENAI_API_KEY" in str(e)
        return
    except Exception as e:
        # Or if openai rejects dummy key over network
        assert "401" in str(e) or "Authentication" in str(e)
        return
        
    assert "reflection" in result
    assert "lesson" in result
    assert result["success"] is False

@pytest.mark.asyncio
async def test_aar_save_lesson(tmp_path):
    os.environ["OPENAI_API_KEY"] = "dummy-key-for-test"
    agent = AfterActionReviewAgent()
    
    # Mock writing to a temporary DYNAMIC_EXPERIENCE.md
    test_doc = tmp_path / "DYNAMIC_EXPERIENCE.md"
    test_doc.write_text("# Dynamic Experience\n")
    
    lesson = "Always consider heavy rain impact on passing teams."
    await agent.save_lesson_to_doc(lesson, str(test_doc))
    
    content = test_doc.read_text()
    assert lesson in content
