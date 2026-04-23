import json
import asyncio
from unittest.mock import MagicMock, AsyncMock
from agents.ai_native_core import AINativeCoreAgent

async def test_bad_args():
    agent = AINativeCoreAgent()
    
    mock_response_1 = MagicMock()
    mock_message_1 = MagicMock()
    mock_message_1.tool_calls = [
        MagicMock(
            id="call_123",
            function=MagicMock(name="get_team_stats", arguments="BAD JSON")
        )
    ]
    # In python mock, .name on a MagicMock returns another MagicMock unless explicitly set via name kwarg or assigned
    mock_message_1.tool_calls[0].function.name = "get_team_stats"
    mock_response_1.choices = [MagicMock(message=mock_message_1)]
    
    mock_response_2 = MagicMock()
    mock_message_2 = MagicMock()
    mock_message_2.tool_calls = None
    mock_message_2.content = "Finished."
    mock_response_2.choices = [MagicMock(message=mock_message_2)]
    
    agent.client = MagicMock()
    agent.client.chat.completions.create = AsyncMock(side_effect=[mock_response_1, mock_response_2])
    
    state = {
        "current_match": {"league": "test", "home_team": "A", "away_team": "B"},
        "params": {"lottery_type": "test", "lottery_desc": "test"}
    }
    
    import agents.ai_native_core
    agents.ai_native_core.MultiAgentDebateEngine = MagicMock()
    mock_debate_instance = MagicMock()
    mock_debate_instance.run_debate = AsyncMock(return_value="Debate Done")
    agents.ai_native_core.MultiAgentDebateEngine.return_value = mock_debate_instance
    
    result = await agent.process(state)
    
    assert "raw_data" in result
    raw_data = result["raw_data"]
    assert "get_team_stats" in raw_data
    error_msg = raw_data["get_team_stats"][0]
    assert error_msg["ok"] is False
    assert error_msg["error"]["code"] == "BAD_ARGS"
    
    print("test_bad_args PASSED")

if __name__ == "__main__":
    asyncio.run(test_bad_args())