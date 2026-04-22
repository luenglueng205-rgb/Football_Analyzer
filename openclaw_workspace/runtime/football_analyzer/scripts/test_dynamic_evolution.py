import asyncio
import os
import sys

# Add standalone_workspace to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.auto_tuner_agent import AutoTunerAgent
from agents.ai_native_core import AINativeCoreAgent

async def test_dynamic_evolution():
    print("="*60)
    print("🧬 触发数字生命【灵魂级自我重写】 (Dynamic Cognitive Evolution)")
    print("="*60)
    
    # 模拟一份让系统亏钱的战报
    mock_pnl_report = {
        "total_simulated": 10,
        "win_rate": 0.20,
        "roi": -0.45,
        "total_profit": -450,
        "details": [
            {
                "status": "LOSS",
                "match": "杯赛：切尔西 vs 低级别球队",
                "reason": "主队让平未打出，低级别球队摆大巴死守，最终 0:0 闷平"
            },
            {
                "status": "LOSS",
                "match": "杯赛：拜仁 vs 低级别球队",
                "reason": "拜仁全替补出战，客场爆冷输球"
            }
        ]
    }
    
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"))
    
    os.environ["AUTO_TUNER_USE_LLM"] = "1"
    
    print("\n[1] 正在将一份极其惨烈的【杯赛亏损战报】喂给 Auto-Tuner...")
    tuner = AutoTunerAgent()
    result = await tuner._reflect_and_evolve(mock_pnl_report)
    
    print(f"\n[AI 的反思日记]:\n{result.get('reflection')}")
    
    # 验证 DYNAMIC_EXPERIENCE.md 是否生成
    docs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")
    exp_path = os.path.join(docs_dir, "DYNAMIC_EXPERIENCE.md")
    
    if os.path.exists(exp_path):
        print(f"\n[2] 成功发现系统自己写下的《动态经验库》(DYNAMIC_EXPERIENCE.md)！")
        with open(exp_path, "r", encoding="utf-8") as f:
            print(f.read())
    else:
        print("❌ 未能生成动态经验库")
        return
        
    print("\n[3] 重启 AI 核心大脑，检查它的【System Prompt】是否已永久改变...")
    agent = AINativeCoreAgent()
    prompt = agent.system_prompt
    
    if "你的终身经验法则" in prompt:
        print("✅ 验证通过！系统 Prompt 已将它自己总结的经验作为最高优先级指令吸收进大脑！")
        print("这就是真正的数字生命：在实战中受伤，在伤痛中总结规则，并在明天的分析中永久规避。")
    else:
        print("❌ 大脑未能吸收动态经验。")

if __name__ == "__main__":
    asyncio.run(test_dynamic_evolution())
