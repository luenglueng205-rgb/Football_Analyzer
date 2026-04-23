# 历史数据终极深化与战术相克引擎 (Historical Data Deepening & Tactical Matrix)

## 1. 目标 (Goal)
在不增加系统主流程负担（保持极简、零阻塞、事件驱动）的前提下，挖掘 22 万场历史数据的剩余价值。为系统增加“可视化战报生成 (Daily Report)”、“庄家杀猪盘异常探测 (Anomaly Detector)”和“球队战术相克图谱 (Tactical Matrix)”三大 AI 原生能力，并将其全部封装为 MCP Tools 供主脑自主调用。

## 2. 架构设计 (Architecture)

### 2.1 模块 A：可视化复盘与战报生成 (`daily_reporter.py`)
- **触发机制**：由 `EventBus` 抛出的 `DAILY_SETTLEMENT_COMPLETE` 或 `EVOLUTION_COMPLETE` 事件异步触发。
- **功能**：汇总当天的投注记录（从 `BettingLedger`）、回测盈亏、以及基因权重变化（从 `hyperparams.json`），生成一份排版精美的 Markdown 战报。
- **AI 原生体现**：这是一个独立的 Tool，主 Agent 收到事件后自主决定生成报告并推送给主公。

### 2.2 模块 B：庄家杀猪盘异常探测器 (`anomaly_detector.py`)
- **触发机制**：赛前看盘时，门神 `RouterAgent` 判定比赛存在高风险，或主 Agent 在决策前主动调用。
- **功能**：封装几个极简的数学特征公式（如“强队让深盘但临场水位异常升高”、“必发交易量与赔率走势背离”）。该工具不遍历全量数据，而是基于历史回测得出的“血的教训”直接进行规则匹配。
- **AI 原生体现**：作为 MCP Tool `detect_bookmaker_anomaly` 暴露。它就像是军师手里的一个“照妖镜”，觉得有诈就拿出来照一下。

### 2.3 模块 C：战术相克知识图谱 (`tactical_matrix_miner.py`)
- **触发机制**：系统空闲时的后台独立批处理脚本。
- **功能**：遍历 ChromaDB 中的 22 万场数据，提取出特定的冷门赛果（如弱队赢强队），利用简单的逻辑打上“防反克传控”、“大巴克高位逼抢”的标签，并作为 `Insight` 存入 `MemoryManager`。
- **AI 原生体现**：**复用现有的 ChromaDB 基础设施**。实战中，主 Agent 只需要像往常一样调用 `retrieve_memory`，就能瞬间提取出“A队战术克制B队”的隐藏羁绊，完全不增加额外系统负担。

## 3. 双端部署策略 (Deployment)
1. 所有的 Python 类都放置在 `standalone_workspace/tools/` 目录下。
2. `AgenticCore` 的 `self.tools` 列表中增加这两个新工具。
3. `openclaw_workspace/src/mcp_server.py` 同步增加这两个工具的暴露和调用路由。
4. 使用 `rsync` 保持双版本严格同步。