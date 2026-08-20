import asyncio
from typing import TYPE_CHECKING, Any, AsyncGenerator

if TYPE_CHECKING:
    from app.schemas.output import OutputEventSchema


class OutputPublisher:
    """Transport-agnostic in-memory publisher/subscriber pattern for streaming live execution output events."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[asyncio.Queue[Any]]] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    async def publish(self, event: Any) -> None:
        """Publish an output event to all active subscribers for its execution_id."""
        async with self._lock:
            exec_id = getattr(event, "execution_id", str(event))
            queues = self._subscribers.get(exec_id, [])
            for q in queues:
                await q.put(event)

    async def subscribe(
        self, execution_id: str
    ) -> AsyncGenerator[Any, None]:
        """Subscribe to live output stream for execution_id as an async generator."""
        q: asyncio.Queue[Any] = asyncio.Queue()

        async with self._lock:
            if execution_id not in self._subscribers:
                self._subscribers[execution_id] = []
            self._subscribers[execution_id].append(q)

        try:
            while True:
                event = await q.get()
                yield event
                q.task_done()
        finally:
            async with self._lock:
                if execution_id in self._subscribers:
                    if q in self._subscribers[execution_id]:
                        self._subscribers[execution_id].remove(q)
                    if not self._subscribers[execution_id]:
                        del self._subscribers[execution_id]
