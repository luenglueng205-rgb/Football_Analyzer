# Git History Purge and LFS Setup Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Purge the 1.12GB of bloated `.git` history caused by accidentally tracking large `.tar.gz` and database files. Ensure the project is lean enough to push to GitHub without errors. Configure Git LFS for any legitimate large files if necessary.

**Architecture:**
1. **History Rewrite**: Use `git filter-repo` to surgically remove all `backups/`, `*.tar.gz`, and `*.db` files from the *entire* Git commit history. This does not delete your current local files, only their historical snapshots.
2. **Garbage Collection**: Run `git gc --prune=now --aggressive` to physically delete the orphaned 1.12GB of data from the `.git` folder.
3. **Re-link and Push**: `filter-repo` strips remote URLs for safety. We will re-add the GitHub remote and force push the newly cleaned, lightweight history.

**Tech Stack:** Git, Git Filter-Repo.

---

### Task 1: Rewrite Git History (Remove Bloat)

**Files:**
- Modify: `.git` object database

- [ ] **Step 1: Execute filter-repo on specific paths**

Run the following commands to remove the bloated files from all past commits.

```bash
# Force filter-repo to run even if it ran recently
echo "Y" | git filter-repo --path-glob '*.tar.gz' --path-glob '*.db' --path backups/ --invert-paths --force
```

Expected: `filter-repo` parses commits and rewrites the history, stripping out the large files.

### Task 2: Aggressive Garbage Collection

**Files:**
- Modify: `.git` folder size

- [ ] **Step 1: Force Git to drop unreachable objects**

Run:
```bash
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

- [ ] **Step 2: Verify the new size of `.git`**

Run:
```bash
du -sh .git
```
Expected: The size should drop from ~1.12GB down to a few megabytes.

### Task 3: Re-link Remote and Force Push

**Files:**
- Modify: Remote repository `https://github.com/luenglueng205-rgb/Football_Analyzer.git`

- [ ] **Step 1: Re-add the origin remote**

Run:
```bash
git remote add origin https://github.com/luenglueng205-rgb/Football_Analyzer.git
```

- [ ] **Step 2: Force push the clean history**

Run:
```bash
git push -u origin main --force
```
Expected: The push succeeds quickly without hitting the 100MB file limit error.