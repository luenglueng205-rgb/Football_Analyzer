# 破坏性与边界测试执行计划 (Destructive & Edge Case Testing Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 对 `LotteryMathEngine` 和 `ParlayFilterMatrix` 两个核心系统进行深度的白盒破坏性测试。输入非法的、极端的、以及违反物理直觉的数据，以逼出系统中尚未暴露的逻辑漏洞和运行时异常。

**Architecture:** 
- 编写 `test_destructive_math.py` 专门用极端的赔率（如 1.01 对 100.0）和负数的 xG 来轰炸 `LotteryMathEngine`。
- 编写 `test_destructive_parlay.py` 专门用同场比赛、非法组合、以及超额本金来轰炸 `ParlayFilterMatrix`。

**Tech Stack:** Python 3.10+, `pytest`

---

### Task 1: 对泊松数学引擎的破坏性测试 (LotteryMathEngine)

**Files:**
- Create: `standalone_workspace/tests/test_destructive_math.py`

- [ ] **Step 1: 编写极端参数测试**

```python
import pytest
from skills.lottery_math_engine import LotteryMathEngine

def test_extreme_xg_values():
    engine = LotteryMathEngine()
    
    # 测试 1: xG 为 0 的情况（不应抛出除零或域错误，应该返回 0-0 概率 100%）
    markets_zero = engine.calculate_all_markets(0.0, 0.0)
    assert markets_zero["total_goals"]["0"] > 0.99
    
    # 测试 2: 负数 xG 的情况（理论上 xG 不能为负，系统应兜底处理或抛出明确异常，而不是静默计算错误）
    with pytest.raises((ValueError, AssertionError)) as excinfo:
        engine.calculate_all_markets(-1.0, 2.0)
    
    # 测试 3: 极大 xG（如 20.0，测试计算性能和内存是否溢出，概率是否收敛）
    markets_huge = engine.calculate_all_markets(20.0, 1.0)
    assert markets_huge["1x2"]["home"] > 0.99
```

- [ ] **Step 2: 运行测试并观察系统的健壮性**

```bash
python3 -m pytest standalone_workspace/tests/test_destructive_math.py -v
```

### Task 2: 对串关矩阵的破坏性与物理规则测试 (ParlayFilterMatrix)

**Files:**
- Create: `standalone_workspace/tests/test_destructive_parlay.py`

- [ ] **Step 1: 编写同场互斥与奖金封顶测试**

```python
import pytest
from tools.parlay_filter_matrix import ParlayFilterMatrix

def test_same_match_mutex():
    matrix = ParlayFilterMatrix()
    
    # 模拟从同一场比赛（match_id: 1001）选了胜平负和总进球
    candidates = [
        {"match_id": "1001", "selection": "HomeWin", "odds": 2.0, "market": "1x2"},
        {"match_id": "1001", "selection": "Over2.5", "odds": 1.9, "market": "total"},
        {"match_id": "1002", "selection": "AwayWin", "odds": 3.0, "market": "1x2"}
    ]
    
    # 测试：系统不应该生成包含两个 1001 的 2串1
    parlays = matrix.generate_parlays(candidates, parlay_type="2x1")
    
    for p in parlays:
        match_ids = [leg["match_id"] for leg in p["legs"]]
        # 如果列表中 match_id 数量不等于集合数量，说明有重复
        assert len(match_ids) == len(set(match_ids)), f"致命错误：生成了同场互斥的非法串关! {p}"

def test_max_payout_cap():
    matrix = ParlayFilterMatrix()
    
    # 模拟极其变态的高赔率，测试奖金封顶（2-3关最高 20万）
    candidates = [
        {"match_id": "2001", "selection": "Draw", "odds": 50.0, "market": "1x2"},
        {"match_id": "2002", "selection": "Draw", "odds": 50.0, "market": "1x2"}
    ]
    
    # 50 * 50 * 100本金 = 250,000 > 200,000 封顶
    parlays = matrix.generate_parlays(candidates, parlay_type="2x1", stake=100)
    
    assert parlays[0]["max_potential_return"] <= 200000, "致命错误：AI 给出了超过体彩中心物理上限的虚假奖金！"
```

- [ ] **Step 2: 运行测试并观察是否暴露出缺陷**

```bash
python3 -m pytest standalone_workspace/tests/test_destructive_parlay.py -v
```