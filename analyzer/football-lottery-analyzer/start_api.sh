#!/bin/bash
# 启动 Analyzer API (System 2)

echo "安装依赖..."
pip install -r requirements.txt

echo "启动 API Server..."
python api_server.py
