import asyncio
from agents.auto_tuner_agent import AutoTunerAgent

async def test():
    tuner = AutoTunerAgent()
    print("Running Daily Reflection...")
    result = await tuner.run_daily_reflection()
    print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(test())
