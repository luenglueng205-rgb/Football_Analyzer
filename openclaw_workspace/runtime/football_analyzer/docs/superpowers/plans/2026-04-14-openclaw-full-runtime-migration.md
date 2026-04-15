# OpenClaw 全运行时搬家式迁移 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将独立版足球分析系统（含 SyndicateOS / MarketSentinel / 规则库 / 记忆库 / 研报 / 周末洪峰 worker pool / browser-use）整体迁移到 `openclaw_workspace/`，使 OpenClaw 适配版在“只拿 openclaw_workspace 目录”的情况下即可 100% 运行，且使用独立的数据目录 `openclaw_workspace/data/`。

**Architecture:** 在 `openclaw_workspace/runtime/` 内落地一份完整可运行的“内置运行时包”，并在 OpenClaw 的 stdio JSON-RPC bridge（[mcp_server.py](file:///Volumes/J%20ZAO%209%20SER%201/Python/TRAE-SOLO/football_analyzer/openclaw_workspace/src/mcp_server.py)）中新增 workflow/daemon 接口（run job / start sentinel / stop sentinel / status）。工具层继续通过 [tool_registry_v2.py](file:///Volumes/J%20ZAO%209%20SER%201/Python/TRAE-SOLO/football_analyzer/tools/tool_registry_v2.py) 动态导出，从而保持工具自动同步。

**Tech Stack:** Python, asyncio, threading, chromadb, scipy, playwright/browser-use, OpenAI SDK, OpenClaw custom JSON-RPC bridge.

---

## File Structure（迁移后的目标结构）

- `openclaw_workspace/`
  - `src/`
    - `mcp_server.py`（扩展：tool + workflow + daemon）
  - `runtime/`
    - `football_analyzer/`（搬家后的完整运行时包）
      - `agents/`
      - `tools/`
      - `skills/`
      - `docs/`（包含 `lottery_rulebook.md`）
      - `market_sentinel.py`（作为可导入模块）
      - `run_live_decision.py`（作为可导入模块/示例）
  - `data/`
    - `chroma_db/`
    - `snapshots.db`
    - `reports/`
  - `requirements.txt`
  - `README.md`（启动方式、环境变量）

---

### Task 1: “搬家包”落地（Runtime Packaging）

**Files:**
- Create: `openclaw_workspace/runtime/football_analyzer/__init__.py`
- Create: `openclaw_workspace/runtime/football_analyzer/...`（复制独立版的 agents/tools/skills/docs 与入口模块）
- Create: `openclaw_workspace/README.md`

- [ ] **Step 1: 复制代码树到 openclaw_workspace/runtime/football_analyzer/**

复制（或按需裁剪）以下目录和文件到新路径（保持相对结构不变）：

- `agents/` → `openclaw_workspace/runtime/football_analyzer/agents/`
- `tools/` → `openclaw_workspace/runtime/football_analyzer/tools/`
- `skills/` → `openclaw_workspace/runtime/football_analyzer/skills/`
- `docs/lottery_rulebook.md` → `openclaw_workspace/runtime/football_analyzer/docs/lottery_rulebook.md`
- `market_sentinel.py` → `openclaw_workspace/runtime/football_analyzer/market_sentinel.py`
- `run_live_decision.py` → `openclaw_workspace/runtime/football_analyzer/run_live_decision.py`

- [ ] **Step 2: 添加包入口文件**

创建 `openclaw_workspace/runtime/football_analyzer/__init__.py`：

```python
__all__ = ["agents", "tools", "skills"]
```

- [ ] **Step 3: 在 openclaw_workspace/README.md 写清楚运行方式**

至少包含：
- `export OPENCLAW_FOOTBALL_DATA_DIR=$PWD/data`
- `python3 src/mcp_server.py`（stdio JSON-RPC）
- Playwright/Chromium 安装命令

---

### Task 2: 数据目录统一（OpenClaw 独立 data/）

**Files:**
- Modify: `openclaw_workspace/runtime/football_analyzer/tools/snapshot_store.py`
- Modify: `openclaw_workspace/runtime/football_analyzer/tools/memory_manager.py`
- Modify: `openclaw_workspace/runtime/football_analyzer/agents/publisher_agent.py`
- Modify: `openclaw_workspace/runtime/football_analyzer/tools/visual_browser.py`（如有缓存/截图目录）

- [ ] **Step 1: 定义统一数据根目录解析函数**

在 `openclaw_workspace/runtime/football_analyzer/tools/paths.py`（新建）落一个最小实现：

```python
import os
from pathlib import Path

def data_dir() -> str:
    root = os.getenv("OPENCLAW_FOOTBALL_DATA_DIR")
    if root:
        return root
    return str(Path(__file__).resolve().parents[3] / "data")
```

- [ ] **Step 2: SnapshotStore 使用 data_dir()**

把 SQLite 路径改为：
- `Path(data_dir()) / "snapshots.db"`

- [ ] **Step 3: MemoryManager（ChromaDB）使用 data_dir()**

把 ChromaDB 路径改为：
- `Path(data_dir()) / "chroma_db"`

- [ ] **Step 4: PublisherAgent 输出目录使用 data_dir()**

把研报目录改为：
- `Path(data_dir()) / "reports"`

- [ ] **Step 5: 写一个验证脚本**

在 `openclaw_workspace/runtime/football_analyzer/tests/test_data_paths.py`（可新建）里验证：
- 不设置环境变量时，默认写入 `openclaw_workspace/data/`
- 设置环境变量时，写入指定目录

---

### Task 3: 依赖可复现（OpenClaw workspace 自给自足）

**Files:**
- Create: `openclaw_workspace/requirements.txt`

- [ ] **Step 1: 固化依赖**

在 `openclaw_workspace/requirements.txt` 写入独立版运行所需核心依赖（按仓库实际使用补齐/对齐版本）：

```txt
openai
pydantic
requests
ddgs
chromadb
scipy
playwright
browser-use
langchain-openai
```

- [ ] **Step 2: 写明 Playwright 安装**

在 README 提供命令：

```bash
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium
```

---

### Task 4: OpenClaw MCP Server 扩展为“工具 + 工作流 + 守护进程”

**Files:**
- Modify: `openclaw_workspace/src/mcp_server.py`
- Create: `openclaw_workspace/src/runtime_bridge.py`

- [ ] **Step 1: 在 mcp_server.py 注入 sys.path 指向 runtime 包**

在 `mcp_server.py` 启动时加入：
- `openclaw_workspace/runtime` 到 `sys.path`
- 默认设置 `OPENCLAW_FOOTBALL_DATA_DIR` 为 `openclaw_workspace/data`（若未设置）

- [ ] **Step 2: 新增 RuntimeBridge**

在 `runtime_bridge.py` 实现：
- `run_once_match(home, away, lottery_desc)` → 调用 `SyndicateOS.process_match`
- `run_once_market_scan()` → 调用 `MarketSentinel` 的“一轮扫描 API”（需要在 runtime 里提供可调用入口）
- `start_sentinel(max_workers, polling_interval)` → 后台线程启动守护循环
- `stop_sentinel()` / `status()` → 查询与停止

要求：不引入全局死锁；daemon 在后台线程运行一个独立 event loop。

- [ ] **Step 3: 在 mcp_server.py 扩展 JSON-RPC methods**

现有：
- `list_tools`
- `call_tool`

新增：
- `run_workflow`（一次性任务：match/market）
- `daemon_start`
- `daemon_stop`
- `daemon_status`

示例 request：

```json
{"id": 2, "method": "run_workflow", "params": {"name": "run_once_match", "arguments": {"home_team": "曼联", "away_team": "切尔西", "lottery_desc": "竞彩足球"}}}
```

---

### Task 5: 运行时对齐（把“脚本入口”变成可调用 API）

**Files:**
- Modify: `openclaw_workspace/runtime/football_analyzer/market_sentinel.py`
- Modify: `openclaw_workspace/runtime/football_analyzer/agents/syndicate_os.py`

- [ ] **Step 1: MarketSentinel 增加 run_once()**

增加一个不进入无限循环的 API：
- `async def run_once(self) -> dict`：完成一次抓赛程→筛选→入队→等待队列清空→返回本轮摘要（分析了多少场/生成了多少报告/跳过原因统计）。

- [ ] **Step 2: SyndicateOS 增加“可控输出”**

为 OpenClaw 调用提供：
- `process_match(..., *, emit_report: bool = True)` 或在返回值里包含结构化字段，便于 OpenClaw UI 展示。

---

### Task 6: 验收用例（必须可重复）

**Files:**
- Create: `openclaw_workspace/tests/test_openclaw_bridge.sh`（或 python）

- [ ] **Step 1: list_tools 必须包含关键工具**

验证工具至少包含：
- `calculate_all_markets`
- `retrieve_team_memory`
- `save_team_insight`

（当前主仓库已验证，迁移后也必须验证）

- [ ] **Step 2: run_once_match 可跑通**

通过 stdio JSON-RPC 调用 `run_workflow/run_once_match`，期望返回：
- `scout_report`
- `debates`
- `final_decision`
- `publisher_report_path`（或生成的报告内容摘要）

- [ ] **Step 3: daemon_start / daemon_status / daemon_stop 可用**

启动 daemon 后：
- status 显示 running=true
- stop 后 status 显示 running=false

---

### Task 7: Commit（只在用户要求时执行）

本任务不自动提交。若你要求提交，将按以下方式提交：

```bash
git add openclaw_workspace
git commit -m "feat(openclaw): migrate full runtime into openclaw workspace with dedicated data dir"
```

---

## Execution Handoff

计划完成并保存至：
- [2026-04-14-openclaw-full-runtime-migration.md](file:///Volumes/J%20ZAO%209%20SER%201/Python/TRAE-SOLO/football_analyzer/docs/superpowers/plans/2026-04-14-openclaw-full-runtime-migration.md)

两种执行方式：
- **1. Subagent-Driven (recommended)**：我按 Task 逐个派发子代理落地并在每个 Task 后做验证回报
- **2. Inline Execution**：我在当前会话逐步修改与验证

你选哪种方式执行？

