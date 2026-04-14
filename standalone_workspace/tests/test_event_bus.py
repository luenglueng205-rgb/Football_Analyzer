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
