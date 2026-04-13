import os
import sys
import json
from typing import Dict, Any

# 导入我们已经重构好的多智能体系统
from main import FootballLotteryMultiAgentSystem

# 实例化我们的系统 (作为底层算力和逻辑引擎)
lottery_system = FootballLotteryMultiAgentSystem()

# =====================================================================
# 以下是为 Hermes Agent (或任何支持 Function Calling 的大模型) 准备的工具定义
# =====================================================================

def analyze_football_match(league: str, home_team: str, away_team: str, lottery_type: str = "jingcai") -> str:
    """
    分析一场足球比赛，获取胜平负、让球、大小球的概率、期望值(EV)以及投注策略推荐。
    
    :param league: 联赛名称，例如 "英超", "西甲"
    :param home_team: 主队名称
    :param away_team: 客队名称
    :param lottery_type: 彩票玩法，可选值: "jingcai" (竞彩), "beijing" (北单), "traditional" (传统足彩)
    :return: 包含多Agent深度分析报告的字符串
    """
    print(f"\n[Hermes Tool Execution] 正在调用底层引擎分析: {home_team} vs {away_team} ({lottery_type})...")
    
    # 调用底层的高效 Handoff 架构
    result = lottery_system.analyze(
        league=league,
        home_team=home_team,
        away_team=away_team,
        lottery_type=lottery_type,
        mode="full"
    )
    
    # 将 JSON 结果格式化为易读的文本，返回给大模型
    return lottery_system._format_result(result)


def reflect_football_match(league: str, home_team: str, away_team: str, home_goals: int, away_goals: int) -> str:
    """
    在比赛结束后，将真实比分录入系统，触发系统的自我反思(Reflection)和记忆更新(Memory Update)。
    
    :param league: 联赛名称
    :param home_team: 主队名称
    :param away_team: 客队名称
    :param home_goals: 主队实际进球数
    :param away_goals: 客队实际进球数
    :return: 复盘结果与提取的教训
    """
    print(f"\n[Hermes Tool Execution] 正在执行赛后复盘: {home_team} {home_goals}-{away_goals} {away_team}...")
    
    match_result = {"home_goals": home_goals, "away_goals": away_goals}
    
    try:
        lottery_system.reflect(
            league=league,
            home_team=home_team,
            away_team=away_team,
            match_result=match_result
        )
        return f"成功完成复盘！已将 {home_team} {home_goals}-{away_goals} {away_team} 的结果写入记忆库，并更新了策略置信度。"
    except Exception as e:
        return f"复盘失败: {str(e)}"

# =====================================================================
# Hermes Agent 注册配置示例 (伪代码，展示架构)
# =====================================================================
"""
from hermes_agent import Agent, Tool

# 1. 注册工具
analyze_tool = Tool.from_function(analyze_football_match)
reflect_tool = Tool.from_function(reflect_football_match)

# 2. 初始化 Hermes Agent
agent = Agent(
    model="hermes-2-pro-llama-3-8b", # 本地 Ollama 模型
    tools=[analyze_tool, reflect_tool],
    system_prompt="你是一个冷血无情的足球量化交易员。当用户问你比赛时，必须调用 analyze_football_match 工具获取数据，不要自己瞎猜。只推荐 EV > 0 的比赛。"
)

# 3. 运行交互
response = agent.chat("今晚英超曼联对切尔西，竞彩怎么买？")
print(response)
"""

if __name__ == "__main__":
    print("Hermes Adapter 工具封装完成。可以被 hermes-agent 直接导入使用。")
