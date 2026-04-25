# 架构硬盘占用差异深度剖析报告

针对您提出的问题：“为什么三个版本大小差别那么大？有几kb的，有1.63gb的，有3.19gb的，整个根目录大小有6.04gb？”

我立即执行了底层磁盘分析 (`du -sh *`)，并为您查明了这种“极度不平衡”的根本原因。这并非代码冗余或错误，而是**三大架构在数据存储与设计哲学上的本质差异导致的**。

## 1. 数据盘点与分布

*   **总根目录占用**：约 6.0GB
*   **OpenClaw Workspace**：约 3.0GB
*   **Standalone Workspace**：约 1.5GB
*   **Hermes Workspace**：约 24KB

## 2. 差异原因深度剖析

### 🔍 为什么 Hermes Agent 只有 24KB？
这是因为它是一个纯粹的 **“插件库 (Plugins Directory)”**。
*   Hermes 的设计哲学是：**大模型基座、本地知识库、依赖环境全部安装在操作系统级别的 `~/.hermes` 核心目录中**。
*   我们在 `hermes_workspace` 中编写的，仅仅是挂载给 Hermes 核心引擎的量化代码（如 `auto_skill_betfair_hot_trap.py`）。它本身不存储历史数据，也不自带数据库，它只提供“大脑逻辑”。因此，它的体积小到可以忽略不计。

### 🔍 为什么 Standalone 独立版有 1.5GB？
因为它是“自给自足”的，携带了庞大的数据基建。
*   **ChromaDB 向量数据库 (`standalone_workspace/data/chroma_db`)：占用约 1.0GB**。我们在前几轮的进化中，把几十万条真实历史比赛数据（球队基本面、历史赔率、天气等）切片并存入了本地向量数据库中，以便独立版大模型能随时进行 RAG (检索增强生成)。其中单单一个 `chroma.sqlite3` 索引文件就高达 500MB+。
*   **原始数据集 (`standalone_workspace/datasets/raw`)：占用约 54MB**。存储了爬虫抓取下来的原始 JSON/CSV 赛果。
*   独立版包含了所有运行所需的测试报告、记忆日志和代码库，是一个完全可以独立打包部署的“重型武器”。

### 🔍 为什么 OpenClaw 适配版高达 3.0GB？
这是由 OpenClaw 的 **“多沙盒运行时 (Runtime Sandboxing)”** 机制决定的。
*   OpenClaw 为了保证我们量化代码的安全性与独立性，它会在自己的工作区内**完整克隆 (Clone/Copy)** 一套数据环境和依赖环境到 `runtime` 目录。
*   我刚刚通过 `du -h -d 2` 命令查明：在 `openclaw_workspace` 下，不仅有它自己原生的 `data` 目录（1.5GB，包含了 ChromaDB 和 datasets），还在 `openclaw_workspace/runtime/football_analyzer` 下面**又硬拷贝了一份高达 1.5GB 的环境**。
*   **结论**：1.5GB 原生数据 + 1.5GB 沙盒 Runtime 数据 = 3.0GB。这是 OpenClaw 为了实现我们在 `swarm_daemon.py` 中规划的“多容器并发隔离”所付出的磁盘空间代价。

## 3. 解决建议与优化方向

虽然这种体积差异反映了三大架构的设计初衷，但为了优化您的硬盘空间，我们可以执行以下动作：

1.  **数据去重 (Symlink 化)**：没必要让 OpenClaw 和 Standalone 各自维护一个高达 1.0GB 的 ChromaDB 数据库。我们可以将底层的历史向量数据剥离到一个公共目录（例如 `global_data/`），然后让三个架构都通过**软链接 (Symlink)** 去读取。这样瞬间就能腾出近 2.5GB 的空间。
2.  **清理 OpenClaw 的冗余 Runtime**：我们在测试阶段不需要保留庞大的沙盒快照，可以定期清理 `openclaw_workspace/runtime` 目录。

