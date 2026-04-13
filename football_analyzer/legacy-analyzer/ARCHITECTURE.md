# 足球彩票分析系统 - 架构文档 v3.0

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           ModernAgentCore (现代化核心)                           │
│                              ┌──────────────────┐                               │
│                              │  Mode Selector   │  自动选择最佳模式               │
│                              │  (ReAct/Plan/AI) │                                │
│                              └────────┬─────────┘                               │
├───────────────────────────────────────┼─────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────────────────────────┴─────────────────────────────────────┐  │
│  │                        Agent 执行模式层                                       │  │
│  │                                                                              │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐          │  │
│  │  │  ReAct Agent    │  │ Plan&Execute    │  │   CrewAI        │          │  │
│  │  │  (推理-行动)    │  │ (规划-执行)     │  │  (多Agent协作) │          │  │
│  │  │                 │  │                 │  │                 │          │  │
│  │  │ • Thought循环   │  │ • 计划生成      │  │ • Crew编排     │          │  │
│  │  │ • Action执行   │  │ • 步骤执行      │  │ • Task定义     │          │  │
│  │  │ • Observation  │  │ • 依赖管理      │  │ • Process流程  │          │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘          │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                        │                                          │
├────────────────────────────────────────┼────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────────────────────────┴─────────────────────────────────────┐  │
│  │                         工具与知识层                                         │  │
│  │                                                                              │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐          │  │
│  │  │ DynamicTools   │  │ RAG Knowledge   │  │ StructuredLog   │          │  │
│  │  │ (动态工具选择) │  │ (向量知识库)    │  │ (结构化日志)   │          │  │
│  │  │                 │  │                 │  │                 │          │  │
│  │  │ • 上下文匹配   │  │ • 语义检索     │  │ • JSON日志     │          │  │
│  │  │ • 自动编排     │  │ • 相似度搜索   │  │ • Trace追踪    │          │  │
│  │  │ • 性能优化     │  │ • 混合检索     │  │ • 指标监控     │          │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘          │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                        │                                          │
├────────────────────────────────────────┼────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────────────────────────┴─────────────────────────────────────┐  │
│  │                         专业Agent层                                         │  │
│  │                                                                              │  │
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │  │
│  │   │ScoutAgent   │  │AnalystAgent│  │Strategist   │  │RiskManager │    │  │
│  │   │ (情报搜集)  │  │ (赔率分析)  │  │ (策略制定)  │  │ (风控)      │    │  │
│  │   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 核心模块说明

### 1. ModernAgentCore (现代化核心)

统一的Agent入口，支持多种执行模式：

```python
from core.modern_agent import ModernAgentCore, AgentMode

agent = ModernAgentCore()
agent.initialize()

# 自动模式选择
result = agent.analyze("分析今晚的比赛", context)

# 指定模式
agent.set_mode(AgentMode.REACT)
result = agent.analyze(...)
```

### 2. ReAct Pattern (推理-行动模式)

增强Agent推理能力：

```python
from core.react_pattern import ReActAgent

react = ReActAgent()
result = react.execute(
    query="分析赔率",
    context={"task_type": "analysis"}
)
# 完整推理链: Thought → Action → Observation → ...
```

**核心特性**:
- **Thought类型**: OBSERVATION, REASONING, PLANNING, REFLECTION, DECISION, HYPOTHESIS
- **Action类型**: FETCH_NEWS, ANALYZE_ODDS, CALCULATE_EV, GENERATE_STRATEGY等
- **动态工具选择**: 基于上下文自动选择最佳工具

### 3. Plan-and-Execute (规划-执行模式)

先规划后执行的Agent架构：

```python
from core.plan_execute import PlanAndExecuteAgent

plan_exec = PlanAndExecuteAgent()
result = plan_exec.run(
    query="完整分析",
    context={"task_type": "full_analysis"}
)
```

**工作流程**:
1. **计划生成**: 根据任务类型自动生成执行计划
2. **依赖管理**: 处理步骤间的依赖关系
3. **并行执行**: 支持步骤间并行执行
4. **重规划**: 失败时自动重新规划

### 4. RAG Knowledge Base (向量知识库)

基于向量检索的增强知识管理：

```python
from core.rag_knowledge import RagKnowledgeBase

rag = RagKnowledgeBase()

# 添加知识
rag.add_league_knowledge("epl", "英超", {"avg_goals": 2.8})
rag.add_team_knowledge("manu", "曼联", "英超", ["胜", "平"], {...})

# 语义检索
results = rag.search("进攻强队", top_k=5)
```

**功能**:
- 向量嵌入 + TF-IDF
- 语义相似度搜索
- 混合检索
- 持久化存储

### 5. Structured Logging & Tracing (结构化日志追踪)

完整的可观测性支持：

```python
from core.logging_tracing import traced, structured_logger

# 追踪装饰器
@traced(span_name="analyze", agent="AnalystAgent")
def analyze():
    ...

# 结构化日志
structured_logger.info("agent.start", "分析开始", 
                       metadata={"league": "英超"})
```

