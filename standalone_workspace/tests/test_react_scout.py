import asyncio
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from agents.react_scout import AsyncReActScoutAgent
from tools.tool_registry import get_scout_tools

async def main():
    print("="*60)
    print(" 2026 Next-Gen AI - ReAct Scout Agent (Tool Calling 演示) ")
    print("="*60)
    print("本测试演示 Agent 如何自主思考并按需调用 Tool（无需静态写死流程）\n")
    
    agent = AsyncReActScoutAgent()
    
    # 模拟用户输入一场比赛
    state = {
        "current_match": {
            "league": "英超",
            "home": "曼联",
            "away": "阿森纳"
        }
    }
    
    result = await agent.process(state)
    
    print("\n[最终情报汇总]:")
    if "scout_data" in result:
        print(result["scout_data"].get("ai_report", result["scout_data"]))
        
if __name__ == "__main__":
    asyncio.run(main())
