---
title: Workstream C Agent Audit（去重与收敛建议）
version: 1.0
---

# 目标

- 明确 China 体彩用例下 Router / Scout / Analyst / Risk Manager 的职责边界与交付物
- 识别重复/未使用的 Agent 变体，提出收敛路径
- 用最小代码改动提升确定性（determinism）并降低幻觉风险（hallucination risk）

# 现状盘点（standalone_workspace）

## Router

- `agents/router_agent.py`：事件入口 Gatekeeper（原实现强依赖 OpenAI）

## Scout

- `agents/scout.py`：同步版 ScoutAgent（可选调用 AnalyzerAPI/LLMService，离线自动降级）
- `agents/async_scout.py`：异步版 ScoutAgent（State Delta 输出）
- `agents/react_scout.py`：ReAct 版 Scout（工具流日志更接近 tool-first）
- `agents/syndicate_agents.py`：SyndicateOS 内部的 LLM Prompt 版 ScoutAgent（与上面三者语义重叠）

## Analyst

- `agents/analyst.py`：同步版 AnalystAgent（包含多玩法 markets / professional_data 输出）
- `agents/async_analyst.py`：异步版 Analyst
- `agents/syndicate_agents.py`：SyndicateOS 内部的 LLM Prompt 版 Quant/Analyst（与 analyst.py 角色边界重叠）

## Risk

- `agents/risk_manager.py`：RiskManagerAgent（具备 reject_and_replan 打回机制）
- `agents/async_risk_manager.py`：异步版 Risk
- `agents/syndicate_agents.py`：SyndicateOS 内部的 Judge（兼具策略与风控，边界更宽）

# 主要重复与风险点

- 多个 Scout/Analyst/Risk 变体并存：易造成“同名不同约束”的漂移，Prompt 口径难统一
- Router 入口依赖 LLM：在无 Key/离线环境不确定；API 异常时过去默认 DEEP_DIVE，会扩大 LLM 调用面
- 缺少统一的“领域内核校验”：不同 Agent 输出字段不稳定，下游易靠猜字段（增加幻觉与耦合）

# 收敛建议（不破坏现有测试的最小方案）

## 1) 选定 canonical（可执行链路）

- 以 `core/mentor_workflow.py` 为“确定性 Domain Kernel 级闭环”主路径（gatekeeper 现有测试已经覆盖）
- Agentic Decision Layer 仅作为“入口过滤 + 结构化对齐”，不得替代闭环工具链

## 2) 统一输出合同（Contract）

- 新增 `core/domain_kernel.py`：提供 normalize/validate/attach
- Router/Scout/Analyst/Risk 输出必须附带 `domain_kernel` 字段，满足 tool-first（至少 data_source 或 evidence/tool_calls）

## 3) Router 去幻觉（优先规则，LLM 可选）

- 无 Key/无 openai 包/显式离线：只走规则引擎（确定性）
- LLM 输出若不合规：自动回退规则引擎，并在 reason 中记录回退原因

## 4) 逐步合并变体（后续迭代）

- 将 `async_scout.py` / `react_scout.py` 收敛为同一“工具流驱动 Scout”，同步版只保留适配层
- 将 `syndicate_agents.py` 的 Prompt 版角色视为“实验沙箱”，生产路径只认 Contract + DomainKernel 校验
- 多份代码并行维护会造成漂移：以 standalone 为唯一 source-of-truth，其他适配版应采用薄适配层或同步生成
