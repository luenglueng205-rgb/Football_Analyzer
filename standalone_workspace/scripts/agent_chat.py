import os
import sys
import json

# ==============================================================================
# 由于真正的 NousResearch/hermes-agent 目前可能未在 PyPI 稳定发布，
# 这里我们自己手写一个极其轻量级的 OpenAI/Ollama 兼容的 Tool Calling 引擎，
# 完全模拟 Hermes Agent 的核心逻辑：
# 1. 把 Python 函数转换为 JSON Schema
# 2. 发给大模型
# 3. 解析大模型返回的 Tool Call
# 4. 执行本地函数
# 5. 把结果返回给大模型生成最终回答
# ==============================================================================

from openai import OpenAI
from hermes_adapter import analyze_football_match, reflect_football_match

# 设定模型端点 (假设你本地运行了 Ollama 的 hermes 模型，或者使用兼容 OpenAI 的 API)
# 这里使用通用的 OpenAI 客户端，如果你有真实的 key，可以在 .env 里配置
client = OpenAI(
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    api_key=os.getenv("OPENAI_API_KEY", "dummy_key_if_using_local_ollama")
)
MODEL_NAME = os.getenv("LLM_MODEL", "gpt-4o-mini") # 可以换成 "hermes-2-pro-llama-3-8b"

# 1. 将 Python 函数转化为大模型认识的 JSON Schema (Tool Definition)
tools = [
    {
        "type": "function",
        "function": {
            "name": "analyze_football_match",
            "description": "分析一场足球比赛，获取胜平负、让球、大小球的概率、期望值(EV)以及投注策略推荐。",
            "parameters": {
                "type": "object",
                "properties": {
                    "league": {"type": "string", "description": "联赛名称，例如 英超, 西甲"},
                    "home_team": {"type": "string", "description": "主队名称"},
                    "away_team": {"type": "string", "description": "客队名称"},
                    "lottery_type": {"type": "string", "enum": ["jingcai", "beijing", "traditional"], "description": "彩票玩法类型"}
                },
                "required": ["league", "home_team", "away_team"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reflect_football_match",
            "description": "在比赛结束后，将真实比分录入系统，触发系统的自我反思(Reflection)和记忆更新(Memory Update)。",
            "parameters": {
                "type": "object",
                "properties": {
                    "league": {"type": "string", "description": "联赛名称"},
                    "home_team": {"type": "string", "description": "主队名称"},
                    "away_team": {"type": "string", "description": "客队名称"},
                    "home_goals": {"type": "integer", "description": "主队实际进球数"},
                    "away_goals": {"type": "integer", "description": "客队实际进球数"}
                },
                "required": ["league", "home_team", "away_team", "home_goals", "away_goals"]
            }
        }
    }
]

# 函数路由表
available_functions = {
    "analyze_football_match": analyze_football_match,
    "reflect_football_match": reflect_football_match,
}

SYSTEM_PROMPT = """你是一个冷血无情的足球量化交易员 (Football Quant Trader)。
你的任务是帮助用户分析足球比赛并给出绝对理性的博彩建议。
你有两个强大的底层工具：
1. analyze_football_match: 用于赛前分析，获取胜率和期望值(EV)。
2. reflect_football_match: 用于赛后复盘，让系统吸取教训。

规则：
- 当用户问你比赛推荐时，你必须调用工具获取数据，绝对不能自己瞎猜。
- 拿到工具返回的数据后，用专业、冷酷的交易员口吻向用户汇报。
- 如果期望值(EV)小于0，直接告诉用户“不建议下注”。
"""

def chat_loop():
    print("==================================================")
    print(f"🤖 Hermes 量化交易员已上线！(模型: {MODEL_NAME})")
    print("支持自然语言提问，例如：")
    print(" - '今晚英超曼联打切尔西，竞彩怎么买？'")
    print(" - '帮我复盘一下昨天英超阿森纳2比0热刺的比赛'")
    print("输入 'exit' 退出")
    print("==================================================\n")
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    while True:
        try:
            user_input = input("\n👨 你: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ['exit', 'quit']:
                print("👋 交易员下线。")
                break
                
            messages.append({"role": "user", "content": user_input})
            
            print("🤖 思考中...")
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )
            
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls
            
            # 检查大模型是否决定调用工具
            if tool_calls:
                messages.append(response_message)
                
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_to_call = available_functions[function_name]
                    function_args = json.loads(tool_call.function.arguments)
                    
                    print(f"🛠️  大模型决定调用工具: {function_name}({function_args})")
                    
                    # 执行真正的 Python 代码
                    function_response = function_to_call(**function_args)
                    
                    # 将工具的执行结果返回给大模型
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
                    })
                
                # 获取大模型根据工具结果生成的最终回答
                print("🤖 分析数据中...")
                second_response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=messages
                )
                final_answer = second_response.choices[0].message.content
                print(f"\n🤖 交易员: {final_answer}")
                messages.append({"role": "assistant", "content": final_answer})
                
            else:
                # 大模型认为不需要调用工具，直接回答
                answer = response_message.content
                print(f"\n🤖 交易员: {answer}")
                messages.append({"role": "assistant", "content": answer})
                
        except Exception as e:
            print(f"\n❌ 发生错误: {e}")
            if "api_key" in str(e).lower() or "authentication" in str(e).lower():
                print("提示: 你似乎没有配置有效的 OPENAI_API_KEY。请在 .env 中配置，或者启动本地 Ollama 服务。")

if __name__ == "__main__":
    chat_loop()
