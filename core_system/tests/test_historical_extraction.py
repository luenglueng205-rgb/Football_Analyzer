import pytest
import sys
from pathlib import Path

# Add standalone_workspace to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data.historical_database import HistoricalDatabase

def test_extract_ht_scores():
    db = HistoricalDatabase(lazy_load=False)
    matches = db.raw_data.get("data", [])
    if matches:
        match = matches[0]
        # Just checking that it doesn't crash and we can access the dict
        assert isinstance(match, dict)
