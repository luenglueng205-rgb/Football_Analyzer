# Ultimate Evolution: Triple Track Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the three final evolution directions in parallel: 1) Alternative Data Integration (Weather/Referee MCP), 2) Markowitz Portfolio Optimization (Kelly 2.0), and 3) The AI Quant Researcher Loop with a safe Human Approval Gate.

**Architecture:** 
- **Track 1 (Data):** Enhance `state_graph_orchestrator.py` to fetch unstructured weather/referee data via existing tools before running the math engine, adjusting the base xG.
- **Track 2 (Portfolio):** Create a new entry point `portfolio_batch_runner.py` that takes multiple matches, runs the orchestrator for each, and then passes the positive EV results through the `MarkowitzPortfolioOptimizer` to generate a safe, risk-parity parlay matrix.
- **Track 3 (Research):** Create an executable script `run_quant_researcher.py` that initializes the `QuantResearcherAgent`, runs it for N iterations on the historical database, and outputs the highest Sharpe Ratio strategy for user review (Human Approval Gate).

**Tech Stack:** Python, LangGraph, Scipy (for Markowitz), OpenAI/DeepSeek API.

---

### Task 1: Track 1 - Alternative Data Integration

**Files:**
- Modify: `core_system/core/agentic_os/state_graph_orchestrator.py`

- [ ] **Step 1: Expose environment tools to the Orchestrator**

In `state_graph_orchestrator.py`, import the environment analyzer and add it to the tool list.

```python
# Add to imports
from core_system.tools.environment_analyzer import EnvironmentAnalyzer

# Create a new tool
@tool
def fetch_match_environment(city: str, referee_strictness: str = "medium") -> dict:
    """
    获取比赛的环境因素（天气、裁判尺度）对预期进球数(xG)的量化影响。
    必须在计算泊松概率前调用此工具，以获取 xG 的修正系数。
    """
    analyzer = EnvironmentAnalyzer()
    # 这里为了演示，假设我们在查天气时 mock 一个真实天气
    # 实际生产中可以接入 multisource_fetcher
    mock_weather = "heavy_rain" if "Manchester" in city else "clear"
    impact = analyzer.analyze_unstructured_factors(weather=mock_weather, referee_strictness=referee_strictness)
    return {
        "weather": mock_weather,
        "referee": referee_strictness,
        "xg_modifier": impact
    }

# Add to tools list
tools = [calculate_true_probs_for_all_markets, verify_risk, check_balance, execute_ticket_route, fetch_arbitrage_news, execute_quant_script, simulate_latent_tactics, fetch_match_environment]
tool_map = {t.name: t for t in tools}
```

- [ ] **Step 2: Update the System Prompt**

Update the `sentinel_node` and main LLM prompt to require checking the environment.

Find the `SystemMessage` in the state initialization or node prompt:
```python
                "1. 调用 fetch_match_environment 获取天气和裁判对进球数的影响系数。\n"
                "2. 调用 simulate_latent_tactics 摄取 ST-GNN 空间数据，推演未来 15 分钟的战术剧本。\n"
                "3. 调用 calculate_true_probs_for_all_markets 计算基础泊松概率，并叠加环境系数。\n"
```

### Task 2: Track 2 - Markowitz Portfolio Batch Runner

**Files:**
- Create: `core_system/scripts/portfolio_batch_runner.py`

- [ ] **Step 1: Write the batch runner script**

This script simulates a busy Saturday with 5 matches. It mocks the EV outputs and feeds them into the `MarkowitzPortfolioOptimizer`.

