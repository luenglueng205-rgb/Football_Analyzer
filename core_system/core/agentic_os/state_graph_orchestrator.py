from typing import Annotated, TypedDict, List, Dict, Any, Literal
import operator
import json
import os
import time
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
from core_system.tools.betting_ledger import BettingLedger
from core_system.skills.news_arbitrage.social_listener import SocialNewsListener

# ==========================================
# 1. 定义工具 (LangChain @tool 配合 MCP 概念)
# ==========================================
math_engine = HardcoreQuantMath()
guard = HallucinationGuard()
router = GrandmasterRouter()
hippo_memory = HippocampusMemory()
ledger = BettingLedger()
news_listener = SocialNewsListener(use_mock=True)

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
def check_balance() -> dict:
    """检查Agent当前的资金余额和下注历史。在做出出票决策前可以调用此工具确认资金是否充足。"""
    return ledger.check_bankroll(agent_id="agentic_os")

@tool
def execute_ticket_route(home_prob: float, official_odds: float, stake: float) -> str:
    """将验证通过的赛事交由顶级指挥官进行实盘出票路由，并从账本中扣除本金。必须传入决定的下注金额 stake。"""
    # 1. 先进行账本扣款
    bet_result = ledger.execute_bet(
        agent_id="agentic_os",
        match_id=f"MATCH_{int(time.time())}", # 模拟一个比赛ID
        lottery_type="jingcai",
        selection="home_win",
        odds=official_odds,
        stake=stake
    )
    
    if bet_result.get("status") == "error":
        return f"[ROUTE_REJECTED] 出票失败: {bet_result.get('message')}。请检查资金余额或降低下注金额。"
        
    # 2. 扣款成功后，进行物理路由分发
    dispatch_msg = router.dispatch_matches({}, {"home_win": home_prob}, {"jingcai_odds": {"home_win": official_odds}})
    
    return f"【账本扣款成功】凭证: {bet_result.get('ticket_code')} | 余额剩余: ${bet_result.get('remaining_balance', 0):.2f}\n【路由结果】: {dispatch_msg}"

@tool
def execute_quant_script(code: str) -> dict:
    """在隔离的沙箱环境中执行 Python 量化回测或数据分析代码。支持 pandas, scikit-learn, numpy。遇到不确定的数学计算时可以使用此工具进行自证。"""
    from core_system.skills.code_interpreter.server import execute_quant_script as run_code
    return run_code(code)

@tool
def fetch_arbitrage_news(team_name: str) -> dict:
    """毫秒级新闻套利监听器：获取球队最新突发新闻（如伤停、内幕）。用于在庄家变盘前捕捉信息差并调整 xG 预期。"""
    return news_listener.fetch_latest_news(team_name)

tools = [calculate_true_probs, verify_risk, check_balance, execute_ticket_route, fetch_arbitrage_news, execute_quant_script]
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
    is_high_value: bool # 是否为高价值赛事 (触发 MCTS)
    debate_done: bool # 标记是否已经完成多空辩论，防止死循环

# ==========================================
# 3. 配置真实的大模型 (Real LLM) - 通过 .env 配置
# ==========================================
def get_base_llm():
    """获取无工具绑定的基础大模型，用于 MCTS 纯逻辑推演"""
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE")
    model_name = os.getenv("MODEL_NAME", "gpt-4o")
    
    client_kwargs = {"api_key": api_key, "model": model_name, "temperature": 0.7} # MCTS需要更高的温度来产生发散性剧本
    if base_url:
        client_kwargs["base_url"] = base_url
        
    return ChatOpenAI(**client_kwargs)

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
def sentinel_node(state: BettingState):
    """哨兵节点：动态评估赛事复杂度与算力分配 (Test-Time Compute)"""
    print("   -> 👁️ [Sentinel] 哨兵节点：正在评估赛事复杂度与算力分配...")
    context = state.get("match_context", "")
    odds = state.get("official_odds", 0)
    
    # 启发式评估：如果赔率较高或包含高不确定性关键词（如伤停、暴雨），分配重度算力
    if "伤停" in context or "缺阵" in context or "暴雨" in context or odds > 1.9:
        print(f"   -> ⚠️ [Sentinel] 发现高价值/高复杂度赛事 (Odds: {odds})，重定向至 MCTS 狂暴模式！")
        return {"is_high_value": True}
    else:
        print(f"   -> ⚡ [Sentinel] 常规赛事 (Odds: {odds})，采用 Fast-Path 极速分析。")
        return {"is_high_value": False}

