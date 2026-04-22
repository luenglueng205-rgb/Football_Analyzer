import logging
import os
from typing import Any, Dict, Optional

try:
    from openai import AsyncOpenAI
except Exception:
    AsyncOpenAI = None  # type: ignore[assignment]

from core.domain_kernel import DomainKernel

logger = logging.getLogger(__name__)

class RouterAgent:
    """
    Mixture of Experts (MoE) Gatekeeper.
    Uses a fast, cheap model to filter out low-value matches before waking up the heavy Syndicate.
    """
    def __init__(self):
        self.model = os.getenv("OPENAI_ROUTER_MODEL", "gpt-4o-mini")
        base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        api_key = os.getenv("OPENAI_API_KEY", "dummy-key-for-test")
        self._api_key = api_key
        self._base_url = base_url
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url) if AsyncOpenAI else None

    def _rule_based_decision(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        home = str(match_data.get("home") or "Unknown")
        away = str(match_data.get("away") or "Unknown")
        odds = match_data.get("odds") or []
        league = str(match_data.get("league") or match_data.get("league_name") or match_data.get("league_code") or "")

        odds_triplet = []
        if isinstance(odds, (list, tuple)):
            odds_triplet = [float(x) for x in odds[:3] if isinstance(x, (int, float))]

        if odds_triplet and odds_triplet[0] < 1.10:
            return {"action": "IGNORE", "reason": "低赔蚊子肉（主胜<1.10），不唤醒重链路"}

        brand = {
            "real madrid",
            "barcelona",
            "man city",
            "manchester city",
            "man utd",
            "manchester united",
            "liverpool",
            "arsenal",
            "chelsea",
            "bayern",
            "bayern munich",
            "psg",
            "paris saint-germain",
            "juventus",
            "inter",
            "ac milan",
            "milan",
        }
        key_leagues = {"EPL", "PL", "LA LIGA", "SERIE A", "BUNDESLIGA", "LIGUE 1", "UCL", "UCLQ", "UEL", "UECL"}

        team_tokens = {home.strip().lower(), away.strip().lower()}
        has_brand = bool(team_tokens & brand)
        has_key_league = league.strip().upper() in key_leagues

        if odds_triplet and len(odds_triplet) == 3:
            mn = min(odds_triplet)
            mx = max(odds_triplet)
            balanced = mn >= 1.55 and mx <= 4.20
            if balanced:
                return {"action": "DEEP_DIVE", "reason": "赔率均衡（潜在价值与波动空间），进入深度链路"}

        if has_key_league or has_brand:
            return {"action": "DEEP_DIVE", "reason": "焦点队/焦点联赛，进入深度链路"}

        if odds_triplet and len(odds_triplet) == 3:
            if max(odds_triplet) >= 9.0:
                return {"action": "DEEP_DIVE", "reason": "强弱分明但冷门赔率高，可能存在诱盘或爆冷空间"}

        return {"action": "IGNORE", "reason": "信息价值不足，避免不必要的 LLM/工具调用"}

    def _offline_mode(self) -> bool:
        if os.getenv("ROUTER_OFFLINE", "").strip() in {"1", "true", "TRUE", "yes", "YES"}:
            return True
        if not self._api_key or self._api_key in {"dummy-key-for-test", "dummy_key", "your_api_key_here"}:
            return True
        return self.client is None

    async def evaluate_match_value(self, match_data: dict) -> dict:
        match_data = match_data if isinstance(match_data, dict) else {}
        home = match_data.get("home", "Unknown")
        away = match_data.get("away", "Unknown")
        odds = match_data.get("odds", [])
        
        logger.info(f"[🚪 Router] Evaluating match value for {home} vs {away}...")

        rule_based = self._rule_based_decision(match_data)
        out: Dict[str, Any] = {
            "status": "success",
            "decision": dict(rule_based),
            "action": rule_based.get("action"),
            "reason": rule_based.get("reason"),
            "signals": {"home": home, "away": away, "odds": odds},
            "confidence": 0.75 if rule_based.get("action") == "DEEP_DIVE" else 0.85,
            "data_source": "router:rule_based",
        }

        if self._offline_mode():
            return DomainKernel.attach("router", out)

        prompt = (
            "你是一个彩票比赛价值路由器（Gatekeeper）。"
            f"请快速判断是否需要进入深度分析链路：{home} vs {away}，赔率：{odds}。"
            '只允许输出 JSON：{"action":"DEEP_DIVE"|"IGNORE","reason":"..."}'
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            import json
            parsed = json.loads(response.choices[0].message.content)
            action = parsed.get("action") if isinstance(parsed, dict) else None
            reason = parsed.get("reason") if isinstance(parsed, dict) else None
            if action not in {"DEEP_DIVE", "IGNORE"}:
                action = rule_based.get("action")
                reason = f"LLM 输出不合规，回退规则：{rule_based.get('reason')}"
            out = {
                **out,
                "decision": {"action": action, "reason": str(reason or "")},
                "action": action,
                "reason": str(reason or ""),
                "data_source": "router:llm+rule_based",
            }
            return DomainKernel.attach("router", out)
        except Exception as e:
            logger.error(f"RouterAgent error: {e}")
            out = {
                **out,
                "decision": {"action": rule_based.get("action"), "reason": f"LLM 异常回退：{rule_based.get('reason')}"},
                "action": rule_based.get("action"),
                "reason": f"LLM 异常回退：{rule_based.get('reason')}",
                "data_source": "router:rule_based_fallback",
            }
            return DomainKernel.attach("router", out)
