import os
import sys
import asyncio


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tools.memory_manager import MemoryManager


async def mine_tactical_matrix():
    print("🕵️  [Tactical Miner] Scanning historical data for tactical upsets...")
    manager = MemoryManager()

    mock_upsets = [
        {"winner": "TeamA", "loser": "TeamB", "tactic": "Counter-Attack beats High-Press"},
        {"winner": "TeamC", "loser": "TeamD", "tactic": "Low-Block beats Tiki-Taka"},
    ]

    for upset in mock_upsets:
        insight = (
            f"Historical Matrix: {upset['tactic']} observed in {upset['winner']} vs {upset['loser']}."
        )
        res = manager.add_episodic_memory(
            content=insight, tags=["tactics", "upset", upset["winner"]], importance=0.9
        )
        if res.get("ok"):
            print(f"💾 Saved tactical insight to MemoryManager: {res.get('doc_id')}")
        else:
            print(f"⚠️ Failed to save tactical insight: {res.get('error')}")

    print("✅ Tactical Matrix Mining complete. Insights injected into Agentic subconscious.")


if __name__ == "__main__":
    asyncio.run(mine_tactical_matrix())

