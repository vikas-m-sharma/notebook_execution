import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence

from app.execution.enums import ExecutionStatus
from app.execution.exceptions import (
    ExecutionCancelledError,
    ExecutionManagerError,
    ExecutionTimeoutError,
    InvalidExecutionStateError,
)
from app.execution.models import (
    ExecutionRequestPayload,
    ExecutionResultPayload,
    ExecutionTask,
)
from app.execution.registry import ExecutionRegistry
from app.execution.session.enums import SessionStatus
from app.execution.session.exceptions import (
    SessionExecutionError,
    SessionNotActiveError,
    SessionNotFoundError,
)
from app.execution.session.manager import SessionManager


class ExecutionManager:
    """Execution Manager orchestrating notebook cell execution lifecycle, validation, monitoring, cancellation, and timeout management."""

    def __init__(
        self,
        session_manager: Optional[SessionManager] = None,
        registry: Optional[ExecutionRegistry] = None,
    ) -> None:
        self.session_manager: SessionManager = session_manager or SessionManager()
        self.registry: ExecutionRegistry = registry or ExecutionRegistry()
        self._running_tasks: dict[str, asyncio.Task] = {}

    async def submit_execution(
        self,
        payload: ExecutionRequestPayload | dict,
    ) -> ExecutionTask:
        """Submit, validate, monitor, and execute a notebook cell execution request."""
        if isinstance(payload, dict):
            req = ExecutionRequestPayload(**payload)
        else:
            req = payload

        # 1. QUEUED: Initialize task
        task = ExecutionTask(
            session_id=req.session_id,
            notebook_id=req.notebook_id,
            cell_id=req.cell_id,
            code=req.code,
            status=ExecutionStatus.QUEUED,
            timeout_seconds=float(req.timeout if req.timeout is not None else 30.0),
        )
        await self.registry.register(task)

        # 2. VALIDATING: Validate session availability
        task.status = ExecutionStatus.VALIDATING
        await self.registry.update(task)

        try:
            session = await self.session_manager.get_session(req.session_id)
            if session.status != SessionStatus.ACTIVE:
                raise SessionNotActiveError(req.session_id, session.status.value)
        except (SessionNotFoundError, SessionNotActiveError) as exc:
            task.status = ExecutionStatus.FAILED
            task.error_message = str(exc)
            task.completed_at = datetime.now(timezone.utc)
            await self.registry.update(task)
            raise ExecutionManagerError(str(exc)) from exc

        # 3. RUNNING: Route cell execution to ExecutionSession
        task.status = ExecutionStatus.RUNNING
        task.started_at = datetime.now(timezone.utc)
        await self.registry.update(task)

        async def _run_cell():
            return await session.execute_cell(
                code=req.code,
                cell_id=req.cell_id,
                timeout=task.timeout_seconds,
                request_id=task.request_id,
            )

        async_task = asyncio.create_task(_run_cell())
        self._running_tasks[task.execution_id] = async_task

        try:
            res = await asyncio.wait_for(async_task, timeout=task.timeout_seconds)

            if res.status == "ok":
                task.status = ExecutionStatus.SUCCEEDED
                task.stdout = res.stdout
                task.stderr = res.stderr
                task.execution_time_ms = res.execution_time_ms
            else:
                # User code exception raised inside worker process
                task.status = ExecutionStatus.FAILED
                task.stdout = res.stdout
                task.stderr = res.stderr
                task.traceback = res.traceback
                task.error_message = "User code execution raised an exception."
                task.execution_time_ms = res.execution_time_ms
        except asyncio.TimeoutError:
            task.status = ExecutionStatus.TIMED_OUT
            task.error_message = (
                f"Execution timed out after {task.timeout_seconds} seconds."
            )
            # Reset hung worker process
            try:
                await session.reset()
            except Exception:
                pass
        except asyncio.CancelledError:
            task.status = ExecutionStatus.CANCELLED
            task.error_message = "Execution was explicitly cancelled."
            try:
                await session.reset()
            except Exception:
                pass
        except SessionExecutionError as exc:
            task.status = ExecutionStatus.FAILED
            task.error_message = str(exc)
        except Exception as exc:
            task.status = ExecutionStatus.FAILED
            task.error_message = str(exc)
        finally:
            self._running_tasks.pop(task.execution_id, None)
            task.completed_at = datetime.now(timezone.utc)
            await self.registry.update(task)

        return task

    async def cancel_execution(self, execution_id: str) -> ExecutionTask:
        """Explicitly cancel an active cell execution request."""
        task = await self.registry.get(execution_id)

        if task.status not in (
            ExecutionStatus.QUEUED,
            ExecutionStatus.VALIDATING,
            ExecutionStatus.RUNNING,
        ):
            raise InvalidExecutionStateError(
                execution_id, task.status.value, "cancel"
            )

        task.status = ExecutionStatus.CANCELLING
        await self.registry.update(task)

        async_task = self._running_tasks.get(execution_id)
        if async_task and not async_task.done():
            async_task.cancel()

        # Reset session worker if running to ensure worker process state clean
        try:
            session = await self.session_manager.get_session(task.session_id)
            await session.reset()
        except Exception:
            pass

        task.status = ExecutionStatus.CANCELLED
        task.completed_at = datetime.now(timezone.utc)
        await self.registry.update(task)
        return task

    async def get_execution(self, execution_id: str) -> ExecutionTask:
        """Retrieve execution task details by execution_id."""
        return await self.registry.get(execution_id)

    async def get_execution_result(
        self, execution_id: str
    ) -> ExecutionResultPayload:
        """Retrieve execution result summary payload."""
        task = await self.get_execution(execution_id)
        return ExecutionResultPayload(
            execution_id=task.execution_id,
            request_id=task.request_id,
            session_id=task.session_id,
            cell_id=task.cell_id,
            status=task.status,
            stdout=task.stdout,
            stderr=task.stderr,
            traceback=task.traceback,
            error_message=task.error_message,
            execution_time_ms=task.execution_time_ms,
        )

    async def list_executions(
        self, session_id: Optional[str] = None
    ) -> Sequence[ExecutionTask]:
        """List execution tasks in registry."""
        return await self.registry.list_by_session(session_id=session_id)
