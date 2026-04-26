import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

import time
import os
from openclaw_workspace.skills.news_arbitrage.social_listener import SocialNewsListener

def test_zsa_latency():
    # Force real mode
    os.environ["NEWS_LISTENER_MOCK"] = "false"
    
    print("Starting SocialNewsListener in background mode...")
    listener = SocialNewsListener()
    
    # Wait for the background thread to boot
    time.sleep(1)
    
    print("\n--- First Call (Cold Start) ---")
    start = time.perf_counter()
    result1 = listener.fetch_latest_news("Arsenal")
    end = time.perf_counter()
    print(f"Time taken: {(end - start) * 1000:.2f} ms")
    print(f"Result: {result1}")
    
    # Wait a bit to let the async fetch finish if it was triggered
    time.sleep(3)
    
    print("\n--- Second Call (Warm Cache) ---")
    start2 = time.perf_counter()
    result2 = listener.fetch_latest_news("Arsenal")
    end2 = time.perf_counter()
    print(f"Time taken: {(end2 - start2) * 1000:.2f} ms")
    print(f"Result: {result2}")
    
    assert (end2 - start2) * 1000 < 5.0, "Latency is too high for ZSA!"
    print("\n✅ Success! ZSA latency is under 5ms.")

if __name__ == "__main__":
    test_zsa_latency()