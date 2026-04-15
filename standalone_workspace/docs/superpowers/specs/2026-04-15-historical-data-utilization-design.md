# 中国体彩历史数据混合降维回测系统 (Historical Data Utilization) 设计规范

## 1. 核心目标 (Goal)
利用 221,415 场历史足球比赛数据（仅包含胜平负初赔和比分），通过“比分标签化”与“泊松逆向工程”的双重降维打击，为 AI 原生足球分析系统注入海量情景记忆（盘感），并构建一个能够验证系统真实 ROI 的时间机器回测沙盒。

## 2. 架构设计 (Architecture)

### 2.1 方案 C：混合降维打击 (Hybrid Dimensionality Reduction)
本系统采用混合架构来解决历史数据缺乏衍生玩法（让球、总进球、半全场等）赔率的问题：
- **记忆层（比分穷举映射）**：在数据注入 ChromaDB 时，直接将比分结果（如 `2-1`）降维翻译为体彩标签（如 `[主胜] [让平] [3球] [胜胜] [上单]`），让 ScoutAgent 能够直接通过文本语义检索出特定赔率结构下的历史打出概率。
- **回测层（泊松逆向重构）**：在回测沙盒中，通过现有的 `LotteryMathEngine`，将历史胜平负初赔反向计算出当场的预期进球数 (xG)，进而生成出当年该场比赛所有衍生玩法的理论赔率，供 SyndicateOS 进行虚拟下注。

### 2.2 核心模块 (Core Components)

#### 模块 1：数据翻译与注入引擎 (Data Translator & Ingestion)
- **文件**：修改 `standalone_workspace/scripts/data_ingestion_pipeline.py`
- **功能**：
  - 增加 `_translate_score_to_tags` 函数。
  - 将 `home_goals` 和 `away_goals` 转换为体彩特有标签。
  - 标签示例：`Jingcai_Result_HomeWin`, `Jingcai_Handicap_-1_Draw`, `Jingcai_Total_3`, `Beidan_ShangDan`。
  - 将带有丰富标签的文本和 Metadata 注入 ChromaDB。

#### 模块 2：ScoutAgent 记忆检索增强 (Scout Memory Retrieval)
- **文件**：修改 `standalone_workspace/agents/async_scout.py`
- **功能**：
  - 在情报收集阶段，新增调用 `MemoryManager.retrieve_memory` 的逻辑。
  - 构建检索 Query：提取当前比赛的联赛和赔率特征（例如：“英超 主胜赔率2.10附近的比赛”）。
  - 将检索到的历史相似比赛的真实赛果统计数据，强行插入 Scout 的最终分析报告中，作为“历史盘感”输出给 Judge。

#### 模块 3：时光机回测沙盒 (Time-Machine Backtester)
- **文件**：新建 `standalone_workspace/scripts/historical_backtest_engine.py`
- **功能**：
  - **历史重演**：随机或按时间顺序抽取过去某天的比赛列表。
  - **赔率重构**：调用 `LotteryMathEngine.calculate_all_markets(home_xg, away_xg)`。由于我们没有历史的 xG，沙盒需要实现一个 `reverse_engineer_xg(home_odds, away_odds)` 方法，通过基础赔率估算 xG。
  - **虚拟下注**：将重构后的赔率数据和基础面对阵信息喂给 `SyndicateOS`。
  - **对账与 ROI 计算**：将 OS 的决策（如推荐买总进球 3 球）与历史真实比分进行比对，计算虚拟资金的盈亏 (PnL)。

## 3. 数据流向 (Data Flow)
1. **注入期**：`JSON 数据` -> `标签翻译器` -> `ChromaDB Episodic Memory`。
2. **决策期**：`SyndicateOS (Scout)` -> `ChromaDB 检索` -> `融合盘感的情报报告` -> `Judge 裁决`。
3. **回测期**：`JSON 历史某日数据` -> `泊松逆向生成衍生赔率` -> `SyndicateOS 虚拟决策` -> `真实比分对账` -> `ROI 报表`。

## 4. 边界条件与错误处理 (Constraints & Error Handling)
- **Token 限制**：ChromaDB 注入过程必须支持断点续传（已实现），并控制 Batch Size 避免大模型 Embedding API 限流。
- **逆向计算异常**：如果历史基础赔率极度扭曲（如主胜 1.01，客胜 50.0），导致 xG 反算失败，沙盒应自动跳过该场比赛，不计入回测。
- **无记忆兜底**：如果 Scout 在 ChromaDB 中找不到高度相似的赔率比赛，应在报告中明确声明“历史盘感样本不足，依赖基本面分析”。