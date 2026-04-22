import asyncio
import os
import sys

# Add standalone_workspace to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.ai_native_core import AINativeCoreAgent

async def run_isolation_tests():
    print("\n" + "="*50)
    print("🚀 启动 16 种玩法绝对物理隔离与深度细节测试 (AI-Native)")
    print("="*50)
    
    agent = AINativeCoreAgent()
    
    test_cases = [
        {
            "lottery": "JINGCAI",
            "match": "阿森纳 vs 卢顿",
            "league": "英超",
            "odds": "1.30 / 5.00 / 9.00",
            "desc": "测试竞彩：重点测试‘让平’和‘混合过关木桶效应’的识别"
        },
        {
            "lottery": "BEIDAN",
            "match": "巴塞罗那 vs 莱切斯特城",
            "league": "友谊赛",
            "odds": "1.45 / 4.20 / 6.50",
            "desc": "测试北单：重点测试‘上下盘单双’、‘胜负过关半球盘’和‘65%返奖率’的识别"
        },
        {
            "lottery": "ZUCAI",
            "match": "皇家马德里 vs 赫罗纳",
            "league": "西甲",
            "odds": "1.25 / 6.00 / 11.00",
            "desc": "测试足彩：重点测试‘14场滚存博弈’和‘任九避难点’的识别"
        }
    ]
    
    for case in test_cases:
        print(f"\n[{case['lottery']}] 测试开始: {case['desc']}")
        print(f"比赛: {case['match']} ({case['league']}) - 赔率: {case['odds']}")
        print("-" * 30)
        
        task_prompt = f"请使用 {case['lottery']} 的规则，为 {case['match']} ({case['league']}) 提供一份深度的玩法策略分析。欧洲赔率约为 {case['odds']}。必须死磕所有你看得到的和看不到的细节规则，证明你完全精通 {case['lottery']} 的专属玩法！"
        
        try:
            state = {
                "current_match": {"home_team": case["match"].split(" vs ")[0], "away_team": case["match"].split(" vs ")[1]},
                "params": {"lottery_type": case["lottery"].lower(), "lottery_desc": case["lottery"]}
            }
            result = await agent.process(state)
            print("【AI 分析结果】:\n")
            print(result.get("ai_native_report", result))
        except Exception as e:
            print(f"执行失败: {e}")
        
        print("="*50)

if __name__ == "__main__":
    asyncio.run(run_isolation_tests())
