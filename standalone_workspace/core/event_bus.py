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
