import asyncio
import os
import sys
import json

# Add standalone_workspace to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.ai_native_core import AINativeCoreAgent

async def run_complex_combination_test():
    print("\n" + "="*50)
    print("🧠 启动数字生命【复式双选与 M串N 组合】高级实战测试")
    print("="*50)
    
    agent = AINativeCoreAgent()
    
    case = {
        "lottery": "JINGCAI",
        "match": "国际米兰 vs 尤文图斯",
        "league": "意甲",
        "odds": "2.20 / 3.10 / 2.80",
        "desc": "高级复式测试：意甲豪门对决，极度势均力敌。测试 AI 是否能打破单选思维，利用 'calculate_complex_parlay' 采用双选防冷策略，并计算出组合注数与最大回报。"
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
    asyncio.run(run_complex_combination_test())
