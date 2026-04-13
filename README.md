# 中国体育彩票足球智能分析系统 v4.0 (Native Multi-Agent Workspace)

![Version](https://img.shields.io/badge/version-4.0%20Native-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-green.svg)
![Platform](https://img.shields.io/badge/platform-OpenClaw%20%7C%20WorkBuddy-orange.svg)

本系统是一个专业级的中国体育彩票足球赛事智能分析 Agent，深度适配 **Tencent WorkBuddy** 桌面工作台与 **OpenClaw** 开源 Agent 框架。它摒弃了传统臃肿的固定模型，转而使用“LLM 大脑 + Python 数学引擎”的解耦架构。

## 🌟 核心特性 (Core Features)

### 1. 三大官方玩法严格隔离
完全遵循中国体育彩票官方规则，底层数据与预测逻辑互不干扰：
- **竞彩足球 (Jingcai)**：胜平负、让球胜平负、总进球、比分、半全场、混合过关（支持同场互斥逻辑与单关校验）。
- **北京单场 (Beidan)**：胜平负（含让球）、总进球、比分、半全场、上下单双、胜负过关（支持SP值挖掘）。
- **传统足彩 (Traditional)**：14场胜负、任选9场、6场半全场、4场进球（支持全局组合预计算与奖池滚存分析）。

### 2. 专业级数学与风控引擎
- **进球预测模型**：泊松分布 (Poisson Distribution) + Dixon-Coles 修正因子，精准预测低比分（如0-0, 1-0, 0-1）概率矩阵。
- **动态调仓与风控**：引入凯利准则 (Kelly Criterion) 与盈亏平衡赔率 (Break-even Odds) 评估真正的投注价值 (EV)，全局最高暴露度严格控制在 15% 以内。
- **官方限制合规**：完美对接 2026 年最新官方规则（停售时间、单注最高奖金封顶 100万 等）。

### 3. 多 Agent 协作与自我进化 (Multi-Agent & Evolution)
- **Orchestrator (调度中心)**：负责任务拆解与工作流控制。
- **Scout (情报搜集)**：获取球队阵容、伤病、天气及历史交锋。
- **Analyst (赔率分析)**：识别赔率异常，探测庄家意图与水位变化。
- **Strategist (策略制定)**：生成 M串N 最优组合与混合过关方案。
- **RiskManager (风险管理)**：执行内部辩论机制，否决高风险投注。
- **记忆系统**：具备情景记忆 (Episodic)、语义记忆 (Semantic) 和程序记忆 (Procedural)，支持通过盲测回测结果进行贝叶斯自动更新，实现策略自我进化。

### 4. 平台生态完美适配
- **Tencent WorkBuddy**：支持本地沙盒执行、文件夹权限控制、多模态图表 (ECharts/AntV) 可视化输出。
- **OpenClaw**：全面封装为标准化的原子技能 (Atomic Skills) 工具集，支持无缝挂载。

## 🛠️ 安装与配置 (Installation)

### 环境要求
- Python 3.10+
- 推荐使用虚拟环境 (`venv`)

### 快速开始
1. **克隆仓库**
   ```bash
   git clone https://github.com/luenglueng205-rgb/Football-AnalystAgent.git
   cd Football-AnalystAgent
   ```

2. **安装依赖**
   ```bash
   pip install -r agent/openclaw-football-lottery-agent/football-lottery-analyst/requirements.txt
   ```

3. **配置环境变量**
   复制 `.env.example` 为 `.env` 并填入相应的 API Key（如果单独运行）。
   *注：如果在 WorkBuddy 或 OpenClaw 中运行，平台会自动接管大模型能力，只需授权本地文件夹即可。*

## 🚀 平台集成指南 (Integration)

### WorkBuddy 集成
1. 打开 WorkBuddy 桌面端，进入“我的技能” -> “导入本地技能”。
2. 选择本项目的根目录。
3. WorkBuddy 会自动读取 `SKILL.md` 的 Metadata。
4. 授权文件夹读写权限后，即可通过自然语言对话框直接触发分析任务。

### OpenClaw 集成
系统根目录下的 `openclaw.json` 和 `football_quant_tools.json` 包含了所有的清单信息，直接将目录挂载到 OpenClaw 的 `agents` 路径下即可激活。

## 📊 常用交互示例 (Usage Examples)

你可以在 Agent 对话框中直接输入以下指令：
- *"帮我分析今天竞彩足球的曼联对阵切尔西，给出比分预测和赔率价值评估。"*
- *"请使用凯利准则帮我生成一个 3串1 的竞彩混合过关方案，预算 200 元。"*
- *"提取今天的北单比赛列表，分析出最适合买‘上下单双’的两场比赛。"*
- *"根据最近的伤病情报和历史进球特征，生成一张英超进球期望的可视化图表。"*

---
**免责声明**: 本系统仅供体育彩票数据分析与技术研究使用。系统预测结果不构成任何投资或购彩建议。购彩有风险，请理性参与，遵守当地法律法规。
