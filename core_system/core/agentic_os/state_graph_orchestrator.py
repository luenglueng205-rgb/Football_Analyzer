from typing import Annotated, TypedDict, List, Dict, Any, Literal
import operator
import json
import os
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END, START
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

# 加载环境变量
load_dotenv()

# 引入我们写好的硬核本地工具
from core_system.tools.math.hardcore_quant_math import HardcoreQuantMath
from core_system.tools.math.chinese_lottery_official_calc import ChineseLotteryOfficialCalculator
from core_system.agents.grandmaster_router import GrandmasterRouter
from core_system.core.agentic_os.hallucination_guard import HallucinationGuard
from core_system.tools.mcp_discoverer import MCPToolDiscoverer
from core_system.core.agentic_os.hippocampus import HippocampusMemory

# ==========================================
# 1. 定义工具 (LangChain @tool 配合 MCP 概念)
# ==========================================
math_engine = HardcoreQuantMath()
guard = HallucinationGuard()
router = GrandmasterRouter()
hippo_memory = HippocampusMemory()

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
    risk_tolerance: float  # 从海马体读取的全局风险容忍度
    historical_lessons: str # 从海马体召回的相似赛事教训

# ==========================================
# 3. 配置真实的大模型 (Real LLM) - 通过 .env 配置
# ==========================================
def get_llm():
    """获取通过环境变量配置的真实大模型，并绑定硬核工具"""
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model_name = os.getenv("MODEL_NAME", "gpt-4o")
    
    if not api_key:
        print("   -> ⚠️ [警告] 未配置 OPENAI_API_KEY！系统将退回演示模式，但由于移除了 Mock，可能会抛出异常。")
        print("   -> 💡 [提示] 请在项目根目录创建 .env 文件，并填入 OPENAI_API_KEY。")
        
    llm = ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model_name,
        temperature=0.0 # 体育投资要求绝对理性和确定性，Temperature设为0
    )
    
    # 彻底实现控制反转：将本地 Python 函数作为 Tools 绑定给大模型
    return llm.bind_tools(tools)

# ==========================================
# 4. 定义节点 (Nodes)
# ==========================================
def memory_retrieval_node(state: BettingState):
    """前置节点：在 LLM 决策前，向海马体查询相关教训"""
    print("   -> 🧠 [Memory] 正在检索海马体中的历史教训...")
    
    try:
        with open(hippo_memory.semantic_memory_file, "r", encoding="utf-8") as f:
            semantic_data = json.load(f)
            risk_tolerance = semantic_data.get("risk_tolerance", 0.05)
            truths = semantic_data.get("truths", [])
    except Exception as e:
        risk_tolerance = 0.05
        truths = []
        
    system_msg = SystemMessage(
        content=f"【数字生命系统指令】:\n"
                f"你目前的全局风险容忍度被海马体限制为: {risk_tolerance}。\n"
                f"这是你从过去的亏损中提炼出的绝对真理（如有）：{', '.join(truths[-3:])}\n"
                f"在接下来的分析中，如果比赛特征命中了上述真理，必须直接拒绝交易！"
    )
    
    # 动态插入记忆提示词，且确保它紧跟在角色的 SystemMessage 后面
    if state["messages"] and isinstance(state["messages"][0], SystemMessage):
        # 如果已经有了外部的角色设定（如压测脚本传入的），将记忆补在第二位
        state["messages"].insert(1, system_msg)
    else:
        state["messages"].insert(0, system_msg)
        
    return {"risk_tolerance": risk_tolerance, "historical_lessons": str(truths)}

def llm_oracle_node(state: BettingState):
    """大脑节点：负责产生带有 tool_calls 的 AIMessage"""
    print("   -> 🧠 [Oracle LLM] 真实大模型正在思考和决策...")
    llm = get_llm()
    # 提取最新的上下文传递给 LLM
    response = llm.invoke(state["messages"])
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
def compile_agentic_graph():
    """编译并返回无状态的图对象，支持外部传入不同的初始状态(实现 Swarm 裂变)"""
    mcp = MCPToolDiscoverer()
    try:
        mcp.discover_local_tools()
    except AttributeError:
        pass # Handle case where mcp_discoverer changed API
    
    workflow = StateGraph(BettingState)
    
    workflow.add_node("memory", memory_retrieval_node)
    workflow.add_node("oracle", llm_oracle_node)
    workflow.add_node("tools", tool_executor_node)
    
    workflow.add_edge(START, "memory")
    workflow.add_edge("memory", "oracle")
    workflow.add_conditional_edges("oracle", should_continue, {"tools": "tools", "end": END})
    workflow.add_edge("tools", "oracle")
    
    return workflow.compile()

def build_and_run_graph():
    print("==================================================")
    print("🌐 [Agentic OS] 启动基于真实 Tool Calling 的 MCP 架构图")
    print("==================================================")
    
    app = compile_agentic_graph()
    
    initial_state = {
        "messages": [
            SystemMessage(content="你是AI原生量化足球分析系统的核心大脑。你必须遵循：\n1. 调用 calculate_true_probs 计算概率。\n2. 调用 verify_risk 进行风控验证。\n3. 风控通过后调用 execute_ticket_route 出票。\n绝对不要自行编造赔率或概率！"),
            HumanMessage(content="新情报：阿森纳今晚主力全出。竞彩主胜赔率 2.10。")
        ],
        "match_context": "Arsenal Full Squad",
        "official_odds": 2.10,
        "risk_status": "PENDING",
        "true_probs": {}
    }
    
    for output in app.stream(initial_state, {"recursion_limit": 10}):
        pass

if __name__ == "__main__":
    build_and_run_graph()
