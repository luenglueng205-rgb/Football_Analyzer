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
