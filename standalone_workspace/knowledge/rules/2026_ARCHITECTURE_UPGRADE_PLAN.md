# 2026 AI 彩票分析系统架构升级蓝图 (Next-Gen Architecture Plan)

基于 2026 年最前沿的 AI Agent 技术趋势，以及中国体育彩票（竞彩、北单、传统足彩）的专业需求，我们制定了以下四个阶段的升级计划。

## 阶段一：异步图状态机引擎 (Async Graph State Engine) - 当前最高优先级
**目标**：彻底解决同步阻塞导致的分析缓慢问题，特别是针对“传统足彩 14 场”等需要大批量并发分析的场景。用基于状态图（StateGraph）的确定性流转，取代目前容易死循环的 `Swarm Handoff`。
**具体行动**：
1. 实现 `AsyncBaseAgent`，全面支持 `asyncio`。
2. 构建轻量级、无依赖的 `AsyncStateGraph` 编排器（借鉴 LangGraph 思想），将全局上下文作为 `State` 在图节点中流转。
3. 针对“传统足彩”场景，实现并发 14 场基本面/赔率分析，最后汇聚到 `PortfolioAgent`（投资组合专家）进行缩水过滤。

## 阶段二：原生工具调用与多模态感知 (Native Tool Calling & Vision)
**目标**：抛弃“全量拉取数据塞给 LLM”的低效做法，转为按需自主调用的 ReAct 模式。
**具体行动**：
1. 封装 `AnalyzerAPI` 的各个方法为独立的异步工具（JSON Schema）。
2. `ScoutAgent` 升级为具备工具调用能力的 ReAct Agent，自主决定是否查询伤病、天气或历史战绩。
3. 引入 Vision 能力，允许 Agent 识别并解读实时的“赔率走势图”、“必发交易量柱状图”，捕捉肉眼可见的“诱盘”特征。

## 阶段三：时序知识图谱与强化学习 (Temporal Graph RAG & RLMF)
**目标**：升级反思引擎，不再只是简单的置信度加减，而是能挖掘“特定裁判+特定盘口+特定天气”的隐藏操盘套路。
**具体行动**：
1. 将本地 `learned_lessons.json` 升级为向量数据库（如 ChromaDB/Qdrant）或轻量级图数据库。
2. 实现 RAG 检索：每次预测前，自动检索历史上最相似的盘口走势和翻车教训。
3. 引入 RLMF（基于市场反馈的强化学习），闭环修正图谱中各项因子的权重。

## 阶段四：常驻事件驱动与实时监控 (Event-Driven Daemon)
**目标**：适应临场盘口的瞬息万变，从“单次静态分析”升级为“实时响应流”。
**具体行动**：
1. 引入 WebSocket/SSE 监听实时赔率流。
2. 将 `AnalystAgent` 和 `RiskManagerAgent` 部署为常驻后台进程（Daemon）。
3. 当触发特定阈值（如：赛前 30 分钟主队水位突然暴跌）时，瞬间唤醒 Agent 进行重算并发出风控警报。
