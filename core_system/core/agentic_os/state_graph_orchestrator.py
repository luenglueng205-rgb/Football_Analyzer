from typing import Annotated, TypedDict, List, Dict, Any, Literal
import operator
import json
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END, START
from langchain_core.tools import tool

# 引入我们写好的硬核本地工具
from core_system.skills.hardcore_quant_math import HardcoreQuantMath
from core_system.skills.chinese_lottery_official_calc import ChineseLotteryOfficialCalculator
from core_system.core.grandmaster_router import GrandmasterRouter
from core_system.core.agentic_os.hallucination_guard import HallucinationGuard
from core_system.core.agentic_os.mcp_tool_discoverer import MCPToolDiscoverer

# ==========================================
# 1. 定义工具 (LangChain @tool 配合 MCP 概念)
# ==========================================
math_engine = HardcoreQuantMath()
guard = HallucinationGuard()
router = GrandmasterRouter()

@tool
def calculate_true_probs(home_xg: float, away_xg: float) -> dict:
    """计算两队的泊松分布真实胜平负概率。"""
    return math_engine.bivariate_poisson_match_simulation(home_xg, away_xg)

@tool
def verify_risk(proposed_stake_percent: float, home_prob: float, official_odds: float) -> dict:
    """风控防火墙，验证大模型的投注建议是否符合期望值(EV)要求。"""
    mock_llm_proposal = {"predicted_win_prob": home_prob, "confidence_score": 0.8, "reasoning_hash": "0x1"}
    return guard.verify_llm_output(mock_llm_proposal, official_odds)

@tool
def execute_ticket_route(home_prob: float, official_odds: float) -> str:
    """将验证通过的赛事交由顶级指挥官进行实盘出票路由。"""
    return router.dispatch_matches({}, {"home_win": home_prob}, {"jingcai_odds": {"home_win": official_odds}})

tools = [calculate_true_probs, verify_risk, execute_ticket_route]
tool_map = {t.name: t for t in tools}

# ==========================================
# 2. 定义全局状态 (The Stateful Memory)
# ==========================================
class BettingState(TypedDict):
    messages: Annotated[list, operator.add]
    match_context: str
    true_probs: Dict[str, float]
    official_odds: float
    proposed_stake: float
    verified_ev: float
    risk_status: str # "PENDING", "APPROVED", "REJECTED"
    execution_route: str

# ==========================================
# 3. 定义模拟的真实大模型 (DevMockLLM) - 开发阶段免 API Key
# ==========================================
class DevMockLLM:
    """开发阶段使用的 Mock 大模型，完全模拟 OpenAI/Anthropic Tool Calling 返回格式"""
    def __init__(self):
        self.step = 0

    def invoke(self, messages: list) -> AIMessage:
        print("   -> 🧠 [Oracle LLM] 大模型思考中 (Dev Mock 零成本模式)...")
        self.step += 1
        
        # 步骤 1：大模型观察到消息，决定调用泊松计算工具
        if self.step == 1:
            print("      💡 [LLM Thought] 发现比赛情报，我需要挂载 MCP 的计算胜负概率工具。")
            return AIMessage(
                content="", 
                tool_calls=[{
                    "name": "calculate_true_probs", 
                    "args": {"home_xg": 1.5, "away_xg": 1.2}, 
                    "id": "call_math_1"
                }]
            )
        # 步骤 2：大模型收到了计算结果，决定调用风控工具
        elif self.step == 2:
            print("      💡 [LLM Thought] 概率已算完，申请进行风控审查。")
            return AIMessage(
                content="", 
                tool_calls=[{
                    "name": "verify_risk", 
                    "args": {"proposed_stake_percent": 0.05, "home_prob": 0.45, "official_odds": 2.10}, 
                    "id": "call_risk_2"
                }]
            )
        # 步骤 3：大模型收到了风控通过的结果，决定调用路由工具出票
        elif self.step == 3:
            print("      💡 [LLM Thought] 风控审核通过！呼叫出票路由指挥官执行。")
            return AIMessage(
                content="", 
                tool_calls=[{
                    "name": "execute_ticket_route", 
                    "args": {"home_prob": 0.45, "official_odds": 2.10}, 
                    "id": "call_route_3"
                }]
            )
        # 步骤 4：所有工具执行完毕，输出最终总结，跳出循环
        else:
            print("      💡 [LLM Thought] 所有工作完成，我将输出最终分析报告。")
            return AIMessage(content="分析完毕。阿森纳今晚胜算可观，风控通过，MCP 工具链调用闭环已完成。")

