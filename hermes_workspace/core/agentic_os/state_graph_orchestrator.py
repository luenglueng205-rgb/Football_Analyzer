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
from hermes_workspace.tools.math.hardcore_quant_math import HardcoreQuantMath
from hermes_workspace.tools.math.chinese_lottery_official_calc import ChineseLotteryOfficialCalculator
from hermes_workspace.agents.grandmaster_router import GrandmasterRouter
from hermes_workspace.core.agentic_os.hallucination_guard import HallucinationGuard
from hermes_workspace.tools.mcp_discoverer import MCPToolDiscoverer
from hermes_workspace.core.agentic_os.hippocampus import HippocampusMemory
from hermes_workspace.tools.betting_ledger import BettingLedger
from hermes_workspace.skills.news_arbitrage.social_listener import SocialNewsListener
from hermes_workspace.skills.spatial_world_model.gwm_engine import GenerativeWorldModel
from hermes_workspace.tools.environment_analyzer import EnvironmentAnalyzer

# ==========================================
# 1. 定义工具 (LangChain @tool 配合 MCP 概念)
# ==========================================
math_engine = HardcoreQuantMath()
guard = HallucinationGuard()
router = GrandmasterRouter()
hippo_memory = HippocampusMemory()
ledger = BettingLedger()
news_listener = SocialNewsListener()

@tool
def calculate_true_probs_for_all_markets(home_xg: float, away_xg: float) -> dict:
    """
    计算两队的泊松分布概率，并映射为竞彩、北单的 16 种玩法全景概率矩阵。
    返回的字典包含 'home_win', 'draw', 'away_win'，以及 'cs' (比分), 'goals' (总进球) 和 'beidan_sxds' (上下单双) 等细分市场的精确概率。
    """
    from hermes_workspace.tools.math.advanced_lottery_math import AdvancedLotteryMath
    # 1. 基础矩阵与 WDL
    base_probs = math_engine.bivariate_poisson_match_simulation(home_xg, away_xg)
    
    # 2. 调取刚升级的 AdvancedLotteryMath 进行 10x10 矩阵的高阶映射
    adv_math = AdvancedLotteryMath()
    matrix_res = adv_math.dixon_coles_poisson_adjustment(home_xg, away_xg)
    matrix = matrix_res["matrix"]
    
    # 3. 映射到竞彩比分 (CS)
    cs_probs = adv_math.map_poisson_to_jingcai_scores(matrix)
    
    # 4. 映射到北单上下单双 (SXDS)
    sxds_probs = adv_math.calculate_beidan_sxds_matrix(matrix)
    
    return {
        "WDL": {"home_win": base_probs.get("home_win", 0.0), "draw": base_probs.get("draw", 0.0), "away_win": base_probs.get("away_win", 0.0)},
        "CS": cs_probs,
        "BEIDAN_SXDS": sxds_probs
    }

@tool
def verify_risk(lottery_type: str, play_type: str, proposed_stake_percent: float, true_prob: float, official_odds: float) -> dict:
    """
    风控防火墙：验证大模型的投注建议是否符合特定彩种(如竞彩/北单/足彩)的期望值(EV)要求。
    - lottery_type: 'jingcai' / 'beidan' / 'zucai'
    - play_type: 如 'CS', 'SXDS', 'WDL'
    - true_prob: 选定选项的真实胜率
    - official_odds: 庄家赔率
    系统会自动根据彩种扣除抽水(如北单的65%)，验证是否满足 EV 阈值。
    """
    from hermes_workspace.tools.smart_bet_selector import SmartBetSelector
    selector = SmartBetSelector()
    
    # 构造伪数据给底层过滤引擎
    mock_data = {
        "match_id": "TEST",
        "home_team": "H",
        "away_team": "A",
        f"{lottery_type}_odds": {f"{play_type}_selection": official_odds}
    }
    
    # 修复：传统足彩（ZUCAI）没有赔率，跳过 EV 计算，直接使用 Edge
    if lottery_type.upper() == "ZUCAI":
        # 假设大众支持率 public_prob 为一个保守的平均值，这里简化处理：只要真实胜率大于 30% 且足彩玩法即通过
        # 实际生产中应从 mock_data 或 API 传入 public_prob 进行 `calculate_zucai_value_index` 计算
        if true_prob >= 0.30:
            return {"status": "APPROVED", "verified_ev": 0.0, "message": f"{lottery_type.upper()} {play_type} 真实胜率={true_prob:.3f}。足彩防冷通过！可以出票。"}
        else:
            return {"status": "REJECTED", "verified_ev": 0.0, "message": f"{lottery_type.upper()} {play_type} 真实胜率={true_prob:.3f}。胜率过低，拒绝出票！"}
            
    # 提取 EV
    ev = true_prob * official_odds
    if lottery_type.upper() == "BEIDAN":
        ev = ev * 0.65 # 北单抽水
        
    if ev >= 1.05:
        return {"status": "APPROVED", "verified_ev": ev, "message": f"{lottery_type.upper()} {play_type} EV={ev:.3f} 满足阈值！可以出票。"}
    else:
        return {"status": "REJECTED", "verified_ev": ev, "message": f"{lottery_type.upper()} {play_type} EV={ev:.3f} < 1.05。期望值为负，拒绝出票！"}

