import asyncio
import json
import time
from typing import Dict, Any

from agents.ai_native_core import AINativeCoreAgent
from tools.mcp_tools import TOOL_MAPPING

# 模拟一个会超时的恶劣工具
async def malicious_timeout_tool(**kwargs):
    print("    [💣 破坏性测试] 模拟工具卡死 60 秒...")
    await asyncio.sleep(60)
    return {"data": "This should not be reached"}

# 模拟一个返回超大上下文的内存炸弹工具
async def malicious_context_bomb_tool(**kwargs):
    print("    [💣 破坏性测试] 模拟返回 10MB 的垃圾数据...")
    return {"data": "A" * 10_000_000}

# 模拟一个无限报错的工具，诱导 LLM 陷入重试死循环
async def malicious_error_storm_tool(**kwargs):
    print("    [💣 破坏性测试] 模拟工具 500 报错...")
    raise ValueError("Internal Server Error 500 - Database connection lost")

async def run_extreme_stress_test():
    print("="*60)
    print("🚀 启动 AI-Native 架构极限边缘测试 (Extreme Edge Case Test)")
    print("="*60)

    # 替换系统中的正常工具为恶意工具，观察大脑(LLM)的反应
    original_odds = TOOL_MAPPING.get("get_live_odds")
    original_stats = TOOL_MAPPING.get("get_team_stats")
    original_intel = TOOL_MAPPING.get("analyze_dark_intel")

    TOOL_MAPPING["get_live_odds"] = malicious_timeout_tool
    TOOL_MAPPING["get_team_stats"] = malicious_context_bomb_tool
    TOOL_MAPPING["analyze_dark_intel"] = malicious_error_storm_tool

    agent = AINativeCoreAgent()
    
    # 缩短超时时间以便快速测试
    # 注意：ai_native_core.py 中目前没有 asyncio.wait_for，这会暴露系统的脆弱性
    
    state = {
        "current_match": {
            "league": "欧冠",
            "home_team": "阿森纳",
            "away_team": "拜仁慕尼黑"
        },
        "params": {
            "lottery_type": "jingcai",
            "lottery_desc": "竞彩足球"
        }
    }

    start_time = time.time()
    try:
        # 这里我们设置一个外部超时，看看 Agent 内部是否自己处理了超时
        result = await asyncio.wait_for(agent.process(state), timeout=180.0)
        print("\n✅ 测试完成，系统存活。结果:", str(result)[:500])
    except asyncio.TimeoutError:
        print("\n❌ 致命缺陷发现：系统被恶意工具阻塞，未实现内部超时控制 (Timeout)，导致整个图流卡死！")
    except Exception as e:
        print(f"\n❌ 致命缺陷发现：系统崩溃，未捕获的异常: {e}")
    finally:
        print(f"耗时: {time.time() - start_time:.2f} 秒")
        
        # 恢复环境
        TOOL_MAPPING["get_live_odds"] = original_odds
        TOOL_MAPPING["get_team_stats"] = original_stats
        TOOL_MAPPING["analyze_dark_intel"] = original_intel

if __name__ == "__main__":
    asyncio.run(run_extreme_stress_test())
