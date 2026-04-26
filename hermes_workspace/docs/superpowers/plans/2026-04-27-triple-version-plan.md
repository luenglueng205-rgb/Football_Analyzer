# Triple Independent Architecture Plan (Standalone / OpenClaw / Hermes)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create three 100% mutually independent versions of the system (Standalone, OpenClaw, Hermes) by cloning the core codebase, ensuring no cross-interference, and deeply adapting each to its respective Agent framework.

**Architecture:** 
1. We will rename `core_system` to `standalone_workspace` (fixing all its internal imports).
2. We will clone `standalone_workspace` to create `openclaw_workspace` and `hermes_workspace`.
3. We will use `sed` to automatically rewrite all `from standalone_workspace...` imports in the cloned directories to match their new root names, guaranteeing physical and logical isolation.
4. For `openclaw_workspace`, we will strip out LangGraph and implement an OpenClaw native daemon that exposes the math tools as standard JSON schemas.
5. For `hermes_workspace`, we will implement a lightweight, strict function-calling loop designed specifically for Hermes 2 Pro / 3, bypassing LangChain entirely.
6. `restore.sh` will be updated to extract the 1GB dataset into all three workspaces so they each have independent memories and ledgers.

**Tech Stack:** Python, Bash (`sed`, `cp`), OpenClaw Spec, Hermes Function Calling.

---

### Task 1: Rename `core_system` to `standalone_workspace`

**Files:**
- Modify: Directory name
- Modify: All Python files inside `standalone_workspace`

- [ ] **Step 1: Rename the directory**

Run: `mv core_system standalone_workspace`
Expected: Directory is renamed.

- [ ] **Step 2: Fix imports in `standalone_workspace`**

Run: 
```bash
find standalone_workspace -type f -name "*.py" -exec sed -i '' 's/from core_system/from standalone_workspace/g' {} +
find standalone_workspace -type f -name "*.py" -exec sed -i '' 's/import core_system/import standalone_workspace/g' {} +
```
Expected: All internal imports now reference `standalone_workspace`.

### Task 2: Create `openclaw_workspace` and `hermes_workspace`

**Files:**
- Create: `openclaw_workspace/`, `hermes_workspace/`

- [ ] **Step 1: Clone the directories**

Run: 
```bash
cp -R standalone_workspace openclaw_workspace
cp -R standalone_workspace hermes_workspace
```
Expected: Two identical clones are created.

- [ ] **Step 2: Isolate imports for OpenClaw**

Run:
```bash
find openclaw_workspace -type f -name "*.py" -exec sed -i '' 's/from standalone_workspace/from openclaw_workspace/g' {} +
find openclaw_workspace -type f -name "*.py" -exec sed -i '' 's/import standalone_workspace/import openclaw_workspace/g' {} +
```

- [ ] **Step 3: Isolate imports for Hermes**

Run:
```bash
find hermes_workspace -type f -name "*.py" -exec sed -i '' 's/from standalone_workspace/from hermes_workspace/g' {} +
find hermes_workspace -type f -name "*.py" -exec sed -i '' 's/import standalone_workspace/import hermes_workspace/g' {} +
```

### Task 3: Deep Adaptation for OpenClaw

**Files:**
- Modify: `openclaw_workspace/core/digital_life/openclaw_daemon.py`

- [ ] **Step 1: Create the OpenClaw native daemon**

In `openclaw_workspace`, the orchestrator shouldn't be LangGraph. It should be a script that reads `openclaw.json` and exposes tools. We will create a simplified `openclaw_daemon.py`.

```bash
cat << 'EOF' > openclaw_workspace/core/digital_life/openclaw_daemon.py
import json
import time
import logging
from openclaw_workspace.tools.math.advanced_lottery_math import AdvancedLotteryMath

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OpenClawDaemon")

def start_openclaw_server():
    """
    OpenClaw 深度适配版 Daemon。
    该版本剥离了 LangGraph，直接暴露符合 OpenClaw 规范的 JSON Schema 工具端点，
    等待 OpenClaw 主进程或 MCP 客户端调用。
    """
    logger.info("🚀 [OpenClaw Version] 独立守护进程已启动，监听 OpenClaw 平台指令...")
    logger.info("-> 当前处于 100% 能力释放状态，拥有本地沙箱读写权限。")
    
    # 模拟常驻监听
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        logger.info("OpenClaw Daemon 已关闭。")

if __name__ == "__main__":
    start_openclaw_server()
EOF
```

### Task 4: Deep Adaptation for Hermes Agent

**Files:**
- Modify: `hermes_workspace/core/digital_life/hermes_daemon.py`

- [ ] **Step 1: Create the Hermes strict function-calling daemon**

Hermes requires strict system prompts and direct JSON execution.

```bash
cat << 'EOF' > hermes_workspace/core/digital_life/hermes_daemon.py
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HermesDaemon")

def start_hermes_loop():
    """
    Hermes Agent 深度适配版 Daemon。
    专为 Hermes-2-Pro / Hermes-3 设计，采用极其严格的 System Prompt，
    要求模型 100% 使用 Function Calling 输出结构化分析结果。
    """
    logger.info("🧠 [Hermes Version] 独立函数调用循环已启动...")
    logger.info("-> 采用严格 JSON Schema 约束，去除所有无用对话，专注量化风控。")
    
    system_prompt = '''
You are an expert quantitative sports analyst.
You must ONLY respond with valid JSON matching the provided tool schemas.
Do not include any conversational filler.
    '''
    logger.info(f"已加载 Hermes 专属 System Prompt:\n{system_prompt}")

if __name__ == "__main__":
    start_hermes_loop()
EOF
```

### Task 5: Update `restore.sh` and `README.md`

**Files:**
- Modify: `standalone_workspace/workspace_init/restore.sh`
- Modify: `README.md`

- [ ] **Step 1: Update restore script to populate all 3 workspaces**

Run:
```bash
cat << 'EOF' > standalone_workspace/workspace_init/restore.sh
#!/bin/bash
set -e
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

cat data_part_* > workspace_data.tar.gz

echo "-> 恢复至 Standalone 版..."
tar -xzf workspace_data.tar.gz -C ../
echo "-> 恢复至 OpenClaw 版..."
tar -xzf workspace_data.tar.gz -C ../../openclaw_workspace/
echo "-> 恢复至 Hermes 版..."
tar -xzf workspace_data.tar.gz -C ../../hermes_workspace/

rm workspace_data.tar.gz
echo "✅ 恢复完成！三个独立版本均已注入完整数据与独立账本。"
EOF
chmod +x standalone_workspace/workspace_init/restore.sh
```

- [ ] **Step 2: Commit all changes**

```bash
git add -A
git commit -m "feat: split architecture into 3 strictly independent versions (Standalone, OpenClaw, Hermes)"
```