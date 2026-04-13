# 足球彩票分析系统 v2.0.0

## 概述

这是一个基于多Agent协作架构的智能足球彩票分析系统，支持对话式交互、定时任务调度和Webhook推送通知。

## 架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    FootballLotteryAgent                         │
│                      (主控Agent)                                │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  Orchestrator │    │ Conversation  │    │   Scheduler   │
│   (调度器)    │    │   (对话系统)   │    │   (调度器)    │
└───────────────┘    └───────────────┘    └───────────────┘
        │
        ▼
┌─────────┬─────────┬─────────┬─────────┐
│  Scout  │ Analyst │Strategist│RiskMgr │
│ Agent   │ Agent   │  Agent   │ Agent   │
└─────────┴─────────┴─────────┴─────────┘
```

## 目录结构

```
football-lottery-analyzer/
├── main_agent.py              # 主控Agent入口
├── core/                      # 核心模块
│   ├── base_agent.py         # Agent基类
│   ├── orchestrator.py       # 调度Agent
│   ├── scout_agent.py        # 情报搜集Agent
│   ├── analyst_agent.py       # 赔率分析Agent
│   ├── strategist_agent.py    # 策略制定Agent
│   ├── risk_manager.py        # 风控Agent
│   ├── conversation.py       # 对话系统
│   ├── webhook_server.py      # Webhook推送
│   └── scheduler.py           # 任务调度器
├── memory/                    # 记忆系统
│   ├── memory_system.py       # 记忆核心
│   ├── reflector.py           # 反思引擎
│   ├── pattern_recognizer.py  # 模式识别
│   └── learning_engine.py     # 学习引擎
├── data_fetch/               # 数据获取
│   ├── config.py             # 配置管理
│   ├── scraper.py            # 爬虫基类
│   └── odds_scraper.py       # 赔率爬虫
└── skills/                   # 分析技能
```

## 核心功能

### 1. 多Agent协作
- **ScoutAgent**: 情报搜集（阵容、伤病、历史对战）
- **AnalystAgent**: 赔率分析（异常检测、价值识别）
- **StrategistAgent**: 策略制定（M串N、资金分配）
- **RiskManagerAgent**: 风控（仓位控制、止损机制）

### 2. 记忆系统
- **EpisodicMemory**: 历史投注案例
- **SemanticMemory**: 联赛/球队知识
- **ProceduralMemory**: 策略执行流程

### 3. 反思引擎
- 从投注结果中学习
- 策略效果评估
- 自我纠错机制

### 4. 对话式交互
```python
agent = FootballLotteryAgent()
agent.chat("分析今晚的比赛")
agent.chat("推荐几场价值投注")
```

### 5. 定时任务调度
```python
agent.start_scheduler()  # 启动调度器
agent.scheduler.run_task_now("daily_analysis")  # 立即执行
```

## 使用方法

### 基本使用
```python
from main_agent import FootballLotteryAgent

# 初始化
agent = FootballLotteryAgent()

# 完整分析
result = agent.analyze("full_analysis", budget=100)

# 对话交互
response = agent.chat("推荐几场价值投注")

# 获取系统状态
status = agent.get_system_status()
```

### 工作流类型
- `full_analysis`: 完整分析（情报+赔率+策略+风控）
- `quick_analysis`: 快速分析（赔率+策略）
- `value_hunt`: 价值猎取（情报+赔率）
- `strategy_generate`: 策略生成（策略+风控）

### 命令行模式
```bash
# CLI模式
python main_agent.py --mode cli --workflow full_analysis --budget 100

# 对话模式
python main_agent.py --mode chat

# 守护进程模式
python main_agent.py --mode daemon
```

## 安装依赖

```bash
pip install requests beautifulsoup4 apscheduler
```

## 注意事项

1. 本系统仅供参考，投注有风险，请理性购彩
2. 历史数据分析不能保证未来结果
3. 请遵守各数据源的使用条款
