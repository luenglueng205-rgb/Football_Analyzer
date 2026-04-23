# 终极领域精通 (Domain Mastery) 进阶量化模型 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 4 个独立的进阶量化与风控模型：球员微观价值量化、蒙特卡洛时间轴剧本模拟、聪明资金异常监控、非结构化因素建模，补齐系统领域精通的最后拼图。

**Architecture:** 每个模型作为独立的 `tool` 或 `skill` 在 `standalone_workspace` 下构建。它们分别处理不同的微观计算与风控逻辑，并通过暴露纯函数接口供外部（如 Agent）调用。

**Tech Stack:** Python 3.10+, `numpy`, `scipy`, `pytest`, `asyncio`

---

### Task 1: 球员微观价值量化 (Player xG Adjuster)

**Files:**
- Create: `standalone_workspace/tools/player_xg_adjuster.py`
- Create: `standalone_workspace/tests/test_player_xg_adjuster.py`

- [ ] **Step 1: Write the failing test**

```python
# standalone_workspace/tests/test_player_xg_adjuster.py
import pytest
from tools.player_xg_adjuster import PlayerXgAdjuster

def test_adjust_xg_for_key_player_injury():
    adjuster = PlayerXgAdjuster()
    
    # 模拟德布劳内伤停，战术权重极高
    base_xg = 2.0
    injuries = [{"name": "Kevin De Bruyne", "role": "playmaker", "importance": 0.9}]
    
    adjusted_xg = adjuster.calculate_adjusted_xg(base_xg, injuries)
    
    # 预期 xG 会因为核心球员伤停而下调约 10-15%
    assert adjusted_xg < base_xg
    assert adjusted_xg > 1.5
    assert round(adjusted_xg, 2) == 1.73 # 假设公式为 base * (1 - importance * 0.15)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest standalone_workspace/tests/test_player_xg_adjuster.py -v`
Expected: FAIL with "ModuleNotFoundError" or "ImportError"

- [ ] **Step 3: Write minimal implementation**

```python
# standalone_workspace/tools/player_xg_adjuster.py
from typing import List, Dict

class PlayerXgAdjuster:
    """
    量化核心球员伤停对球队整体预期进球 (xG) 的微观衰减。
    """
    def __init__(self):
        # 定义不同角色的基础衰减系数上限
        self.role_impact_caps = {
            "striker": 0.20,      # 主力前锋伤停最多影响 20% 进球
            "playmaker": 0.15,    # 核心前腰最多影响 15% 进球
            "winger": 0.10,       # 边锋最多影响 10%
            "defender": -0.15,    # 后卫伤停主要增加失球(此处暂作为对方xG加成，本类聚焦本队xG衰减，故这里用负值表示防守端影响)
            "goalkeeper": -0.20
        }

    def calculate_adjusted_xg(self, base_xg: float, injuries: List[Dict[str, Any]]) -> float:
        """
        计算衰减后的 xG。
        injuries 格式: [{"name": "KDB", "role": "playmaker", "importance": 0.9}]
        """
        total_decay_penalty = 0.0
        
        for player in injuries:
            role = player.get("role", "striker")
            importance = player.get("importance", 0.5) # 0.0 到 1.0，1.0为绝对核心
            
            cap = self.role_impact_caps.get(role, 0.05)
            if cap > 0: # 只计算对进球有直接正面贡献的角色的衰减
                penalty = cap * importance
                total_decay_penalty += penalty
                
        # 限制总衰减不超过 35%
        total_decay_penalty = min(total_decay_penalty, 0.35)
        
        adjusted_xg = base_xg * (1.0 - total_decay_penalty)
        return round(max(0.1, adjusted_xg), 2)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest standalone_workspace/tests/test_player_xg_adjuster.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add standalone_workspace/tests/test_player_xg_adjuster.py standalone_workspace/tools/player_xg_adjuster.py
git commit -m "feat: implement PlayerXgAdjuster for micro-valuation of injuries"
```

### Task 2: 蒙特卡洛时间轴剧本模拟 (Monte Carlo Simulator)

**Files:**
- Create: `standalone_workspace/tools/monte_carlo_simulator.py`
- Create: `standalone_workspace/tests/test_monte_carlo.py`

- [ ] **Step 1: Write the failing test**

