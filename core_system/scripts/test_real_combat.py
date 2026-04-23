import asyncio
import os
import sys
import json

# Add standalone_workspace to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.ai_native_core import AINativeCoreAgent

async def run_real_combat_test():
    print("\n" + "="*50)
    print("🏆 启动数字生命“真实战场”全方位压力测试 (Real-World Combat Test)")
    print("="*50)
    
    # 模拟今天晚上的真实焦点比赛 (例如欧冠或英超焦点战)
    # 我们故意设置一场方差极大、充满博弈的比赛：拜仁慕尼黑 vs 阿森纳 (欧冠)
    # 拜仁近期状态低迷，阿森纳表现强劲，这正是考验 AI 选场与防冷能力的绝佳场景
    
    agent = AINativeCoreAgent()
    
    case = {
        "lottery": "JINGCAI",
        "match": "拜仁慕尼黑 vs 阿森纳",
        "league": "欧冠",
        "odds": "2.35 / 3.40 / 2.50",
        "desc": "实战测试：检验 AI 在面对基本面反转（拜仁衰退，阿森纳强势）且势均力敌的比赛时，能否通过去水概率和凯利公式做出冷静的 EV 决策。"
    }
    
    print(f"\n[实战开启] {case['desc']}")
    print(f"比赛: {case['match']} ({case['league']}) - 竞彩初赔: {case['odds']}")
    print("-" * 30)
    
    try:
        state = {
            "current_match": {"home_team": case["match"].split(" vs ")[0], "away_team": case["match"].split(" vs ")[1]},
            "params": {"lottery_type": case["lottery"].lower(), "lottery_desc": case["lottery"]}
        }
        result = await agent.process(state)
        print("\n【AI 实战分析与出票结果】:\n")
        print(result.get("ai_native_report", result))
        
        # 提取原始数据，展示一下它是怎么调用工具的
        raw_data = result.get("raw_data", {})
        print("\n【后台工具调用轨迹 (审计追踪)】:")
        for tool, outputs in raw_data.items():
            print(f"- 🔧 {tool} 被调用了 {len(outputs)} 次")
            
    except Exception as e:
        print(f"执行失败: {e}")
        
    print("="*50)

if __name__ == "__main__":
    asyncio.run(run_real_combat_test())
