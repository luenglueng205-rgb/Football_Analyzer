# 极限边界测试与系统加固 (Dogfood Testing) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 针对足球分析系统中的核心算法组件，设计极端的输入用例（负数 xG、同场串关冲突、极高赔率等），暴露系统在不规范输入或违反物理规则时的崩溃风险，并在代码层面进行强健的兜底和异常拦截修复。

**Architecture:** 
1. `LotteryMathEngine`: 添加输入值边界检查，限制极大 xG 时的动态矩阵扩展上限，防止内存溢出和矩阵丢失；在非预期输入时快速失败（Fail-Fast）。
2. `ParlayFilterMatrix`: 添加同场比赛的去重检查 (`len(set(match_ids))`)，防止生成体彩违规单；在计算最高奖金时应用 `min(payout, 200000)` 的阶梯封顶机制。

**Tech Stack:** Python 3.10+, `pytest`

---

### Task 1: 修复泊松引擎的极端值处理 (LotteryMathEngine)

**Files:**
- Modify: `standalone_workspace/skills/lottery_math_engine.py`

- [ ] **Step 1: 添加负数校验与动态矩阵扩展逻辑**

在 `LotteryMathEngine.calculate_all_markets` 函数的开头和矩阵计算部分进行修改。

```python
    def calculate_all_markets(self, home_xg: float, away_xg: float, handicap: float = -1.0) -> dict:
        """
        计算一场比赛的所有体彩玩法概率
        :param home_xg: 主队预期进球
        :param away_xg: 客队预期进球
        :param handicap: 让球数 (如 -1.0 表示主让一球)
        """
        # 1. 破坏性测试修复：防范负数 xG 导致的 NaN 崩溃
        if home_xg < 0 or away_xg < 0:
            raise ValueError("xG (预期进球) 必须大于等于 0")
            
        # 2. 破坏性测试修复：当遇到极大 xG 时，动态扩展泊松矩阵，防止截断导致概率丢失
        # 正常比赛 7 个球够了，如果是 20.0 xG，矩阵需要扩大到至少 45 才能收敛
        dynamic_max_goals = max(self.max_goals, int(max(home_xg, away_xg) * 2 + 5))
        
        # 构建泊松概率矩阵
        prob_matrix = np.zeros((dynamic_max_goals, dynamic_max_goals))
        for h in range(dynamic_max_goals):
            for a in range(dynamic_max_goals):
                prob_matrix[h, a] = poisson.pmf(h, home_xg) * poisson.pmf(a, away_xg)
```

- [ ] **Step 2: Commit**

```bash
git add standalone_workspace/skills/lottery_math_engine.py
git commit -m "fix: add bounds checking and dynamic matrix scaling for extreme xG values"
```

### Task 2: 修复串关矩阵的同场互斥与奖金封顶 (ParlayFilterMatrix)

**Files:**
- Modify: `standalone_workspace/tools/parlay_filter_matrix.py`

- [ ] **Step 1: 增加体彩物理规则校验**

在 `ParlayFilterMatrix.generate_parlays` 中增加去重逻辑，并在 `calculate_parlay` 中增加封顶逻辑。

```python
import itertools

class ParlayFilterMatrix:
    
    def generate_parlays(self, candidate_legs: list, parlay_type: str = "2x1", stake: float = 100.0) -> list:
        # 解析玩法，如 "2x1" 取 n=2
        n_legs = int(parlay_type.split("x")[0])
        valid_parlays = []
        
        # 遍历所有可能的 n 场组合
        for combo in itertools.combinations(candidate_legs, n_legs):
            # 1. 破坏性测试修复：同场互斥校验
            # 提取这组方案中所有的 match_id
            match_ids = [leg.get("match_id") for leg in combo if leg.get("match_id")]
            
            # 如果去重后的长度小于原长度，说明存在同场比赛的不同选项串在了一起，必须废弃
            if len(set(match_ids)) < len(match_ids):
                continue
                
            # 计算这个合法组合的奖金
            result = self.calculate_parlay(list(combo), stake)
            if result["status"] == "success":
                valid_parlays.append(result)
                
        return valid_parlays

    def calculate_parlay(self, legs: list, stake: float = 100.0) -> dict:
        # 再次执行同场互斥兜底检查（防御直接调用该方法的场景）
        match_ids = [leg.get("match_id") for leg in legs if leg.get("match_id")]
        if len(set(match_ids)) < len(match_ids):
            return {"status": "error", "message": "Illegal parlay: Contains mutually exclusive legs from the same match."}
            
        total_odds = 1.0
        for leg in legs:
            total_odds *= leg.get("odds", 1.0)
            
        theoretical_return = total_odds * stake
        
        # 2. 破坏性测试修复：体彩最高奖金封顶限制
        # 根据官方规则，2-3 关单注最高 20 万，4-5 关 50 万，6 关及以上 100 万
        n = len(legs)
        if n <= 3:
            max_cap = 200000.0
        elif n <= 5:
            max_cap = 500000.0
        else:
            max_cap = 1000000.0
            
        capped_return = min(theoretical_return, max_cap)
        
        return {
            "status": "success",
            "legs": legs,
            "total_odds": round(total_odds, 2),
            "theoretical_return": round(theoretical_return, 2),
            "max_potential_return": round(capped_return, 2), # 暴露给前端或风控的真实奖金
            "is_capped": theoretical_return > max_cap
        }
```

- [ ] **Step 2: Commit**

```bash
git add standalone_workspace/tools/parlay_filter_matrix.py
git commit -m "fix: implement same-match mutual exclusion and official payout caps for parlays"
```