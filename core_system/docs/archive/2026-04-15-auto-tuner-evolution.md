# 自进化反思引擎 (Auto-Tuner & Reflection Engine) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现一个数字生命的自进化引擎（AutoTuner）。它将每日读取历史投注记录（Ledger）的真实赛果，使用 LLM 对比预测与现实的偏差进行深度反思，并自主修改底层数学模型的超参数 (`hyperparams.json`)，从而完成“经验沉淀 -> 基因重写”的 AI 原生闭环。该引擎需在 `standalone_workspace` 与 `openclaw_workspace` 中同步实现。

**Architecture:**
- **数据源**：`BettingLedger` 提供过去的预测与赛果。
- **大脑 (Brain)**：`AutoTunerAgent` 使用大模型读取对账数据，反思模型误差（如天气权重、聪明资金阈值是否需要调整）。
- **基因修改 (Gene Rewriting)**：将反思后得出的新参数写入 `configs/hyperparams.json`。
- **多空间同步**：在独立版和 OpenClaw 版中同时部署此 Agent 和配置。

**Tech Stack:** Python 3.10+, OpenAI API, JSON, SQLite

---

### Task 1: 建立超参数基因库 (Hyperparameters Config)

**Files:**
- Create: `standalone_workspace/configs/hyperparams.json`
- Create: `openclaw_workspace/runtime/football_analyzer/configs/hyperparams.json`

- [x] **Step 1: 创建独立的 `hyperparams.json`**

我们需要为底层的硬核数学模型设定可被 AI 动态修改的超参数。

```json
{
  "version": 1,
  "last_updated": "2026-04-15",
  "player_xg_adjuster": {
    "max_decay_cap": 0.35,
    "role_multipliers": {
      "striker": 1.0,
      "playmaker": 1.0
    }
  },
  "smart_money_tracker": {
    "drop_threshold": 0.25
  },
  "environment_analyzer": {
    "weather_impact_multiplier": 1.0,
    "referee_strictness_penalty": -0.05
  },
  "poisson_engine": {
    "home_advantage_bonus": 1.15
  }
}
```

将该文件写入 `standalone_workspace/configs/hyperparams.json` 和 `openclaw_workspace/runtime/football_analyzer/configs/hyperparams.json` (如果目录不存在则创建)。

- [ ] **Step 2: Commit**

```bash
git add standalone_workspace/configs/ openclaw_workspace/runtime/football_analyzer/configs/
git commit -m "feat: initialize dynamic hyperparams config for auto-tuning"
```

### Task 2: 编写自进化反思引擎 (AutoTunerAgent)

**Files:**
- Create: `standalone_workspace/agents/auto_tuner_agent.py`
- Copy to: `openclaw_workspace/runtime/football_analyzer/agents/auto_tuner_agent.py`

- [ ] **Step 1: 编写核心反射逻辑**

