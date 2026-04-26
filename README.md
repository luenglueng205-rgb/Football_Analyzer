# Agentic Football Analyzer 使用指南

> 本指南将指导您如何启动、监控并维护这个基于 2026 年绝对前沿架构（ZSA + GWM + RLEF + MCTS）的数字生命体。

---

## 1. 环境准备与配置

系统采用全异步、内存驻留的双轨架构，在启动前请确保环境配置正确。

### 1.1 恢复系统“记忆与粮草” (首次克隆必做)
为了绕过 GitHub 100MB 的单文件上传限制，系统近 1GB 的历史比赛数据集和 ChromaDB 向量数据库被切分成了 50MB 的小块上传。

克隆代码后，**请务必首先执行数据恢复脚本**：
```bash
# 执行后会自动将分卷数据合并并解压至 core_system/workspace/ 目录
./core_system/workspace_init/restore.sh
```

### 1.2 安装依赖
确保您已安装 Python 3.10+，并在项目根目录下执行：
```bash
pip install -r requirements.txt
# 包含 transformers, torch, langchain, langgraph, openai 等核心库
```

### 1.3 环境变量配置
在项目根目录创建或编辑 `.env` 文件（系统极度依赖大模型推演，**务必配置 API Key**）：
```env
# 主脑大模型配置 (用于 MCTS 多分支推演与 RLEF 赛后反思)
OPENAI_API_KEY=your_api_key_here
MODEL_NAME=gpt-4o  # 或 deepseek-chat
OPENAI_BASE_URL=https://api.openai.com/v1 # 如果使用代理或 DeepSeek 请修改此项

# ZSA 快轨配置
USE_LOCAL_SLM=true        # 启用本地 sub-200ms 推理模型 (强烈建议 true)
NEWS_LISTENER_MOCK=false  # 关闭 Mock，接入真实 RSS/Twitter 监听流

# RLEF 反思引擎配置
AUTO_TUNER_USE_LLM=true   # 启用 LLM 深度反思，否则只能进行硬编码的数学权重调整
```

---

## 2. 核心模块启动方式

系统被设计为“常驻守护进程”+“事件驱动”的模式，您不需要手动逐场比赛点击运行。

### 2.1 启动主系统心跳 (The Heartbeat)
系统的核心驱动力是 `Heartbeat Daemon`。它会自动扫描赛程，并在午夜进行 RLEF 进化。

```bash
PYTHONPATH=. python3 core_system/core/digital_life/heartbeat_daemon.py
```
**启动后系统将执行以下行为**：
1. **日间模式**：自动扫描并启动针对高价值比赛的 MCTS 推演（慢思考轨道）。
2. **夜间模式**：在凌晨 3:00 自动唤醒 `AutoTunerAgent`，读取 SQLite 账本中的真实盈亏数据，进行 RLEF 闭环反思，并动态调整第二天 ZSA 快轨的截胡阈值。

### 2.2 启动 ZSA 极速截胡监听器 (The Front-Runner)
由于 ZSA 快轨需要实现 5 毫秒级的出票拦截，它在后台以守护线程的方式常驻内存。

在生产环境中，ZSA 会伴随系统初始化自动启动（见 `social_listener.py` 的 `__init__`）。如果您想单独测试突发新闻截胡：
```bash
python3 core_system/tests/architecture_tests/test_zsa_front_running.py
```
*此脚本模拟了阿森纳前锋受伤的突发事件，您将看到系统如何在 6ms 内完成做空出票。*

### 2.3 测试高价值比赛的 MCTS + GWM 联合推演
如果您想观察系统在遇到复杂比赛（如欧冠决赛）时，是如何触发红蓝军辩论（MoA），并调用生成式世界模型（GWM）进行几何战术推演的：
```bash
python3 core_system/tests/architecture_tests/test_gwm_mcts_parallel.py
```

---

## 3. 监控与运维

由于系统具有“自主意识”，日常运维的重点是“看它怎么想”，而不是“教它怎么做”。

### 3.1 查看系统资金与账本
系统所有的交易记录、滑点、盈亏（PnL）都记录在本地的高并发 SQLite 数据库中：
* **路径**: `core_system/workspace/data/ledger.db`
* **表结构**: `bankroll` (各代理余额), `bets` (具体注单), `transactions` (资金流水)

您可以通过简单的 SQLite 客户端（如 DBeaver）打开查看，或者系统会通过 RLEF 自动提取分析。

### 3.2 观察系统的“思想演化” (Dynamic Experience)
系统在每次出现亏损后，会通过 RLEF 引擎提取一条“实战纪律”，永久写入它的经验库。
* **路径**: `core_system/docs/DYNAMIC_EXPERIENCE.md`
* 没事的时候打开这个文件，您能看到这个 AI 是如何在市场的毒打下逐渐变得冷酷无情的。

### 3.3 检查当前超参数状态
RLEF 每天都会根据战绩修改底层权重。
* **路径**: `core_system/configs/hyperparams.json`
* 重点关注 `weights` (基本面/反买/聪明钱的比例) 和 `zsa_thresholds` (突发新闻的敏感度阈值)。

---

## 4. 常见问题排查 (FAQ)

1. **ZSA 截胡没有触发？**
   - 检查 `.env` 中的 `USE_LOCAL_SLM=true`。
   - 首次运行 `cross-encoder/nli-distilroberta-base` 时需要从 HuggingFace 下载几百兆的模型权重，请确保网络通畅。
2. **LangGraph 陷入死循环？**
   - 检查 `state_graph_orchestrator.py` 中的 `debate_done` 标志是否被正确传递。我们已经加入了强制防死循环机制：只要执行过出票工具，流转必定结束。
3. **API 费用过高？**
   - 系统的 MCTS 和 MoA 辩论极其消耗 Token。请确保 `Heartbeat Daemon` 中的哨兵节点（Sentinel）正常工作，将 90% 的垃圾比赛过滤掉，只让 LLM 深度思考那 10% 的高价值盘口。

---
*愿代码与期望值(EV)同在。*