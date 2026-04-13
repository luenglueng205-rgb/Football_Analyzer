---
name: global-macro-quant-system
description: 全球宏观量化投资原生多智能体系统。支持美股、外汇、大宗商品及加密货币的跨资产宏观研判、风险平价资产配置 (Risk Parity) 与高保真向量化历史回测。
trigger:
  - "宏观经济分析"
  - "降息预测"
  - "通胀数据"
  - "资产配置"
  - "风险平价"
  - "量化回测"
  - "多因子模型"
metadata: 
  openclaw: 
    requires: 
      bins: ["python3"]
      env: ["ALPHA_VANTAGE_API_KEY", "FRED_API_KEY"]
      config: []
    os: ["darwin", "linux", "win32"]
    always: true
  workbuddy: 
    capabilities: 
      - "multi_agent"
      - "background_daemons"
      - "file_sandbox"
      - "local_execution"
      - "dynamic_skill_discovery"
    permissions: 
      - "folder_read"
      - "folder_write"
---

# 全球宏观量化投资系统 (Global Macro Quant)

这是一个原生多智能体网络 (Native Multi-Agent Workspace)，被设计为运行在 WorkBuddy 或 OpenClaw 集群环境下的数字化量化对冲基金团队。

## 核心架构：Master-Worker 投研编排
- **Orchestrator (基金经理)**：负责接收市场指令，协调各研究部门。
- **Macro Analyst (宏观分析师)**：解读新闻与经济数据。具备通过 `dynamic_skill_discovery` 在运行时自动挂载第三方 API 的能力。
- **Quant Strategist (量化策略师)**：挖掘多空因子，提出原始仓位。
- **Risk Manager (首席风控官)**：强制执行 Risk Parity（风险平价）模型，并通过本地沙箱执行 Event-Driven Backtest（历史回测）。如果最大回撤超标（如 -15%），将打回方案。