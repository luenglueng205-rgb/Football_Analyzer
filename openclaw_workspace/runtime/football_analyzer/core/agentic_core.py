import json
import logging
import os
from typing import Dict, Any
from openai import AsyncOpenAI
from tools.parlay_rules_engine import ParlayRulesEngine
from tools.lottery_router import LotteryRouter

logger = logging.getLogger(__name__)

class AgenticCore:
    """
    The True AI-Native Brain.
    Replaces SyndicateOS. Uses OpenAI Function Calling to autonomously use tools.
    """
    def __init__(self):
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        api_key = os.getenv("OPENAI_API_KEY", "dummy-key-for-test")
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        
        # The tools the LLM is allowed to call autonomously
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "calculate_chuantong_combinations",
                    "description": "Calculate combinations for Traditional Football Lottery (14-match, Renjiu, etc.).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "match_selections": {"type": "array", "items": {"type": "integer"}},
                            "play_type": {"type": "string", "enum": ["14_match", "renjiu", "6_htft", "4_goals"]}
                        },
                        "required": ["match_selections", "play_type"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "validate_ticket_physics",
                    "description": "Route a ticket through the physical firewall to ensure it meets official rules (Jingcai/Beidan/Zucai).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "lottery_type": {"type": "string", "enum": ["JINGCAI", "BEIDAN", "ZUCAI"]},
                            "ticket_data": {"type": "object"}
                        },
                        "required": ["lottery_type", "ticket_data"]
                    }
                }
            }
        ]

    async def handle_event(self, event_data: Dict[str, Any]):
        """
        Triggered by the EventBus.
        The LLM decides what to do based on the event.
        """
        match_id = event_data.get("match_id")
        logger.info(f"🧠 [AgenticCore] Woken up by event for match {match_id}. Thinking...")
        
        messages = [
            {"role": "system", "content": "You are an autonomous AI betting syndicate manager. Use the tools provided to analyze the event and formulate a legally valid ticket."},
            {"role": "user", "content": f"Event received: {json.dumps(event_data)}"}
        ]
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools,
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            
            # If the LLM decided to call a tool
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    func_name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)
                    logger.info(f"🛠️ [AgenticCore] Autonomously calling tool: {func_name} with {args}")
                    
                    if func_name == "calculate_chuantong_combinations":
                        engine = ParlayRulesEngine()
                        result = engine.calculate_chuantong_combinations(args["match_selections"], args["play_type"])
                        logger.info(f"🔧 Tool Result: {result} tickets")
                        
                    elif func_name == "validate_ticket_physics":
                        router = LotteryRouter()
                        result = router.route_and_validate(args["lottery_type"], args["ticket_data"])
                        logger.info(f"🔧 Tool Result: {result['message']}")
            else:
                logger.info(f"🗣️ [AgenticCore] Decision: {message.content}")
                
        except Exception as e:
            logger.error(f"AgenticCore execution failed: {e}")
