# Tasks

- [x] Task 1: 盘点当前系统入口与双版本边界
  - [x] 子任务 1.1: 梳理独立版入口（CLI/Mentor CLI/MarketSentinel）与其默认数据目录、默认工作流
  - [x] 子任务 1.2: 梳理 OpenClaw 适配版入口（MCP Server/Runtime tools）与其默认数据目录、默认工作流
  - [x] 子任务 1.3: 输出“双版本契约”检查项：隔离、schema 一致性、能力矩阵一致性

- [x] Task 2: 建立 Self-Audit 自检命令（standalone）
  - [x] 子任务 2.1: 设计自检输出 schema（JSON），包含版本信息、能力矩阵、历史数据状态、漂移诊断
  - [x] 子任务 2.2: 实现自检命令（不触发真实网络，默认使用离线夹具/快照；可通过开关启用在线）
  - [x] 子任务 2.3: 为自检添加单元测试（离线确定性）

- [x] Task 3: 建立 Self-Audit 自检命令（openclaw/runtime）
  - [x] 子任务 3.1: 暴露 MCP tool `self_audit` 或等价入口，复用同一份输出 schema
  - [x] 子任务 3.2: 添加 runtime 侧离线测试（验证 tool 可调用、输出 schema 正确）

- [x] Task 4: 生成 Capability Matrix（竞彩足球 / 北单 / 足彩）
  - [x] 子任务 4.1: 将“能力矩阵”映射为可执行的 smoke tests（每项输出 PASS/DEGRADED/FAIL + reason）
  - [x] 子任务 4.2: 将结果纳入 Gatekeeper Core suite（确保后续迭代不再“越改越坏”）

- [x] Task 5: 22 万历史数据利用的现状对齐与可见化
  - [x] 子任务 5.1: 识别 root/data 与 standalone_workspace/data 的错配，并在自检里明确输出
  - [x] 子任务 5.2: 自检输出：原始 JSON 存在性、向量库规模、默认工作流引用点
  - [x] 子任务 5.3: 提供最小修复策略（仅切换引用路径或仅调整检索 where/type），使历史数据“可见可用”

- [x] Task 6: Drift & Bloat 诊断与瘦身路线图
  - [x] 子任务 6.1: 定义“臃肿信号”（重复模块、分叉实现、入口过多、抓取路径过多、mock 混入实盘）
  - [x] 子任务 6.2: 输出 Keep / Cut / Merge 列表（带文件清单）
  - [x] 子任务 6.3: 输出“分阶段瘦身计划”（先止血修复失效能力，再合并重复，再删冗余）

- [x] Task 7: 修复自检相关回归（embedding 接口 + OpenClaw 能力矩阵）
  - [x] 子任务 7.1: 让 LocalHashEmbeddingFunction 实现 ChromaDB 期望的 embedding function 接口（embed_query/embed_documents 等），修复闭环测试与 Gatekeeper
  - [x] 子任务 7.2: 修复 OpenClaw runtime capability_matrix_smoke 离线模式不应整体 FAIL（应为 PASS/DEGRADED）

# Task Dependencies
- Task 2/3/4/5 依赖 Task 1 的入口与边界盘点结果
- Task 6 依赖 Task 4/5 的自检数据作为证据
