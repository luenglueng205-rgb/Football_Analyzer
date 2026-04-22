# Ultimate Chinese Lottery Arbitrage Modules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement 3 ultimate arbitrage and risk-avoidance modules for Chinese lotteries: Low Odds Trap Identifier, Latency Arbitrage Monitor, and Betfair Anomaly Detector.

**Architecture:** Create three new files in `standalone_workspace/skills/`: `trap_identifier.py`, `latency_arbitrage.py`, `betfair_anomaly.py`. These will act as static analysis functions that can be imported by the AI or backtesting engine to filter out bad bets and identify high-value arbitrage.

**Tech Stack:** Python 3.10+

---

### Task 1: Low Odds Trap Identifier (蚊子肉排雷器)

**Files:**
- Create: `standalone_workspace/skills/trap_identifier.py`
- Test: `standalone_workspace/tests/test_arbitrage_modules.py`

- [ ] **Step 1: Write the failing test**

```python
# standalone_workspace/tests/test_arbitrage_modules.py
import pytest
from skills.trap_identifier import identify_low_odds_trap

def test_identify_low_odds_trap():
    # Jingcai offers 1.25 for Home Win. Implied prob (with 11% vig) = 0.89 / 1.25 = 71.2%
    # But our Poisson engine says the true prob is only 55.0%
    result = identify_low_odds_trap(jingcai_odds=1.25, true_prob=0.55)
    
    assert result["is_trap"] is True
    assert "蚊子肉陷阱" in result["warning"]
    
    # Safe bet: Jingcai 1.80 (Implied = 0.89/1.8 = 49.4%). True prob = 50.0%
    result_safe = identify_low_odds_trap(jingcai_odds=1.80, true_prob=0.50)
    assert result_safe["is_trap"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest standalone_workspace/tests/test_arbitrage_modules.py::test_identify_low_odds_trap -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Write minimal implementation**

```python
# standalone_workspace/skills/trap_identifier.py
from typing import Dict, Any

