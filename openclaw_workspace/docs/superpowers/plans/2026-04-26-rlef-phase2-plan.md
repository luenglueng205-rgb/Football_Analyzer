# RLEF Phase 2: Environment Feedback Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Reinforcement Learning from Environment Feedback (RLEF) closed loop. The AutoTunerAgent will analyze real PnL data from the SQLite `BettingLedger` (distinguishing between ZSA's fast track and Agentic OS's slow track) and dynamically adjust ZSA trigger thresholds and Agentic OS hyperparameters.

**Architecture:** 
1. `BettingLedger` gets new query methods for real PnL extraction.
2. `AutoTunerAgent` gets a new `reflect_on_real_ledger` method to evaluate ZSA vs Agentic OS performance.
3. `hyperparams.json` is expanded to include `zsa_thresholds`.
4. `SocialNewsListener` dynamically reads `zsa_thresholds` instead of using hardcoded `0.8` / `0.5` limits.

**Tech Stack:** Python, SQLite, OpenAI (LLM), JSON.

---

### Task 1: Enhance `BettingLedger` for RLEF Data Extraction

**Files:**
- Modify: `core_system/tools/betting_ledger.py`

- [ ] **Step 1: Add `get_recent_resolved_bets` method**

Add this method to fetch recent bets for LLM analysis.

```python
    def get_recent_resolved_bets(self, agent_id: str, limit: int = 10, only_losses: bool = False) -> list:
        """为 RLEF 提取最近已结算的订单"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            query = "SELECT * FROM bets WHERE agent_id=? AND status='RESOLVED'"
            if only_losses:
                query += " AND pnl < 0"
            query += " ORDER BY timestamp DESC LIMIT ?"
            
            c.execute(query, (agent_id, limit))
            rows = c.fetchall()
            return [dict(r) for r in rows]
```

- [ ] **Step 2: Add `get_agent_metrics` method**

Add this method to compute ROI and Win Rate directly from the DB.

```python
    def get_agent_metrics(self, agent_id: str) -> dict:
        """获取指定 Agent 的真实历史盈亏指标"""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*), SUM(stake), SUM(pnl) FROM bets WHERE agent_id=? AND status='RESOLVED'", (agent_id,))
            row = c.fetchone()
            total_resolved = row[0] or 0
            total_stake = row[1] or 0.0
            total_pnl = row[2] or 0.0
            
            c.execute("SELECT COUNT(*) FROM bets WHERE agent_id=? AND status='RESOLVED' AND pnl > 0", (agent_id,))
            wins = c.fetchone()[0] or 0
            
            win_rate = (wins / total_resolved) if total_resolved > 0 else 0.0
            roi = (total_pnl / total_stake) if total_stake > 0 else 0.0
            
            return {
                "total_resolved": total_resolved,
                "win_rate": round(win_rate, 4),
                "roi": round(roi, 4),
                "total_pnl": round(total_pnl, 2)
            }
```

### Task 2: Dynamize ZSA Thresholds

**Files:**
- Modify: `core_system/agents/auto_tuner_agent.py`
- Modify: `core_system/skills/news_arbitrage/social_listener.py`

- [ ] **Step 1: Update `_safe_read_hyperparams` in `AutoTunerAgent`**

Ensure `zsa_thresholds` exists in the default hyperparams. Add it to the default dictionary returned when the file is missing or broken.

```python
# In core_system/agents/auto_tuner_agent.py, update the return statement of _safe_read_hyperparams:
            return {
                "system_version": "1.0.0",
                "last_evolution_date": None,
                "weights": {"fundamental_quant": 0.33, "contrarian_quant": 0.33, "smart_money_quant": 0.34},
                "poisson_engine": {"xg_variance_penalty": 0.05, "draw_bias_adjustment": 1.05},
                "risk_management": {"min_ev_threshold": 1.05, "max_stake_percent": 0.05, "fuzzy_banker_tolerance": 0.8},
                "zsa_thresholds": {"negative_impact_threshold": -0.8, "positive_impact_threshold": 0.5},
                "evolution_memory": {"total_simulations_run": 0, "win_rate": 0.0, "roi": 0.0, "latest_reflection": ""},
                "evolution_audit": {"history": []},
            }
```

- [ ] **Step 2: Read dynamic thresholds in `SocialNewsListener`**

Update `SocialNewsListener` to read `zsa_thresholds` from `hyperparams.json`. If reading fails, fallback to defaults.

