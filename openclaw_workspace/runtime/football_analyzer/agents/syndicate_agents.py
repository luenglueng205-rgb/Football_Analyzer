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
                
            try:
                response = await self.client.chat.completions.create(**kwargs)
            except Exception as e:
                print(f"[🤖 {self.name}] LLM API 错误: {e}")
                return {"report": f"Agent {self.name} encountered a critical LLM API error: {e}", "data": gathered_data}
                
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

class FundamentalQuantAgent(BaseAgent):
    def __init__(self):
        prompt = "你是基本面原教旨主义者(Fundamentalist)。你坚信足球是实力的体现，无视盘口诱导。你主要依靠泊松分布、全景概率引擎、蒙特卡洛模拟和伤停情报来计算纯粹的胜负及各类衍生玩法概率。输出你认为最稳妥的选项和数学期望。"
        tools = ["calculate_poisson_probabilities", "calculate_all_markets", "run_monte_carlo_simulation", "get_team_stats"]
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

class JudgeAgent(BaseAgent):
    def __init__(self):
        prompt = """你是中国体育彩票的顶级策略专家与风控法官。
你的任务是阅读三大宽客的报告，并结合【体彩领域知识库】做出最聪明的决策。
你的绝对原则：
1. 【打破胜平负偏见】：绝对不要只盯着胜平负！如果发现某场比赛胜平负 EV 过低（蚊子肉），你必须去审视宽客提供的“全景衍生概率”（如总进球、半全场、上下单双），挑选出性价比最高的一个或两个具体玩法！
2. 【严格遵守规则】：如果是竞彩，注意同场互斥；如果是北单，注意让球小数。
3. 如果所有玩法都没有价值，或者宽客分歧巨大，坚决执行 Skip (放弃)。
你拥有唯一的开火权，并在最终报告中明确写出你推荐的【具体玩法】和【赔率/概率理由】。"""
        tools = ["check_bankroll", "execute_bet", "save_team_insight", "send_webhook_notification", "generate_qr_code"]
        super().__init__("Judge", prompt, tools)
