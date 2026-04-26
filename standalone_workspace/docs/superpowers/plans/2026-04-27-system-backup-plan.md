# System Backup and Archiving Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a comprehensive, updated backup of the entire `football_analyzer` system after the recent major architectural evolutions (ZSA, GWM, RLEF, and Directory Consolidation).

**Architecture:** 
1. We will use the `tar` command to create a compressed `.tar.gz` archive.
2. The naming convention will follow the existing pattern: `football_analyzer_ultimate_evolution_YYYYMMDD_HHMMSS.tar.gz`.
3. We will exclude unnecessary files that bloat the backup, such as `.git/`, `__pycache__/`, `.DS_Store`, and existing backups in the `backups/` directory to prevent recursive archiving.
4. The generated archive will be placed securely in the `backups/` directory.

**Tech Stack:** Bash (`tar`, `date`).

---

### Task 1: Generate the Ultimate Evolution Backup Archive

**Files:**
- Create: `backups/football_analyzer_ultimate_evolution_*.tar.gz`

- [ ] **Step 1: Execute the tar command with exclusions**

Run the following bash command from the project root to create the backup. It uses `date` to dynamically generate the timestamp.

```bash
# 获取当前时间戳
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="football_analyzer_ultimate_evolution_${TIMESTAMP}.tar.gz"

# 执行打包，排除 git、缓存和已有的备份文件
tar -czvf "backups/${BACKUP_NAME}" \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.DS_Store' \
    --exclude='backups/*.tar.gz' \
    .

echo "Backup created: backups/${BACKUP_NAME}"
```

- [ ] **Step 2: Verify the backup file was created**

Run: `ls -lh backups/`
Expected: Shows the newly created `football_analyzer_ultimate_evolution_*.tar.gz` file with a reasonable file size.
