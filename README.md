# ⚽️ AI-Native 足球竞彩量化分析系统 (v4.1 Native Multi-Agent Workspace)

[![OpenClaw Compatible](https://img.shields.io/badge/OpenClaw-2026.04.11-blue.svg)](https://openclaw.ai)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **极简、AI 原生、专为竞彩/北单/传统足彩打造的量化大脑。**
> 抛弃沉重的传统历史脚本，采用“LLM 做 CPU，Python 做肌肉”的 4.0 时代先进架构。

---

## 🌟 v4.1 核心进化：Native Multi-Agent
本系统已深度重构，完美适配 **OpenClaw (2026.04.11)** 和 **WorkBuddy** 平台的原生多智能体沙箱架构。
不再是简单的被动 API 工具调用，而是由多个 AI Agent 在后台进行激烈的博弈、推演与风控把关。

### 🤖 核心智能体团队 (Agents)
1. **首席分析师 (Analyst)**：负责读取赛事基本面，结合历史交锋数据，进行第一层定性研判。
2. **情报员 (Scout)**：拥有实时网络检索能力，抓取最新的球队伤停、天气突变、裁判安排等场外 X 因素。
3. **量化策略师 (Strategist)**：冷酷的数学机器。负责调用蒙特卡洛模拟、泊松分布等数学模型，将定性分析转化为量化胜率和凯利投注比例。
4. **首席风控官 (Risk Manager)**：拥有一票否决权。对所有产出的策略进行极端压力测试，监控聪明钱(Smart Money)异动，计算组合 VaR 尾部风险。
5. **统筹者 (Orchestrator)**：系统的中枢大脑，负责调度上述所有 Agent 的工作流，并输出最终的、包含明确赔率和注码的投注建议。

---

## 🛠️ 纯 Python 量化肌肉库 (Muscle Tools)
本系统内置了十余种硬核的量化数学引擎，供大模型随时调用：

*   **🎲 蒙特卡洛赛事推演 (`monte_carlo_simulator.py`)**：基于 xG (预期进球) 和泊松分布，在毫秒内进行 10,000 次比赛时间线推演，计算胜平负及半全场概率。
*   **💸 聪明钱追踪器 (`smart_money_tracker.py`)**：剥离博彩公司抽水 (Margin)，捕捉亚盘/欧赔的异常资金线变动，发现被隐藏的真实市场倾向。
*   **📊 贝叶斯动态更新 (`bayesian_updater.py`)**：将新赛季的初期数据与上赛季的先验数据进行平滑融合，防止数据样本过少导致的预测失真。
*   **🎯 CLV 预测模型 (`clv_predictor.py`)**：(Closing Line Value) 预测赛前赔率的最终落点，寻找统计套利机会。
*   **🏃‍♂️ 球员级 xG 衰减 (`player_xg_adjuster.py`)**：当核心射手/助攻王伤停时，自动按权重扣减球队的进攻火力期望。
*   **⚖️ 组合优化与凯利公式 (`portfolio_optimizer.py`)**：多场比赛同时下注时，自动利用风险平价和凯利公式分配资金，最大化夏普比率。

---

## 🚀 平台部署与使用 (Deployment)

### 方案 A：OpenClaw 平台原生导入 (推荐)
1. 将本项目根目录下的 `Football-AnalystAgent-v4.1-Native-MultiAgent-Backup.zip` 下载到本地。
2. 登录 OpenClaw Workspace 平台，选择 **"Import Native Workspace"**。
3. 平台将自动解析 `configs/openclaw.json`，并为你生成由上述 5 个 Agent 组成的专属量化团队。

### 方案 B：本地命令行运行
如果你拥有本地 LLM 环境（如通过 API 接入 Anthropic 或 OpenAI），可直接运行中枢大脑：
```bash
# 1. 安装极其轻量的依赖 (numpy, scipy, pandas 等)
pip install -r configs/requirements.txt

# 2. 启动系统 (Orchestrator 将接管终端)
python main.py
```

---

## 🛡️ 架构特色与测试
*   **后台守护进程 (Daemon)**：内置 `market_monitor.py`，可以在后台持续轮询赔率变化，一旦发现“断崖式降水”，立即唤醒风控官介入。
*   **自我进化引擎 (Auto-Tuner)**：内置 `auto_tuner.py`，能够根据周末复盘的实际赛果，自动修改底层的模型参数配置 (JSON)，实现“吃一堑长一智”。
*   **并发安全**：采用 `fcntl` 文件锁，确保多 Agent 并发写入反思日志时不会造成 JSON 数据损坏。
*   **抗极端环境**：经历了千万级蒙特卡洛压测和 `Infinity/NaN` 数学溢出破坏性测试，系统依然坚如磐石。

---
*“在 4.0 时代，量化分析不再是写死代码的规则树，而是由 AI 大脑和数学肌肉共同演奏的交响乐。”*
