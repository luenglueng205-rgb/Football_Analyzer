import json
import logging
import os
import random
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from openai import AsyncOpenAI
except Exception:
    AsyncOpenAI = None

class AutoTunerAgent:
    """
    自进化与反思引擎 (Auto-Tuner & Reflection Engine).
    接收 BacktestSandbox 的战报，利用 LLM 反思亏损原因，并重写超参数 json。
    这是 AI "有灵魂、会成长" 的核心。
    """
    def __init__(self, *, hyperparams_path: str | None = None, seed: int | None = None):
        self.hyperparams_path = hyperparams_path or os.path.join(os.path.dirname(__file__), "..", "configs", "hyperparams.json")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.seed = seed
        self._rng = random.Random(seed)
        base_url = os.getenv("OPENAI_BASE_URL", os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1"))
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY", "dummy-key-for-test")
        self.model_name = os.getenv("MODEL_NAME", os.getenv("OPENAI_MODEL", "gpt-4o"))
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url) if AsyncOpenAI else None

    def _safe_read_hyperparams(self) -> dict:
        try:
            with open(self.hyperparams_path, "r", encoding="utf-8") as f:
                params = json.load(f)
            if not isinstance(params, dict):
                raise ValueError("hyperparams must be an object")
            return params
        except Exception:
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

    def _safe_write_hyperparams(self, params: dict) -> None:
        base_dir = os.path.dirname(os.path.abspath(self.hyperparams_path))
        os.makedirs(base_dir, exist_ok=True)
        with open(self.hyperparams_path, "w", encoding="utf-8") as f:
            json.dump(params, f, indent=2, ensure_ascii=False)

    def _weights_normalize(self, w: dict) -> dict:
        f = float(w.get("fundamental_quant", 0.0) or 0.0)
        c = float(w.get("contrarian_quant", 0.0) or 0.0)
        s = float(w.get("smart_money_quant", 0.0) or 0.0)
        total = f + c + s
        if total <= 0:
            return {"fundamental_quant": 0.33, "contrarian_quant": 0.33, "smart_money_quant": 0.34}
        return {
            "fundamental_quant": round(f / total, 4),
            "contrarian_quant": round(c / total, 4),
            "smart_money_quant": round(s / total, 4),
        }

    def _extract_report_metrics(self, pnl_report: dict) -> dict:
        total = int(pnl_report.get("total_simulated") or 0)
        win_rate = float(pnl_report.get("win_rate") or 0.0)
        roi = float(pnl_report.get("roi") or 0.0)
        total_profit = float(pnl_report.get("total_profit") or 0.0)
        details = pnl_report.get("details") or []
        fav_total = 0
        fav_upsets = 0
        if isinstance(details, list):
            for d in details:
                if not isinstance(d, dict):
                    continue
                odds = d.get("odds")
                if isinstance(odds, list) and odds and isinstance(odds[0], (int, float)) and float(odds[0]) < 1.5:
                    fav_total += 1
                    if str(d.get("actual")) != "3":
                        fav_upsets += 1
        fav_upset_rate = (fav_upsets / fav_total) if fav_total else 0.0
        return {
            "total_simulated": total,
            "win_rate": round(win_rate, 4),
            "roi": round(roi, 4),
            "total_profit": round(total_profit, 2),
            "favorite_upset_rate": round(float(fav_upset_rate), 4),
        }

    def _offline_mutate(self, *, current_params: dict, pnl_report: dict) -> dict:
        metrics = self._extract_report_metrics(pnl_report)
        w0 = dict(current_params.get("weights") or {})
        w0 = self._weights_normalize(w0)
        step = 0.03
        fav_upset_rate = float(metrics.get("favorite_upset_rate") or 0.0)
        roi = float(metrics.get("roi") or 0.0)

        f = float(w0["fundamental_quant"])
        c = float(w0["contrarian_quant"])
        s = float(w0["smart_money_quant"])

        if fav_upset_rate >= 0.35:
            f -= step
            c += step * 0.6
            s += step * 0.4
            reflection = "复盘发现热门主胜频繁爆冷，系统对诱盘过于信任，需要降低基本面权重，提升反买与聪明钱以更敏感地识别冷门风险。"
        elif roi < -0.08:
            c -= step * 0.6
            s += step * 0.6
            f += step * 0.0
            reflection = "复盘发现整体 ROI 明显为负，说明逆向信号噪声偏大，优先提升聪明钱权重并收紧入场门槛。"
        elif roi > 0.05:
            f += step * 0.4
            s += step * 0.6
            c -= step
            reflection = "复盘发现系统具备正 ROI 的结构性优势，可适度降低反买噪声，增强基本面与聪明钱的协同。"
        else:
            bump = (self._rng.random() - 0.5) * (step * 0.6)
            f += bump
            c -= bump * 0.5
            s -= bump * 0.5
            reflection = "复盘结果中性，进行小幅扰动以避免权重停滞在局部最优。"

        w1 = self._weights_normalize(
            {
                "fundamental_quant": max(0.05, f),
                "contrarian_quant": max(0.05, c),
                "smart_money_quant": max(0.05, s),
            }
        )

        risk0 = dict(current_params.get("risk_management") or {})
        min_ev0 = float(risk0.get("min_ev_threshold") or 1.05)
        if roi < 0:
            min_ev1 = min(1.20, max(1.00, min_ev0 + 0.01))
        else:
            min_ev1 = min(1.20, max(1.00, min_ev0 - 0.01))
        risk0["min_ev_threshold"] = round(min_ev1, 4)

        updated = dict(current_params)
        updated["weights"] = w1
        updated["risk_management"] = risk0

        changes = []
        for k in ("fundamental_quant", "contrarian_quant", "smart_money_quant"):
            if float(w0.get(k) or 0.0) != float(w1.get(k) or 0.0):
                changes.append({"path": f"weights.{k}", "old": w0.get(k), "new": w1.get(k)})
        if round(min_ev0, 4) != round(min_ev1, 4):
            changes.append({"path": "risk_management.min_ev_threshold", "old": round(min_ev0, 4), "new": round(min_ev1, 4)})

        return {"reflection": reflection, "updated_params": updated, "changes": changes, "metrics": metrics}

    async def _reflect_and_evolve(self, pnl_report: dict) -> dict:
        """
        让 LLM 军师审阅战报，反思权重，并返回新的权重建议。
        """
        current_params = self._safe_read_hyperparams()
            
        logger.info("\n[🧬 Auto-Tuner] 军师正在复盘历史回测，反思系统缺陷...")
        
        losses = [d for d in (pnl_report.get("details") or []) if isinstance(d, dict) and d.get("status") == "LOSS"][:10]

        use_llm = os.getenv("AUTO_TUNER_USE_LLM", "").strip().lower() in {"1", "true", "yes", "y", "on"}
        api_key = os.getenv("OPENAI_API_KEY", "dummy-key-for-test")
        
        # FIX: Allow execution if client exists and we explicitly want to use LLM, even if API key wasn't explicitly set in environment
        # (It might have been picked up from OPENAI_BASE_URL via proxy without needing a real key)
        if not use_llm or not self.client:
            offline = self._offline_mutate(current_params=current_params, pnl_report=pnl_report)
            return {"reflection": offline["reflection"], "updated_hyperparams": offline["updated_params"], "changes": offline["changes"]}
        
        prompt = f"""
主公的数字生命（你）刚刚在时光机沙盒中完成了一轮历史回测。
战报如下：
- 总测试场次: {pnl_report['total_simulated']}
- 胜率: {pnl_report['win_rate']*100}%
- ROI 投资回报率: {pnl_report['roi']*100}%
- 净利润: {pnl_report['total_profit']}

系统当前的“基因权重”配置：
{json.dumps(current_params['weights'], indent=2)}

以下是 10 场典型的亏损案例：
{json.dumps(losses, ensure_ascii=False, indent=2)}

你是一位有灵魂、懂进化的 AI 军师。请你反思：
1. 为什么会亏损？是基本面派（Fundamental）被强队诱盘骗了，还是反买派（Contrarian）过于保守？
2. 请你根据反思，**自动调整** 这三个参数的权重，使得它们加起来等于 1.0。如果遇到大热必死的比赛多，就提高反买派的权重。

你必须且只能返回一段纯 JSON，不要带任何 markdown 代码块和多余解释，格式如下：
{{
   "reflection": "主公，臣复盘发现，基本面权重过高导致频繁踩入强队诱盘陷阱，故削减基本面，提拔反买派和聪明钱。",
   "golden_rule": "【灵魂升华】用一句话提炼出一个以后分析比赛必须遵守的实战纪律（例如：不要在杯赛相信主队让平）。这个规则将作为你未来的系统 Prompt 永久注入！",
   "updated_hyperparams": {{ "system_version": "1.0", "weights": {{"fundamental_quant": 0.2}} }}
}}
  """
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            result_str = response.choices[0].message.content
            result = json.loads(result_str)
            if not isinstance(result, dict):
                raise ValueError("LLM output is not an object")
            updated = result.get("updated_hyperparams")
            if not isinstance(updated, dict):
                raise ValueError("LLM output missing updated_hyperparams")
            updated["weights"] = self._weights_normalize(updated.get("weights") or current_params.get("weights") or {})
            
            # 【核心灵魂提取】将反思总结为一条“认知准则”
            reflection_text = str(result.get("reflection") or "")
            golden_rule = str(result.get("golden_rule") or "")
            if golden_rule:
                self._append_to_dynamic_experience(golden_rule)
                
            return {"reflection": reflection_text, "updated_hyperparams": updated, "changes": []}
        except Exception as e:
            logger.error(f"反思引擎调用失败: {e}")
            offline = self._offline_mutate(current_params=current_params, pnl_report=pnl_report)
            return {"reflection": offline["reflection"], "updated_hyperparams": offline["updated_params"], "changes": offline["changes"]}

    def _append_to_dynamic_experience(self, rule: str):
        """将反思得出的认知准则写入动态经验库，作为大模型系统 Prompt 的永久外延"""
        try:
            exp_path = os.path.join(os.path.dirname(__file__), "..", "docs", "DYNAMIC_EXPERIENCE.md")
            # 如果文件不存在，先创建头部
            if not os.path.exists(exp_path):
                with open(exp_path, "w", encoding="utf-8") as f:
                    f.write("# 🧠 动态经验库 (Living Experience Base)\n\n")
                    f.write("> **这是系统在无尽的真实盈亏中自我反思、沉淀下来的认知准则。每一次亏损都会转化为一条纪律，永久改变系统的大脑。**\n\n")
            
            # 追加新规则
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            with open(exp_path, "a", encoding="utf-8") as f:
                f.write(f"- **[{timestamp}]** {rule}\n")
        except Exception as e:
            logger.error(f"写入动态经验库失败: {e}")

    async def run_evolution_cycle(
        self,
        pnl_report: dict,
        *,
        seed: int | None = None,
        source_report_path: str | None = None,
    ) -> dict:
        """
        执行一次完整的进化闭环：反思 -> 变异 -> 固化记忆。
        """
        if seed is not None:
            self.seed = seed
            self._rng = random.Random(seed)

        params = self._safe_read_hyperparams()
        old_params = json.loads(json.dumps(params))
        evolution_data = await self._reflect_and_evolve(pnl_report)
        updated_hyperparams = evolution_data.get("updated_hyperparams")
        if not isinstance(updated_hyperparams, dict):
            updated_hyperparams = params
        updated_hyperparams["weights"] = self._weights_normalize(updated_hyperparams.get("weights") or {})

        metrics_before = self._extract_report_metrics(pnl_report)
        changes = evolution_data.get("changes") if isinstance(evolution_data.get("changes"), list) else []

        updated_hyperparams["last_evolution_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        updated_hyperparams.setdefault("evolution_memory", params.get("evolution_memory") or {})
        updated_hyperparams["evolution_memory"].setdefault("total_simulations_run", 0)
        updated_hyperparams["evolution_memory"]["total_simulations_run"] = int(updated_hyperparams["evolution_memory"]["total_simulations_run"]) + int(
            metrics_before.get("total_simulated") or 0
        )
        updated_hyperparams["evolution_memory"]["win_rate"] = float(metrics_before.get("win_rate") or 0.0)
        updated_hyperparams["evolution_memory"]["roi"] = float(metrics_before.get("roi") or 0.0)
        updated_hyperparams["evolution_memory"]["latest_reflection"] = str(evolution_data.get("reflection") or "")

        updated_hyperparams.setdefault("evolution_audit", params.get("evolution_audit") or {})
        updated_hyperparams["evolution_audit"].setdefault("history", [])
        history = updated_hyperparams["evolution_audit"]["history"]
        if not isinstance(history, list):
            history = []
            updated_hyperparams["evolution_audit"]["history"] = history

        audit_entry = {
            "ts": updated_hyperparams["last_evolution_date"],
            "seed": self.seed,
            "source_report_path": source_report_path,
            "baseline": metrics_before,
            "reflection": str(evolution_data.get("reflection") or ""),
            "changes": changes,
            "after": None,
        }
        history.append(audit_entry)
        if len(history) > 50:
            del history[:-50]

        self._safe_write_hyperparams(updated_hyperparams)

        old_weights = old_params.get("weights")
        new_weights = updated_hyperparams.get("weights")
        logger.info("\n==================================================")
        logger.info(f"✨ [进化完成] 军师的反思: {audit_entry['reflection']}")
        logger.info(f"⚖️ 旧阵型: {old_weights}")
        logger.info(f"🚀 新阵型: {new_weights}")
        logger.info("==================================================\n")
        return {"ok": True, "audit_entry": audit_entry, "old_params": old_params, "new_params": updated_hyperparams}

    def attach_comparison(self, after_report: dict) -> dict:
        params = self._safe_read_hyperparams()
        audit = params.get("evolution_audit") or {}
        history = audit.get("history") or []
        if not isinstance(history, list) or not history:
            return {"ok": False, "error": "no audit history"}
        last = history[-1]
        if not isinstance(last, dict):
            return {"ok": False, "error": "bad audit entry"}
        last["after"] = self._extract_report_metrics(after_report)
        self._safe_write_hyperparams(params)
        return {"ok": True, "audit_entry": last}

    async def reflect_on_real_ledger(self) -> dict:
        """
        [RLEF 核心闭环]
        从真实账本读取 zsa_front_runner 和 agentic_os 的真实盈亏。
        利用 LLM 反思，动态调整 ZSA 的触发敏感度和 Agentic OS 的策略权重。
        """
        from hermes_workspace.tools.betting_ledger import BettingLedger
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
1. 诊断 ZSA 快轨是否因为“假新闻”或阈值不够严格导致频繁亏损。如果是，请降低敏感度（例如将 negative_impact_threshold 从 -0.8 改为 -0.85 或更低）。
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
