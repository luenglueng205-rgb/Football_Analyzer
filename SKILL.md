---
name: football-lottery-analyst-pro
description: 中国体育彩票足球彩票智能分析系统 v3.0 Pro，深度适配 WorkBuddy 与 OpenClaw 平台。支持竞彩足球、北京单场、传统足彩三大玩法。核心功能包括泊松进球预测、赔率异常检测、凯利准则动态调仓、多模态图表输出与自进化记忆。
trigger:
  - "竞彩"
  - "足彩分析"
  - "北京单场"
  - "传统足彩"
  - "比分预测"
  - "进球预测"
  - "串关方案"
  - "盘口分析"
  - "赔率分析"
  - "价值投注"
metadata: {
  "openclaw": {
    "requires": {"bins": ["python3"], "env": [], "config": []},
    "os": ["darwin", "linux", "win32"],
    "always": true
  },
  "workbuddy": {
    "capabilities": ["multi_agent", "file_sandbox", "local_execution"],
    "permissions": ["folder_read", "folder_write"]
  }
}
---

# 中国体育彩票足球智能分析系统 v3.0 Pro (WorkBuddy & OpenClaw 适配版)

## 系统概述
本系统是一个专业级的中国体育彩票足球赛事分析 Agent，已深度适配 **Tencent WorkBuddy** 桌面工作台与 **OpenClaw** 开源 Agent 框架。
它摒弃了传统臃肿的固定模型，转而使用“LLM 大脑 + Python 数学引擎”的解耦架构。具备严谨的体育彩票官方玩法隔离（竞彩、北单、传统足彩）、泊松分布+Dixon-Coles 进球模型、以及凯利准则动态调仓风控。

## 平台适配说明

### 1. Tencent WorkBuddy 适配
- **沙盒与文件权限**：在 WorkBuddy 中运行时，本技能会自动请求当前项目目录的读写权限，以保障数据隐私与安全。
- **本地执行**：利用 WorkBuddy 的本地桌面执行能力，直接调用底层的 Python 数学引擎进行高强度的数据计算，无需将全量数据回传云端。
- **多模态图表**：生成的 ECharts / AntV JSON 配置可直接被 WorkBuddy 的前端工作台渲染为可视化分析报告。

### 2. OpenClaw 适配
- **工具化封装 (Toolify)**：所有的底层分析能力均已通过 `atomic_skills.py` 封装为符合 OpenClaw JSON Schema 标准的工具集。
- **Agent 协作编排**：利用 OpenClaw 的多 Agent 框架，实现 Analyst（分析师）、Strategist（策略师）与 RiskManager（风控师）的内部辩论与协同。

## 核心能力与工具 (Tools)

当用户发起分析请求时，Agent 可通过调用以下底层工具进行专业计算：

1. **`get_today_matches_list`**: 获取今日官方赛事列表，并严格执行停售时间过滤与单关限制校验。
2. **`calculate_poisson_probability`**: 使用泊松分布结合 Dixon-Coles 修正因子，预测比分矩阵与进球数概率。
3. **`evaluate_betting_value`**: 结合凯利准则与盈亏平衡赔率 (Break-even Odds) 评估投注价值。
4. **`get_live_odds_and_water_changes`**: 抓取即时赔率与水位变化。
5. **`get_team_news_and_injuries`**: 获取基本面情报。
6. **`calculate_traditional_rx9_cost`**: 针对传统足彩（如任选9场）计算组合成本与资金预算。
7. **`generate_visual_chart`**: 输出可视化图表配置。

## 严格的官方玩法隔离

本系统强制实施不同彩种的逻辑隔离，不可混用策略：
- **竞彩足球 (Jingcai)**：胜平负、让球胜平负、总进球、比分、半全场、混合过关（支持同场互斥逻辑）。
- **北京单场 (Beidan)**：胜平负（含让球）、总进球、比分、半全场、上下单双、胜负过关。
- **传统足彩 (Traditional)**：14场胜负、任选9场、6场半全场、4场进球（采用全局组合预计算）。

## 使用示例

在 WorkBuddy 或 OpenClaw 聊天框中，你可以这样触发系统：

- *"帮我分析今天竞彩足球的曼联对阵切尔西，给出比分预测和赔率价值评估。"*
- *"请使用凯利准则帮我生成一个 3串1 的竞彩混合过关方案，预算 200 元。"*
- *"提取今天的北单比赛列表，分析出最适合买‘上下单双’的两场比赛。"*
- *"根据最近的伤病情报和历史进球特征，生成一张英超进球期望的可视化图表。"*

---
**开发者提示**: 
系统已内置 `main.py` 和 `atomic_skills.py`，请确保运行环境中已安装 `requirements.txt` 内的依赖。
对于 WorkBuddy 用户，请在首次授权时勾选系统所在的本地文件夹权限。