import asyncio
from agents.async_scout import AsyncScoutAgent

async def test():
    scout = AsyncScoutAgent()
    match_info = {"home_team": "Manchester United"}
    weather = scout._get_weather_info(match_info)
    print(f"Weather for {match_info['home_team']}: {weather}")

if __name__ == "__main__":
    asyncio.run(test())