```python
import os
import json
import sqlite3
from typing import Dict, Any, List
from openai import AsyncOpenAI
from tools.paths import data_dir, project_root

class AutoTunerAgent:
    """
    数字生命自进化引擎。
    每日复盘历史预测与真实赛果的偏差，反思并重写底层数学超参数。
    """
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY", "dummy"),
            base_url=os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        )
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
        # 兼容两个工作区的路径
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.hyperparams_path = os.path.join(base_dir, "configs", "hyperparams.json")
        self.ledger_db = os.path.join(data_dir(), "ledger.db")
        
    def _fetch_recent_resolved_bets(self, limit: int = 50) -> List[Dict]:
        """从账本获取最近已结算的比赛记录用于反思"""
        if not os.path.exists(self.ledger_db):
            return []
            
        conn = sqlite3.connect(self.ledger_db)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # 获取状态为 RESOLVED (已开奖) 的记录
        c.execute('''SELECT match_id, lottery_type, selection, odds, result, pnl 
                     FROM bets WHERE status="RESOLVED" ORDER BY id DESC LIMIT ?''', (limit,))
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]
        
    def _load_current_hyperparams(self) -> Dict:
        if os.path.exists(self.hyperparams_path):
            with open(self.hyperparams_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_new_hyperparams(self, params: Dict):
        os.makedirs(os.path.dirname(self.hyperparams_path), exist_ok=True)
        with open(self.hyperparams_path, "w", encoding="utf-8") as f:
            json.dump(params, f, ensure_ascii=False, indent=2)
            
    async def run_daily_reflection(self) -> Dict[str, Any]:
        print("\n[🧬 Auto-Tuner] 启动自进化反思引擎...")
        
        recent_bets = self._fetch_recent_resolved_bets(20)
        if not recent_bets:
            return {"status": "skipped", "message": "近期无已结算的实盘记录可供反思"}
            
        current_params = self._load_current_hyperparams()
        
        # 计算粗略胜率
        wins = sum(1 for b in recent_bets if b.get('pnl', 0) > 0)
        win_rate = wins / len(recent_bets) if recent_bets else 0
        
        print(f"    [复盘] 获取到 {len(recent_bets)} 场近期完赛记录，胜率: {win_rate:.1%}")
        
        prompt = f"""
你是一个顶级的足彩量化系统架构师。系统最近的胜率是 {win_rate:.1%}。
以下是系统近期的部分预测和赛果记录（包含预测方向、赔率、盈亏）：
{json.dumps(recent_bets[:10], ensure_ascii=False)}

系统当前的底层数学超参数如下：
{json.dumps(current_params, ensure_ascii=False)}

请反思近期预测失败的原因，并微调超参数。
例如：如果经常在客胜高赔率上亏损，说明对聪明资金反应太慢，可以把 smart_money_tracker.drop_threshold 从 0.25 调低到 0.20。
如果经常因为主队爆冷输球，可能高估了主场优势，把 home_advantage_bonus 调低。

请严格返回一个 JSON，格式必须为：
{{
    "reflection": "你反思的日记（200字以内），说明哪里做错了，为什么要修改参数",
    "updated_hyperparams": {{ ...完整的、修改后的超参数JSON结构... }}
}}
"""
        try:
            print("    [思考] 正在通过大模型进行深度反思...")
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            
            reflection = result.get("reflection", "无反思")
            new_params = result.get("updated_hyperparams", current_params)
            
            # 基因重写
            self._save_new_hyperparams(new_params)
            
            print(f"    [觉醒] 反思日记: {reflection}")
            print("    [进化] 底层基因 (hyperparams.json) 已重写！")
            
            return {"status": "success", "reflection": reflection, "new_params": new_params}
            
        except Exception as e:
            print(f"    [错误] 反思引擎崩溃: {e}")
            return {"status": "error", "message": str(e)}
```

- [ ] **Step 2: 将文件同步到 OpenClaw 目录**

复制 `standalone_workspace/agents/auto_tuner_agent.py` 到 `openclaw_workspace/runtime/football_analyzer/agents/auto_tuner_agent.py`，因为它们的路径逻辑 `tools.paths` 是完全兼容的。如果原先有 `auto_tuner.py` 废案，直接覆盖。

- [ ] **Step 3: Commit**

```bash
git add standalone_workspace/agents/auto_tuner_agent.py openclaw_workspace/runtime/football_analyzer/agents/auto_tuner_agent.py
git commit -m "feat: implement AutoTunerAgent for self-evolution and gene rewriting in both workspaces"
```

### Task 3: 底层数学模型接入动态基因 (Read Config)

**Files:**
- Modify: `standalone_workspace/tools/smart_money_tracker.py` (及 OpenClaw 同名文件)

- [x] **Step 1: 修改底层模型，使其运行时读取 `hyperparams.json`**

以 `SmartMoneyTracker` 为例，不要硬编码 `drop_threshold = 0.25`，而是从文件中读取。

```python
import os
import json

class SmartMoneyTracker:
    def __init__(self, default_drop_threshold: float = 0.25):
        self.hyperparams_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs", "hyperparams.json")
        self.drop_threshold = self._load_dynamic_threshold(default_drop_threshold)

    def _load_dynamic_threshold(self, default_val):
        try:
            if os.path.exists(self.hyperparams_path):
                with open(self.hyperparams_path, "r", encoding="utf-8") as f:
                    params = json.load(f)
                    return params.get("smart_money_tracker", {}).get("drop_threshold", default_val)
        except Exception:
            pass
        return default_val
```

*注意：同理可推广至 `player_xg_adjuster` 和 `environment_analyzer` 等模型，在后续开发中逐步接入。*

- [x] **Step 2: 同步修改到 OpenClaw 目录**

将修改后的 `smart_money_tracker.py` 覆盖到 `openclaw_workspace/runtime/football_analyzer/tools/smart_money_tracker.py`。

- [ ] **Step 3: Commit**

```bash
git add standalone_workspace/tools/smart_money_tracker.py openclaw_workspace/runtime/football_analyzer/tools/smart_money_tracker.py
git commit -m "feat: wire underlying math models to dynamic hyperparams config"
```