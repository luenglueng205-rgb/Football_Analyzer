# OpenClaw 足球分析 Runtime Workspace

该目录是一个可被 OpenClaw 直接导入的 Native Workspace，包含：

- `src/`：OpenClaw stdio JSON-RPC / MCP Bridge（入口：`src/mcp_server.py`）
- `runtime/football_analyzer/`：搬家后的完整运行时包（agents/tools/skills/docs/入口）
- `data/`：OpenClaw 独立数据目录（ChromaDB、SQLite snapshots、研报输出）

## 安装

```bash
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium
```

## 运行（OpenClaw Stdio）

```bash
export OPENCLAW_FOOTBALL_DATA_DIR=$PWD/data
python3 src/mcp_server.py
```

## 在 OpenClaw 中导入

1. 将 `openclaw_workspace/` 压缩为 zip（例如 `football_analyzer_openclaw.zip`）。
2. 在 OpenClaw 中选择 "Import Native Workspace"。
3. OpenClaw 会读取 `openclaw.json` 并启动 `python3 src/mcp_server.py`（stdio）。
