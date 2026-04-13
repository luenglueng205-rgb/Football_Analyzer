# 全球宏观量化投资系统 (Global Macro Quant System) 架构规划

## 1. 核心理念与愿景
构建一个**完全自主进化**的全球资产量化投资系统。该系统不仅具备本地的数学分析与风控引擎，更能够像真实的基金经理一样，**主动去 OpenClaw / WorkBuddy 技能市场“招聘”新工具**（如：最新的非农数据抓取器、马斯克推特情感分析器、币安资金费率监控器），并通过沙盒测试后永久固化为自己的能力。

## 2. 架构设计：自主进化的闭环 (Self-Evolving Loop)
系统将实现真正的“越用越强”，核心循环如下：
1. **需求感知 (Perception)**：当系统需要预测特斯拉 (TSLA) 股价，发现本地缺乏“期权异动数据”时，触发 `SkillDiscovery` 机制。
2. **市场检索 (Discovery)**：通过 OpenClaw 协议向 ClawHub 技能大厅发起语义检索，寻找 `options_flow_analyzer` 技能。
3. **沙盒测试 (Sandbox Evaluation)**：拉取该技能的 JSON Schema，在本地隔离环境中进行模拟调用，验证其返回的数据格式是否符合量化要求。
4. **永久集成 (Permanent Integration)**：测试通过后，将该技能的 Schema、调用方式和鉴权信息写入本地的 `learned_skills.json`（长期记忆），以后遇到类似任务直接调用，不再依赖硬编码。

## 3. 核心模块与文件结构规划

```text
global-macro-quant/
├── agents/                      # 多智能体投研委员会
│   ├── orchestrator.py          # 基金经理：统筹任务，触发技能发现
│   ├── macro_analyst.py         # 宏观分析师：调用宏观经济、新闻情感技能
│   ├── quant_strategist.py      # 量化策略师：计算夏普比率、多因子模型
│   └── risk_manager.py          # 首席风控官：凯利准则、最大回撤控制、相关性矩阵
├── core/
│   ├── skill_manager.py         # 【核心】动态技能大厅交互与固化引擎
│   ├── portfolio_math.py        # 本地不可替代的量化数学引擎 (如协方差计算)
│   └── execution_engine.py      # 模拟盘/实盘交易执行路由
├── memory/
│   ├── learned_skills.json      # 永久固化的第三方技能库 (自我进化的结晶)
│   ├── market_reflections.json  # 交易反思与市场周期记忆
│   └── factor_weights.json      # 动态调整的因子权重
├── prompts/
│   └── MACRO_SOP.md             # 投资决策标准流程 (大模型指令)
├── main.py                      # 系统入口
└── openclaw.json                # 平台集成配置
```

## 4. 投资标的与策略支持
- **全球权益 (Equities)**：美股 (S&P 500)、A股、ETF 轮动。
- **加密资产 (Crypto)**：BTC/ETH 链上数据、资金费率套利。
- **大宗商品与外汇 (FICC)**：黄金、原油、美元指数宏观对冲。

## 5. 初步代码实现计划
接下来将为您生成核心的 `skill_manager.py`（负责动态吸取技能）和 `orchestrator.py`（负责投研调度）的骨架代码。