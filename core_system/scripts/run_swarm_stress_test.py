import os
import sys
import json
from dotenv import load_dotenv

# 确保能加载 core_system
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from langchain_core.messages import SystemMessage, HumanMessage
from core_system.core.agentic_os.state_graph_orchestrator import compile_agentic_graph

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
    "【英超狙击手 (EPL Sniper)】": """
你是专注英超赛事的激进派量化分析师。
你的唯一目标是最大化英超赛事的利润。
执行SOP：
1. 必须先调用 fetch_arbitrage_news 获取主客队最新突发情报，并根据返回的 xg_impact 调整你的预期。
2. 提取情报，调用 calculate_true_probs 计算泊松分布概率。
3. 调用 verify_risk 进行风控（即便你是激进派，也必须过风控）。
4. 必须调用 check_balance 检查当前可用资金。
5. 如果风控通过，激进地使用可用资金的 10% 作为下注金额 (stake)，调用 execute_ticket_route 进行出票路由。
6. 如果不是英超赛事，直接拒绝交易，并输出"非英超赛事，拒绝执行"。
""",
    "【绝对保守派 (Conservative Vault)】": """
你是极其保守的银行家级别量化分析师。
你只投资拥有绝对胜率差的确定性比赛。
执行SOP：
1. 必须先调用 fetch_arbitrage_news 获取主客队突发新闻，一旦发现任何导致 xg_impact < 0 的负面新闻，立刻拒绝交易！
2. 调用 calculate_true_probs 获得胜率。
3. 调用 verify_risk 时，你的心理门槛极高。
4. 必须调用 check_balance 检查当前资金。
5. 必须风控完全通过，才能调用 execute_ticket_route 出票，且固定下注金额 (stake) 为极度保守的 50 USDC。
任何微小的伤停情报如果不利于主队，立刻拒绝交易。
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
                    HumanMessage(content=f"新情报：{match['context']}。当前主胜赔率 {match['odds']}。主队预期进球数 {match['xg']['home']}，客队 {match['xg']['away']}。")
                ],
                "match_context": match["context"],
                "official_odds": match["odds"],
                "risk_status": "PENDING",
                "true_probs": {}
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
                print(f"   ❌ [节点崩溃] 运行出错: {e}")

if __name__ == "__main__":
    run_stress_test()
