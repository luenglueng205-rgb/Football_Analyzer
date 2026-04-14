import asyncio
import time
import random
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from agents.async_base import AsyncBaseAgent
from agents.graph_orchestrator import AsyncStateGraph

# --- 模拟的 2026 版 Agent (异步改造) ---

class AsyncScoutAgent(AsyncBaseAgent):
    def __init__(self):
        super().__init__("scout", "情报侦察兵")
        
    async def process(self, state: dict) -> dict:
        match = state.get("current_match")
        # 模拟调用外部 API 的延迟 (I/O Block)
        await asyncio.sleep(random.uniform(0.5, 1.5))
        print(f"    [Scout] {match['home']} vs {match['away']} 情报收集完成 (耗时极低)")
        return {
            "scout_data": {"injuries": "无重大伤停", "weather": "晴"}
        }

class AsyncAnalystAgent(AsyncBaseAgent):
    def __init__(self):
        super().__init__("analyst", "盘口分析师")
        
    async def process(self, state: dict) -> dict:
        match = state.get("current_match")
        scout_data = state.get("scout_data", {})
        # 模拟进行泊松分布、凯利公式和 LLM 分析 (I/O Block)
        await asyncio.sleep(random.uniform(0.5, 1.0))
        print(f"    [Analyst] {match['home']} vs {match['away']} 泊松分布计算完成 (高置信度)")
        return {
            "analyst_data": {"expected_goals": "2.1 - 0.8", "home_win_prob": 0.65}
        }

class AsyncPortfolioAgent(AsyncBaseAgent):
    def __init__(self):
        super().__init__("portfolio", "投资组合与缩水过滤专家")
        
    async def process(self, state: dict) -> dict:
        matches_results = state.get("matches_results", [])
        print(f"\n[Portfolio] 开始对 {len(matches_results)} 场比赛进行全局资金分配与缩水过滤...")
        await asyncio.sleep(2.0) # 模拟大模型全局分析
        
        # 简单模拟缩水逻辑
        cost = 2 ** 5 * 2 # 模拟复式成本
        print(f"[Portfolio] 过滤缩水完成！原成本: 2048元，优化后实票成本: {cost}元，保留了 98% 的中奖概率。")
        return {
            "portfolio_recommendation": f"建议方案：单挑 9 场正路，双选 4 场，全包 1 场。总成本 {cost} 元。"
        }

# --- 异步图编排逻辑 ---

async def analyze_single_match(match: dict) -> dict:
    """并发执行单场比赛的全套分析流程 (Scout -> Analyst)"""
    scout = AsyncScoutAgent()
    analyst = AsyncAnalystAgent()
    
    state = {"current_match": match}
    
    # 串行执行，但整个函数是异步的，可与其他比赛并发
    state.update(await scout.process(state))
    state.update(await analyst.process(state))
    
    return {
        "match": match,
        "scout": state["scout_data"],
        "analyst": state["analyst_data"]
    }

async def run_14_match_lottery():
    print("="*60)
    print(" 2026 Next-Gen AI - 传统足彩14场 (Graph State 异步并发引擎) ")
    print("="*60)
    
    # 模拟 14 场比赛数据
    matches = [{"id": i, "home": f"主队{i}", "away": f"客队{i}"} for i in range(1, 15)]
    
    # 定义图编排器
    graph = AsyncStateGraph()
    
    async def orchestrator_node(state: dict) -> dict:
        """主调度节点：并发派发 14 场任务"""
        print("[Orchestrator] 瞬间裂变 14 个 Agent 并发执行任务...")
        tasks = [analyze_single_match(match) for match in state["matches"]]
        results = await asyncio.gather(*tasks) # 并发核心
        return {"matches_results": results}
        
    async def portfolio_node(state: dict) -> dict:
        """投资组合节点：接收所有结果并过滤"""
        agent = AsyncPortfolioAgent()
        return await agent.process(state)
        
    # 构建图
    graph.add_node("Orchestrator", orchestrator_node)
    graph.add_node("Portfolio", portfolio_node)
    
    graph.add_edge("Orchestrator", "Portfolio")
    graph.add_edge("Portfolio", "END")
    
    graph.set_entry_point("Orchestrator")
    
    # 初始状态
    initial_state = {"matches": matches}
    
    # 运行图
    final_state = await graph.compile_and_run(initial_state)
    
    print("\n最终输出:")
    print(final_state.get("portfolio_recommendation"))
    
if __name__ == "__main__":
    asyncio.run(run_14_match_lottery())
