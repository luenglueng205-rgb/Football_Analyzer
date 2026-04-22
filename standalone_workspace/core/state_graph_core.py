import asyncio
import json
import logging
from typing import TypedDict, Dict, Any, List, Optional
from tools.global_odds_fetcher import get_global_arbitrage_data
from skills.latency_arbitrage import detect_latency_arbitrage

logger = logging.getLogger(__name__)

# State-of-the-Art Architecture: Reflexion + Actor-Critic + Plan-and-Solve
class AdvancedAgentState(TypedDict):
    match_id: str
    home_team: str
    away_team: str
    plan: List[str]            # 规划步骤
    current_step: str          # 当前执行的步骤
    memory: Dict[str, Any]     # 数据记忆库
    reflections: List[str]     # Critic 产生的反思/报错日志
    status: str                # running, replan, skip, success
    final_ticket: Optional[Dict[str, Any]]

class AdvancedStateGraph:
    """
    独立版 2026 前沿架构：抛弃死板流水线，引入 Planner (规划师)、Actor (执行官)、Critic (风控评论家)
    """
    def __init__(self):
        self.nodes = {}
    
    def add_node(self, name, func):
        self.nodes[name] = func
        
    async def ainvoke(self, state: AdvancedAgentState) -> AdvancedAgentState:
        # 初始进入 Planner
        current_node = "planner"
        max_loops = 10
        loops = 0
        
        while current_node and loops < max_loops:
            loops += 1
            print(f"\n🧠 [Graph Router] 当前节点: {current_node.upper()} | 循环: {loops}")
            state = await self.nodes[current_node](state)
            
            # 动态路由 (Dynamic Routing based on Status)
            if state["status"] == "skip":
                print(f"🛑 [Graph Router] 风控否决，终止对本场比赛的分析。")
                break
            elif state["status"] == "success":
                print(f"✅ [Graph Router] 成功生成套利票。")
                break
            elif state["status"] == "replan":
                current_node = "planner"
            elif state["status"] == "running":
                # 如果 Planner 给了步骤，则去 Actor
                if state["current_step"]:
                    current_node = "actor"
                else:
                    # 如果 Actor 执行完，去 Critic
                    current_node = "critic"
            elif state["status"] == "critique_passed":
                # Critic 审核通过，返回 Planner 取下一步
                state["status"] = "running"
                current_node = "planner"
            else:
                break
                
        return state

# 1. 规划师 (Planner)
async def node_planner(state: AdvancedAgentState) -> AdvancedAgentState:
    """
    任务：基于当前记忆和反思，决定下一步干什么。
    """
    if state["status"] == "replan":
        print(f"   -> 🔄 Planner 接收到反思日志: {state['reflections'][-1]}，正在重新规划...")
        state["plan"] = ["FETCH_ODDS", "CALC_LATENCY", "RISK_CHECK"]
        state["status"] = "running"
    
    if not state.get("plan"):
        print("   -> 📝 Planner 制定初始计划: ['FETCH_ODDS', 'CALC_LATENCY', 'RISK_CHECK']")
        state["plan"] = ["FETCH_ODDS", "CALC_LATENCY", "RISK_CHECK"]
        
    if len(state["plan"]) > 0:
        state["current_step"] = state["plan"].pop(0)
        print(f"   -> 📝 Planner 分发任务: {state['current_step']}")
    else:
        state["current_step"] = ""
        state["status"] = "success" # 计划全部执行完
        
    return state

# 2. 执行官 (Actor)
async def node_actor(state: AdvancedAgentState) -> AdvancedAgentState:
    """
    任务：单纯执行当前分配的 Step，不负责评判对错。
    """
    step = state["current_step"]
    print(f"   -> 🦾 Actor 正在执行任务: {step}")
    
    if step == "FETCH_ODDS":
        odds_data = get_global_arbitrage_data("英超", state["home_team"], state["away_team"])
        state["memory"]["global_odds"] = json.loads(odds_data)
        
    elif step == "CALC_LATENCY":
        odds_data = state["memory"].get("global_odds", {})
        pinnacle = odds_data.get("pinnacle_home_odds")
        if pinnacle:
            jingcai_odds = 1.85  # Mock 竞彩赔率
            res = detect_latency_arbitrage(jingcai_odds, pinnacle)
            state["memory"]["latency_res"] = res
            
    elif step == "RISK_CHECK":
        res = state["memory"].get("latency_res", {})
        if res.get("is_arbitrage"):
            state["memory"]["risk_passed"] = True
        else:
            state["memory"]["risk_passed"] = False

    # 执行完后，必须去 Critic 接受审查
    state["current_step"] = ""
    state["status"] = "running"
    return state

# 3. 风控法官 (Critic / Reflexion)
async def node_critic(state: AdvancedAgentState) -> AdvancedAgentState:
    """
    任务：Actor-Critic 架构中的审查者。对 Actor 的产出进行严格验证。
    """
    print("   -> ⚖️ Critic 正在审查 Actor 的工作成果...")
    
    # 检查是否因为 API 报错导致没有获取到数据
    if "global_odds" in state["memory"] and "error" in state["memory"]["global_odds"]:
        error_msg = state["memory"]["global_odds"]["error"]
        print(f"   -> ❌ Critic 发现错误: {error_msg}")
        state["reflections"].append("API Fetch failed. Cannot proceed with latency check.")
        state["status"] = "skip" # 严重错误，直接掐断
        return state
        
    # 检查风控结果
    if "risk_passed" in state["memory"]:
        if not state["memory"]["risk_passed"]:
            print("   -> ❌ Critic 审查不通过: 未发现套利空间 (EV<0 或被诱盘)。")
            state["reflections"].append("Risk Check Failed. No arbitrage found.")
            state["status"] = "skip"
        else:
            print("   -> ✅ Critic 审查通过: 套利空间真实存在！")
            state["final_ticket"] = {"match": state["match_id"], "action": "BUY_HOME", "confidence": "HIGH"}
            state["status"] = "critique_passed"
        return state
        
    # 默认通过当前步骤，回传给 Planner 取下一步
    print("   -> ✅ Critic 审查通过，允许继续执行计划。")
    state["status"] = "critique_passed"
    return state

def compile_advanced_football_graph():
    graph = AdvancedStateGraph()
    graph.add_node("planner", node_planner)
    graph.add_node("actor", node_actor)
    graph.add_node("critic", node_critic)
    return graph
