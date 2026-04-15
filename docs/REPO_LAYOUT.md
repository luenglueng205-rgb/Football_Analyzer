# Repository Layout

This repo contains two runnable distributions:

- `standalone_workspace/`: standalone edition (primary dev target)
- `openclaw_workspace/`: OpenClaw adapter edition (MCP / runtime bridge)

## What is safe to commit

Commit source code, configuration, and docs:

- `standalone_workspace/agents/`, `standalone_workspace/tools/`, `standalone_workspace/core/`
- `standalone_workspace/docs/`
- `openclaw_workspace/src/`, `openclaw_workspace/docs/`, `openclaw_workspace/README.md`
- `.github/workflows/`

## What should stay local (ignored by git)

Local runtime artifacts and large data files are intentionally ignored:

- Repo root `data/` (local DB/vector store/snapshots)
- `**/chroma_db/**`, `**/chroma.sqlite3`
- `**/ledger.db`, `**/snapshots.db`
- `**/tests/qa_reports/*.json` and gatekeeper logs
- Root-level large data packages (zip/json dumps)

## Data directories (common confusion)

- Repo root `data/`
  - Local runtime cache for quick experiments.
  - Not part of the stable source tree.
- `standalone_workspace/data/`
  - Standalone edition runtime data directory.
  - Contains some versioned metadata files plus local DBs.
- `openclaw_workspace/data/`
  - OpenClaw adapter runtime data directory.

If you want a fully reproducible environment, keep only the source trees in git and regenerate the local DB/vector store from ingestion scripts.