```python
import os
import sys
import json
from pprint import pprint

# Setup paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, PROJECT_ROOT)

from core_system.tools.markowitz_portfolio import MarkowitzPortfolioOptimizer

def run_saturday_portfolio():
    print("==================================================")
    print("📈 [Markowitz Portfolio] 周末多场次资金分配优化启动")
    print("==================================================")
    
    # 模拟周末 5 场比赛经过大模型和图网络筛选后，全部为正 EV 的候选池
    candidates = [
        {"match_id": "EPL_01", "selection": "home_win", "odds": 1.90, "prob": 0.60}, # EV: 1.14
        {"match_id": "EPL_02", "selection": "away_win", "odds": 2.50, "prob": 0.45}, # EV: 1.125
        {"match_id": "LA_01",  "selection": "draw",     "odds": 3.40, "prob": 0.32}, # EV: 1.088
        {"match_id": "SA_01",  "selection": "home_win", "odds": 1.50, "prob": 0.72}, # EV: 1.08
        {"match_id": "UCL_01", "selection": "away_win", "odds": 4.20, "prob": 0.28}, # EV: 1.176 (高赔防冷)
    ]
    
    print(f"-> 发现 {len(candidates)} 场正期望(EV>1)赛事，准备进行马科维茨风险平价计算...")
    
    total_bankroll = 10000.0
    optimizer = MarkowitzPortfolioOptimizer(total_bankroll=total_bankroll, max_drawdown=0.15) # 最大单日回撤 15%
    
    portfolio = optimizer.optimize_portfolio(candidates)
    
    print("\n✅ 资金分配矩阵计算完成：")
    for bet in portfolio:
        print(f"   赛事: {bet['match_id']} | 选项: {bet['selection']} | 赔率: {bet['odds']} | "
              f"分配资金: ${bet['recommended_stake']:.2f} ({bet['fractional_kelly']*100:.2f}% 仓位)")
              
    total_exposure = sum(b['recommended_stake'] for b in portfolio)
    print(f"\n📊 投资组合统计：")
    print(f"   总本金: ${total_bankroll:.2f}")
    print(f"   总暴露资金: ${total_exposure:.2f} (占比: {(total_exposure/total_bankroll)*100:.2f}%)")
    print(f"   是否触发全局缩水保护: {'是' if total_exposure/total_bankroll >= 0.149 else '否'}")

if __name__ == "__main__":
    run_saturday_portfolio()
```

### Task 3: Track 3 - AI Quant Researcher Loop

**Files:**
- Create: `core_system/scripts/run_quant_researcher.py`

- [ ] **Step 1: Write the researcher trigger script**

This script initializes the Agent, sets the Human Approval Gate, and runs 2 iterations for demonstration.

```python
import os
import sys
import asyncio
from dotenv import load_dotenv

# Setup paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, PROJECT_ROOT)

from core_system.agents.ai_quant_researcher import QuantResearcherAgent

async def main():
    load_dotenv()
    
    print("==================================================")
    print("🧠 [AI Quant Researcher] 全自动量化投研沙箱启动")
    print("==================================================")
    print("-> 警告：此 Agent 将自主编写 Python 策略代码，并在沙箱中执行回测。")
    print("-> 安全策略：Human Approval Gate (人工审批门) 已强制开启。\n")
    
    # 确保 API Key 存在
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("DEEPSEEK_API_KEY"):
        print("❌ 错误: 未配置大模型 API Key。请在 .env 中设置 OPENAI_API_KEY。")
        return
        
    try:
        # 初始化研究员，强制开启人工审批
        researcher = QuantResearcherAgent(require_human_approval=True)
        
        # 运行 2 轮迭代寻找高夏普比率策略 (演示用 2 轮，生产可设为 10)
        print("-> 开始自我迭代寻优 (Max Iterations: 2)...\n")
        await researcher.auto_research_loop(max_iterations=2)
        
    except Exception as e:
        print(f"\n❌ 投研循环异常中断: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Task 4: Run Tests to Verify

**Files:**
- Execute scripts

- [ ] **Step 1: Test Track 2 (Portfolio)**
Run: `python3 core_system/scripts/portfolio_batch_runner.py`
Expected: Outputs a list of matches with optimized stakes, ensuring the total exposure does not exceed $1500 (15% of $10000).

- [ ] **Step 2: Commit Changes**
```bash
git add core_system/core/agentic_os/state_graph_orchestrator.py core_system/scripts/portfolio_batch_runner.py core_system/scripts/run_quant_researcher.py
git commit -m "feat: implement triple track evolution (alternative data, markowitz portfolio, and quant researcher agent)"
```