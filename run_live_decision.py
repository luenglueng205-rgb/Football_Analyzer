import asyncio
import json
from agents.syndicate_os import SyndicateOS
from tools.analyzer_api import AnalyzerAPI

async def main():
    print("==================================================")
    print("🚀 [P3 实战决策阶段] 启动全链路真实数据推演")
    print("==================================================")
    
    # 1. 抓取今日真实赛程
    print("\n[1] 正在通过 AgentBrowser 抓取 500.com 今日赛程...")
    fixtures = AnalyzerAPI.get_live_fixtures()
    if not fixtures:
        print("❌ 未找到今日赛程或抓取失败。")
        return
        
    print(f"✅ 成功获取 {len(fixtures)} 场比赛。")
    # 挑选一场尚未开赛的，或者直接拿第一场
    target_match = None
    for f in fixtures:
        if f.get("status") == "upcoming":
            target_match = f
            break
            
    if not target_match:
        print("⚠️ 今日比赛均已开赛或结束，随机挑选一场进行复盘推演...")
        target_match = fixtures[0]
        
    home = target_match.get("home_team", "未知主队")
    away = target_match.get("away_team", "未知客队")
    print(f"🎯 锁定目标赛事: {home} vs {away} (状态: {target_match.get('status')})")
    
    # 2. 拉起 SyndicateOS 核心大脑
    print("\n[2] 唤醒 SyndicateOS 进行深度决策...")
    agent = SyndicateOS()
    
    result = await agent.process_match(home, away, "竞彩足球 (胜平负/让球)")
    
    print("\n==================================================")
    print("🧠 [Scout 情报报告]")
    print("==================================================")
    print(result.get("scout_report", "无报告"))
    
    print("\n==================================================")
    print("📈 [Quant 量化报告]")
    print("==================================================")
    print(result.get("quant_report", "无报告"))

    print("\n==================================================")
    print("⚖️ [Judge 裁决报告]")
    print("==================================================")
    print(result.get("final_decision", "无裁决"))

if __name__ == "__main__":
    asyncio.run(main())
