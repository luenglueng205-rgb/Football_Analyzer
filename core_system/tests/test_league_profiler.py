import pytest
import json
from tools.league_profiler import get_league_persona

def test_league_profiler_returns_persona():
    result_str = get_league_persona("Premier League")
    result = json.loads(result_str)
    assert "profile" in result
    assert "persona" in result["profile"]
    assert "variance" in result["profile"]
    assert "tactical_style" in result["profile"]
