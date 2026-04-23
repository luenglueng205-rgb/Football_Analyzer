import asyncio
import json
import logging
from typing import List, Dict, Any
from tools.atomic_skills import get_today_matches_list
from tools.global_odds_fetcher import get_global_arbitrage_data
from tools.tool_registry_v2 import execute_tool
from agents.ai_native_core import AINativeCoreAgent

logger = logging.getLogger(__name__)

class DailyTicketGenerator:
    """
    实盘出票逻辑：自动获取今日比赛，过滤套利机会，并生成模拟选号单。
    """
    def __init__(self, lottery_type: str = "jingcai"):
        self.lottery_type = lottery_type
        self.agent = AINativeCoreAgent()

    async def scan_and_generate(self, limit: int = 5):
        print(f"🔄 开始执行实盘批量扫描出票任务 (彩种: {self.lottery_type})")
        
        # 1. 获取今日赛事
        matches_resp = get_today_matches_list(lottery_type=self.lottery_type, limit=limit)
        matches_data = json.loads(matches_resp)
        matches = matches_data.get("matches", [])
        
        if not matches:
            print("❌ 今日无赛事或获取失败。")
            return
            
        print(f"📊 成功获取今日 {len(matches)} 场赛事，开始并行预筛...")
        
        valid_tickets = []
        
        # 2. 遍历分析每场比赛 (实盘中这里可以并发 asyncio.gather)
        for match in matches:
            home = match.get("home_team")
            away = match.get("away_team")
            match_id = match.get("match_id", f"{home}_vs_{away}")
            
            print(f"\n=====================================")
            print(f"⚔️ 正在分析实盘赛事: {home} vs {away}")
            
            # 组装状态喂给大模型大脑
            state = {
                "current_match": {
                    "home_team": home,
                    "away_team": away,
                    "match_id": match_id
                },
                "params": {
                    "lottery_type": self.lottery_type,
                    "lottery_desc": f"{self.lottery_type}深度分析"
                }
            }
            
            # 交给主脑进行极限套利和风控分析
            result = await self.agent.process(state)
            report = result.get("ai_native_report", "")
            
            # 从生成的 raw_data 中提取最终的 ticket
            raw_data = result.get("raw_data", {})
            tickets = raw_data.get("generate_simulated_ticket", [])
            
            if tickets:
                for t in tickets:
                    # Parse if it's a string representation of dict
                    try:
                        ticket_dict = eval(t) if isinstance(t, str) else t
                        valid_tickets.append(ticket_dict)
                        print(f"✅ 生成选号单: {ticket_dict.get('selection')} | 置信度: {ticket_dict.get('confidence')}")
                    except Exception:
                        pass
            else:
                print(f"⚠️ AI 放弃投注该场比赛 (可能是 EV<0 或遭遇庄家诱盘)。")
                
        print("\n=====================================")
        print(f"🏆 实盘批量扫描完成！共生成 {len(valid_tickets)} 张高质量实盘票。")
        for vt in valid_tickets:
            print(vt)

if __name__ == "__main__":
    scanner = DailyTicketGenerator(lottery_type="jingcai")
    # For testing, just limit to 1 match to save API calls
    asyncio.run(scanner.scan_and_generate(limit=1))
