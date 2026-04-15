# Event-Driven Agentic Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the football analyzer into a true AI-Native Event-Driven architecture, replacing rigid Python `while True` loops with an Event Bus and exposing all core capabilities as Tool Calling functions for the LLM to orchestrate autonomously.

**Architecture:** 
1. `EventBus` to handle asynchronous events (e.g., `MATCH_UPCOMING`, `MATCH_FINISHED`).
2. `AgenticCore` (The new `SyndicateOS`) utilizing OpenAI's `tools` API (Function Calling) to autonomously decide which physical tools (`LotteryRouter`, `SettlementEngine`, etc.) to invoke based on the event context.
3. `RouterAgent` (MoE Gatekeeper) to filter out low-value matches before waking up the heavy Multi-Agent debate society.

**Tech Stack:** Python `asyncio`, `openai` (Function Calling), `pydantic` (for strict tool schemas).

---

### Task 1: Create the Event Bus

**Files:**
- Create: `standalone_workspace/core/event_bus.py`
- Test: `standalone_workspace/tests/test_event_bus.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest
import asyncio
from core.event_bus import EventBus

@pytest.mark.asyncio
async def test_event_bus_pub_sub():
    bus = EventBus()
    received_events = []
    
    async def dummy_handler(event_data):
        received_events.append(event_data)
        
    bus.subscribe("MATCH_UPCOMING", dummy_handler)
    await bus.publish("MATCH_UPCOMING", {"match_id": "123", "home": "ARS", "away": "CHE"})
    
    # Allow time for async task to process
    await asyncio.sleep(0.1)
    
    assert len(received_events) == 1
    assert received_events[0]["match_id"] == "123"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest standalone_workspace/tests/test_event_bus.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'core'"

- [ ] **Step 3: Write minimal implementation**

```python
import asyncio
import logging
from typing import Callable, Dict, List, Any

logger = logging.getLogger(__name__)

class EventBus:
    """
    Central Event Bus for the Agentic OS.
    Replaces rigid while loops with an asynchronous pub/sub model.
    """
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, handler: Callable):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.info(f"Subscribed to {event_type}")

    async def publish(self, event_type: str, event_data: Dict[str, Any]):
        if event_type in self._subscribers:
            logger.info(f"Publishing event: {event_type} | Data: {event_data}")
            tasks = []
            for handler in self._subscribers[event_type]:
                tasks.append(asyncio.create_task(handler(event_data)))
            if tasks:
                await asyncio.gather(*tasks)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest standalone_workspace/tests/test_event_bus.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add standalone_workspace/core/event_bus.py standalone_workspace/tests/test_event_bus.py
git commit -m "feat: implement asynchronous EventBus for event-driven architecture"
```

---

### Task 2: Create the MoE Router Agent (Gatekeeper)

**Files:**
- Create: `standalone_workspace/agents/router_agent.py`

- [ ] **Step 1: Write the implementation**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add standalone_workspace/agents/router_agent.py
git commit -m "feat: implement RouterAgent for MoE match filtering"
```

---

### Task 3: Refactor SyndicateOS into AgenticCore (Tool Calling)

**Files:**
- Create: `standalone_workspace/core/agentic_core.py`
- Modify: `standalone_workspace/agents/syndicate_os.py` (Deprecate)

- [ ] **Step 1: Write the implementation for AgenticCore**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add standalone_workspace/core/agentic_core.py
git commit -m "feat: implement AgenticCore with OpenAI Function Calling"
```

---

### Task 4: Connect the Pipeline (Event Producer)

**Files:**
- Create: `standalone_workspace/run_event_driven_pipeline.py`

- [ ] **Step 1: Write the implementation**

```python
import asyncio
import logging
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'standalone_workspace')))

from core.event_bus import EventBus
from agents.router_agent import RouterAgent
from core.agentic_core import AgenticCore

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(message)s')

async def mock_event_producer(bus: EventBus):
    """Mocks external webhooks pushing events into the system."""
    await asyncio.sleep(1)
    
    # Event 1: A boring match (should be filtered by Router)
    await bus.publish("MATCH_UPCOMING", {
        "match_id": "M001",
        "home": "Man City", "away": "League Two Team",
        "odds": [1.02, 15.0, 34.0]
    })
    
    await asyncio.sleep(2)
    
    # Event 2: A high-value match (should wake up the Core)
    await bus.publish("MATCH_UPCOMING", {
        "match_id": "M002",
        "home": "Bayern Munich", "away": "Real Madrid",
        "odds": [2.30, 3.50, 2.80]
    })

async def main():
    print("🚀 Starting AI-Native Event-Driven Architecture...")
    bus = EventBus()
    router = RouterAgent()
    core = AgenticCore()
    
    # The brain subscribes to "DEEP_DIVE_APPROVED" events
    bus.subscribe("DEEP_DIVE_APPROVED", core.handle_event)
    
    # The router acts as the middleware for raw events
    async def router_middleware(event_data):
        decision = await router.evaluate_match_value(event_data)
        if decision.get("action") == "DEEP_DIVE":
            await bus.publish("DEEP_DIVE_APPROVED", event_data)
        else:
            logging.info(f"🛑 [Router] Ignored match {event_data.get('match_id')}: {decision.get('reason')}")
            
    bus.subscribe("MATCH_UPCOMING", router_middleware)
    
    # Start the producer
    await mock_event_producer(bus)
    
    # Keep alive briefly to let async tasks finish
    await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Commit**

```bash
git add standalone_workspace/run_event_driven_pipeline.py
git commit -m "feat: create main event-driven pipeline entry point"
```

---

### Task 5: Sync to OpenClaw Adapter

**Files:**
- Modify: `openclaw_workspace/src/mcp_server.py` (Add syncing for core modules if needed, though MCP tools are already exposed).
- Command: Copy the new `core` directory to `openclaw_workspace/runtime/football_analyzer/`

- [ ] **Step 1: Execute sync commands**

```bash
mkdir -p openclaw_workspace/runtime/football_analyzer/core/
cp standalone_workspace/core/event_bus.py openclaw_workspace/runtime/football_analyzer/core/
cp standalone_workspace/core/agentic_core.py openclaw_workspace/runtime/football_analyzer/core/
cp standalone_workspace/agents/router_agent.py openclaw_workspace/runtime/football_analyzer/agents/
```

- [ ] **Step 2: Commit**

```bash
git add openclaw_workspace/runtime/football_analyzer/core/ openclaw_workspace/runtime/football_analyzer/agents/router_agent.py
git commit -m "feat: sync Event-Driven Core to OpenClaw runtime"
```
