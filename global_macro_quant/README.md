# Global Macro Quantitative Investment System (Multi-Agent Architecture)

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-green.svg)
![Platform](https://img.shields.io/badge/platform-OpenClaw%20%7C%20WorkBuddy-orange.svg)

这是一个为全球金融市场设计的专业级 AI 宏观量化投资系统。它原生支持通过 **OpenClaw (ClawHub)** 和 **WorkBuddy** 技能市场动态挂载第三方金融工具，并利用多智能体协作完成宏观分析、因子挖掘、风险平价组合优化与历史回测。

## 🌟 核心特性 (Core Features)

### 1. 动态技能挂载 (Dynamic Skill Discovery)
系统摒弃了硬编码数据爬虫的落后方式，支持在运行时通过大语言模型 (LLM) 语义路由，动态向 ClawHub/WorkBuddy 技能大厅请求并挂载所需的第三方 API（如雅虎财经、美联储经济数据、币安链上数据、新闻情感分析）。

### 2. 多资产统一抽象 (Multi-Asset Class Support)
- **权益市场 (Equities)**：美股 (S&P 500, Nasdaq)、A股。
- **加密资产 (Crypto)**：BTC, ETH 等主流代币。
- **外汇与大宗商品 (FICC)**：美元指数、日元、黄金、原油。
*(系统内置数据对齐引擎，解决 7x24 小时的 Crypto 与 5x8 小时传统金融市场的时间轴错位问题)*

### 3. 专业级数学与风控引擎 (Quant & Risk Engine)
- **风险平价组合 (Risk Parity)**：摒弃传统的均值-方差优化，利用底层 SciPy 优化器计算协方差矩阵，确保各资产对组合的风险贡献度完全相等，极大降低宏观黑天鹅事件的冲击。
- **事件驱动回测 (Event-Driven Backtester)**：内置高性能向量化回测沙箱，Agent 生成调仓比例后，强制进行历史回测，并输出夏普比率 (Sharpe Ratio) 与最大回撤 (Max Drawdown)。

### 4. 多 Agent 投研委员会 (Investment Committee)
系统采用标准的 Master-Worker 原生多智能体拓扑结构：
- **Orchestrator (调度中心)**：基金经理，负责意图拆解与动态技能发现。
- **Macro Analyst (宏观分析师)**：解读美联储政策、通胀数据与新闻情感。
- **Quant Strategist (量化策略师)**：挖掘 Alpha 因子，制定多空方向。
- **Risk Manager (首席风控官)**：执行风险平价数学计算，执行严格的资金敞口熔断。

## 📂 目录结构 (Directory Structure)

```text
global_macro_quant/
├── agents/                     # 多智能体投研委员会 (Orchestrator, Analyst, RiskManager)
├── core/                       # 核心引擎 (配置管理与多资产标的池抽象)
├── skills/                     # 动态技能挂载层 (ClawHub/WorkBuddy 发现引擎)
├── quant/                      # 纯数学与量化引擎 (风险平价与协方差矩阵计算)
├── data/                       # 多资产数据标准化层 (时间序列对齐)
├── backtest/                   # 向量化回测验证框架 (夏普比率与最大回撤计算)
├── workspace/                  # 运行时沙箱 (存放 Agent 长期记忆与调仓 JSON 报告)
├── configs/                    # 平台部署清单 (openclaw.json, SKILL.md)
└── main.py                     # 系统主入口
```

## 🚀 快速开始 (Quick Start)

### 1. 环境安装
```bash
pip install numpy pandas scipy requests
```

### 2. 本地独立运行测试
可以直接运行主入口文件，系统将模拟“动态发现技能 -> 获取多资产数据 -> 风险平价优化 -> 历史回测”的完整闭环：
```bash
python main.py
```

### 3. OpenClaw / WorkBuddy 平台挂载
系统已配置好 `configs/openclaw.json`，包含了原生多智能体沙箱的拓扑声明与后台守护进程 (Daemons) 权限。直接将项目目录导入 WorkBuddy 工作台，或置于 OpenClaw 的 `skills/` 目录下即可激活完整的 AI 投研团队。

---
**免责声明**: 本系统仅供量化投资架构研究与 AI 智能体技术验证使用。系统输出的任何资产权重与回测报告均不构成真实的投资建议。金融市场具有极高风险，实盘交易请务必谨慎。