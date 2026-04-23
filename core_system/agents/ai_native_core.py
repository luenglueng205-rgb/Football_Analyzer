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
        self.model = os.getenv("DEEPSEEK_REASONING_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
        api_key = os.getenv("DEEPSEEK_API_KEY", os.getenv("OPENAI_API_KEY", "dummy-key-for-test"))
        base_url = os.getenv("DEEPSEEK_API_BASE", os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1"))
        
        try:
            self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        except Exception as e:
            logger.error(f"OpenAI 初始化失败: {e}")
            self.client = None
            
        from tools.tool_registry_v2 import get_openai_tools
        from tools.mcp_discoverer import MCPToolDiscoverer
        
        self.mcp_discoverer = MCPToolDiscoverer()
        mcp_tools = self.mcp_discoverer.discover_local_tools()
        
        self.tools = get_openai_tools() + mcp_tools
        self.mcp_tool_mapping = self.mcp_discoverer.mcp_tool_mapping

        self._load_rules()
        
    def _load_rules(self):
        """加载知识库作为 System Prompt"""
        rule_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "LOTTERY_RULES.md")
        market_rule_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "16_MARKETS_RULES.md")
        
        self.system_prompt = ""
        if os.path.exists(rule_path):
            with open(rule_path, "r", encoding="utf-8") as f:
                self.system_prompt += f.read() + "\n\n"
                
        try:
            with open(market_rule_path, "r", encoding="utf-8") as f:
                markets_rules = f.read()
            self.system_prompt += f"\n\n{markets_rules}"
        except Exception:
            pass

        # 动态加载【灵魂记忆库】
        try:
            docs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")
            exp_path = os.path.join(docs_dir, "DYNAMIC_EXPERIENCE.md")
            if os.path.exists(exp_path):
                with open(exp_path, "r", encoding="utf-8") as f:
                    dynamic_exp = f.read()
                self.system_prompt += f"\n\n### 🧠 【你的终身经验法则 (Living Memory)】\n" \
                                      f"以下是你在过去的真实盈亏中用血泪换来的认知准则！\n" \
                                      f"你在执行任何分析时，**必须将以下经验作为最高优先级的风控指令**。任何违背这些法则的投注都是绝对禁止的！\n\n" \
                                      f"{dynamic_exp}"
        except Exception:
            pass
                
        if not self.system_prompt:
            self.system_prompt = "你是一名顶级的 AI 彩票精算师。你需要自主调用工具来分析赛事。"

    async def process_graph(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用 2026 版 StateGraph (DAG) 架构执行分析，避免 ReAct 死循环。
        """
        from core.state_graph_core import compile_football_graph
        graph = compile_football_graph()
        
        # Format initial state
        initial_state = {
            "match": f"{state.get('current_match', {}).get('home_team')} vs {state.get('current_match', {}).get('away_team')}",
            "data": state.get("params", {}),
            "hypothesis": "",
            "math_verified": False,
            "debate_passed": False,
            "final_decision": "",
            "messages": []
        }
        
        final_state = await graph.ainvoke(initial_state)
        
        # Convert graph output to standard report format
        report = f"# AI-Native Graph Analysis Report\n\n## 最终决策\n{final_state.get('final_decision')}\n\n## 验证状态\n数学验证: {final_state.get('math_verified')}\n风控辩论: {final_state.get('debate_passed')}"
        
        return {"report": report, "state": final_state}

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
            {"role": "user", "content": f"请为我执行【全流程死磕分析】：主队 '{home}' 对阵 客队 '{away}'。当前彩种为：'{lottery_desc}'。\n"
                                         f"【AI-Native 实战量化指令】：\n"
                                         f"=== 第一阶段：选场策略 (Match Selection) ===\n"
                                         f"1. 【联赛降维】：调用 get_league_persona 了解联赛方差特征。\n"
                                         f"2. 【经验召回与衰减】：调用 retrieve_team_memory 检索主客队教训，注意系统会自动过滤过时记忆。\n"
                                         f"3. 【赛前筛查】：判断本场比赛是否符合 {lottery_desc} 的选场逻辑。\n"
                                         f"=== 第二阶段：多维战术与数据分析 (Multi-Dimensional Analysis) ===\n"
                                         f"4. 【战术相克验证】：结合主客场战术风格进行微观相克推理。\n"
                                         f"5. 【情报与战意感知】：调用 gather_match_intelligence 获取突发新闻与战意考量。\n"
                                         f"6. 【历史数据 EV 引擎】：调用 deep_evaluate_all_markets 获取基于22万场历史数据的 EV。\n"
                                         f"7. 【让球整数铁律】：中国体彩常规让球永远是整数球！强队让-1刚好赢1球叫【让平】。\n"
                                         f"=== 第三阶段：死磕庄家思维与极限套利 (Bookmaker Mindset & Arbitrage) ===\n"
                                         f"8. 【获取外围活水】：调用 get_global_arbitrage_data 获取平博(Pinnacle)赔率、必发(Betfair)冷热数据以及百家赔率方差矩阵。如果因为没有匹配到赛事报错，则跳过后续套利步骤。\n"
                                         f"9. 【低赔诱盘排雷】：必须调用 identify_low_odds_trap 识别低于1.40的蚊子肉选项，防止掉入庄家诱导串关的陷阱。\n"
                                         f"10. 【时差套利扫描】：如果获取到了平博等外围赔率，调用 detect_latency_arbitrage，发现竞彩赔率大于外围去水真实赔率的绝对套利空间。\n"
                                         f"11. 【资金冷热探测】：如果获取到了必发数据，调用 detect_betfair_anomaly 对比隐含概率与资金热度，坚决防范“大热必死”和跟随“聪明钱冷遇”。\n"
                                         f"12. 【默契球/假球防范】：调用 analyze_kelly_variance 获取百家赔率离散度，若方差极低（共谋）或极高（分歧），需作为最高风控参考。\n"
                                         f"=== 第四阶段：投注与仓位风控 (Betting & Bankroll Strategy) ===\n"
                                         f"13. 【复式与双选策略】：严禁思维僵化！绝大多数情况下不要只买单选！如果发现一场比赛胜平负 EV 接近，或需要防冷门，必须采用『双选』(Double Chance)。你可以调用 `calculate_complex_parlay` 计算包含双选的复式投注总成本与最大回报，也可以调用 `calculate_chuantong_combinations` 计算足彩复式。\n"
                                         f"14. 【严格隔离】：只从属于【{lottery_desc}】专属玩法中挑选。\n"
                                         f"15. 【拓扑对冲与凯利风控】：利用复式投注构建对冲拓扑。计算出总注数后，结合凯利仓位给出精确的投注金额。EV为负，坚决空仓！\n"
                                         f"16. 【模拟选号与账本入库】：调用 generate_simulated_ticket 生成模拟选号单。如果是复式，请在 selection 字段或 reasoning 中写明包含的组合注数！"}
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
                
                # Pydantic v1 vs v2 compatibility fix: use model_dump() if available, else dict()
                if hasattr(response_message, "model_dump"):
                    msg_dict = response_message.model_dump(exclude_unset=True)
                elif hasattr(response_message, "dict"):
                    msg_dict = response_message.dict(exclude_unset=True)
                else:
                    msg_dict = {"role": response_message.role, "content": response_message.content}
                    if hasattr(response_message, "tool_calls") and response_message.tool_calls:
                        msg_dict["tool_calls"] = [{"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in response_message.tool_calls]

                messages.append(msg_dict)
                
                # 如果没有调用工具，说明推理完成
                if not getattr(response_message, "tool_calls", None):
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
                for tool_call in getattr(response_message, "tool_calls", []):
                    function_name = tool_call.function.name
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                        print(f"      [🛠️ MCP Tool] 正在调用 {function_name}({str(arguments)[:200]})")
                    except Exception as e:
                        logger.error(f"Failed to parse tool arguments for {function_name}: {e}")
                        error_msg = {
                            "ok": False,
                            "error": {"code": "BAD_ARGS", "message": f"Failed to parse arguments as JSON: {str(e)}"},
                            "meta": {"mock": False}
                        }
                        
                        msg_dict = {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "content": json.dumps(error_msg, ensure_ascii=False),
                            "name": function_name
                        }
                        messages.append(msg_dict)
                        
                        if function_name not in gathered_data:
                            gathered_data[function_name] = []
                        try:
                            gathered_data[function_name].append(str(error_msg)[:100])
                        except Exception:
                            pass
                            
                        continue
                        
                    try:
                        # 引入单次工具调用最高 15 秒的严格超时机制，防止死锁
                        if function_name in self.mcp_tool_mapping:
                            tool_result = await asyncio.wait_for(self.mcp_tool_mapping[function_name](**arguments), timeout=15.0)
                        else:
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

                    # 将工具返回结果喂给大模型
                    content_str = safe_content if isinstance(safe_content, str) else json.dumps(safe_content, ensure_ascii=False)
                    
                    msg_dict = {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "content": content_str,
                        "name": function_name
                    }
                    messages.append(msg_dict)
                    
                    if function_name not in gathered_data:
                        gathered_data[function_name] = []
                    try:
                        gathered_data[function_name].append(str(safe_content)[:100])
                    except Exception:
                        pass
                    
            except Exception as e:
                import traceback
                traceback.print_exc()
                logger.error(f"核心推理崩溃，触发系统级降级容灾: {e}")
                return {"ai_native_report": "系统遭遇毁灭性打击，已触发降级保护，分析中止。"}

        print(f"\n[🧠 AI-Native Brain] ⚠️ 达到最大思考循环次数，强行终止。")
        return {"ai_native_report": "推理过深，强行终止。请检查你的逻辑是否陷入死循环。"}