def mcts_deep_think_node(state: BettingState):
    """算力折叠：MCTS 多分支潜空间推演节点"""
    print("   -> 🌳 [MCTS Expand] 算力折叠：正在裂变 3 条平行宇宙赛果线...")
    llm = get_base_llm()
    
    prompt = (
        f"你是一个基于蒙特卡洛树搜索(MCTS)的战术推演引擎。\n"
        f"请基于以下情报，推演这3种最可能发生的比赛剧本（字数简短精炼）：\n"
        f"1. 剧本A（主队早早破门，顺风局）\n"
        f"2. 剧本B（客队偷袭得手或主队红牌，逆风局）\n"
        f"3. 剧本C（沉闷的战术对耗，胶着局）\n"
        f"\n情报：{state['match_context']}\n"
        f"赔率：主胜 {state['official_odds']}\n"
        f"\n最后，结合这3个分支，评估当前主胜赔率的【抗脆弱性评分(0-100)】，并给出综合建议。"
    )
    
    response = llm.invoke([HumanMessage(content=prompt)])
    print("   -> ⚖️ [MCTS Evaluate & Backprop] 价值网络评估完毕，多分支共识已收敛。")
    
    consensus_msg = SystemMessage(
        content=f"【MCTS 深度推演共识】\n{response.content}\n"
                f"请基于上述 MCTS 多步推演的结论，结合你的自身性格，进行最终的概率计算、风控验证与出票决策。"
    )
    
    return {"messages": [consensus_msg]}

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
    """大脑节点：混合智能体辩论 (Mixture-of-Agents Debate) 及最终裁决"""
    print("   -> 🧠 [MoA Judge] 红蓝军法官正在进行最终的分析与工具调度...")
    
    # 1. 触发红蓝军对抗机制 (如果处于 MCTS 高价值模式下)
    # 这里通过 Prompt 内部化实现简单的多空博弈，避免图结构膨胀导致断层
    if state.get("is_high_value") and not state.get("debate_done", False):
        print("   -> 🔴🔵 [MoA Debate] 触发红蓝军对抗，提取极端多空观点...")
        base_llm = get_base_llm()
        context_msg = state["messages"][-1]
        
        try:
            # Bull (多头)
            bull_prompt = SystemMessage(content="你是极端多头分析师。请只看利好，忽略风险，给我3个必须下注主队的绝对理由。")
            bull_res = base_llm.invoke([bull_prompt, context_msg])
            
            # Bear (空头)
            bear_prompt = SystemMessage(content="你是极端空头风控官。请只看利空，挑刺找茬，给我3个绝对不能下注主队的致命隐患。")
            bear_res = base_llm.invoke([bear_prompt, context_msg])
            
            debate_summary = (
                f"【🔴 多头观点 (Bull)】\n{bull_res.content}\n\n"
                f"【🔵 空头观点 (Bear)】\n{bear_res.content}\n\n"
                f"请作为大法官 (Judge)，综合以上双方观点，结合你的工具库进行最后验证（风控、资金）并决定是否出票。"
            )
            state["messages"].append(SystemMessage(content=debate_summary))
            # 标记辩论已完成，防止在下一次工具返回后死循环辩论
            state["debate_done"] = True
            
        except Exception as e:
            print(f"   -> ⚠️ [MoA Debate] 辩论节点 API 异常，降级回退至单体决策: {e}")

    # 2. 最终裁决 (绑定了 Tools 的主 LLM)
    llm = get_llm()
    response = llm.invoke(state["messages"])
    
    return {"messages": [response], "debate_done": state.get("debate_done", False)}

def tool_executor_node(state: BettingState):
    """四肢节点：通用工具执行器 (完全接管所有的 tool_calls)"""
    last_msg = state["messages"][-1]
    results = []
    state_updates = {}
    
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
            state_updates["true_probs"] = output
        elif tool_call["name"] == "verify_risk":
            state_updates["risk_status"] = output["status"]
            state_updates["verified_ev"] = output.get("verified_ev", 0.0)
        elif tool_call["name"] == "execute_ticket_route":
            state_updates["execution_route"] = output
            
    return {"messages": results, **state_updates}

# ==========================================
# 5. 定义条件路由边 (Conditional Edge) - 控制反转核心
# ==========================================
def route_after_sentinel(state: BettingState) -> Literal["mcts", "oracle"]:
    """哨兵节点的条件路由：决定是否进入 MCTS 狂暴模式"""
    if state.get("is_high_value"):
        return "mcts"
    return "oracle"

def should_continue(state: BettingState) -> Literal["tools", "end"]:
    """判断大模型是否发起了工具调用"""
    last_msg = state["messages"][-1]
    
    # 强制防死循环阻断：只要历史中成功执行过出票工具，必须强制结束图流转
    for msg in reversed(state["messages"]):
        if getattr(msg, "name", None) == "execute_ticket_route":
            return "end"

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
    workflow.add_node("sentinel", sentinel_node)
    workflow.add_node("mcts", mcts_deep_think_node)
    workflow.add_node("oracle", llm_oracle_node)
    workflow.add_node("tools", tool_executor_node)
    
    workflow.add_edge(START, "memory")
    workflow.add_edge("memory", "sentinel")
    workflow.add_conditional_edges("sentinel", route_after_sentinel, {"mcts": "mcts", "oracle": "oracle"})
    workflow.add_edge("mcts", "oracle")
    
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
    
    for output in app.stream(initial_state, {"recursion_limit": 30}):
        pass

if __name__ == "__main__":
    build_and_run_graph()
