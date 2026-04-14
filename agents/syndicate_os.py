import asyncio
from typing import Dict, Any
from agents.syndicate_agents import ScoutAgent, FundamentalQuantAgent, ContrarianQuantAgent, SmartMoneyQuantAgent, JudgeAgent

class SyndicateOS:
    def __init__(self):
        self.scout = ScoutAgent()
        self.fundamentalist = FundamentalQuantAgent()
        self.contrarian = ContrarianQuantAgent()
        self.smart_money = SmartMoneyQuantAgent()
        self.judge = JudgeAgent()

    async def process_match(self, home_team: str, away_team: str, lottery_desc: str) -> Dict[str, Any]:
        print(f"\n==================================================")
        print(f"🏛️ 交易大厅开启: {home_team} vs {away_team}")
        print(f"==================================================")
        
        # 1. Scout 获取基础情报
        scout_task = f"目标赛事：{home_team} vs {away_team}。请收集双方伤停、新闻，并检索历史记忆。"
        scout_res = await self.scout.run(scout_task)
        
        # 2. 三大宽客并行工作 (并发执行，极大提升效率)
        quant_base_task = f"目标赛事：{home_team} vs {away_team}。玩法：{lottery_desc}。基于你的流派哲学，给出你的专属投资建议。"
        
        results = await asyncio.gather(
            self.fundamentalist.run(quant_base_task),
            self.contrarian.run(quant_base_task),
            self.smart_money.run(quant_base_task),
            return_exceptions=True
        )
        
        fun_res = results[0] if not isinstance(results[0], Exception) else {"report": "基本面派崩溃"}
        con_res = results[1] if not isinstance(results[1], Exception) else {"report": "反买派崩溃"}
        smt_res = results[2] if not isinstance(results[2], Exception) else {"report": "聪明资金派崩溃"}
        
        # 3. Judge 终极裁决
        judge_task = f"""
目标赛事：{home_team} vs {away_team}。玩法：{lottery_desc}。
请主持以下辩论并做出最终的真金白银投资决策：

【Scout 客观情报】
{scout_res.get('report', '缺失')}

【基本面派观点】
{fun_res.get('report', '缺失')}

【反买狗庄派观点】
{con_res.get('report', '缺失')}

【聪明资金派观点】
{smt_res.get('report', '缺失')}
"""
        judge_res = await self.judge.run(judge_task)
        
        return {
            "scout_report": scout_res.get('report'),
            "debates": {
                "fundamentalist": fun_res.get('report'),
                "contrarian": con_res.get('report'),
                "smart_money": smt_res.get('report')
            },
            "final_decision": judge_res.get('report')
        }
