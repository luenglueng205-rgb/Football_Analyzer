import os
import json
import asyncio
import logging
from typing import Dict, Any, List
from openai import AsyncOpenAI
from dotenv import load_dotenv

from agents.async_base import AsyncBaseAgent
from tools.tool_registry import get_scout_tools
from tools.analyzer_api import AnalyzerAPI

# Try to load env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

class AsyncReActScoutAgent(AsyncBaseAgent):
    """
    2026 Next-Gen ReAct Scout Agent
    自主决策使用哪些工具来收集情报，而不是静态写死流程。
    """
    def __init__(self):
        super().__init__("scout", "全能情报侦察兵 (ReAct)")
        # 兼容兼容第三方 OpenAI 代理（如 DeepSeek/Claude 等的 API 包装）
        base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        api_key = os.getenv("OPENAI_API_KEY", "dummy-key-for-test")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        try:
            self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        except Exception as e:
            print(f"⚠️ OpenAI 初始化失败: {e}. 将使用降级 Mock 模式。")
            self.client = None
        self.tools = get_scout_tools()

    async def _execute_tool(self, function_name: str, arguments: Dict[str, Any]) -> Any:
        """执行本地 Python 函数映射"""
        print(f"      [🛠️ Tool Use] 正在调用 {function_name}({json.dumps(arguments, ensure_ascii=False)})")
        
        # 实际生产中由于 requests 是阻塞的，我们需要放到线程池或者改写 AnalyzerAPI 为 aiohttp
        # 这里用 asyncio.to_thread 包裹同步 API 以防阻塞主 EventLoop
        
        if function_name == "get_team_stats":
            return await asyncio.to_thread(AnalyzerAPI.get_team_stats, **arguments)
        elif function_name == "get_recent_matches":
            return await asyncio.to_thread(AnalyzerAPI.get_recent_matches, **arguments)
        elif function_name == "get_live_injuries":
            return await asyncio.to_thread(AnalyzerAPI.get_live_injuries, **arguments)
        elif function_name == "get_live_odds":
            return await asyncio.to_thread(AnalyzerAPI.get_live_odds, **arguments)
        elif function_name == "search_knowledge":
            return await asyncio.to_thread(AnalyzerAPI.search_knowledge, **arguments)
        else:
            return {"error": f"Unknown function: {function_name}"}

    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        match = state.get("current_match", {})
        home = match.get("home", "主队")
        away = match.get("away", "客队")
        league = match.get("league", "未知联赛")
        
        print(f"\n    [Scout(ReAct)] 接收到任务：分析 {league} - {home} vs {away}")
        print(f"    [Scout(ReAct)] 正在思考需要拉取哪些数据...")

        messages = [
            {"role": "system", "content": "你是一个世界顶级的体彩情报专家。你需要通过调用提供的工具来搜集对阵双方的基本面数据、伤停情况、以及实时盘口。\n请根据具体对阵，自主决定要调用哪些工具（可以并发调用多个）。当收集到足够的情报后，给出总结性的情报简报。"},
            {"role": "user", "content": f"请为这场比赛收集情报：{league}联赛，主队 '{home}' 对阵 客队 '{away}'。重点关注伤病和最新水位。"}
        ]

        if self.client is None:
            return await self._mock_process(home, away)

        max_loops = 5
        gathered_data = {}
        
        try:
            for i in range(max_loops):
                # 1. 呼叫大模型
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=self.tools,
                    tool_choice="auto"
                )
                
                response_message = response.choices[0].message
                messages.append(response_message)
                
                # 2. 如果模型决定不再调用工具，则说明情报收集完成
                if not response_message.tool_calls:
                    print(f"    [Scout(ReAct)] 情报总结完成。")
                    return {
                        "scout_data": {
                            "raw_data": gathered_data,
                            "ai_report": response_message.content
                        }
                    }
                
                # 3. 如果模型决定调用工具，执行这些工具
                tool_calls = response_message.tool_calls
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                    except Exception:
                        arguments = {}
                        
                    # 执行工具
                    tool_result = await self._execute_tool(function_name, arguments)
                    
                    # 记录结果
                    if function_name not in gathered_data:
                        gathered_data[function_name] = []
                    gathered_data[function_name].append(tool_result)
                    
                    # 将工具结果反馈给模型
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(tool_result, ensure_ascii=False)[:2000] # 截断防爆Token
                    })
                    
        except Exception as e:
            # 捕获没有配对 API KEY 的错误，走降级 Mock 模式
            print(f"    ⚠️ [Scout(ReAct)] LLM 调用异常 (可能是未配置 Key) : {e}")
            print(f"    ⚠️ [Scout(ReAct)] 自动降级为 Mock 工具流...")
            return await self._mock_process(home, away)

        return {"scout_data": gathered_data}
        
    async def _mock_process(self, home: str, away: str) -> Dict[str, Any]:
        """本地无 Key 时的降级展示模式"""
        # 模拟 ReAct 思考过程
        print(f"      [🛠️ Tool Use] 正在调用 get_live_injuries({{'team_name': '{home}'}})")
        await asyncio.sleep(0.5)
        print(f"      [🛠️ Tool Use] 正在调用 get_live_injuries({{'team_name': '{away}'}})")
        await asyncio.sleep(0.5)
        print(f"      [🛠️ Tool Use] 正在调用 get_live_odds({{'home_team': '{home}', 'away_team': '{away}'}})")
        await asyncio.sleep(0.5)
        
        return {
            "scout_data": {
                "ai_report": f"{home} 主力前锋伤停，{away} 阵容齐整。亚指初盘主让半球，即时盘退盘至平半，水位震荡，存在客队爆冷可能。",
                "mocked": True
            }
        }
