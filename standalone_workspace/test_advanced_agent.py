import asyncio
from core.state_graph_core import compile_advanced_football_graph, AdvancedAgentState

async def test_agent():
    graph = compile_advanced_football_graph()
    
    # 模拟一场没有套利空间的普通比赛
    state = AdvancedAgentState(
        match_id="EPL_001",
        home_team="Bournemouth",
        away_team="Leeds United",
        plan=[],
        current_step="",
        memory={},
        reflections=[],
        status="running",
        final_ticket=None
    )
    
    print("\n============================================")
    print(f"🚀 开始测试 2026 前沿架构 (Actor-Critic) - {state['match_id']}")
    print("============================================")
    
    final_state = await graph.ainvoke(state)
    
    print("\n============================================")
    print("🎯 测试结束。最终状态报告：")
    print(f"状态: {final_state['status']}")
    print(f"反思日志: {final_state['reflections']}")
    print(f"最终出票: {final_state['final_ticket']}")

if __name__ == "__main__":
    asyncio.run(test_agent())
