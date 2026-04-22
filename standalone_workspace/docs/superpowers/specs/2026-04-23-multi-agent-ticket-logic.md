# 实盘出票逻辑与多智能体协作优化方案

## 1. 进一步完善实盘出票逻辑 (Daily Ticket Generator)

为了解决单次对话大模型处理过多赛事的“上下文过载”问题，我们设计了分布式的实盘出票流水线：

- **新增文件**：[`standalone_workspace/agents/daily_ticket_generator.py`](file:///Volumes/J%20ZAO%209%20SER%201/Python/TRAE-SOLO/football_analyzer/standalone_workspace/agents/daily_ticket_generator.py)
- **运行机制**：该脚本会调用 `get_today_matches_list` 抓取当日所有在售体彩赛事，然后**并行（Async）**将每一场赛事丢入 StateGraph（或 AINativeCore）中进行预筛。
- **出票漏斗**：
    1. 外围水位探测（淘汰 60% 无套利场次）
    2. 基本面/xG 泊松测算（淘汰 30% EV < 0 的场次）
    3. 凯利风控拦截（防范黑天鹅，淘汰 5%）
    4. **最终出票（生成 `ticket`）**：对剩下的 5% 黄金场次，调用 `generate_simulated_ticket` 生成包含具体投注金额（基于凯利仓位）的模拟单，并聚合打印成最终推荐清单。

## 2. 智能体协作优化：从“大黑盒”到“流水线工厂”

为了深度利用 Agent 能力，我们重构了 [`state_graph_core.py`](file:///Volumes/J%20ZAO%209%20SER%201/Python/TRAE-SOLO/football_analyzer/standalone_workspace/core/state_graph_core.py)，将单一的“全能型大模型”拆分为三位高度专业化的专家智能体：

1. **📡 Data Agent (数据采集官)**: 
    - 专职负责调用 API（Pinnacle / Betfair）和爬虫抓取新闻。
    - **行为**：它是流水线的第一步，不负责判断，只负责将全网的“杂音”清洗为结构化的 `global_odds` 数据。
2. **🧮 Quant Agent (量化精算师)**:
    - 专职负责数学公式。它拿到 Data Agent 的数据后，立刻进行时差套利 (`detect_latency_arbitrage`) 和赔率方差 (`analyze_kelly_variance`) 的运算。
3. **🛡️ Risk Officer (风控法官)**:
    - 专职做减法。根据 Quant 的计算结果，执行“一票否决”。如果触发了“低赔陷阱”或“无套利空间”，立刻将状态置为 `skip`，提前终止运算（阻断爆仓风险，也节省 LLM Token）。