Add imports at the top of `core_system/skills/news_arbitrage/social_listener.py`:
```python
import json
from core_system.tools.paths import data_dir
```

In `__init__`, load the thresholds:
```python
        # ZSA Phase 3: 内存总线回调机制
        self._callbacks = []
        
        # RLEF: 动态加载 ZSA 触发阈值
        self._load_zsa_thresholds()

    def _load_zsa_thresholds(self):
        self.neg_threshold = -0.8
        self.pos_threshold = 0.5
        try:
            # 尝试从 hyperparams.json 读取
            hp_path = os.path.join(os.path.dirname(__file__), "..", "..", "configs", "hyperparams.json")
            if os.path.exists(hp_path):
                with open(hp_path, "r", encoding="utf-8") as f:
                    params = json.load(f)
                    zsa_t = params.get("zsa_thresholds", {})
                    if "negative_impact_threshold" in zsa_t:
                        self.neg_threshold = float(zsa_t["negative_impact_threshold"])
                    if "positive_impact_threshold" in zsa_t:
                        self.pos_threshold = float(zsa_t["positive_impact_threshold"])
        except Exception as e:
            print(f"   -> ⚠️ [ZSA] 无法加载动态阈值，使用默认值: {e}")
```

- [ ] **Step 3: Apply dynamic thresholds to the intercept logic**

In `_background_poll`, `_force_sync_fetch`, and `inject_mock_news` of `SocialNewsListener`, replace hardcoded `-0.8` and `0.5` with `self.neg_threshold` and `self.pos_threshold`.

For example, in `_background_poll`:
```python
                            # 触发内存总线截胡
                            if xg_impact <= self.neg_threshold or xg_impact >= self.pos_threshold:
                                self._fire_callbacks(team, combined, xg_impact)
```

*(Do the same for `_force_sync_fetch` and `inject_mock_news`)*

### Task 3: Implement `reflect_on_real_ledger` in `AutoTunerAgent`

**Files:**
- Modify: `core_system/agents/auto_tuner_agent.py`

- [ ] **Step 1: Write the RLEF evaluation logic**

Add `reflect_on_real_ledger` method. It queries the `BettingLedger`, passes real data to the LLM, and applies the changes.

```python
    async def reflect_on_real_ledger(self) -> dict:
        """
        [RLEF 核心闭环]
        从真实账本读取 zsa_front_runner 和 agentic_os 的真实盈亏。
        利用 LLM 反思，动态调整 ZSA 的触发敏感度和 Agentic OS 的策略权重。
        """
        from core_system.tools.betting_ledger import BettingLedger
        ledger = BettingLedger()
        
        zsa_metrics = ledger.get_agent_metrics("zsa_front_runner")
        os_metrics = ledger.get_agent_metrics("agentic_os")
        
        zsa_losses = ledger.get_recent_resolved_bets("zsa_front_runner", limit=5, only_losses=True)
        os_losses = ledger.get_recent_resolved_bets("agentic_os", limit=5, only_losses=True)
        
        current_params = self._safe_read_hyperparams()
        
        logger.info("\n[🧬 RLEF Auto-Tuner] 正在从真实账本提取环境反馈 (Environment Feedback)...")
        
        use_llm = os.getenv("AUTO_TUNER_USE_LLM", "").strip().lower() in {"1", "true", "yes", "y", "on"}
        
        if not use_llm or not self.client:
            logger.info("   -> [RLEF] LLM 未启用，跳过真实账本反思。")
            return {"status": "skipped", "reason": "LLM not enabled"}

        prompt = f"""
你是由 RLEF (环境反馈强化学习) 驱动的自进化引擎。
你目前正在监控双轨架构：ZSA（零样本快轨）与 Agentic OS（GWM慢轨）。

【环境反馈 - 真实账本数据】
ZSA 快轨表现：
- 交易数: {zsa_metrics['total_resolved']} | 胜率: {zsa_metrics['win_rate']} | ROI: {zsa_metrics['roi']}
- 最近亏损案例: {json.dumps(zsa_losses, ensure_ascii=False)}

Agentic OS 慢轨表现：
- 交易数: {os_metrics['total_resolved']} | 胜率: {os_metrics['win_rate']} | ROI: {os_metrics['roi']}
- 最近亏损案例: {json.dumps(os_losses, ensure_ascii=False)}

【当前参数状态】
ZSA 阈值 (负数越小越严格): {json.dumps(current_params.get('zsa_thresholds', {}))}
慢轨权重: {json.dumps(current_params.get('weights', {}))}

任务：
1. 诊断 ZSA 快轨是否因为“假新闻”或阈值过低导致频繁亏损。如果是，请降低敏感度（例如将 negative_impact_threshold 从 -0.8 改为 -0.85 或更低）。
2. 诊断慢轨亏损原因，并给出针对慢轨的动态纪律 (golden_rule)。
3. 返回更新后的参数。

请严格返回以下 JSON 格式：
{{
   "reflection": "综合双轨表现的分析...",
   "golden_rule": "写给慢轨的一句话实战纪律...",
   "updated_hyperparams": {{
       "weights": {{"fundamental_quant": 0.3, "contrarian_quant": 0.4, "smart_money_quant": 0.3}},
       "zsa_thresholds": {{"negative_impact_threshold": -0.85, "positive_impact_threshold": 0.55}}
   }}
}}
"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            result = json.loads(response.choices[0].message.content)
            
            updated = current_params.copy()
            new_params = result.get("updated_hyperparams", {})
            
            if "weights" in new_params:
                updated["weights"] = self._weights_normalize(new_params["weights"])
            if "zsa_thresholds" in new_params:
                updated["zsa_thresholds"] = new_params["zsa_thresholds"]
                
            self._safe_write_hyperparams(updated)
            
            golden_rule = str(result.get("golden_rule") or "")
            if golden_rule:
                self._append_to_dynamic_experience(golden_rule)
                
            logger.info(f"✨ [RLEF 进化完成] 反思: {result.get('reflection')}")
            logger.info(f"🚀 [RLEF] 新 ZSA 阈值: {updated.get('zsa_thresholds')}")
            
            return {"status": "success", "reflection": result.get("reflection"), "new_params": updated}
            
        except Exception as e:
            logger.error(f"[RLEF] LLM 反思异常: {e}")
            return {"status": "error", "error": str(e)}
```

