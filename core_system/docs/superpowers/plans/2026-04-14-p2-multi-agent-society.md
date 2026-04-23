# Phase 2: Multi-Agent Society (多智能体重构) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有的单一庞大 `AINativeCoreAgent` 拆解为 `ScoutAgent` (情报球探)、`QuantAgent` (量化宽客) 和 `JudgeAgent` (风控法官) 三个独立的微型智能体，并通过轻量级事件驱动框架串联。

**Architecture:** 创建三个独立的 Agent 类，每个类拥有自己专属的精简版 Prompt 和可用的工具集。创建一个主调度器 `SyndicateOS` (辛迪加操作系统)，它接收一场比赛的任务，依次调用 Scout (找情报) -> Quant (算模型) -> Judge (综合决策)，彻底消除单一 LLM 幻觉和工具死循环。

**Tech Stack:** `openai` (AsyncOpenAI), `pydantic`

---

### Task 1: 创建独立的子智能体类 (Scout, Quant, Judge)

**Files:**
- Create: `agents/syndicate_agents.py`

- [ ] **Step 1: 编写基础智能体类和具体的子智能体**

```python
import os
import json
from typing import Dict, Any, List
from openai import AsyncOpenAI
from tools.tool_registry_v2 import get_openai_tools, execute_tool

class BaseAgent:
    def __init__(self, name: str, role_prompt: str, allowed_tools: List[str]):
        self.name = name
        self.role_prompt = role_prompt
        self.allowed_tools = allowed_tools
        
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        api_key = os.getenv("OPENAI_API_KEY", "dummy-key-for-test")
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    def _filter_tools(self) -> List[Dict]:
        all_tools = get_openai_tools()
        if not self.allowed_tools:
            return []
        if "*" in self.allowed_tools:
            return all_tools
        return [t for t in all_tools if t["function"]["name"] in self.allowed_tools]

    async def run(self, task_context: str) -> Dict[str, Any]:
        print(f"\n[🤖 {self.name}] 正在执行任务...")
        messages = [
            {"role": "system", "content": self.role_prompt},
            {"role": "user", "content": task_context}
        ]
        
        tools = self._filter_tools()
        gathered_data = {}
        
        # 限制循环次数，子 Agent 必须速战速决
        for _ in range(5):
            kwargs = {"model": self.model, "messages": messages}
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"
                
            response = await self.client.chat.completions.create(**kwargs)
            msg = response.choices[0].message
            messages.append(msg)
            
            if not msg.tool_calls:
                print(f"[🤖 {self.name}] 任务完成。")
                return {"report": msg.content, "data": gathered_data}
                
            for tc in msg.tool_calls:
                func_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                    print(f"  └─ 🛠️ 调用工具: {func_name}({str(args)[:100]})")
                    res = await execute_tool(func_name, args)
                    safe_res = str(res)[:1000] # 截断保护
                except Exception as e:
                    safe_res = f"Error: {e}"
                    
                gathered_data[func_name] = safe_res
                messages.append({
                    "tool_call_id": tc.id,
                    "role": "tool",
                    "name": func_name,
                    "content": safe_res
                })
                
        return {"report": "Reached max tool loops without final answer.", "data": gathered_data}

class ScoutAgent(BaseAgent):
    def __init__(self):
        prompt = "你是情报探子(Scout)。你的唯一任务是获取球队基本面、伤停情报和近期新闻，并检索历史记忆。输出一段纯情报总结。不要做任何投资决策。"
        tools = ["get_live_injuries", "get_live_news", "search_news", "retrieve_team_memory"]
        super().__init__("Scout", prompt, tools)

class QuantAgent(BaseAgent):
    def __init__(self):
        prompt = "你是量化宽客(Quant)。你的唯一任务是获取赔率数据，运行数学模型(泊松/蒙特卡洛)，计算EV值。输出纯数据报告和模型计算结果。不要做最终决策。"
        tools = ["get_live_odds", "calculate_poisson_probabilities", "run_monte_carlo_simulation", "detect_smart_money", "analyze_asian_handicap_divergence"]
        super().__init__("Quant", prompt, tools)

class JudgeAgent(BaseAgent):
    def __init__(self):
        prompt = """你是风控法官(Judge)。你的任务是阅读 Scout 的情报报告和 Quant 的量化报告。
你必须调用 check_bankroll。
如果你决定下注，你必须调用 execute_bet 和 save_team_insight，并推送通知(send_webhook_notification, generate_qr_code)。
如果决定放弃，说明理由。
你拥有最终开火权。"""
        tools = ["check_bankroll", "execute_bet", "save_team_insight", "send_webhook_notification", "generate_qr_code"]
        super().__init__("Judge", prompt, tools)
```

