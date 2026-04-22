# 2026 AI-Native Football Quant Analyzer
> The ultimate autonomous multi-agent system for sports arbitrage, featuring OpenClaw, Hermes Agent, and Standalone StateGraph architectures.

## 🚀 Quick Start (How to Clone and Run)

Due to GitHub's strict 100MB file limit, the massive 1.5GB historical database (`chroma.sqlite3`) and raw datasets required by the AI are **NOT** included in the `git clone` by default. This keeps the repository extremely lightweight (~1.5MB) and lightning-fast to clone.

To set up the complete system locally, please follow these 3 simple steps:

### Step 1: Clone the repository
```bash
git clone https://github.com/luenglueng205-rgb/football_analyzer.git
cd football_analyzer
```

### Step 2: Download the Data Pack (1.5GB)
*(Note: As the maintainer, you need to upload your local `global_knowledge_base` folder as a `.zip` file to GitHub Releases or a cloud drive like Google Drive/Baidu Wangpan, and place the link here for your users).*
1. Download `global_knowledge_base.zip` from [Your Release/Drive Link Here].
2. Extract the `.zip` file directly into the root folder of this project so that you have a `global_knowledge_base/` folder alongside `README.md`.

### Step 3: Run the Initialization Script
We provide a setup script that will automatically configure the correct symlinks (soft links) so that all 3 architectures (OpenClaw, Hermes, Standalone) can share the same 1.5GB database without wasting your hard drive space!

```bash
bash scripts/setup_env.sh
```

### Step 4: Verify the System
Run the ultimate 2026 Chaos Engineering test to ensure all three AI architectures are fully functional:
```bash
python3 standalone_workspace/docs/superpowers/tests/test_all_evolution.py
```
If you see ✅ passing logs for MCTS, AST Injection defense, and Swarm clustering, your system is 100% complete and ready for real-world arbitrage!