mock_llm = DevMockLLM()

# ==========================================
# 4. 定义节点 (Nodes)
# ==========================================
def llm_oracle_node(state: BettingState):
    """大脑节点：负责产生带有 tool_calls 的 AIMessage"""
    response = mock_llm.invoke(state["messages"])
    return {"messages": [response]}

def tool_executor_node(state: BettingState):
    """四肢节点：通用工具执行器 (完全接管所有的 tool_calls)"""
    last_msg = state["messages"][-1]
    results = []
    
    # 遍历 LLM 指定要调用的所有工具
    for tool_call in last_msg.tool_calls:
        print(f"   -> 🔧 [Tool Executor] 正在执行 MCP 挂载工具: 【{tool_call['name']}】")
        tool_func = tool_map[tool_call["name"]]
        output = tool_func.invoke(tool_call["args"])
        
        # 将工具的输出封装为标准的 ToolMessage，供大模型下一步阅读
        results.append(ToolMessage(
            content=str(output), 
            name=tool_call["name"], 
            tool_call_id=tool_call["id"]
        ))
        
        # 业务字段状态更新（可选，为了让前端UI更容易读取状态）
        if tool_call["name"] == "calculate_true_probs":
            return {"messages": results, "true_probs": output}
        if tool_call["name"] == "verify_risk":
            return {"messages": results, "risk_status": output["status"], "verified_ev": output.get("verified_ev", 0.0)}
        if tool_call["name"] == "execute_ticket_route":
            return {"messages": results, "execution_route": output}
            
    return {"messages": results}

# ==========================================
# 5. 定义条件路由边 (Conditional Edge) - 控制反转核心
# ==========================================
def should_continue(state: BettingState) -> Literal["tools", "end"]:
    """判断大模型是否发起了工具调用"""
    last_msg = state["messages"][-1]
    # 如果 LLM 的回复里包含 tool_calls，则流向 "tools" 节点
    if getattr(last_msg, "tool_calls", None):
        return "tools"
    # 否则直接走向终点
    return "end"

# ==========================================
# 6. 编译与运行图 (Compile Graph)
# ==========================================
def build_and_run_graph():
    print("==================================================")
    print("🌐 [Agentic OS] 启动基于真实 Tool Calling 的 MCP 架构图")
    print("==================================================")
    
    # 模拟启动时动态发现 MCP 工具并挂载到大模型
    mcp = MCPToolDiscoverer()
    mcp.discover_tools()
    
    workflow = StateGraph(BettingState)
    
    # 我们现在只有两个核心节点了：大脑(Oracle) 和 肢体(Tools)
    workflow.add_node("oracle", llm_oracle_node)
    workflow.add_node("tools", tool_executor_node)
    
    # 定义控制流
    workflow.add_edge(START, "oracle")
    workflow.add_conditional_edges("oracle", should_continue, {"tools": "tools", "end": END})
    workflow.add_edge("tools", "oracle")  # 工具执行完必须返回大脑复盘
    
    app = workflow.compile()
    
    initial_state = {
        "messages": [HumanMessage(content="新情报：阿森纳今晚主力全出。竞彩主胜赔率 2.10。")],
        "match_context": "Arsenal Full Squad",
        "official_odds": 2.10,
        "risk_status": "PENDING",
        "true_probs": {}
    }
    
    for output in app.stream(initial_state, {"recursion_limit": 10}):
        pass

if __name__ == "__main__":
    build_and_run_graph()
