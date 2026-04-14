import asyncio
from typing import Dict, Any
from agents.syndicate_agents import ScoutAgent, QuantAgent, JudgeAgent

class SyndicateOS:
    """
    数字博彩辛迪加操作系统 (The Agentic OS)。
    负责事件驱动流转：Scout -> Quant -> Judge。
    彻底取代庞大的 AINativeCoreAgent。
    """
    def __init__(self):
        self.scout = ScoutAgent()
        self.quant = QuantAgent()
        self.judge = JudgeAgent()

    async def process_match(self, home_team: str, away_team: str, lottery_desc: str) -> Dict[str, Any]:
        print(f"\n==================================================")
        print(f"🏛️ Syndicate OS 开始分析: {home_team} vs {away_team}")
        print(f"==================================================")
        
        # 1. Scout 阶段：搜集情报与记忆
        scout_task = f"目标赛事：{home_team} vs {away_team}。请收集双方伤停、新闻，并检索关于这两支球队的长期记忆。"
        scout_res = await self.scout.run(scout_task)
        
        # 2. Quant 阶段：获取赔率与跑模型
        quant_task = f"目标赛事：{home_team} vs {away_team}。玩法：{lottery_desc}。请获取实时赔率和亚盘，运行泊松和蒙特卡洛模型，计算EV。"
        quant_res = await self.quant.run(quant_task)
        
        # 3. Judge 阶段：综合裁决并执行
        judge_task = f"""
目标赛事：{home_team} vs {away_team}。玩法：{lottery_desc}。
请根据以下两份报告做出最终的真金白银投资决策（必须查资金、必须写账本、必须发通知、必须保存新记忆）：

【Scout 提交的情报报告】
{scout_res['report']}

【Quant 提交的量化报告】
{quant_res['report']}
"""
        judge_res = await self.judge.run(judge_task)
        
        return {
            "scout_report": scout_res['report'],
            "quant_report": quant_res['report'],
            "final_decision": judge_res['report']
        }