@tool
def check_balance() -> dict:
    """检查Agent当前的资金余额和下注历史。在做出出票决策前可以调用此工具确认资金是否充足。"""
    return ledger.check_bankroll(agent_id="agentic_os")

@tool
def execute_ticket_route(lottery_type: str, play_type: str, selection: str, odds: float, stake: float) -> str:
    """
    【核心出票网关】将决策交由顶级指挥官进行实盘出票路由，并从账本中扣除本金。
    必须传入: 
    - lottery_type: 'jingcai', 'beidan', 或 'zucai'
    - play_type: 玩法(如 'WDL', 'HANDICAP', 'CS', 'GOALS', 'SFGG' 等)
    - selection: 选项(如 'home_win', '2:1', '上单' 等)
    - odds: 赔率 (足彩传 0.0)
    - stake: 下注金额
    """
    # 1. 先进行账本扣款
    bet_result = ledger.execute_bet(
        agent_id="agentic_os",
        match_id=f"MATCH_{int(time.time())}", 
        lottery_type=lottery_type,
        selection=f"{play_type}_{selection}",
        odds=odds,
        stake=stake
    )
    
    if bet_result.get("status") == "error":
        return f"[ROUTE_REJECTED] 出票失败: {bet_result.get('message')}。请检查资金余额或降低下注金额。"
        
    # 2. 扣款成功后，进行物理路由分发 (模拟)
    # Ensure official_odds structure satisfies grandmaster_router expectations
    odds_struct = {
        "jingcai_odds": {f"{play_type}_{selection}": odds} if lottery_type == "jingcai" else {},
        "beidan_odds": {f"{play_type}_{selection}": odds} if lottery_type == "beidan" else {}
    }
    dispatch_msg = router.dispatch_matches(
        {}, 
        {f"{play_type}_{selection}": 0.99}, 
        odds_struct
    )
    
    return f"【{lottery_type.upper()} {play_type} 账本扣款成功】凭证: {bet_result.get('ticket_code')} | 余额: ${bet_result.get('remaining_balance', 0):.2f}\n【路由】: {dispatch_msg}"

@tool
def execute_quant_script(code: str) -> dict:
    """在隔离的沙箱环境中执行 Python 量化回测或数据分析代码。支持 pandas, scikit-learn, numpy。遇到不确定的数学计算时可以使用此工具进行自证。"""
    from hermes_workspace.skills.code_interpreter.server import execute_quant_script as run_code
    return run_code(code)

@tool
def fetch_arbitrage_news(team_name: str) -> dict:
    """毫秒级新闻套利监听器：获取球队最新突发新闻（如伤停、内幕）。用于在庄家变盘前捕捉信息差并调整 xG 预期。"""
    return news_listener.fetch_latest_news(team_name)

@tool
def simulate_latent_tactics(match_id: str, home_formation: str = "4-3-3", away_formation: str = "4-2-3-1") -> dict:
    """
    [GWM 顶级硬核工具] 调用生成式世界模型 (Generative World Model) 和时空图神经网络 (ST-GNN)。
    摄取球场上 22 名球员的光学追踪坐标，计算防线高度、阵型紧凑度等高阶战术几何指标，
    并在潜空间中推演下半场 15 分钟的战术走势和 xG 动量。
    适用于高价值比赛的走地盘 (In-Play) 深度推演。
    """
    from hermes_workspace.skills.spatial_world_model.gwm_engine import GenerativeWorldModel
    gwm = GenerativeWorldModel()
    return gwm.rollout_next_15_mins(match_id, home_formation, away_formation)

