# Beidan SXDS Matrix Evolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the specialized Beidan 4-Quadrant Matrix (上下盘单双 - Over/Under & Odd/Even) analyzer for deep structural investment.

**Architecture:** Add `calculate_beidan_sxds_matrix` to `standalone_workspace/skills/advanced_lottery_math.py`. It maps the Poisson matrix into the four Beidan specific quadrants.

**Tech Stack:** Python 3.10+

---

### Task 1: Beidan SXDS (Over/Under & Odd/Even) Mapper

**Files:**
- Modify: `standalone_workspace/skills/advanced_lottery_math.py`
- Modify: `standalone_workspace/tests/test_advanced_math.py`

- [ ] **Step 1: Write the failing test**

```python
# standalone_workspace/tests/test_advanced_math.py
# Append:
from skills.advanced_lottery_math import calculate_beidan_sxds_matrix

def test_calculate_beidan_sxds_matrix():
    # Create a dummy 5x5 poisson matrix
    matrix = [[0.0 for _ in range(5)] for _ in range(5)]
    
    # 0:0 -> 0 goals (Under), Even -> 下双
    matrix[0][0] = 0.1
    # 1:0 -> 1 goal (Under), Odd -> 下单
    matrix[1][0] = 0.2
    # 2:1 -> 3 goals (Over), Odd -> 上单
    matrix[2][1] = 0.3
    # 2:2 -> 4 goals (Over), Even -> 上双
    matrix[2][2] = 0.4
    
    result = calculate_beidan_sxds_matrix(matrix)
    
    assert abs(result["下双"] - 0.1) < 0.001
    assert abs(result["下单"] - 0.2) < 0.001
    assert abs(result["上单"] - 0.3) < 0.001
    assert abs(result["上双"] - 0.4) < 0.001
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest standalone_workspace/tests/test_advanced_math.py::test_calculate_beidan_sxds_matrix -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# standalone_workspace/skills/advanced_lottery_math.py
# Append:
def calculate_beidan_sxds_matrix(poisson_matrix: List[List[float]]) -> Dict[str, float]:
    """
    计算北京单场专属玩法：上下盘单双 (SXDS)。
    上盘: 总进球 >= 3; 下盘: 总进球 < 3
    单双: 总进球数的奇偶
    """
    sxds = {
        "上单": 0.0,
        "上双": 0.0,
        "下单": 0.0,
        "下双": 0.0
    }
    
    max_goals = len(poisson_matrix)
    for h in range(max_goals):
        for a in range(max_goals):
            prob = poisson_matrix[h][a]
            if prob == 0: continue
            
            total_goals = h + a
            is_over = total_goals >= 3
            is_even = total_goals % 2 == 0
            
            if is_over and not is_even:
                sxds["上单"] += prob
            elif is_over and is_even:
                sxds["上双"] += prob
            elif not is_over and not is_even:
                sxds["下单"] += prob
            elif not is_over and is_even:
                sxds["下双"] += prob
                
    # Normalize in case of rounding errors, though it should sum to 1.0 if matrix is full
    total = sum(sxds.values())
    if total > 0:
        for k in sxds:
            sxds[k] = round(sxds[k] / total, 4)
            
    return sxds
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest standalone_workspace/tests/test_advanced_math.py::test_calculate_beidan_sxds_matrix -v`
Expected: PASS

- [ ] **Step 5: Sync and Commit**

```bash
cp standalone_workspace/skills/advanced_lottery_math.py openclaw_workspace/runtime/football_analyzer/skills/
git add .
git commit -m "feat(math): implement Beidan SXDS (Over/Under & Odd/Even) matrix calculator for deep arbitrage"
```
