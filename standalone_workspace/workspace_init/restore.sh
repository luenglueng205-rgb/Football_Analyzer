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
echo "📂 正在解压恢复数据 (Extracting to Standalone version)..."
echo "========================================================"
echo "-> 恢复至 Standalone (独立版) 工作区..."
tar -xzvf workspace_data.tar.gz -C ../

echo "========================================================"
echo "🧹 清理临时合并文件 (Cleaning up)..."
echo "========================================================"
rm workspace_data.tar.gz

echo "✅ 恢复完成！Standalone 独立版本已注入完整记忆，拥有独立的账本数据库。"