### Task 4: Write the RLEF Integration Test

**Files:**
- Create: `test_rlef_feedback_loop.py`

- [ ] **Step 1: Write the test**

```python
import os
import asyncio
from core_system.tools.betting_ledger import BettingLedger
from core_system.agents.auto_tuner_agent import AutoTunerAgent

async def test_rlef():
    os.environ["AUTO_TUNER_USE_LLM"] = "true"
    
    # 1. Mock some DB records
    ledger = BettingLedger()
    
    # 模拟 ZSA 亏损 (因为门槛 -0.8 不够严格，被假新闻骗了)
    ledger.reset_economy("zsa_front_runner")
    res = ledger.execute_bet("zsa_front_runner", "M_001", "jingcai", "away_win", 2.0, 100.0)
    ledger.record_result(res["bet_id"], "LOSS", -100.0)
    res = ledger.execute_bet("zsa_front_runner", "M_002", "jingcai", "away_win", 2.0, 100.0)
    ledger.record_result(res["bet_id"], "LOSS", -100.0)
    
    # 模拟 Agentic OS 亏损
    ledger.reset_economy("agentic_os")
    res = ledger.execute_bet("agentic_os", "M_003", "jingcai", "home_win", 1.5, 100.0)
    ledger.record_result(res["bet_id"], "LOSS", -100.0)
    
    print("✅ 模拟真实环境账本数据注入完成...")
    
    # 2. 触发 RLEF
    tuner = AutoTunerAgent()
    print("🚀 触发 RLEF 环境反馈反思引擎...")
    result = await tuner.reflect_on_real_ledger()
    
    print("\n================ RLEF 结果 ================")
    print(f"状态: {result['status']}")
    print(f"反思: {result.get('reflection')}")
    print(f"新参数: {result.get('new_params', {}).get('zsa_thresholds')}")

if __name__ == "__main__":
    asyncio.run(test_rlef())
```

- [ ] **Step 2: Run the test**

Run: `PYTHONPATH=. python3 test_rlef_feedback_loop.py`
Expected: Output showing the LLM analyzed the losses and adjusted the `zsa_thresholds` to be stricter (e.g. `-0.85` or `-0.9`).

- [ ] **Step 3: Commit**
```bash
git add core_system/tools/betting_ledger.py core_system/agents/auto_tuner_agent.py core_system/skills/news_arbitrage/social_listener.py test_rlef_feedback_loop.py
git commit -m "feat(rlef): implement phase 2 real environment feedback loop for auto-tuning"
```
