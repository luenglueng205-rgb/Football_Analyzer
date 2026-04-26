# Root Directory Archiving and Cleanup Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fully organize the root directory by moving all 7 `test_*.py` files into `core_system/tests/architecture_tests`, archiving the `tar.gz` backup into a new `backups/` directory, and moving `rlef_architecture.html` into `core_system/docs/specs/`.

**Architecture:**
1. A new `backups` directory at the root level for storing system snapshots.
2. A new `core_system/tests/architecture_tests` directory to house the experimental sandbox scripts, separating them from standard unit tests.
3. Move the HTML blueprint to `core_system/docs/specs/` where the markdown spec currently resides.
4. Since the tests will be moved one level deeper, we need to ensure they can still run properly by adjusting `sys.path` or providing instructions to run them with `PYTHONPATH=../..`.

**Tech Stack:** Bash, Python.

---

### Task 1: Archive Backup and HTML Files

**Files:**
- Modify: File system (Root)

- [ ] **Step 1: Create directories**

Run: `mkdir -p backups core_system/docs/specs`
Expected: Directories created without error.

- [ ] **Step 2: Move the files**

Run:
```bash
mv football_analyzer_ai_native_backup_20260426_191854.tar.gz backups/
mv rlef_architecture.html core_system/docs/specs/
```
Expected: Files moved successfully.

### Task 3: Move and Refactor Test Scripts

**Files:**
- Modify: File system (Root -> `core_system/tests/architecture_tests`)
- Modify: `test_circadian.py`, `test_gwm_mcts_parallel.py`, `test_gwm_spatial_data.py`, `test_rlef_feedback_loop.py`, `test_zsa_front_running.py`, `test_zsa_latency.py`, `test_zsa_slm_latency.py`

- [ ] **Step 1: Create test directory**

Run: `mkdir -p core_system/tests/architecture_tests`
Expected: Directory created.

- [ ] **Step 2: Move the test files**

Run: `mv test_*.py core_system/tests/architecture_tests/`
Expected: 7 files moved successfully.

- [ ] **Step 3: Update `sys.path` in all test files**

Since the files are moved from the root directory to `core_system/tests/architecture_tests` (3 levels deep from root, or 2 levels deep from `core_system`), we must inject code at the very top of each script to add the project root to `sys.path`. Otherwise, `from core_system.xxx` imports will fail.

For each file in `core_system/tests/architecture_tests/`:
Insert the following at the top (before other imports):
```python
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
```

- [ ] **Step 4: Verify tests still run**

Run: `python3 core_system/tests/architecture_tests/test_zsa_slm_latency.py`
Expected: The test executes successfully without `ModuleNotFoundError`.

### Task 4: Update README.md Instructions

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update execution paths in README**

Search for `PYTHONPATH=. python3 test_*.py` in `README.md` and replace with `python3 core_system/tests/architecture_tests/test_*.py` (since we added sys.path injection, `PYTHONPATH=.` is no longer strictly necessary, but can be kept or removed).

- [ ] **Step 2: Commit changes**

```bash
git add -A
git commit -m "chore: archive root directory files and move architecture tests to dedicated folder"
```