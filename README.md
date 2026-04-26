# 🤖 Agentic Football Analyzer (AFA)
> **2026年绝对前沿架构：基于大模型自治与时空图神经网络的中国体彩量化投研与风控系统**

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Architecture](https://img.shields.io/badge/Architecture-AI--Native-success)
![License](https://img.shields.io/badge/License-MIT-green)

Agentic Football Analyzer (AFA) 并不是一个传统的“调用 API 查赔率”的脚本，而是一个**具有自治意识、能够自我进化、自我反思并自动编写量化策略的数字生命体**。

系统专为中国体育彩票（竞彩足球、北京单场、传统足彩）的实体店物理规则深度定制，集成了从底层数据摄取、高阶数学建模、大语言模型（LLM）多分支推演到最终资金分配的全链路自动化。

---

## 🌟 核心架构与五大引擎 (The 5 Pillars)

本系统由五大绝对前沿的 AI 引擎驱动，彻底告别人工干预：

### 1. ⚡ ZSA (Zero-Shot Arbitrage) 零样本极速套利快轨
*   **毫秒级截胡**：后台常驻守护线程监听海外突发新闻（如主力热身受伤）。一旦发现足以改变基本面的情报，直接绕过大模型（LLM），调用本地 Sub-200ms SLM（小语言模型）进行情感与影响力分类。
*   **5ms 物理出票**：在庄家精算师反应过来并降水/封盘前的 **5 毫秒内**，完成内存总线穿透与做空出票拦截。

### 2. 🌌 GWM (Generative World Model) 生成式世界模型与时空推演
*   **光学追踪数据摄取**：告别干瘪的 xG（预期进球）数据，系统支持摄取 105m x 68m 球场上 22 名球员的 (X, Y) 光学追踪坐标序列。
*   **ST-GNN 几何战术**：通过时空图神经网络计算“防线高度”与“阵型紧凑度”。
*   **潜空间录像推演**：在走地盘（In-Play）中，AI 能够推演下半场未来 15 分钟的战术剧本（如：主队防线畸高且客队低位密集，极易被打反击）。

### 3. 🌳 MCTS & MoA (蒙特卡洛树搜索与混合专家辩论)
*   **高价值赛事过滤**：90% 的垃圾赛事会被哨兵节点直接抛弃。
*   **算力折叠**：对于高价值赛事（如欧冠决赛），系统展开 MCTS 分支树，推演不同剧本。
*   **红蓝军对抗**：引入 MoA (Mixture of Agents) 机制，由多位虚拟专家对核心争议点进行激烈辩论，最终由 LLM Judge 做出最冷血的期望值 (EV) 决策。

### 4. 🧬 RLEF (Reinforcement Learning from Environment Feedback) 赛后环境反馈进化
*   **数字生物钟**：系统具备昼夜节律。每天凌晨 3:00 自动唤醒 `AutoTunerAgent`。
*   **真实账本反思**：系统会读取 SQLite 本地账本中前一天的真实亏损注单，对比赛果与赛前预测，让大模型撰写“血泪教训（Golden Rules）”并永久固化至系统基因。
*   **动态阈值**：自动微调第二天 ZSA 快轨的敏感度阈值和图网络权重。

### 5. 💼 机构级风控与资金管理 (Portfolio Optimization)
*   **三大彩种物理隔离**：严格遵循体彩实体店规则。竞彩拦截小数让球且限 8 串 1；北单支持 15 串 1 且强制扣除 65% 奖池抽水；足彩采用无赔率概率优势模型。
*   **税务优化拆单**：自动监测单注 1 万元（20% 偶然所得税）红线，利用法定最高赔付上限（如 4 串 1 最高 50 万）自动拆分选号单合法避税。
*   **马科维茨风险平价 (Markowitz)**：周末多场比赛并发时，计算协方差矩阵，强制使用“分数凯利”分配资金。若总暴露资金超过设定红线（如 15%），触发全局等比缩水保护。

---

## 🚀 极速安装与开箱即用 (Out-of-the-Box Setup)

为了绕过 GitHub 100MB 的单文件限制，系统近 1GB 的核心资产（22万场历史比赛 JSON 数据集 + 几百兆的 ChromaDB 向量数据库）被高压缩并切分成了 50MB 的小块。

**只需三步，瞬间满血复活：**

### 1. 克隆代码库
```bash
git clone https://github.com/luenglueng205-rgb/Football_Analyzer.git
cd Football_Analyzer
```

系统内含 **3 个绝对独立的版本（互不干涉，拥有独立的数据库和内存）**：
- `standalone_workspace/`：纯 Python 独立守护版（自带 LangGraph）。
- `openclaw_workspace/`：OpenClaw 深度适配版（剥离 LangGraph，暴露 JSON Schema 接口，支持 100% 本地沙箱权限）。
- `hermes_workspace/`：Hermes Agent 深度适配版（专为 Hermes 2 Pro/3 的 Strict Function Calling 打造）。

### 2. 恢复系统的“记忆与粮草” (核心！)
**必须执行此脚本**，它会自动合并分卷包，并将 22 万场比赛记忆和 ChromaDB **同时注入到这三个独立版本的目录中**：
```bash
chmod +x ./standalone_workspace/workspace_init/restore.sh
./standalone_workspace/workspace_init/restore.sh
```

### 3. 安装依赖与配置环境
安装 Python 依赖（推荐 Python 3.10+）：
```bash
pip install -r requirements.txt
```

复制环境变量模板并填入你的 API Key：
```bash
cp .env.example .env
```
编辑 `.env` 文件：
```env
OPENAI_API_KEY=sk-your-api-key-here
MODEL_NAME=gpt-4o  # 或 deepseek-chat
OPENAI_BASE_URL=https://api.openai.com/v1

USE_LOCAL_SLM=true
AUTO_TUNER_USE_LLM=true
```

---

## 🕹️ 使用指南 (How to Run)

系统被设计为“全自动自治”，你无需手动输入比赛，系统会自动扫描、过滤、推演并记录。

### 1. 生产环境：启动主系统心跳 (The Heartbeat)
这是系统的核心驱动力。启动后挂在后台即可：
- **白天**：自动扫描赛程，拦截垃圾赛事，对高价值比赛启动 MCTS 推演。
- **午夜**：自动唤醒 RLEF 引擎复盘盈亏并微调参数。
```bash
python3 standalone_workspace/core/digital_life/heartbeat_daemon.py
```

### 2. 实验室：测试各个前沿架构模块
如果你想单独观察某个黑科技模块是如何工作的，可以直接运行以下脚本：

- **测试 ZSA 5ms 极速截胡** (模拟突发伤病新闻)：
  ```bash
  python3 standalone_workspace/tests/architecture_tests/test_zsa_front_running.py
  ```
- **测试 GWM 空间战术推演 + MCTS 辩论** (模拟高复杂度欧冠决赛)：
  ```bash
  python3 standalone_workspace/tests/architecture_tests/test_gwm_mcts_parallel.py
  ```
- **测试周末 50 场并发时的马科维茨风控** (观察全局缩水保护)：
  ```bash
  python3 standalone_workspace/scripts/portfolio_batch_runner.py
  ```
- **测试 RLEF 赛后反思闭环** (强行注入亏损，看 AI 如何修改自己的代码权重)：
  ```bash
  python3 standalone_workspace/tests/architecture_tests/test_rlef_feedback_loop.py
  ```

### 3. 终极武器：AI 全自动量化投研 (Quant Researcher)
如果你觉得现有的策略赚得不够多，可以唤醒系统内置的“AI 投研智能体”。
它会**自己构思数学公式 -> 自己写 Python 策略代码 -> 自己在安全沙箱里跑几十万条数据的回测 -> 计算夏普比率**。
如果发现能打破记录的“神级策略”，它会提交一份研报等你审批（Human Approval Gate）：
```bash
python3 standalone_workspace/scripts/run_quant_researcher.py
```

---

## 📂 项目核心目录结构 (Directory Structure)

```text
├── backups/                             # 系统的物理快照备份档案
├── standalone_workspace/                # 独立版系统 (Standalone) - 自带 LangGraph，适合个人跑实盘
│   ├── agents/                          # 智能体目录 (AutoTuner, QuantResearcher 等)
│   ├── core/                            # 核心引擎 (Agentic OS, LangGraph 状态机, Heartbeat)
│   ├── docs/                            # 文档与系统演化经验 (DYNAMIC_EXPERIENCE.md)
│   ├── scripts/                         # 常用运维与执行脚本
│   ├── skills/                          # 核心业务技能 (GWM 时空模型, ZSA 新闻截胡)
│   ├── tests/                           # 单元测试与前沿架构沙盒测试
│   ├── tools/                           # 量化数学工具、路由、资金管理、API 抓取
│   ├── workspace/                       # 核心数据区 (解压 restore.sh 后生成)
│   │   ├── data/                        # SQLite 账本 (ledger.db), ChromaDB 向量库, 回测报告
│   │   └── datasets/                    # 海量 JSON 历史数据集
│   └── workspace_init/                  # GitHub 分卷压缩包与数据恢复脚本
├── openclaw_workspace/                  # OpenClaw 深度适配版 - 剥离 LangGraph，暴露原生 Tools
├── hermes_workspace/                    # Hermes 深度适配版 - 剥离 LangChain，严格函数调用风控
├── .env.example                         # 环境变量配置参考
├── README.md                            # 本文档
└── requirements.txt                     # 依赖清单
```

---

## 📈 监控与查账 (Monitoring)

系统是冷酷无情的，它所有的交易记录、滑点、盈亏（PnL）都记录在本地的高并发 SQLite 数据库中。
- **账本位置**: [standalone_workspace/workspace/data/ledger.db](file:///absolute/path/to/standalone_workspace/workspace/data/ledger.db)
- **演化日志**: 打开 [standalone_workspace/docs/DYNAMIC_EXPERIENCE.md](file:///absolute/path/to/standalone_workspace/docs/DYNAMIC_EXPERIENCE.md)，你可以看到这个 AI 是如何在市场的毒打下逐渐变得越来越聪明的。

---
> **Disclaimer (免责声明)**: 本系统仅供人工智能架构、时空图神经网络及量化投资组合理论的学术研究与技术探讨。系统内置的所有体彩出票均在本地 SQLite 虚拟账本中模拟完成，不包含任何真实的自动化真金投注接口。请遵守当地法律法规，理性看待体育赛事。
