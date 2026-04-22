#!/bin/bash
echo "=================================================="
echo "🚀 2026 AI Native Football Analyzer - 环境初始化脚本"
echo "=================================================="

# 1. 创建全局知识库目录
echo "[1/4] 创建全局数据挂载点 (Global Knowledge Base)..."
mkdir -p global_knowledge_base/data/chroma_db
mkdir -p global_knowledge_base/datasets/raw

# 2. 建立各架构的软链接
echo "[2/4] 建立三大架构的底层数据软链接..."
# Standalone 独立版
rm -rf standalone_workspace/data standalone_workspace/datasets
ln -s ../global_knowledge_base/data standalone_workspace/data
ln -s ../global_knowledge_base/datasets standalone_workspace/datasets

# OpenClaw 适配版
rm -rf openclaw_workspace/data openclaw_workspace/datasets
ln -s ../global_knowledge_base/data openclaw_workspace/data
ln -s ../global_knowledge_base/datasets openclaw_workspace/datasets

echo "[3/4] 准备下载核心向量数据库 (ChromaDB) 与echo "[3/4] 准?."
echo "⚠️ 注意：1.5GB 的核心数据库由于 GitHub 限制，未包含在源码中。"
echo "请从以下链接手动下载完整的 global_knowledge_base.zip，并解压到项目根目录："
echo "👉 下载链接: (请在此处填入您的云盘/Release下载链接)"
echo "或者联系系统管理员获取内部数据包。"

echo "[4/4] 初始化完成！"
echo "在数据解压完成后，您可以通过以下命令启动测试："
echo "python3 standalone_workspace/docs/superpowers/tests/test_all_evolution.py"
