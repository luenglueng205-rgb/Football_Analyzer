# Phase 4: Domain Mastery - Multi-Strategy Debate Society (多策略辩论社会) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有的单一 `QuantAgent` 裂变为三个具有极端投资偏好的宽客（基本面派、反买狗庄派、聪明资金追踪派），并在 `JudgeAgent` 面前展开多空博弈（Debate），最终由新加入的 `PublisherAgent` 将辩论过程和实单结果生成专业的 Markdown/HTML 研报。

**Architecture:** 
1. 扩展 `agents/syndicate_agents.py`，新增三个 `Quant` 子类，各自配置极端的 Prompt 和受限工具集。
2. 重构 `agents/syndicate_os.py`，实现并行的 `asyncio.gather` 获取三方量化报告，并将其交由 `JudgeAgent` 裁决。
3. 创建 `PublisherAgent`，负责提取 JSON/文本日志，调用专门的模板工具生成研报，并可通过 Webhook 或静态文件分发。

**Tech Stack:** `asyncio`, `openai`

---

### Task 1: 裂变量化宽客 (Multi-Persona Quants)

**Files:**
- Modify: `agents/syndicate_agents.py`

- [ ] **Step 1: 将 QuantAgent 拆分为三个极端流派**

删除旧的 `QuantAgent`，替换为以下三个类：

```python
class FundamentalQuantAgent(BaseAgent):
    def __init__(self):
        prompt = "你是基本面原教旨主义者(Fundamentalist)。你坚信足球是实力的体现，无视盘口诱导。你主要依靠泊松分布、蒙特卡洛模拟和伤停情报来计算纯粹的胜负概率。输出你认为最稳妥的选项和数学期望。"
        tools = ["calculate_poisson_probabilities", "run_monte_carlo_simulation", "get_team_stats"]
        super().__init__("Fundamentalist", prompt, tools)

class ContrarianQuantAgent(BaseAgent):
    def __init__(self):
        prompt = "你是反买狗庄派(Contrarian)。你坚信机构永远在诱导散户，'大热必死'。你的任务是分析初盘到临场的水位异动和亚盘偏差，专门寻找强队降水诱盘的陷阱，果断推荐下盘或冷门选项。"
        tools = ["analyze_asian_handicap_divergence", "get_live_odds"]
        super().__init__("Contrarian", prompt, tools)

class SmartMoneyQuantAgent(BaseAgent):
    def __init__(self):
        prompt = "你是聪明资金追踪者(Smart Money Tracker)。你认为基本面都是滞后的，只有钱不会骗人。你只盯着必发指数和大额资金异动，跟庄走。如果没有明显资金异动，你建议放弃。"
        tools = ["detect_smart_money", "get_live_odds"]
        super().__init__("SmartMoneyTracker", prompt, tools)
```

- [ ] **Step 2: 调整 JudgeAgent 的 Prompt 以适应辩论**

修改 `JudgeAgent` 的 `prompt`：

```python
class JudgeAgent(BaseAgent):
    def __init__(self):
        prompt = """你是华尔街数字博彩基金的风控法官(Judge)。你的任务是主持多空辩论。
你将收到一份球探情报，以及来自【基本面派】、【反买狗庄派】和【聪明资金派】的三份相互冲突的投资建议。
你需要：
1. 找出他们逻辑中的漏洞并进行最终裁决。
2. 必须调用 check_bankroll 检查资金。
3. 严格使用凯利准则计算仓位。如果决定下注，调用 execute_bet 和 save_team_insight，并调用通知工具(send_webhook_notification, generate_qr_code)。
4. 如果三方分歧过大或 EV < 0，坚决执行 Skip (放弃)。
你拥有唯一的开火权。"""
        tools = ["check_bankroll", "execute_bet", "save_team_insight", "send_webhook_notification", "generate_qr_code"]
        super().__init__("Judge", prompt, tools)
```

### Task 2: 重构 SyndicateOS 调度逻辑 (The Debate Floor)

**Files:**
- Modify: `agents/syndicate_os.py`

- [ ] **Step 1: 在 SyndicateOS 中引入并发量化分析**

```python
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
```

### Task 3: 引入 PublisherAgent 自动生成研报

**Files:**
- Create: `agents/publisher_agent.py`
- Modify: `run_live_decision.py`

- [ ] **Step 1: 创建 PublisherAgent**

```python
import os
import json
from openai import AsyncOpenAI
from datetime import datetime

class PublisherAgent:
    """
    负责将冷冰冰的终端日志，转化为具有极强专业性和传播性的《AI数字博彩研报》。
    """
    def __init__(self):
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        api_key = os.getenv("OPENAI_API_KEY", "dummy-key-for-test")
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        
    async def publish(self, home: str, away: str, os_result: dict) -> str:
        print(f"\n[📰 Publisher] 正在撰写《AI 华尔街数字博彩研报》...")
        
        prompt = f"""
你是《华尔街数字博彩研报》的首席AI分析师，文风专业、犀利、带有一点华尔街交易员的傲慢。
请根据以下内部多空博弈会议的记录，撰写一篇针对 {home} vs {away} 的公开投资研报。
研报必须包含：
1. 赛事基本面概述。
2. 交易大厅激辩实录（简述三派宽客的分歧点）。
3. 首席风控官(Judge)的最终裁决与资金管理建议。
4. 使用 Markdown 格式，排版精美，适合发到公众号或 Telegram。

会议记录：
{json.dumps(os_result, ensure_ascii=False)}
"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            report = response.choices[0].message.content
            
            # 保存到本地文件
            date_str = datetime.now().strftime("%Y%m%d")
            filename = f"reports/{date_str}_{home}_vs_{away}.md"
            os.makedirs("reports", exist_ok=True)
            with open(filename, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"[📰 Publisher] 研报已生成并保存至: {filename}")
            return report
            
        except Exception as e:
            print(f"[📰 Publisher] 研报生成失败: {e}")
            return "研报生成失败"
```

- [ ] **Step 2: 接入 run_live_decision.py**

```python
# 修改 run_live_decision.py 的 main() 末尾
# 引入: from agents.publisher_agent import PublisherAgent

# 找到: print("\n⚖️ [法官裁决报告]") ...
# 在之后追加：
# publisher = PublisherAgent()
# report = await publisher.publish(home, away, result)
# print("\n==================================================")
# print("📰 [最终公开发布研报]")
# print("==================================================")
# print(report)
```

- [ ] **Step 3: 运行完整真实链路测试并验证文件**

```bash
python3 run_live_decision.py
```
Expected: 终端并发打印三大宽客的进度。最后 `reports/` 目录下生成一篇漂亮的 Markdown 研报。

- [ ] **Step 4: Commit**

```bash
git add agents/syndicate_agents.py agents/syndicate_os.py agents/publisher_agent.py run_live_decision.py
git commit -m "feat(p4): implement multi-strategy debate society and publisher agent"
```