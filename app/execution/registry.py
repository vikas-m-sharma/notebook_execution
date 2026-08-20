import asyncio
from typing import Optional, Sequence

from app.execution.exceptions import ExecutionTaskNotFoundError
from app.execution.models import ExecutionTask


class ExecutionRegistry:
    """Thread-safe and async-safe in-memory registry for tracking active and completed ExecutionTask instances."""

    def __init__(self) -> None:
        self._tasks: dict[str, ExecutionTask] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    async def register(self, task: ExecutionTask) -> None:
        """Register a new execution task."""
        async with self._lock:
            self._tasks[task.execution_id] = task

    async def get(self, execution_id: str) -> ExecutionTask:
        """Retrieve an execution task by execution_id or raise ExecutionTaskNotFoundError."""
        async with self._lock:
            task = self._tasks.get(execution_id)
            if task is None:
                raise ExecutionTaskNotFoundError(execution_id)
            return task

    async def update(self, task: ExecutionTask) -> None:
        """Update an existing execution task."""
        async with self._lock:
            if task.execution_id not in self._tasks:
                raise ExecutionTaskNotFoundError(task.execution_id)
            self._tasks[task.execution_id] = task

    async def list_by_session(
        self, session_id: Optional[str] = None
    ) -> Sequence[ExecutionTask]:
        """List execution tasks, optionally filtered by session_id."""
        async with self._lock:
            tasks = list(self._tasks.values())
            if session_id is not None:
                tasks = [t for t in tasks if t.session_id == session_id]
            return tasks

    async def clear(self) -> None:
        """Clear all registered execution tasks."""
        async with self._lock:
            self._tasks.clear()
