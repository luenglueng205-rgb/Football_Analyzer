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