- [ ] **Step 2: 编写测试脚本验证单个 Agent**

```bash
cat << 'EOF' > test_agents.py
import asyncio
from agents.syndicate_agents import ScoutAgent

async def test():
    scout = ScoutAgent()
    res = await scout.run("帮我查一下 曼联 vs 切尔西 这场比赛的基本面情报。")
    print(res["report"])

if __name__ == "__main__":
    asyncio.run(test())
EOF
python3 test_agents.py
```
Expected: PASS (ScoutAgent 应该只调用情报类工具，并输出一段情报总结)

### Task 2: 创建主调度器 SyndicateOS

**Files:**
- Create: `agents/syndicate_os.py`

- [ ] **Step 1: 编写 SyndicateOS 调度逻辑**

```python
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
```

- [ ] **Step 2: 编写并运行临时测试脚本**

```bash
cat << 'EOF' > test_os.py
import asyncio
from agents.syndicate_os import SyndicateOS

async def test():
    os_system = SyndicateOS()
    res = await os_system.process_match("皇家马德里", "曼城", "竞彩足球")
    print("\n[最终裁决结果]\n", res["final_decision"])

if __name__ == "__main__":
    asyncio.run(test())
EOF
python3 test_os.py
```
Expected: PASS (终端应该依次打印出 Scout, Quant, Judge 的执行日志)

### Task 3: 替换旧的 AI 核心

**Files:**
- Modify: `market_sentinel.py`
- Modify: `run_live_decision.py`

- [ ] **Step 1: 修改 market_sentinel.py 使用新大脑**

修改 `market_sentinel.py` 第4行和第15行左右，使用 `SyndicateOS` 替代 `AINativeCoreAgent`。

```python
# 修改 market_sentinel.py
# 找到: from agents.ai_native_core import AINativeCoreAgent
# 替换为: from agents.syndicate_os import SyndicateOS

# 找到: self.agent = AINativeCoreAgent()
# 替换为: self.agent = SyndicateOS()

# 找到: result = await self.agent.process(state)
# 替换为:
# result = await self.agent.process_match(home, away, state["params"]["lottery_desc"])
# decision = result.get("final_decision", "")
```

- [ ] **Step 2: 修改 run_live_decision.py 使用新大脑**

修改 `run_live_decision.py`，删除 `AINativeCoreAgent` 的引用。

```python
# 修改 run_live_decision.py
# 找到: from agents.ai_native_core import AINativeCoreAgent
# 替换为: from agents.syndicate_os import SyndicateOS

# 找到: agent = AINativeCoreAgent()
# 替换为: agent = SyndicateOS()

# 找到: result = await agent.process(state)
# 替换为: result = await agent.process_match(home, away, "竞彩足球 (胜平负/让球)")

# 修改最后打印报告的逻辑，打印 scout, quant, judge 的三份报告。
```

- [ ] **Step 3: 运行完整真实链路测试**

```bash
python3 run_live_decision.py
```
Expected: 终端打印出完整的流水线日志，从抓取真实赛程，到 Scout 工作，Quant 工作，Judge 裁决，再到存入 SnapshotStore 回测库，全链路畅通无阻，且无任何单节点陷入死循环。

- [ ] **Step 4: Commit**

```bash
rm test_agents.py test_os.py
git add agents/syndicate_agents.py agents/syndicate_os.py market_sentinel.py run_live_decision.py
git commit -m "feat(p2): refactor to multi-agent society (Scout, Quant, Judge)"
```