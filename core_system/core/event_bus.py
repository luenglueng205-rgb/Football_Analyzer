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
                # Force ALL handlers into an async task or thread to prevent ANY blocking
                if asyncio.iscoroutinefunction(handler):
                    # For async handlers, we create a task
                    tasks.append(asyncio.create_task(handler(event_data)))
                else:
                    # For sync handlers, offload to a thread pool and wrap in a task
                    coro = asyncio.to_thread(handler, event_data)
                    tasks.append(asyncio.create_task(coro))
            
            # Important: Don't await tasks here if you want completely non-blocking publish.
            for t in tasks:
                # Add a callback to log exceptions if they occur in the background tasks
                t.add_done_callback(lambda fut: self._handle_task_result(fut))
                
    def _handle_task_result(self, task: asyncio.Task):
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Background task failed: {e}")
