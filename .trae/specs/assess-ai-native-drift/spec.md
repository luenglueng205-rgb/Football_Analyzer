# AI 原生足球分析系统“漂移自检与瘦身”Spec

## Why
项目最初以“AI 原生”方式开发，但近期迭代后出现系统臃肿、能力失效、双版本（独立版 / OpenClaw 适配版）边界与一致性不清，导致无法判断当前系统是否仍符合最初目标。

## What Changes
- 增加一套“系统自检（Self-Audit）”能力，用于回答“系统现状是什么、哪些能力坏了、是否偏离 AI 原生设计、双版本适配度如何”。
- 输出“能力矩阵（Capability Matrix）”与“漂移/臃肿诊断（Drift & Bloat Diagnosis）”，覆盖 竞彩足球 / 北京单场 / 传统足彩 的关键链路。
- 明确并固化双版本策略：独立版与 OpenClaw 适配版的“边界、入口、数据目录隔离、能力一致性要求”。
- 给出可执行的“瘦身与修复路线图”，按优先级把复杂度降回到可维护状态。

## Impact
- Affected specs: AI 原生设计原则（信息获取方式、工具薄层、可解释与保守拒绝）、三大彩种全链路能力、双版本一致性。
- Affected code: 入口层（CLI/MCP）、数据获取层（Info-First 与 fallback）、玩法路由/串关/结算、记忆与历史数据利用、调度器（MarketSentinel）。

---

## ADDED Requirements

### Requirement: Self-Audit 命令（现状可见）
系统 SHALL 提供一个可重复执行的“自检命令”，在不依赖人工阅读代码的情况下输出系统现状。

#### Scenario: 运行自检成功
- **WHEN** 用户在独立版或 OpenClaw 适配版运行自检
- **THEN** 输出至少包含：
  - 当前版本信息（standalone/openclaw/runtime）
  - 核心入口可用性（CLI/MCP 工具列表、关键命令可运行）
  - 三大彩种（竞彩足球/北单/足彩）能力矩阵（见 Requirement: Capability Matrix）
  - 22 万历史数据利用状态（存在性、注入状态、默认链路是否引用）
  - “臃肿与漂移”诊断（见 Requirement: Drift Diagnosis）

### Requirement: Capability Matrix（针对三大彩种的链路自检）
系统 SHALL 生成“能力矩阵”，逐项验证以下链路是否可用（允许降级，但必须可解释）。

#### Matrix: 竞彩足球
- 数据：fixtures / odds(SP) / live / results
- 决策：推荐（含 risk_tags / audit）
- 交易：ticket 构建与路由校验
- 临场：live_check（可为空但必须解释原因）
- 结算：settlement（90 分钟口径）+ pnl 回写（可模拟）

#### Matrix: 北京单场
- 数据：fixtures / odds(SP)
- 交易：过关/单关路由约束
- 结算：对应玩法结算口径

#### Matrix: 传统足彩（14/任九/6 半全/4 进球）
- 交易：串关注数计算与票据结构适配
- 结算：玩法结果映射口径

### Requirement: Drift Diagnosis（AI 原生偏离与臃肿识别）
系统 SHALL 给出“偏离 AI 原生”的诊断信号与建议。

#### Scenario: 识别过度工程化
- **WHEN** 自检扫描到多条并行数据路径（DOM 解析/视觉抽取/API/缓存/foreign API）混杂且职责不清
- **THEN** 输出：
  - 复杂度热点（文件/模块名单）
  - 重复实现/分叉风险（standalone vs openclaw/runtime、registry v1/v2、手写 MCP tools vs registry）
  - 建议的 Keep / Cut / Merge 清单

### Requirement: Dual-Edition Contract（双版本契约）
系统 SHALL 明确并保证以下双版本契约：
- 独立版与 OpenClaw 适配版各自拥有独立入口与数据目录（不得互相读写）。
- 两版本对“关键能力矩阵”具备一致性（允许实现方式不同，但输出 schema 与规则口径一致）。

---

## MODIFIED Requirements

### Requirement: 22 万历史数据“可见可用”
系统 SHALL 在自检中明确回答：
- 原始数据文件是否存在（路径、大小、条数）
- 向量库是否存在且规模合理（collection/doc_count 近似值）
- 默认工作流（mentor_workflow/market_sentinel/main）是否实际引用历史数据（是/否、引用点）

---

## REMOVED Requirements

### Requirement: 强依赖 DOM 确定性爬取作为主路径
**Reason**: AI 原生目标更强调“工具薄层 + 浏览器/搜索获取 + 保守拒绝”，不应把维护成本锁死在反爬/验证码对抗上。
**Migration**: 将“确定性 DOM 解析”降级为可选 fallback；主路径以 Info-First（WebIntel/BrowserUse）为准，并由自检报告体现降级策略与数据置信度。

