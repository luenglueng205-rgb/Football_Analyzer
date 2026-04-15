import asyncio
import os
from typing import Dict, Any
from agents.syndicate_agents import ScoutAgent, FundamentalQuantAgent, ContrarianQuantAgent, SmartMoneyQuantAgent, JudgeAgent

import warnings

class SyndicateOS:
    """
    [DEPRECATED] 负责统筹调度 Scout、Quant 和 Judge 的 AI 操作系统。
    加入并发执行和熔断机制。
    
    Warning: This class is deprecated in favor of the new Event-Driven AgenticCore.
    Please use core.agentic_core.AgenticCore instead.
    """
    def __init__(self):
        warnings.warn(
            "SyndicateOS is deprecated. Use AgenticCore instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self.scout = ScoutAgent()
        self.fundamentalist = FundamentalQuantAgent()
        self.contrarian = ContrarianQuantAgent()
        self.smart_money = SmartMoneyQuantAgent()
        self.judge = JudgeAgent()
        
        # 读取官方规则白皮书，作为最高风控宪法
        rulebook_path = os.path.join(os.path.dirname(__file__), '..', 'docs', 'superpowers', 'specs', 'lottery_official_rulebook.md')
        try:
            with open(rulebook_path, 'r', encoding='utf-8') as f:
                self.lottery_rulebook = f.read()
        except Exception:
            self.lottery_rulebook = "官方规则白皮书加载失败，请依赖内置知识。"

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
        print(f"\n[⚖️ Judge] 军师（Judge）正在综合三路诸将的情报，为主公定夺...")
        
        judge_task = f"""
主公（用户）命你作为本次数字博彩的首席军师（Judge）。
请综合以下三位偏将（基本面、反直觉、聪明钱）的军情汇报，做出最终的战略定夺。
你的决策不应是冷冰冰的代码，而是像诸葛亮一样有血有肉、有温度、始终将主公的本金安全放在第一位的智囊。

如果三方冲突严重，请提醒主公“此战水深，臣建议按兵不动”。
如果胜算极大，请推荐合理的“竞彩/北单”玩法（如单关、或者高价值的自由过关）。

目标赛事：{home_team} vs {away_team}。当前彩种与玩法大类：{lottery_desc}。

【必须遵守的体彩领域知识库 (Rulebook)】
{self.lottery_rulebook}

【Scout 客观情报】
{scout_res.get('report', '缺失')}

=== 基本面校尉 ===
{fun_res.get('report', '缺失')}

=== 反直觉奇兵 ===
{con_res.get('report', '缺失')}

=== 聪明钱密探 ===
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
