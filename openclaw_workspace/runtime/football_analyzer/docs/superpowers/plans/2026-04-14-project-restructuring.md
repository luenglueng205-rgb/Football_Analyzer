# Project Restructuring Plan (平行双子星架构大扫除)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 执行大扫除，将散落在项目根目录的独立版代码（如 agents, tools, skills 等）全部移入新建的 `standalone_workspace` 文件夹，实现与 `openclaw_workspace` 的完全物理隔离。

**Architecture:** 将项目根目录重构为纯粹的容器，包含两个平行的、互不干扰的独立工作区。调整相关脚本（如测试脚本、入口脚本）内的 `import` 路径（如果需要）或依靠 `PYTHONPATH` 确保运行正常。

**Tech Stack:** `bash`, `git mv`

---

### Task 1: 创建 standalone_workspace 并迁移核心代码

**Files:**
- Create: `standalone_workspace/`
- Move: `agents/`, `tools/`, `skills/`, `docs/`, `data/`, `reports/`, `tests/`
- Move: 根目录下的 python 脚本（`market_sentinel.py`, `run_live_decision.py`, `test_api.py`, `test_memory.py`）

- [ ] **Step 1: 创建 standalone_workspace 目录**

```bash
mkdir -p standalone_workspace
```

- [ ] **Step 2: 移动核心模块目录**

```bash
# 使用 git mv 保留提交历史
git mv agents standalone_workspace/
git mv tools standalone_workspace/
git mv skills standalone_workspace/
git mv data standalone_workspace/
git mv reports standalone_workspace/
git mv tests standalone_workspace/
# docs 目录包含我们的 specs 和 plans，也一起移入
git mv docs standalone_workspace/
```

- [ ] **Step 3: 移动根目录脚本和配置文件**

```bash
git mv market_sentinel.py standalone_workspace/
git mv run_live_decision.py standalone_workspace/
git mv test_api.py standalone_workspace/
git mv test_memory.py standalone_workspace/
git mv configs standalone_workspace/ 2>/dev/null || true
git mv tickets standalone_workspace/ 2>/dev/null || true
```

- [ ] **Step 4: 补充或移动依赖文件**

```bash
# 如果根目录有 requirements.txt，也移进去
if [ -f "requirements.txt" ]; then git mv requirements.txt standalone_workspace/; fi
```

### Task 2: 验证独立版与 OpenClaw 版的运行隔离性

**Files:**
- None

- [ ] **Step 1: 验证 standalone_workspace (独立版) 能否独立运行**

```bash
# 在 standalone_workspace 目录下执行
cd standalone_workspace
PYTHONPATH=. python3 run_live_decision.py
```
Expected: PASS (输出推演日志，不受根目录变更影响)

- [ ] **Step 2: 验证 openclaw_workspace 能否独立运行**

```bash
# 回到项目根目录
cd ..
# 在 openclaw_workspace 目录下执行之前的验收脚本
cd openclaw_workspace
PYTHONPATH=runtime/football_analyzer python3 tests/task6_acceptance_test.py
```
Expected: PASS (Task6 acceptance test: OK)

### Task 3: 提交重构变更

**Files:**
- All moved files

- [ ] **Step 1: Commit 大扫除变更**

```bash
# 回到根目录
cd ..
git add standalone_workspace/
git commit -m "refactor: complete physical isolation of standalone and openclaw workspaces"
```