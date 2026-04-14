import asyncio
import os
import requests
from unittest.mock import patch
from agents.syndicate_os import SyndicateOS

def mock_requests_get(*args, **kwargs):
    raise requests.exceptions.ConnectionError("Connection refused!")

async def run_network_chaos():
    print("\n" + "="*60)
    print("CHAOS TEST 1: Extreme Network and API Failure")
    print("="*60)
    
    os.environ["OPENAI_API_KEY"] = "sk-invalid-key-for-chaos-testing-12345"
    os.environ["ODDS_API_KEY"] = "invalid-odds-api-key"
    
    with patch("requests.get", side_effect=mock_requests_get):
        os_system = SyndicateOS()
        try:
            print("  -> Testing offline: Arsenal vs Chelsea")
            res = await asyncio.wait_for(os_system.process_match("Arsenal", "Chelsea", "JCZQ"), timeout=60.0)
            
            decision = res.get("final_decision", "")
            print("\nSystem survived offline environment gracefully.")
            print(f"Judge decision: {decision[:150]}...")
            
        except asyncio.TimeoutError:
            print("\nFailed: System hung during offline test (Timeout > 60s).")
        except Exception as e:
            print(f"\nFailed: Fatal unhandled exception: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(run_network_chaos())
