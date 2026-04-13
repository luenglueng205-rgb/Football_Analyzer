---
name: football-lottery-analyst
description: 中国体育彩票足球彩票智能分析系统 v3.0 Pro，支持竞彩足球、北京单场、传统足彩三大玩法全覆盖。核心功能包括：泊松进球预测、盘口深度分析、跨玩法协同策略、SP值挖掘、奖池分析、多Agent协作、自进化长记忆。
trigger:
  - "竞彩"
  - "足彩分析"
  - "赔率分析"
  - "价值投注"
  - "串关方案"
  - "足球预测"
  - "博彩分析"
  - "投注策略"
  - "北单"
  - "传统足彩"
  - "今天买什么"
  - "分析比赛"
  - "进球预测"
  - "比分预测"
  - "盘口分析"
  - "胜平负"
  - "让球胜平负"
  - "总进球"
  - "半全场"
  - "上下单双"
  - "SP值"
  - "14场"
  - "任选9"
  - "泊松模型"
  - "跨玩法"
  - "套利"
  - "奖池"
metadata: {"openclaw": {
  "requires": {"bins": ["python3"], "env": [], "config": []},
  "os": ["darwin", "linux"],
  "always": true
},
  "workbuddy": {
    "capabilities": ["multi_agent", "file_sandbox", "local_execution", "dynamic_skill_discovery", "background_daemons"],
    "permissions": ["folder_read", "folder_write"]
  }
}
---

# 足球彩票分析Agent v3.0 Pro

## 如何使用本技能 (For LLM / OpenClaw)

当用户询问足球比赛预测或彩票投注时，你应该使用 `bash` 或 `run_command` 工具执行 `main.py` 脚本。
返回的 JSON 或 文本日志会包含分析师、策略师和风控的详细建议。

**常用命令示例：**
1. 单场竞彩分析（包含泊松比分矩阵）:
   `python3 main.py --mode analyze --league 英超 --home 曼联 --away 切尔西 --lottery-type jingcai`
2. 北京单场分析（包含上下单双预测）:
   `python3 main.py --mode analyze --league 英超 --home 曼联 --away 切尔西 --lottery-type beijing`
3. 赛后复盘（让系统自我学习）:
   `python3 main.py --reflect --league 英超 --home 曼联 --away 切尔西 --result '{"home_goals": 1, "away_goals": 2}'`

请注意：你不需要自己计算赔率，只需要将用户的意图转化为对应的 CLI 参数，执行脚本后，将系统的输出转化为人类友好的文字报告返回给用户即可。

## 核心功能

### 1. 多Agent协作架构
- **Orchestrator**: 任务调度中心，协调各专业Agent
- **ScoutAgent**: 情报搜集（阵容、伤病、天气）
- **AnalystAgent**: 赔率分析（异常检测、价值识别）
- **StrategistAgent**: 策略制定（M串N方案）
- **RiskManager**: 风险管理（仓位控制、止损）

### 2. 记忆系统
- **EpisodicMemory**: 历史投注案例记忆
- **SemanticMemory**: 联赛知识、球队特征
- **ProceduralMemory**: 策略执行流程

### 3. 反思引擎
- 从投注结果中自动学习
- 策略效果评估
- 自我纠错机制

## 三大玩法专业覆盖 (v3.0)

### 竞彩足球专业分析
| 玩法 | 功能 | 状态 |
|------|------|------|
| 胜平负 | 基础分析+价值识别 | ✅ |
| 让球胜平负 | 盘口深度分析 | ✅ |
| 总进球 | 泊松预测模型 | ✅ |
| 比分 | 比分矩阵预测 | ✅ |
| 半全场 | 半场概率预测 | ✅ |
| 混合过关 | M串N优化 | ✅ |

### 北京单场专业分析
| 玩法 | 功能 | 状态 |
|------|------|------|
| 胜平负(含让球) | SPF分析 | ✅ |
| 总进球 | 进球分布分析 | ✅ |
| 比分 | 比分概率矩阵 | ✅ |
| 半全场 | 半全场预测 | ✅ |
| 上下单双 | SXD分析 | ✅ |
| 胜负过关 | SFGG分析 | ✅ |
| SP值 | 浮动赔率挖掘 | ✅ |
| 串关(15关) | 跨玩法串关优化 | ✅ |

### 传统足彩专业分析
| 玩法 | 功能 | 状态 |
|------|------|------|
| 14场胜负 | 深度分析+胆拖优化 | ✅ |
| 任选9场 | 智能胆拖+信心指数 | ✅ |
| 6场半全场 | 概率预测模型 | ✅ |
| 4场进球 | 进球数预测 | ✅ |
| 奖池分析 | 奖金估算+滚存 | ✅ |

### 跨玩法协同策略
| 功能 | 说明 | 状态 |
|------|------|------|
| 赔率对比 | 竞彩vs北单赔率差异 | ✅ |
| 套利检测 | 跨平台套利机会 | ✅ |
| 协同推荐 | 多玩法组合策略 | ✅ |

## 专业分析模块详情

### 泊松进球预测
- 基于泊松分布的概率模型
- 支持总进球数和比分预测
- 联赛历史数据校准

### 盘口深度分析
- 让球胜平负盘口解读
- 水位变化趋势分析
- 庄家意图识别

### 跨玩法协同
- 竞彩足球与北京单场赔率对比
- 套利机会检测
- 综合推荐引擎

## 使用方法

### 基础分析
```
/football 分析 曼联 vs 利物浦
```

### 专业预测
```
/football 进球预测 曼城 vs 切尔西  # 泊松进球预测
/football 盘口分析 阿森纳 vs 热刺  # 让球盘口分析
/football 比分预测 巴萨 vs 皇马    # 比分矩阵预测
```

### 玩法分析
```
/football 胜平负分析
/football 总进球推荐
/football 上下单双分析
/football SP值挖掘
```

### 串关方案
```
/football 生成2串1方案 预算100元
/football 混合过关优化
```

## 工具列表

| 工具 | 功能 |
|-----|------|
| odds_analyzer | 赔率分析工具 |
| mxn_calculator | 串关计算器 |
| smart_selector | 智能选场引擎 |
| strategy_backtest | 策略回测 |
| report_generator | 报告生成 |
| professional_analyzer | 专业分析入口 |

## Agent配置

系统使用OpenClaw多Agent架构，可在 `openclaw.json` 中配置：

```json
{
  "agents": {
    "orchestrator": "任务调度中心",
    "scout": "情报搜集",
    "analyst": "赔率分析",
    "strategist": "策略制定",
    "risk_manager": "风险管理"
  }
}
```
