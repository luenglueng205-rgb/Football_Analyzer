# Kelly Variance Analyzer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the final "Bookmaker's Mindset" tool: A Kelly Variance Analyzer to detect match fixing and deep institutional consensus.

**Architecture:** Create `standalone_workspace/skills/kelly_variance_analyzer.py`. It will take a list of odds from different bookmakers for a single outcome (e.g., Home Win), calculate the implied probabilities, normalize them against the average market vig, compute the Kelly Index for each, and return the statistical variance.

**Tech Stack:** Python 3.10+, `statistics`

---

### Task 1: Kelly Variance Analyzer

**Files:**
- Create: `standalone_workspace/skills/kelly_variance_analyzer.py`
- Modify: `standalone_workspace/tests/test_arbitrage_modules.py`

- [ ] **Step 1: Write the failing test**

```python
# standalone_workspace/tests/test_arbitrage_modules.py
# Append:
from skills.kelly_variance_analyzer import analyze_kelly_variance

def test_analyze_kelly_variance():
    # Scenario 1: High consensus (Low variance). All bookies agree Home is strong.
    # Odds: Bet365: 1.50, Pinnacle: 1.51, William Hill: 1.49, Macauslot: 1.50
    odds_consensus = [1.50, 1.51, 1.49, 1.50]
    result_consensus = analyze_kelly_variance(odds_consensus)
    
    assert "variance" in result_consensus
    assert result_consensus["variance"] < 0.005
    assert result_consensus["is_consensus"] is True
    
    # Scenario 2: High variance (Bookies are confused or someone knows something)
    # Odds: Bet365: 1.50, Pinnacle: 1.80, William Hill: 1.40, Macauslot: 1.90
    odds_chaos = [1.50, 1.80, 1.40, 1.90]
    result_chaos = analyze_kelly_variance(odds_chaos)
    
    assert result_chaos["variance"] > 0.01
    assert result_chaos["is_consensus"] is False
    assert "分歧极大" in result_chaos["analysis"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest standalone_workspace/tests/test_arbitrage_modules.py::test_analyze_kelly_variance -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# standalone_workspace/skills/kelly_variance_analyzer.py
import statistics
from typing import List, Dict, Any

def analyze_kelly_variance(bookmaker_odds: List[float], global_avg_prob: float = None) -> Dict[str, Any]:
    """
    百家赔率离散度与凯利方差分析器 (Kelly Index Variance Analyzer)。
    用于识别全球博彩公司对某场比赛是否存在“高度共谋 (Consensus)”或“严重分歧 (Anomaly)”。
    极低的方差且配合亚洲盘口异常，通常是“假球/默契球”的终极信号。
    """
    if not bookmaker_odds or len(bookmaker_odds) < 2:
        return {"variance": 0.0, "is_consensus": False, "analysis": "数据样本不足"}
        
    # 过滤无效赔率
    valid_odds = [o for o in bookmaker_odds if o > 1.0]
    if len(valid_odds) < 2:
        return {"variance": 0.0, "is_consensus": False, "analysis": "有效赔率样本不足"}
        
    # 计算隐含概率 (假设平均抽水 5%，即 0.95 返奖率)
    implied_probs = [0.95 / o for o in valid_odds]
    
    # 如果没有提供全球平均真实概率，则使用样本的平均隐含概率作为基准
    if global_avg_prob is None:
        global_avg_prob = sum(implied_probs) / len(implied_probs)
        
    # 计算每家公司的凯利指数 (Kelly Index)
    # 凯利指数 = 某公司赔率 * 全球平均真实胜率
    # 如果指数 > 1.0，说明该公司面临亏损风险；如果大家都在 0.90-0.95 之间且方差极小，说明步调一致
    kelly_indices = [o * global_avg_prob for o in valid_odds]
    
    # 计算方差 (Variance)
    variance = statistics.variance(kelly_indices)
    
    is_consensus = False
    analysis = ""
    
    if variance < 0.002:
        is_consensus = True
        analysis = f"🕵️‍♂️ 极度共谋！百家赔率凯利方差仅为 {variance:.4f}。全球庄家对该赛果的防范高度一致，属于绝对的‘机构共识’。若此时亚盘疯狂退盘，极可能是诱导资金的默契球陷阱。"
    elif variance > 0.015:
        is_consensus = False
        analysis = f"⚠️ 分歧极大！百家赔率凯利方差高达 {variance:.4f}。各路资金和情报在此刻发生严重冲突，机构之间存在巨大分歧，建议放弃该场比赛。"
    else:
        is_consensus = True # Normal market consensus
        analysis = f"✅ 正常市场波动。凯利方差为 {variance:.4f}，属于合理的机构间水位差。"
        
    return {
        "variance": round(variance, 4),
        "mean_kelly": round(sum(kelly_indices) / len(kelly_indices), 3),
        "is_consensus": is_consensus,
        "analysis": analysis
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest standalone_workspace/tests/test_arbitrage_modules.py::test_analyze_kelly_variance -v`
Expected: PASS

- [ ] **Step 5: Sync to OpenClaw and Commit**

```bash
cp standalone_workspace/skills/kelly_variance_analyzer.py openclaw_workspace/runtime/football_analyzer/skills/
git add .
git commit -m "feat(arbitrage): implement Kelly Variance Analyzer to detect match-fixing, deep consensus, and bookmaker divergence"
```
