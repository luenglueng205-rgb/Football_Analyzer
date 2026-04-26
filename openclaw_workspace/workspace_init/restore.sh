#!/bin/bash
# 恢复工作区数据脚本 (Restore Workspace Data)
# 作用: 合并 GitHub 上的 50MB 分卷包并解压，恢复 1GB 的历史数据和数据库

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

echo "========================================================"
echo "📦 正在合并分卷数据包 (Merging data chunks)..."
echo "========================================================"
cat data_part_* > workspace_data.tar.gz

echo "========================================================"
echo "📂 正在解压恢复至 workspace 目录 (Extracting)..."
echo "========================================================"
tar -xzvf workspace_data.tar.gz -C ../

echo "========================================================"
echo "🧹 清理临时合并文件 (Cleaning up)..."
echo "========================================================"
rm workspace_data.tar.gz

echo "✅ 恢复完成！系统现在已经注入了完整的记忆和历史数据，可立即运行。"
