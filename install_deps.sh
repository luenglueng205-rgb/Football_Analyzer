#!/bin/bash
echo "Installing real production dependencies (PyTorch, LangGraph, Playwright, ONNX)..."
python3 -m pip install torch onnx langgraph langchain-core playwright gymnasium --break-system-packages
python3 -m playwright install chromium
echo "Dependencies installed."