**特性**:
- JSON格式日志
- Trace ID链路追踪
- Span嵌套追踪
- 性能指标收集

### 6. Dynamic Tool Selection (动态工具选择)

基于上下文的智能工具选择：

```python
from core.dynamic_tool_selection import DynamicToolRegistry

registry = DynamicToolRegistry()

# 自动选择工具
tools = registry.select_tools(
    context={"query": "分析赔率", "task_type": "analysis"},
    max_tools=3
)
```

**工具类别**:
- SCOUT: 情报搜集工具
- ANALYSIS: 数据分析工具
- STRATEGY: 策略生成工具
- RISK: 风险管理工具
- MEMORY: 记忆存储工具
- RAG: 知识检索工具
- NOTIFICATION: 通知推送工具

### 7. CrewAI Integration (CrewAI集成)

现代化多Agent协作框架：

```python
from core.crewai_integration import FootballCrewFactory

factory = FootballCrewFactory()
crew = factory.create_full_analysis_crew(match_info)
result = factory.run_full_analysis(match_info)
```

**预定义Agent**:
- ScoutAgent: 情报分析专家
- AnalystAgent: 赔率分析专家
- StrategistAgent: 投注策略专家
- RiskManagerAgent: 风险管理专家

### 8. Orchestrator (调度Agent)

负责协调所有专业Agent，执行工作流：
- `full_analysis`: 情报→分析→策略→风控
- `quick_analysis`: 分析→策略
- `value_hunt`: 情报→分析
- `strategy_generate`: 策略→风控

### 9. ScoutAgent (情报搜集)
- 球队状态分析（伤病、阵容）
- 历史对战数据
- 近期表现趋势
- 联赛趋势分析

### 10. AnalystAgent (赔率分析)
- 赔率异常检测
- 盘口解读
- 价值投注识别
- 市场情绪分析

### 11. StrategistAgent (策略制定)
- M串N方案生成
- 资金分配建议
- 风险评估
- 期望值计算

### 12. RiskManagerAgent (风控)
- 仓位控制
- 止损机制
- Kelly Criterion
- 每日限额

### 13. MemorySystem (记忆系统)
- **EpisodicMemory**: 历史投注记录
- **SemanticMemory**: 联赛/球队知识
- **ProceduralMemory**: 策略执行流程

### 14. Reflector (反思引擎)
- 失败案例反思
- 连胜/连败分析
- 策略效果评估
- 教训提取

### 15. TaskScheduler (任务调度)
- 定时任务配置
- 每日自动分析
- 赛后结果更新
- 反思日志生成

### 16. WebhookServer (Webhook推送)
- 多渠道通知（微信/Telegram/邮件）
- 价值投注提醒
- 每日报告推送

## 数据流

```
用户输入 → ModernAgentCore → 模式选择
                            ↓
         ┌──────────────────┼──────────────────┐
         │                  │                  │
         ▼                  ▼                  ▼
    ReAct模式         Plan&Execute         CrewAI
         │                  │                  │
         └──────────────────┼──────────────────┘
                            ↓
                    DynamicTools + RAG
                            ↓
         ┌──────────────────┼──────────────────┐
         │                  │                  │
         ▼                  ▼                  ▼
   ScoutAgent        AnalystAgent       StrategistAgent
         │                  │                  │
         └──────────────────┴──────────────────┘
                            ↓
                    RiskManagerAgent
                            ↓
         ┌──────────────────┼──────────────────┐
         │                  │                  │
         ▼                  ▼                  ▼
   MemorySystem         Response          Webhook
```

## Agent间通信

```python
# 通过MessageBus进行Agent间消息传递
message = AgentMessage(
    sender="ScoutAgent",
    recipient="AnalystAgent",
    content={"matches": [...], "intelligence": {...}}
)
message_bus.send(message)

# Agent接收消息
messages = agent.receive_messages()
```

## 扩展性

系统设计遵循开闭原则，便于扩展：

1. **新增Agent**: 继承`BaseAgent`，实现`initialize()`、`process()`、`get_capabilities()`
2. **新增记忆类型**: 继承`BaseMemory`
3. **新增工作流**: 在`Orchestrator._workflow_templates`中添加
4. **新增通知渠道**: 继承`NotificationSender`
5. **新增工具**: 使用`DynamicToolRegistry.register_tool()`
6. **新增知识**: 使用`RagKnowledgeBase.add_knowledge()`

## 版本历史

- v1.0.0: 基础Agent架构
- v2.0.0: 
  - 多Agent协作架构
  - Memory System
  - 反思引擎
  - 对话式交互
  - 定时任务调度
  - Webhook推送
- v3.0.0: **现代化升级**
  - **ReAct Pattern**: 增强Agent推理能力
  - **Plan-and-Execute**: 先规划后执行模式
  - **RAG Knowledge Base**: 向量知识库支持
  - **Structured Logging**: 完整的日志追踪体系
  - **Dynamic Tool Selection**: 动态工具选择机制
  - **CrewAI Integration**: 现代化框架集成
