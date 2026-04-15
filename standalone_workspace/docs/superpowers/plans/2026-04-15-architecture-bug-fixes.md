# 历史数据核心架构修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复系统中历史数据利用的两大核心架构级 Bug：1. 摒弃 ChromaDB 的语义查询，改用精确的浮点数元数据 (Metadata) 范围查询；2. 摒弃线性的 xG 估算，采用 `scipy.optimize.root_scalar` 进行高精度非线性泊松逆推。

**Architecture:** 
- **MemoryManager 改造**：重写 `query_historical_odds`，移除基于 `query_texts` 的文本语义查询，改用 ChromaDB 的 `$and`, `$gte`, `$lte` 逻辑运算符进行精确的数值区间过滤。
- **Backtest Sandbox 改造**：在 `historical_backtest_engine.py` 中引入 `scipy.optimize`，通过非线性求解器求解泊松分布方程组，逼近最精确的主客队预期进球 (xG)。

**Tech Stack:** Python 3.10+, ChromaDB, `scipy.optimize`, `scipy.stats.poisson`

---

### Task 1: 修复 ScoutAgent 历史盘感的“语义盲区”Bug

**Files:**
- Modify: `standalone_workspace/tools/memory_manager.py`

- [ ] **Step 1: 重写 `query_historical_odds` 方法**

```python
    def query_historical_odds(self, league: str, home_odds: float, draw_odds: float, away_odds: float, tolerance: float = 0.10, limit: int = 20) -> dict:
        """
        [修复版] 精确数值过滤查询：彻底摒弃大模型对数字极度不敏感的语义向量查询。
        改用 ChromaDB 的结构化 Metadata 逻辑运算符 ($and, $gte, $lte) 进行硬逻辑区间匹配。
        """
        try:
            # 构建容差区间
            h_min, h_max = home_odds * (1 - tolerance), home_odds * (1 + tolerance)
            d_min, d_max = draw_odds * (1 - tolerance), draw_odds * (1 + tolerance)
            a_min, a_max = away_odds * (1 - tolerance), away_odds * (1 + tolerance)
            
            # 使用 ChromaDB 强大的 Metadata 过滤语法
            where_clause = {
                "$and": [
                    {"type": {"$eq": "historical_match"}},
                    {"league": {"$eq": league}},
                    {"home_odds": {"$gte": h_min}},
                    {"home_odds": {"$lte": h_max}},
                    {"draw_odds": {"$gte": d_min}},
                    {"draw_odds": {"$lte": d_max}},
                    {"away_odds": {"$gte": a_min}},
                    {"away_odds": {"$lte": a_max}}
                ]
            }
            
            # 注意：这里我们传入一个虚拟的查询文本或直接留空，完全依靠 where 过滤。
            # ChromaDB 要求必须有 query_texts 或 query_embeddings，我们随便传一个即可，因为完全靠 where 拦截。
            results = self.collection.query(
                query_texts=["odds matching"],
                n_results=limit,
                where=where_clause
            )
            
            if not results["documents"] or not results["documents"][0]:
                return {"ok": True, "data": [], "message": "未找到相似赔率的历史比赛"}
                
            return {"ok": True, "data": results["documents"][0]}
        except Exception as e:
            return {"ok": False, "error": str(e)}
```

- [ ] **Step 2: Commit**

```bash
git add standalone_workspace/tools/memory_manager.py
git commit -m "fix: replace semantic search with exact metadata range query for odds"
```

### Task 2: 修复时光机回测的“非线性 xG 逆推”Bug

**Files:**
- Modify: `standalone_workspace/scripts/historical_backtest_engine.py`

- [ ] **Step 1: 引入 `scipy.optimize` 并重写 `reverse_engineer_xg`**

```python
from scipy.optimize import root_scalar
from scipy.stats import poisson

def reverse_engineer_xg(home_odds: float, draw_odds: float, away_odds: float, juice: float = 0.05) -> tuple:
    """
    [修复版] 非线性泊松逆推：彻底抛弃粗糙的线性映射。
    利用 scipy.optimize.root_scalar 非线性求解器，强行逼近最精确的主客队预期进球 (xG)。
    """
    # 1. 去除抽水，获取庄家眼中的真实概率
    total_prob = (1/home_odds) + (1/draw_odds) + (1/away_odds)
    p_home_target = (1/home_odds) / total_prob
    p_away_target = (1/away_odds) / total_prob
    p_draw_target = (1/draw_odds) / total_prob
    
    # 2. 定义目标函数：寻找一个基础 xG，使得双泊松算出的胜率与真实概率最接近
    # 为了简化非线性方程组，我们假设总进球的基数 base_xg，并且主客队 xG 的比例与 p_home/p_away 的比例强相关
    ratio = p_home_target / p_away_target
    
    def objective_function(base_xg):
        # 根据 ratio 分配主客 xG
        h_xg = base_xg * (ratio / (1 + ratio)) * 2 # 乘以2是因为总进球是两队之和
        a_xg = base_xg * (1 / (1 + ratio)) * 2
        
        # 使用泊松分布计算 0-5 球的概率矩阵，求主胜概率
        calc_home_win = 0.0
        for h in range(1, 6):
            for a in range(0, h):
                calc_home_win += poisson.pmf(h, h_xg) * poisson.pmf(a, a_xg)
                
        # 目标：计算出的主胜概率 - 真实的 p_home_target = 0
        return calc_home_win - p_home_target
        
    try:
        # 使用 scipy.optimize 寻找根 (root)，假设一场比赛总进球在 0.5 到 5.5 之间
        result = root_scalar(objective_function, bracket=[0.5, 5.5], method='brentq')
        if result.converged:
            optimal_base_xg = result.root
            h_xg = optimal_base_xg * (ratio / (1 + ratio)) * 2
            a_xg = optimal_base_xg * (1 / (1 + ratio)) * 2
            return round(h_xg, 2), round(a_xg, 2)
    except ValueError:
        # 如果非线性求解失败（例如赔率极度悬殊，找不到根），回退到粗糙的线性映射
        pass
        
    # Fallback 机制
    base_xg = 2.5
    home_xg = base_xg * p_home_target * 1.2
    away_xg = base_xg * p_away_target
    return max(0.1, round(home_xg, 2)), max(0.1, round(away_xg, 2))
```

- [ ] **Step 2: Commit**

```bash
git add standalone_workspace/scripts/historical_backtest_engine.py
git commit -m "fix: upgrade xG reverse engineering to non-linear poisson solver"
```