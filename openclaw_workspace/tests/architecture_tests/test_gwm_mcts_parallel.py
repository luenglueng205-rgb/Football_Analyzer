import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

import os
from langchain_core.messages import SystemMessage, HumanMessage
from openclaw_workspace.core.agentic_os.state_graph_orchestrator import compile_agentic_graph, get_base_llm

def test_gwm_mcts_parallel():
    """
    测试 GWM 与 MCTS 的并行推进。
    场景：一场高价值的滚球比赛（欧冠决赛，下半场70分钟）。
    预期行为：
    1. Sentinel 评估为 HIGH，触发 MCTS。
    2. MCTS 深层思考，并由 LLM Oracle 发起 MoA 辩论。
    3. LLM 应该调用 simulate_latent_tactics 工具，利用 GWM/ST-GNN 获取战术参数。
    4. 结合推演结果进行出票。
    """
    
    print("==================================================")
    print("🚀 [Parallel Evolution] 启动 MCTS + GWM 联合压测")
    print("==================================================")
    
    app = compile_agentic_graph()
    
    # 模拟一个高复杂度的下半场滚球场景
    scenario = (
        "【赛事状态】欧冠决赛，阿森纳(主) vs 皇家马德里(客)。目前比分 1:1，比赛进行到第 70 分钟。\n"
        "【情报】皇马中场核心体力下降，阿森纳刚换上两名速度型边锋，全线压上。\n"
        "【盘口】目前滚球盘口：下一个进球(Next Goal) - 阿森纳进球赔率 2.10，皇马进球赔率 3.80。\n"
        "【指令】请调用 simulate_latent_tactics(match_id='UCL_FINAL_001') 分析空间数据，并决定下注策略。"
    )
    
    initial_state = {
        "messages": [
            SystemMessage(content=(
                "你是AI原生量化足球分析系统的核心大脑。\n"
                "你必须遵循以下步骤：\n"
                "1. 调用 simulate_latent_tactics 摄取 ST-GNN 空间数据，推演未来 15 分钟的战术剧本。\n"
                "2. 调用 calculate_true_probs_for_all_markets 计算基础泊松概率（可忽略，重点看GWM的动量）。\n"
                "3. 调用 verify_risk 对选中的玩法进行 EV 验证。\n"
                "4. 验证通过后调用 execute_ticket_route 出票，明确 lottery_type 和 play_type。\n"
                "绝对不要自行编造赔率或概率！"
            )),
            HumanMessage(content=scenario)
        ],
        "match_context": scenario,
        "official_odds": 2.10,
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
    
    print("-> 提交初始状态至 LangGraph...")
    
    for output in app.stream(initial_state, {"recursion_limit": 30}):
        # 打印状态流转，方便观察调用栈
        if "tools" in output:
            for msg in output["tools"]["messages"]:
                print(f"\n🔧 [Tool Execution Result]: {msg.name}")
                print(f"    {msg.content[:500]}...")

    print("\n✅ 测试结束。请检查上方日志，确认系统是否成功进入 MCTS 节点，并调用了 GWM 潜空间推演工具。")

if __name__ == "__main__":
    test_gwm_mcts_parallel()