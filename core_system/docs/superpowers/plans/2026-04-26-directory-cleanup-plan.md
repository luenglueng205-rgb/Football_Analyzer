# Project Directory Cleanup and Consolidation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clean up the project directory by removing redundant `data`, `datasets`, and `global_knowledge_base` folders from the root directory, consolidating `core_system/data` and `core_system/datasets` into `core_system/workspace/data` and `core_system/workspace/datasets`, and fixing hardcoded paths in the codebase to use the centralized `paths.py` configuration.

**Architecture:** 
1. The single source of truth for paths is `core_system/tools/paths.py`, which defines the workspace root and data directories.
2. We will safely delete the unused root-level directories.
3. We will move any existing data from `core_system/data` and `core_system/datasets` to their correct locations under `core_system/workspace/`.
4. We will refactor scripts that currently hardcode `data/` or `datasets/` paths to use `paths.py` instead, preventing future fragmentation.

**Tech Stack:** Bash (for file operations), Python (for refactoring).

---

### Task 1: Clean Up Root Directory

**Files:**
- Modify: File system (Root directory)

- [ ] **Step 1: Verify root directories are safe to delete**

Run: `ls -la data datasets global_knowledge_base`
Expected: Lists contents of these directories or shows they don't exist.

- [ ] **Step 2: Delete redundant root directories**

Run: `rm -rf data datasets global_knowledge_base`
Expected: Directories are removed without errors.

### Task 2: Consolidate `core_system` Data Directories

**Files:**
- Modify: File system (`core_system/`)

- [ ] **Step 1: Ensure target workspace directories exist**

Run: `mkdir -p core_system/workspace/data core_system/workspace/datasets`
Expected: Directories are created or already exist.

- [ ] **Step 2: Move contents and remove old directories**

Run: 
```bash
# Move contents if directories exist, ignore errors if they don't or are empty
[ -d "core_system/data" ] && cp -R core_system/data/* core_system/workspace/data/ 2>/dev/null || true
[ -d "core_system/datasets" ] && cp -R core_system/datasets/* core_system/workspace/datasets/ 2>/dev/null || true

# Remove the old directories
rm -rf core_system/data core_system/datasets
```
Expected: Contents are merged into `workspace` and old directories are deleted.

### Task 3: Refactor Hardcoded Paths in Codebase

**Files:**
- Modify: `core_system/tools/paths.py` (Verify it points to workspace)
- Modify: Scripts using hardcoded paths

- [ ] **Step 1: Verify `paths.py` configuration**

Ensure `paths.py` correctly points to `core_system/workspace`.

Run: `cat core_system/tools/paths.py`
Expected: Should show `_workspace_root = os.path.join(_project_root, "core_system", "workspace")` or similar. If it points to `global_knowledge_base`, we will update it to point to `workspace` to match the current architectural standard.

*(If needed based on Step 1 output, we will update `paths.py`)*

- [ ] **Step 2: Find hardcoded paths**

Run: `grep -r "[\"']data/" core_system/` and `grep -r "os.path.join(.*\"data\"" core_system/`
Expected: A list of files containing hardcoded paths like `"data/elo"` or `os.path.join(..., "data", ...)`.

- [ ] **Step 3: Refactor `core_system/scripts/data_ingestion_pipeline.py`**

If found in Step 2, update the ingestion checkpoint path.

```python
# Before
checkpoint_file = os.path.join(PROJECT_ROOT, "data", "ingestion_checkpoint.json")

# After
from core_system.tools.paths import data_dir
checkpoint_file = os.path.join(data_dir(), "ingestion_checkpoint.json")
```

- [ ] **Step 4: Refactor ELO storage paths**

If found in Step 2, update `elo_storage.py` and `elo_update_service.py` (or similar files) to use `data_dir()`.

```python
# Before
_DEFAULT_ELO_DIR = "data/elo"

# After
from core_system.tools.paths import data_dir
_DEFAULT_ELO_DIR = os.path.join(data_dir(), "elo")
```

- [ ] **Step 5: Refactor JSON configs (if applicable)**

If files like `openclaw.json` contain hardcoded `"storage": "data/memory/..."`, we need to ensure the code that *reads* these configs resolves the paths relative to `data_dir()`. 

- [ ] **Step 6: Commit changes**

```bash
git add -A
git commit -m "chore: clean up project directory and consolidate data paths to workspace"
```
