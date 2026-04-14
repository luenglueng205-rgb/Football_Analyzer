import logging
import os
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

class RouterAgent:
    """
    Mixture of Experts (MoE) Gatekeeper.
    Uses a fast, cheap model to filter out low-value matches before waking up the heavy Syndicate.
    """
    def __init__(self):
        self.model = os.getenv("OPENAI_ROUTER_MODEL", "gpt-4o-mini") # Use cheap model
        base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        api_key = os.getenv("OPENAI_API_KEY", "dummy-key-for-test")
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def evaluate_match_value(self, match_data: dict) -> dict:
        home = match_data.get("home", "Unknown")
        away = match_data.get("away", "Unknown")
        odds = match_data.get("odds", [])
        
        logger.info(f"[🚪 Router] Evaluating match value for {home} vs {away}...")
        
        # Fast rule-based filtering first (save tokens)
        if odds and odds[0] < 1.10:
            return {"action": "IGNORE", "reason": "Odds too low (waste of time/tokens)"}
            
        prompt = f"""
        Analyze this upcoming match quickly: {home} vs {away}. Odds: {odds}.
        Is this a high-profile match (derby, top league, Champions League) or a suspicious odds trap?
        Reply strictly with JSON: {{"action": "DEEP_DIVE" or "IGNORE", "reason": "brief explanation"}}
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            import json
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"RouterAgent error: {e}")
            # Fail-safe: if API fails, default to deep dive so we don't miss anything
            return {"action": "DEEP_DIVE", "reason": "API Error, fallback to deep dive"}
