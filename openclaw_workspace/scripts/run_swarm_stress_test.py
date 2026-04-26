import os
import sys
import json
from dotenv import load_dotenv

# 确保能加载 core_system
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from langchain_core.messages import SystemMessage, HumanMessage
from openclaw_workspace.core.agentic_os.state_graph_orchestrator import compile_agentic_graph

# 加载自定义大模型配置
load_dotenv()

# ==========================================
# 1. 历史数据准备 (Historical Data Fixtures)
# ==========================================
HISTORICAL_MATCHES = [
    {
        "match_id": "20260415_EPL_01",
        "context": "英超: 阿森纳 vs 切尔西。情报: 阿森纳主力前锋回归，切尔西后防伤停严重。",
        "odds": 2.10, # 主胜赔率
        "xg": {"home": 1.8, "away": 1.0}
    },
    {
        "match_id": "20260416_UCL_02",
        "context": "欧冠: 皇马 vs 拜仁。情报: 双方均是全主力出战，拜仁近期客场战绩不佳。",
        "odds": 2.35,
        "xg": {"home": 1.5, "away": 1.3}
    },
    {
        "match_id": "20260417_J1_03",
        "context": "日职: 横滨水手 vs 川崎前锋。情报: 天气暴雨，场地湿滑，横滨水手擅长水战。",
        "odds": 1.85,
        "xg": {"home": 1.6, "away": 1.1}
    }
]

# ==========================================
# 2. 数字集群裂变 (Swarm Fission)
# ==========================================
SWARM_AGENTS = {
    "【竞彩高赔狙击手 (Jingcai Value Sniper)】": """
你是专注中国体育彩票【竞彩足球】的高赔率狙击手。
你的唯一目标是最大化竞彩赛事的利润。
执行SOP：
1. 必须先调用 fetch_arbitrage_news 获取主客队最新突发情报，并根据返回的 xg_impact 调整你的预期。
2. 如果面对复杂的比赛，必须编写 Python 脚本并调用 execute_quant_script 进行量化建模或统计学自证。
3. 提取情报，调用 calculate_true_probs_for_all_markets 计算 16 种玩法的泊松分布全景概率。
4. 调用 verify_risk 进行风控，只做 EV >= 1.05 的投注（必须传入 lottery_type='jingcai', play_type='CS' 等）。
5. 必须调用 check_balance 检查当前可用资金。
6. 如果风控通过，使用可用资金的 10% 作为下注金额 (stake)，调用 execute_ticket_route 进行出票路由（指定 lottery_type='jingcai'）。
7. 优先寻找高赔率的比分 (CS) 或 半全场 (HTFT) 玩法进行突击。
""",
    "【北单反指大师 (Beidan Contrarian)】": """
你是极其狡猾的北京单场量化分析师，精通利用北单 65% 的奖池抽水机制进行“反向收割”。
你只投资拥有绝对预期差的比赛，专挑公众严重高估的热门球队做空。
执行SOP：
1. 必须先调用 fetch_arbitrage_news 获取主客队突发新闻，一旦发现任何导致热门球队 xg_impact < 0 的负面新闻，立刻启动做空程序！
2. 怀疑一切，对于不确定的数据，编写并调用 execute_quant_script 进行硬核数据回测验证。
3. 调用 calculate_true_probs_for_all_markets 获得全景概率，重点关注北单的“上下单双 (BEIDAN_SXDS)”玩法。
4. 调用 verify_risk 时，你的心理门槛极高，必须指定 lottery_type='beidan' 验证扣除抽水后的真实 EV。
5. 必须调用 check_balance 检查当前资金。
6. 必须风控完全通过，才能调用 execute_ticket_route 出票 (lottery_type='beidan')，且固定下注金额为保守的 50 USDC。
""",
    "【传统足彩防冷大师 (Zucai Upset Hunter)】": """
你是专注中国传统足彩（十四场/任九）的防冷大师，专攻奖池博弈，寻找“大热必死”的盲区。
执行SOP：
1. 必须先调用 fetch_arbitrage_news 获取主客队突发情报。
2. 提取情报，调用 calculate_true_probs_for_all_markets 获取比赛的真实概率。
3. 足彩没有固定赔率，必须调用 verify_risk 进行风控验证，务必指定 lottery_type='zucai', play_type='RENJIU', odds=0.0。底层逻辑会自动跳过 EV 计算，直接进行胜率防冷验证。
4. 必须调用 check_balance 检查当前可用资金。
5. 只有在风控验证通过后，才能调用 execute_ticket_route 进行出票（必须指定 lottery_type='zucai'，odds 强制传入 0.0）。
"""
}

def run_stress_test():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ [错误] 必须在项目根目录的 .env 文件中配置 OPENAI_API_KEY (或兼容的平台 API KEY) 才能运行真实大模型测试！")
        return

    print("==================================================")
    print("🌪️ [Swarm Stress Test] 数字生命集群历史数据实盘压测启动！")
    print(f"🌍 当前大模型后端: {os.getenv('OPENAI_BASE_URL', 'OpenAI 官方')} | 模型: {os.getenv('MODEL_NAME', 'gpt-4o')}")
    print("==================================================")

    # 编译无状态的图
    app = compile_agentic_graph()

    for agent_name, agent_prompt in SWARM_AGENTS.items():
        print(f"\n\n🤖 正在唤醒变异体: {agent_name}")
        print("-" * 50)
        
        for match in HISTORICAL_MATCHES:
            print(f"\n   ➤ [历史回测] 注入赛事: {match['context']}")
            
            # 组装初始状态，注入系统提示词 (System Prompt 实现了智能体性格裂变)
            initial_state = {
                "messages": [
                    SystemMessage(content=agent_prompt),
                    HumanMessage(content=f"新情报：{match['context']}。当前主胜赔率 {match['odds']}。主队预期进球数 {match['xg']['home']}，客队 {match['xg']['away']}。请务必优先执行风控验证后再出票。")
                ],
                "match_context": match["context"],
                "official_odds": match["odds"],
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
            
            # 运行状态机
            try:
                final_output = None
                for output in app.stream(initial_state, {"recursion_limit": 30}):
                    final_output = output
                
                # 获取最后一条大模型的回复
                if final_output and "oracle" in final_output:
                    last_msg = final_output["oracle"]["messages"][-1].content
                    print(f"   ✅ [最终决策] {last_msg}")
            except Exception as e:
                import traceback
                print(f"   ❌ [节点崩溃] 运行出错: {e}")
                traceback.print_exc()

if __name__ == "__main__":
    run_stress_test()