def identify_low_odds_trap(jingcai_odds: float, true_prob: float, vig: float = 0.89) -> Dict[str, Any]:
    """
    泊松分布低赔诱盘识别器 (Low Odds Trap Identifier)。
    专门识别竞彩中低于 1.40 的“蚊子肉”毒药选项，防止串关爆仓。
    """
    if jingcai_odds <= 1.0:
        return {"is_trap": True, "warning": "无效赔率"}
        
    implied_prob = vig / jingcai_odds
    
    # 定义陷阱逻辑：
    # 1. 赔率低于 1.40（极度热门）
    # 2. 庄家给出的隐含胜率 远大于 我们算出的真实胜率 (差值 > 10%)
    is_low_odds = jingcai_odds < 1.40
    prob_divergence = implied_prob - true_prob
    
    is_trap = is_low_odds and (prob_divergence > 0.10)
    
    warning = ""
    if is_trap:
        warning = f"🚨 蚊子肉陷阱警告！竞彩开出 {jingcai_odds} 极低赔率诱导串关，其隐含胜率为 {implied_prob:.1%}，但真实胜率仅为 {true_prob:.1%}。严重高估，坚决规避！"
    elif is_low_odds:
        warning = f"⚠️ 赔率较低 ({jingcai_odds})，但真实胜率 ({true_prob:.1%}) 足以支撑，可作串关稳胆。"
    else:
        warning = "✅ 赔率处于正常区间，无明显诱盘迹象。"
        
    return {
        "is_trap": is_trap,
        "implied_prob": round(implied_prob, 3),
        "true_prob": round(true_prob, 3),
        "divergence": round(prob_divergence, 3),
        "warning": warning
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest standalone_workspace/tests/test_arbitrage_modules.py::test_identify_low_odds_trap -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add standalone_workspace/skills/trap_identifier.py standalone_workspace/tests/test_arbitrage_modules.py
git commit -m "feat(arbitrage): implement Low Odds Trap Identifier to filter fake Jingcai favorites"
```

### Task 2: Latency Arbitrage Monitor (时差套利)

**Files:**
- Create: `standalone_workspace/skills/latency_arbitrage.py`
- Modify: `standalone_workspace/tests/test_arbitrage_modules.py`

- [ ] **Step 1: Write the failing test**

```python
# standalone_workspace/tests/test_arbitrage_modules.py
# Append:
from skills.latency_arbitrage import detect_latency_arbitrage

def test_detect_latency_arbitrage():
    # Pinnacle odds for Home: 2.10 (Fair prob ~ 47.6%)
    # Jingcai odds for Home: 2.30
    # Normally Jingcai is lower than Pinnacle due to high vig. 
    # If Jingcai > Pinnacle, it means Jingcai hasn't reacted to a market crash yet.
    
    result = detect_latency_arbitrage(jingcai_odds=2.30, pinnacle_odds=2.10)
    
    assert result["is_arbitrage"] is True
    assert result["ev"] > 0
    assert "时差套利" in result["alert"]
    
    # Normal situation: Pinnacle 1.80, Jingcai 1.60
    result_normal = detect_latency_arbitrage(jingcai_odds=1.60, pinnacle_odds=1.80)
    assert result_normal["is_arbitrage"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest standalone_workspace/tests/test_arbitrage_modules.py::test_detect_latency_arbitrage -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# standalone_workspace/skills/latency_arbitrage.py
from typing import Dict, Any

def detect_latency_arbitrage(jingcai_odds: float, pinnacle_odds: float, pinnacle_margin: float = 0.025) -> Dict[str, Any]:
    """
    赔率时差套利监控器 (Latency Arbitrage Monitor)。
    对比竞彩固定赔率与国际主流公司（如平博 Pinnacle）的即时赔率。
    如果竞彩赔率高于国际市场“去抽水”后的公平赔率，说明竞彩操盘手反应滞后，存在绝对套利空间。
    """
    if jingcai_odds <= 1.0 or pinnacle_odds <= 1.0:
        return {"is_arbitrage": False, "alert": "无效赔率"}
        
    # 计算 Pinnacle 的真实概率 (剔除 2.5% 的平博标准抽水)
    # Fair Prob = (1 / Pinnacle Odds) * (1 - Margin) 简化计算
    fair_prob = (1.0 / pinnacle_odds) * (1.0 - pinnacle_margin)
    
    # 计算在竞彩下注的期望值 EV
    ev = (fair_prob * jingcai_odds) - 1.0
    
    # 只要 EV > 0，就是绝对的降维打击套利
    is_arbitrage = ev > 0.02 # 设定 2% 的最小摩擦阈值
    
    alert = ""
    if is_arbitrage:
        alert = f"💰 时差套利触发！平博赔率已跌至 {pinnacle_odds} (真实胜率 {fair_prob:.1%})，而竞彩仍停留在 {jingcai_odds}。立即买入，期望收益率: {ev:.2%}！"
    else:
        alert = "无套利空间，竞彩赔率处于正常被抽水状态。"
        
    return {
        "is_arbitrage": is_arbitrage,
        "fair_prob": round(fair_prob, 3),
        "ev": round(ev, 3),
        "alert": alert
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest standalone_workspace/tests/test_arbitrage_modules.py::test_detect_latency_arbitrage -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add standalone_workspace/skills/latency_arbitrage.py standalone_workspace/tests/test_arbitrage_modules.py
git commit -m "feat(arbitrage): implement Latency Arbitrage Monitor for identifying delayed Jingcai odds drops"
```

### Task 3: Betfair Volume Anomaly Detector (必发冷热)

**Files:**
- Create: `standalone_workspace/skills/betfair_anomaly.py`
- Modify: `standalone_workspace/tests/test_arbitrage_modules.py`

- [ ] **Step 1: Write the failing test**

```python
# standalone_workspace/tests/test_arbitrage_modules.py
# Append:
from skills.betfair_anomaly import detect_betfair_anomaly

def test_detect_betfair_anomaly():
    # Betfair market: Home odds 2.0 (Implied prob 50%).
    # But matched volume on Home is 85% of total market volume.
    # Money is pouring into Home, but odds aren't dropping -> Smart Money is Laying (Selling) Home.
    
    result = detect_betfair_anomaly(odds=2.0, volume_percentage=0.85)
    
    assert result["is_anomaly"] is True
    assert "大热必死" in result["analysis"] or "主力派发" in result["analysis"]
    assert result["suggested_action"] == "FADE" # 反向操作
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest standalone_workspace/tests/test_arbitrage_modules.py::test_detect_betfair_anomaly -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# standalone_workspace/skills/betfair_anomaly.py
from typing import Dict, Any

def detect_betfair_anomaly(odds: float, volume_percentage: float) -> Dict[str, Any]:
    """
    必发交易量异常探测器 (Betfair Volume Anomaly Detector)。
    对比某选项的“赔率隐含概率”与“实际成交资金比例”。
    专门用于传统足彩（任九）和北单的“冷热防爆”与反向套利。
    """
    if odds <= 1.0 or volume_percentage < 0 or volume_percentage > 1:
        return {"is_anomaly": False, "analysis": "无效数据"}
        
    implied_prob = 1.0 / odds
    
    # 计算资金热度偏差 (Volume Divergence)
    divergence = volume_percentage - implied_prob
    
    is_anomaly = False
    analysis = ""
    suggested_action = "OBSERVE"
    
    if divergence > 0.25:
        # 资金极度集中，但赔率并未反映出这种胜率（即赔率居高不下）
        # 典型的“主力派发 / 散户接盘”陷阱，俗称大热必死
        is_anomaly = True
        analysis = f"🚨 主力派发警告！成交量占比高达 {volume_percentage:.1%}，但赔率维持在 {odds} (概率仅 {implied_prob:.1%})。存在巨大的卖单(Lay)压制，大热必死。"
        suggested_action = "FADE" # 建议反买（防冷）
        
    elif divergence < -0.15 and implied_prob > 0.40:
        # 赔率很低（看似稳赢），但市场上根本没人买
        # 典型的“诱盘冷遇”或“聪明钱撤退”
        is_anomaly = True
        analysis = f"🥶 聪明钱冷遇！赔率仅 {odds} (概率 {implied_prob:.1%})，但成交量极度萎靡 ({volume_percentage:.1%})。庄家可能在诱导串关，缺乏主力资金背书。"
        suggested_action = "FADE"
        
    else:
        analysis = f"✅ 资金与赔率分布合理。隐含概率 {implied_prob:.1%}，成交比例 {volume_percentage:.1%}。"
        suggested_action = "FOLLOW" if implied_prob > 0.5 else "OBSERVE"
        
    return {
        "is_anomaly": is_anomaly,
        "implied_prob": round(implied_prob, 3),
        "divergence": round(divergence, 3),
        "analysis": analysis,
        "suggested_action": suggested_action
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest standalone_workspace/tests/test_arbitrage_modules.py::test_detect_betfair_anomaly -v`
Expected: PASS

- [ ] **Step 5: Sync to OpenClaw and Commit**

```bash
cp standalone_workspace/skills/trap_identifier.py openclaw_workspace/runtime/football_analyzer/skills/
cp standalone_workspace/skills/latency_arbitrage.py openclaw_workspace/runtime/football_analyzer/skills/
cp standalone_workspace/skills/betfair_anomaly.py openclaw_workspace/runtime/football_analyzer/skills/
git add .
git commit -m "feat(arbitrage): fully implement Latency Arbitrage, Betfair Anomaly, and Trap Identifier modules for Chinese lottery exploitation"
```
