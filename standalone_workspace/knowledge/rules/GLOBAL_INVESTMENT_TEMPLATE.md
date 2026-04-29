---
name: global-macro-quant-agent
description: 全球宏观量化投资与资产配置智能分析系统 v1.0。基于多Agent协作架构，支持全球股票、外汇、加密货币及大宗商品的宏观趋势分析、因子挖掘、组合优化及动态风控调仓。
trigger:
  - "全球宏观"
  - "量化投资"
  - "资产配置"
  - "美股分析"
  - "加密货币预测"
  - "外汇趋势"
  - "多因子模型"
  - "投资组合优化"
  - "动态调仓"
  - "风险平价"
metadata: {
  "workbuddy": {
    "capabilities": ["multi_agent", "file_sandbox", "local_execution", "dynamic_skill_discovery"],
    "permissions": ["folder_read", "folder_write"]
  }
}
---

# 全球宏观量化投资分析系统 (Global Macro Quant Agent)

## 系统概述
这是一个为全球金融市场（美股、A股、加密货币、外汇、大宗商品）设计的专业级 AI 宏观量化投资系统。
它继承了底层“LLM 大脑 + Python 数学引擎 + 多Agent协作”的解耦架构，并支持通过技能市场动态挂载第三方金融工具。

## 核心架构特性

### 1. 动态技能挂载 (Dynamic Skill Discovery)
本系统无需自己编写所有的数据抓取代码。通过平台的语义路由与 Tool Calling 机制，Agent 可在运行时按需调用第三方技能市场中的海量专业工具：
- **数据源获取**：按需挂载 `yahoo-finance-data` 获取美股秒级行情，挂载 `macro-economic-indicators` 获取美联储利率决议与非农数据。
- **情感分析**：挂载 `enterprise-news-sentiment` 实时分析彭博社、华尔街日报的宏观新闻情感得分。
- **执行交易**：甚至可以挂载受监管的 `broker-execution-api` 进行模拟盘或实盘的 API 自动下单。

### 2. 多资产类别覆盖
- **权益市场 (Equities)**：美股 (S&P 500, Nasdaq)、A股、港股。
- **加密资产 (Crypto)**：BTC, ETH 等主流代币的链上数据与资金费率分析。
- **宏观对冲 (Macro/FX/Commodities)**：外汇交叉盘、黄金、原油的宏观周期定价。

### 3. 量化数学引擎与风控 (Quant & Risk Engine)
- **多因子模型 (Multi-Factor Model)**：动量 (Momentum)、价值 (Value)、质量 (Quality)、低波动 (Low Volatility) 因子的动态权重分配。
- **风险平价组合 (Risk Parity)**：基于资产间的协方差矩阵，计算最优的风险平价配置比例。
- **凯利准则与最大回撤控制**：根据大模型对宏观事件的置信度，动态调整仓位暴露 (Exposure)，强制执行止损与止盈逻辑。

### 4. 多 Agent 投研委员会 (Investment Committee)
- **Macro Analyst (宏观分析师)**：解读美联储政策、通胀数据 (CPI/PPI)、地缘政治事件。
- **Quant Strategist (量化策略师)**：基于数据计算因子得分，生成马科维茨有效前界 (Efficient Frontier) 与最优夏普比率 (Sharpe Ratio) 组合。
- **Risk Manager (首席风控官)**：执行内部辩论机制，否决单一资产高集中度或高波动率的激进方案。

## 使用示例 (Usage Examples)

在任意支持工具调用与工作流编排的平台中，你可以这样触发系统：

- *"帮我分析下周美联储降息对标普500和黄金的宏观影响，并调用市场中的财经新闻分析工具提取市场情绪。"*
- *"使用风险平价模型，帮我构建一个包含美股、美债、比特币的投资组合，初始资金 10 万美元，要求最大回撤不超过 15%。"*
- *"提取英伟达 (NVDA) 最近一季度的财报数据，结合当前半导体行业的宏观周期，评估其长期投资价值。"*

---
**开发者提示**: 
系统依赖外部技能市场提供实时金融数据。运行时可按需发现并挂载第三方数据工具。请确保平台已授权相应的 API 访问权限。