```python
# standalone_workspace/tests/test_monte_carlo.py
import pytest
from tools.monte_carlo_simulator import TimeSliceMonteCarlo

def test_monte_carlo_simulation():
    simulator = TimeSliceMonteCarlo()
    
    # 主队 xG = 2.0, 客队 xG = 1.0
    result = simulator.simulate_match(home_xg=2.0, away_xg=1.0, simulations=1000)
    
    assert "home_win_prob" in result
    assert "draw_prob" in result
    assert "away_win_prob" in result
    assert "half_full_time" in result
    
    # 主队胜率应该大于客队
    assert result["home_win_prob"] > result["away_win_prob"]
    # 胜胜 (Home-Home) 的概率应该被计算出来
    assert "HH" in result["half_full_time"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest standalone_workspace/tests/test_monte_carlo.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Write minimal implementation**

```python
# standalone_workspace/tools/monte_carlo_simulator.py
import numpy as np
from typing import Dict, Any

class TimeSliceMonteCarlo:
    """
    将 90 分钟切片，进行蒙特卡洛微观模拟，彻底颠覆静态双泊松，精准预测半全场。
    """
    def __init__(self, time_slices: int = 90):
        self.time_slices = time_slices

    def simulate_match(self, home_xg: float, away_xg: float, simulations: int = 10000) -> Dict[str, Any]:
        # 每个时间片进球概率
        home_prob_per_slice = home_xg / self.time_slices
        away_prob_per_slice = away_xg / self.time_slices
        
        home_wins = 0
        draws = 0
        away_wins = 0
        
        # 统计半全场 (Half-Time / Full-Time)
        # H: Home, D: Draw, A: Away
        ht_ft_counts = {"HH": 0, "HD": 0, "HA": 0, "DH": 0, "DD": 0, "DA": 0, "AH": 0, "AD": 0, "AA": 0}
        
        # 批量模拟矩阵运算以提高速度
        home_goals_matrix = np.random.binomial(1, home_prob_per_slice, (simulations, self.time_slices))
        away_goals_matrix = np.random.binomial(1, away_prob_per_slice, (simulations, self.time_slices))
        
        # 半场进球汇总 (前 45 分钟)
        ht_home = np.sum(home_goals_matrix[:, :45], axis=1)
        ht_away = np.sum(away_goals_matrix[:, :45], axis=1)
        
        # 全场进球汇总
        ft_home = np.sum(home_goals_matrix, axis=1)
        ft_away = np.sum(away_goals_matrix, axis=1)
        
        for i in range(simulations):
            ht_h, ht_a = ht_home[i], ht_away[i]
            ft_h, ft_a = ft_home[i], ft_away[i]
            
            # 全场赛果
            if ft_h > ft_a:
                home_wins += 1
                ft_res = "H"
            elif ft_h == ft_a:
                draws += 1
                ft_res = "D"
            else:
                away_wins += 1
                ft_res = "A"
                
            # 半场赛果
            if ht_h > ht_a:
                ht_res = "H"
            elif ht_h == ht_a:
                ht_res = "D"
            else:
                ht_res = "A"
                
            ht_ft_counts[f"{ht_res}{ft_res}"] += 1
            
        return {
            "home_win_prob": round(home_wins / simulations, 4),
            "draw_prob": round(draws / simulations, 4),
            "away_win_prob": round(away_wins / simulations, 4),
            "half_full_time": {k: round(v / simulations, 4) for k, v in ht_ft_counts.items()}
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest standalone_workspace/tests/test_monte_carlo.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add standalone_workspace/tests/test_monte_carlo.py standalone_workspace/tools/monte_carlo_simulator.py
git commit -m "feat: implement Monte Carlo time-slice simulator for half-full time prediction"
```

### Task 3: 聪明资金异常监控 (Smart Money Tracker)

**Files:**
- Create: `standalone_workspace/tools/smart_money_tracker.py`
- Create: `standalone_workspace/tests/test_smart_money.py`

- [ ] **Step 1: Write the failing test**

```python
# standalone_workspace/tests/test_smart_money.py
import pytest
from tools.smart_money_tracker import SmartMoneyTracker

def test_detect_anomaly():
    tracker = SmartMoneyTracker()
    
    # 模拟初赔到即时赔的剧烈震荡 (客胜从 6.0 暴跌至 3.5)
    odds_history = [
        {"timestamp": "10:00", "home": 1.5, "draw": 4.0, "away": 6.0},
        {"timestamp": "11:00", "home": 1.8, "draw": 3.8, "away": 4.5},
        {"timestamp": "12:00", "home": 2.1, "draw": 3.5, "away": 3.5}
    ]
    
    alert = tracker.detect_anomaly(odds_history)
    
    assert alert["is_anomaly"] is True
    assert alert["trigger_side"] == "away"
    assert "暴跌" in alert["reason"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest standalone_workspace/tests/test_smart_money.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Write minimal implementation**

```python
# standalone_workspace/tools/smart_money_tracker.py
from typing import List, Dict, Any

class SmartMoneyTracker:
    """
    监控赔率时间序列的加速度，发现“断崖式”剧烈震荡拉响风控警报。
    """
    def __init__(self, drop_threshold: float = 0.25):
        # 赔率跌幅超过 25% 视为异常资金介入
        self.drop_threshold = drop_threshold

    def detect_anomaly(self, odds_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        if len(odds_history) < 2:
            return {"is_anomaly": False, "reason": "数据不足"}
            
        initial = odds_history[0]
        latest = odds_history[-1]
        
        home_drop = (initial["home"] - latest["home"]) / initial["home"]
        away_drop = (initial["away"] - latest["away"]) / initial["away"]
        draw_drop = (initial["draw"] - latest["draw"]) / initial["draw"]
        
        if home_drop > self.drop_threshold:
            return {"is_anomaly": True, "trigger_side": "home", "reason": f"主胜赔率暴跌 {home_drop*100:.1f}%，疑似聪明资金砸盘主队"}
            
        if away_drop > self.drop_threshold:
            return {"is_anomaly": True, "trigger_side": "away", "reason": f"客胜赔率暴跌 {away_drop*100:.1f}%，疑似聪明资金砸盘客队"}
            
        if draw_drop > self.drop_threshold:
            return {"is_anomaly": True, "trigger_side": "draw", "reason": f"平局赔率暴跌 {draw_drop*100:.1f}%，疑似默契球防范"}
            
        return {"is_anomaly": False, "reason": "赔率波动正常"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest standalone_workspace/tests/test_smart_money.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add standalone_workspace/tests/test_smart_money.py standalone_workspace/tools/smart_money_tracker.py
git commit -m "feat: implement SmartMoneyTracker for odds anomaly detection"
```

### Task 4: 非结构化因素建模 (Environment Analyzer)

**Files:**
- Create: `standalone_workspace/tools/environment_analyzer.py`
- Create: `standalone_workspace/tests/test_environment.py`

- [ ] **Step 1: Write the failing test**

```python
# standalone_workspace/tests/test_environment.py
import pytest
from tools.environment_analyzer import EnvironmentAnalyzer

def test_environment_impact():
    analyzer = EnvironmentAnalyzer()
    
    base_home_xg = 1.5
    base_away_xg = 1.0
    
    # 模拟大雨天气，通常会导致总进球减少
    weather_data = {"condition": "heavy_rain", "temperature": 5}
    referee_data = {"cards_per_game": 5.5, "strictness": "high"}
    
    adj_home_xg, adj_away_xg = analyzer.calculate_impact(base_home_xg, base_away_xg, weather_data, referee_data)
    
    # 双方 xG 均应受大雨影响下降
    assert adj_home_xg < base_home_xg
    assert adj_away_xg < base_away_xg
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest standalone_workspace/tests/test_environment.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Write minimal implementation**

```python
# standalone_workspace/tools/environment_analyzer.py
from typing import Dict, Any, Tuple

class EnvironmentAnalyzer:
    """
    量化天气、场地、主裁判尺度等非结构化因素对比赛的干扰。
    """
    def __init__(self):
        self.weather_impacts = {
            "heavy_rain": -0.15, # 大雨导致双方进攻效率下降 15%
            "snow": -0.20,       # 积雪导致下降 20%
            "extreme_heat": -0.10,
            "clear": 0.0
        }

    def calculate_impact(self, home_xg: float, away_xg: float, weather: Dict[str, Any], referee: Dict[str, Any]) -> Tuple[float, float]:
        condition = weather.get("condition", "clear")
        weather_modifier = self.weather_impacts.get(condition, 0.0)
        
        # 裁判严格度：掏牌多通常破坏比赛流畅性，微降 xG；但点球判罚严可能增加特定队 xG。此处简化为整体流畅性衰减。
        referee_modifier = 0.0
        if referee.get("strictness") == "high":
            referee_modifier = -0.05
            
        total_modifier = weather_modifier + referee_modifier
        
        # 限制最大干扰幅度
        total_modifier = max(-0.30, min(0.30, total_modifier))
        
        adj_home_xg = home_xg * (1 + total_modifier)
        adj_away_xg = away_xg * (1 + total_modifier)
        
        return round(max(0.1, adj_home_xg), 2), round(max(0.1, adj_away_xg), 2)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest standalone_workspace/tests/test_environment.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add standalone_workspace/tests/test_environment.py standalone_workspace/tools/environment_analyzer.py
git commit -m "feat: implement EnvironmentAnalyzer for unstructured weather/referee impact"
```