# GitHub Push Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Safely and completely push the current local codebase to the remote GitHub repository (`https://github.com/luenglueng205-rgb/Football_Analyzer.git`), ensuring no large files (>100MB) are accidentally pushed which would break the Git history.

**Architecture:** 
1. We must verify and update the `.gitignore` file to strictly ignore `backups/`, `*.tar.gz`, `*.db` (SQLite databases can get large), and large JSON datasets if they exceed GitHub's limits.
2. We must remove any accidentally tracked large files from the Git cache (like the `tar.gz` we just committed).
3. We will amend the previous commit or create a new one with the clean index.
4. We will set the remote URL and forcefully push the `main` branch.

**Tech Stack:** Git, Bash.

---

### Task 1: Secure `.gitignore` Against Large Files

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Append ignore rules**

Run:
```bash
echo "" >> .gitignore
echo "# Archiving & Large Files" >> .gitignore
echo "backups/" >> .gitignore
echo "*.tar.gz" >> .gitignore
echo "*.db" >> .gitignore
echo "*.sqlite3" >> .gitignore
echo "core_system/workspace/datasets/raw/*.json" >> .gitignore
```
Expected: The rules are successfully added to `.gitignore`.

### Task 2: Purge Large Files from Git Cache

**Files:**
- Modify: Git Index

- [ ] **Step 1: Untrack the backup archives**

We previously ran `git add backups/football_analyzer_ultimate_evolution_*.tar.gz` and committed it. We MUST undo this, otherwise the push will fail because the 490MB file is in the commit history.

Run:
```bash
# Soft reset the last commit to keep working tree changes but uncommit them
git reset --soft HEAD~1

# Remove the large tar.gz files from the Git cache
git rm --cached -r backups/ || true
git rm --cached *.tar.gz || true

# Re-add everything else (which now respects the updated .gitignore)
git add -A

# Re-commit
git commit -m "chore: create ultimate evolution system backup archive (untracked)"
```
Expected: The large files are removed from Git's tracking, and the commit is recreated safely.

### Task 3: Push to GitHub

**Files:**
- Modify: Remote Repository

- [ ] **Step 1: Set remote URL**

Ensure the remote is correct.

Run:
```bash
git remote set-url origin https://github.com/luenglueng205-rgb/Football_Analyzer.git || git remote add origin https://github.com/luenglueng205-rgb/Football_Analyzer.git
```
Expected: Remote is configured.

- [ ] **Step 2: Push code**

Run:
```bash
git push -u origin main --force
```
Expected: The code is pushed 100% to GitHub. (Note: using `--force` because we altered the local commit history in Task 2 to purge the large file).