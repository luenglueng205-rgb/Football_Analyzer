import asyncio
import os
import json
import logging
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

from openai import AsyncOpenAI

from tools.tool_registry_v2 import get_openai_tools, execute_tool
from agents.debate_judge import MultiAgentDebateEngine

logger = logging.getLogger(__name__)

class AINativeCoreAgent:
    """
    2026 纯正 AI-Native 核心推理者 (The LLM Brain)
    不再依赖硬编码的 Python 工作流，而是完全依赖 LLM 自主规划和调用 MCP Tools。
    业务规则通过 System Prompt (LOTTERY_RULES.md) 注入。
    """
    def __init__(self):
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        api_key = os.getenv("OPENAI_API_KEY", "dummy-key-for-test")
        
        try:
            self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        except Exception as e:
            logger.error(f"OpenAI 初始化失败: {e}")
            self.client = None
            
        self._load_rules()
        
    def _load_rules(self):
        """加载知识库作为 System Prompt"""
        rule_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "LOTTERY_RULES.md")
        market_rule_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "16_MARKETS_RULES.md")
        
        self.system_prompt = ""
        if os.path.exists(rule_path):
            with open(rule_path, "r", encoding="utf-8") as f:
                self.system_prompt += f.read() + "\n\n"
                
        if os.path.exists(market_rule_path):
            with open(market_rule_path, "r", encoding="utf-8") as f:
                self.system_prompt += f.read()
                
        if not self.system_prompt:
            self.system_prompt = "你是一名顶级的 AI 彩票精算师。你需要自主调用工具来分析赛事。"

    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """单脑/多脑的 ReAct 循环入口"""
        if not self.client:
            print("⚠️ 未配置 API KEY，降级为 Mock 模式。")
            return {"ai_native_report": "降级模式：模拟的最终投注建议。"}
            
        match_info = state.get("current_match", {})
        home = match_info.get("home_team", "主队")
        away = match_info.get("away_team", "客队")
        lottery_type = state.get("params", {}).get("lottery_type", "jingcai")
        lottery_desc = state.get("params", {}).get("lottery_desc", lottery_type)
        
        print(f"\n[🧠 AI-Native Brain] 接收到任务：{home} vs {away} (玩法: {lottery_desc})")
        print(f"[🧠 AI-Native Brain] 正在阅读《LOTTERY_RULES.md》与《16_MARKETS_RULES.md》并开始自主规划分析链路...")

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"请为我深度量化分析这场比赛：主队 '{home}' 对阵 客队 '{away}'。当前彩种为：'{lottery_desc}'。\n"
                                         f"【最高指令】：你是一个统治华尔街的数字博彩基金大脑。你需要自主调用所有可用工具：\n"
                                         f"1. 必须调用 check_bankroll 查看当前真实可用资金。\n"
                                         f"2. 【长期记忆】：在开始分析前，必须调用 retrieve_team_memory 提取主客队的历史经验！\n"
                                         f"3. 必须分析亚盘水位异动和欧亚转换偏差（不要只用泊松）。\n"
                                         f"4. 决定投资后，必须调用 execute_bet 真正生成实单并写入账本！\n"
                                         f"5. 【经验沉淀】：在给出最终结论前，必须调用 save_team_insight 将你对本场比赛两队的战术发现或盘口规律分别存入记忆库，供未来使用！\n"
                                         f"6. 【极致闭环】：如果发现多个机会，必须调用 calculate_parlay 计算串关组合。决定下注后，必须调用 generate_qr_code 生成物理二维码，并调用 send_webhook_notification 将决策推送到手机！\n"
                                         f"7. 【MOCK 数据隔离】：如果你调用的工具返回了 `\"meta\": {{\"mock\": true}}`，说明该数据为模拟/离线数据，不可信。你在最终决策时，必须对这类数据降权，或者直接拒绝基于该数据进行大额下注（仅输出观察不下注，或者极小仓位）。"}
        ]

        max_loops = 15  # 允许 LLM 最多进行 15 轮的连续工具调用
        gathered_data = {}
        
        for i in range(max_loops):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=get_openai_tools(),
                    tool_choice="auto"
                )
                
                response_message = response.choices[0].message
                messages.append(response_message)
                
                # 如果没有调用工具，说明推理完成
                if not response_message.tool_calls:
                    # 在最终输出前，拉起 Multi-Agent Debate 进行终极风控裁决
                    debate_engine = MultiAgentDebateEngine()
                    debate_result = await debate_engine.run_debate(
                        match_info=f"{home} vs {away}", 
                        evidence=json.dumps(gathered_data, ensure_ascii=False)[:3000]
                    )
                    
                    print(f"\n[🧠 AI-Native Brain] 🏆 量化分析与法官裁决完成！")
                    return {
                        "ai_native_report": response_message.content,
                        "debate_judge_report": debate_result,
                        "raw_data": gathered_data
                    }
                
                # 执行工具
                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                        print(f"      [🛠️ MCP Tool] 正在调用 {function_name}({str(arguments)[:200]})")
                    except Exception as e:
                        logger.error(f"Failed to parse tool arguments for {function_name}: {e}")
                        error_msg = {"ok": False, "error": {"code": "BAD_ARGS", "message": f"Failed to parse arguments as JSON: {str(e)}"}, "meta": {"mock": False}}
                        if function_name not in gathered_data:
                            gathered_data[function_name] = []
                        gathered_data[function_name].append(error_msg)
                        messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": str(error_msg)
                        })
                        continue
                        
                    try:
                        # 引入单次工具调用最高 15 秒的严格超时机制，防止死锁
                        tool_result = await asyncio.wait_for(execute_tool(function_name, arguments), timeout=15.0)
                    except asyncio.TimeoutError:
                        logger.error(f"工具调用超时 ({function_name})")
                        tool_result = {"ok": False, "error": f"Timeout execution {function_name} after 15 seconds. Proceed with alternative tools."}
                    except Exception as e:
                        logger.error(f"工具执行异常 ({function_name}): {e}")
                        tool_result = {"ok": False, "error": f"Tool execution failed: {str(e)}. Do not retry this exact same tool."}
                    
                    # 语义压缩：防止大 payload 撑爆上下文或阻塞 JSON 解析
                    try:
                        result_str = str(tool_result)
                        if len(result_str) > 3000:
                            result_str = result_str[:1500] + "\n...[CONTENT TRUNCATED FOR CONTEXT WINDOW]...\n" + result_str[-1500:]
                            safe_content = result_str
                        else:
                            safe_content = tool_result
                    except Exception:
                        safe_content = {"error": "Unserializable or extremely large tool response."}

                    if function_name not in gathered_data:
                        gathered_data[function_name] = []
                    # 仅保存压缩后的安全内容
                    gathered_data[function_name].append(safe_content)
                        
                    # 将工具返回结果喂给大模型
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": str(safe_content)
                    })
                    
            except Exception as e:
                logger.error(f"核心推理崩溃，触发系统级降级容灾: {e}")
                return {"ai_native_report": "系统遭遇毁灭性打击，已触发降级保护，分析中止。"}

        print(f"\n[🧠 AI-Native Brain] ⚠️ 达到最大思考循环次数，强行终止。")
        return {"ai_native_report": "推理过深，强行终止。请检查你的逻辑是否陷入死循环。"}