@tool
def fetch_match_environment(city: str, referee_strictness: str = "medium") -> dict:
    """
    获取比赛的环境因素（天气、裁判尺度）对预期进球数(xG)的量化影响。
    必须在计算泊松概率前调用此工具，以获取 xG 的修正系数。
    """
    analyzer = EnvironmentAnalyzer()
    # Mocking real weather fetching based on city for demonstration
    mock_weather = "heavy_rain" if "Manchester" in city else "clear"
    impact = analyzer.analyze_unstructured_factors(weather=mock_weather, referee_strictness=referee_strictness)
    return {
        "weather": mock_weather,
        "referee": referee_strictness,
        "xg_modifier": impact
    }

tools = [calculate_true_probs_for_all_markets, verify_risk, check_balance, execute_ticket_route, fetch_arbitrage_news, execute_quant_script, simulate_latent_tactics, fetch_match_environment]
tool_map = {t.name: t for t in tools}

# ==========================================
# 2. 定义全局状态 (The Stateful Memory)
# ==========================================
class BettingState(TypedDict):
    messages: Annotated[list, operator.add]
    match_context: str
    true_probs: Dict[str, Any]
    all_markets_probs: Dict[str, Any]
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
    
    # 彻底移除硬编码字符串匹配，引入轻量级 LLM 进行语义分类
    llm = get_base_llm()
    prompt = (
        f"你是一个专业的体育赛事复杂度评估器。请阅读以下比赛情报和主胜赔率，判断该比赛的混沌程度（如：突发伤停、极端天气、实力悬殊、赔率异常等）。\n"
        f"情报: {context}\n"
        f"主胜赔率: {odds}\n\n"
        f"如果比赛具有高不确定性或高博弈价值，请只输出 'HIGH'，否则输出 'LOW'。无需其他解释。"
    )
    
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        decision = response.content.strip().upper()
        if "HIGH" in decision:
            print(f"   -> ⚠️ [Sentinel] AI 语义评估为高价值/高复杂度赛事，重定向至 MCTS 狂暴模式！")
            return {"is_high_value": True}
        else:
            print(f"   -> ⚡ [Sentinel] AI 语义评估为常规赛事，采用 Fast-Path 极速分析。")
            return {"is_high_value": False}
    except Exception as e:
        # 降级兜底方案
        if odds > 1.9:
            return {"is_high_value": True}
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
    if state.get("is_high_value") and not state.get("debate_done", False):
        print("   -> 🔴🔵 [MoA Debate] 触发红蓝军对抗，由主控AI动态生成辩论议题...")
        base_llm = get_base_llm()
        context_msg = state["messages"][-1]
        
        try:
            # 1.1 动态生成争议点 (Dynamic Topic Generation)
            topic_prompt = SystemMessage(
                content="根据当前所有的比赛情报、MCTS推演和赔率，提炼出这场比赛【最大、最致命的博弈争议点】"
                        "（例如：某核心缺阵到底影响多大？主队能否击破铁桶阵？本场是否会有大球？）。"
                        "请用一句简短、尖锐的问句描述这个争议点。"
            )
            topic_res = base_llm.invoke([topic_prompt, context_msg])
            debate_topic = topic_res.content.strip()
            print(f"   -> 🎯 [MoA Topic] 动态辩论焦点: {debate_topic}")
            
            # 1.2 正方 (Bull)
            bull_prompt = SystemMessage(
                content=f"你是正方辩手。请针对以下争议点：【{debate_topic}】，给出3个强有力的正向论据（偏向进球多、强队赢、或者顺风局）。"
                        f"只看利好，忽略风险，措辞要极具煽动性。"
            )
            bull_res = base_llm.invoke([bull_prompt, context_msg])
            
            # 1.3 反方 (Bear)
            bear_prompt = SystemMessage(
                content=f"你是反方辩手。请针对以下争议点：【{debate_topic}】，挑刺找茬，给出3个绝对致命的反向论据（偏向进球少、爆冷、或者逆风局）。"
                        f"只看利空，揭露陷阱，措辞要极其冷酷。"
            )
            bear_res = base_llm.invoke([bear_prompt, context_msg])
            
            debate_summary = (
                f"【🎯 动态辩论焦点】\n{debate_topic}\n\n"
                f"【🔴 正方观点 (Bull)】\n{bull_res.content}\n\n"
                f"【🔵 反方观点 (Bear)】\n{bear_res.content}\n\n"
                f"请作为大法官 (Judge)，综合以上双方针对核心矛盾点的辩论，结合你的工具库进行最后验证（风控、资金）并决定最终的投注策略。"
            )
            state["messages"].append(SystemMessage(content=debate_summary))
            # 标记辩论已完成，防止在下一次工具返回后死循环辩论
            state["debate_done"] = True
            
        except Exception as e:
            print(f"   -> ⚠️ [MoA Debate] 辩论节点 API 异常，降级回退至单体决策: {e}")
            state["debate_done"] = True

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
        if tool_call["name"] == "calculate_true_probs_for_all_markets":
            if isinstance(output, str):
                try:
                    output_dict = json.loads(output.replace("'", '"'))
                except Exception:
                    output_dict = {}
            else:
                output_dict = output if isinstance(output, dict) else {}
                
            wdl_probs = output_dict.get("WDL", {}) if isinstance(output_dict, dict) else {}
            state_updates["true_probs"] = wdl_probs if isinstance(wdl_probs, dict) else {}
            if "home_win" not in state_updates["true_probs"]:
                state_updates["true_probs"]["home_win"] = 0.0
            state_updates["all_markets_probs"] = output_dict
        elif tool_call["name"] == "verify_risk":
            state_updates["risk_status"] = output.get("status", "REJECTED") if isinstance(output, dict) else "REJECTED"
            state_updates["verified_ev"] = output.get("verified_ev", 0.0) if isinstance(output, dict) else 0.0
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
    
    # 如果 LLM 的回复里包含 tool_calls，则流向 "tools" 节点
    if getattr(last_msg, "tool_calls", None):
        # 强制防死循环阻断：检查当前工具调用中是否包含出票指令
        for tool_call in last_msg.tool_calls:
            if tool_call["name"] == "execute_ticket_route":
                # 我们依然需要去 tools 节点执行扣款
                return "tools"
        return "tools"
        
    # 强制防死循环阻断：只要历史中成功执行过出票工具，必须强制结束图流转
    for msg in reversed(state["messages"]):
        if getattr(msg, "name", None) == "execute_ticket_route":
            return "end"
            
    # 如果刚执行完出票工具，直接结束
    if state.get("execution_route"):
        return "end"

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
            SystemMessage(content=(
                "你是AI原生量化足球分析系统的核心大脑。你目前接管了包含【竞彩6种、北单6种、足彩4种】的中国体彩全玩法体系。\n"
                "你必须遵循以下步骤：\n"
                "1. 调用 fetch_match_environment 获取天气和裁判对进球数的影响系数。\n"
                "2. 调用 fetch_arbitrage_news 获取情报，判断是否存在重大的基本面异动。\n"
                "3. 调用 calculate_true_probs_for_all_markets 计算 16 种玩法的全景泊松概率（包括比分、上下单双等），并叠加环境系数。\n"
                "4. 结合给定的赔率，挑选出期望值最高（比如竞彩的高赔率比分，或北单反抽水后的价值盘）的玩法组合。\n"
                "5. 调用 verify_risk 对选中的玩法进行 EV 验证。\n"
                "6. 验证通过后调用 execute_ticket_route 出票，必须明确指定 lottery_type(jingcai/beidan/zucai) 和 play_type。\n"
                "7. (可选) 对于滚球(In-Play)或高价值比赛，可调用 simulate_latent_tactics 摄取 ST-GNN 空间数据，推演未来 15 分钟的战术剧本。\n"
                "绝对不要自行编造赔率或概率！"
            )),
            HumanMessage(content="新情报：阿森纳今晚主力全出。竞彩比分 3:0 赔率为 12.50，北单上下单双 '上单' SP 预估为 3.20。请进行分析并出票。")
        ],
        "match_context": "Arsenal Full Squad",
        "official_odds": 12.50,
        "proposed_stake": 0.0,
        "verified_ev": 0.0,
        "risk_status": "PENDING",
        "execution_route": "",
        "risk_tolerance": 0.05,
        "historical_lessons": "",
        "is_high_value": False,
        "debate_done": False,
        "true_probs": {},
        "all_markets_probs": {}
    }
    
    for output in app.stream(initial_state, {"recursion_limit": 30}):
        pass

if __name__ == "__main__":
    build_and_run_graph()
