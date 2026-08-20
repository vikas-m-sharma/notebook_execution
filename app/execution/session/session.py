import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.execution.session.enums import SessionStatus
from app.execution.session.exceptions import (
    SessionExecutionError,
    SessionNotActiveError,
)
from app.execution.session.models import ExecutionResult
from app.runtime.base import BaseRuntime


class ExecutionSession:
    """Stateful execution context maintaining Python memory namespace across cell executions."""

    def __init__(
        self,
        notebook_id: uuid.UUID,
        runtime: BaseRuntime,
        session_id: Optional[str] = None,
    ) -> None:
        self.session_id: str = session_id or f"session-{uuid.uuid4().hex[:12]}"
        self.notebook_id: uuid.UUID = notebook_id
        self.runtime: BaseRuntime = runtime
        self.status: SessionStatus = SessionStatus.CREATED
        self.created_at: datetime = datetime.now(timezone.utc)
        self.updated_at: datetime = datetime.now(timezone.utc)
        self._lock: asyncio.Lock = asyncio.Lock()

    async def start(self) -> None:
        """Establish session binding with Phase 5 PythonRuntime worker."""
        if self.status not in (SessionStatus.CREATED, SessionStatus.STOPPED):
            return

        self.status = SessionStatus.STARTING
        self.updated_at = datetime.now(timezone.utc)

        try:
            if not await self.runtime.is_alive():
                await self.runtime.start()

            self.status = SessionStatus.ACTIVE
            self.updated_at = datetime.now(timezone.utc)
        except Exception as exc:
            self.status = SessionStatus.FAILED
            self.updated_at = datetime.now(timezone.utc)
            raise SessionExecutionError(self.session_id, str(exc)) from exc

    async def execute_cell(
        self,
        code: str,
        cell_id: Optional[str] = None,
        timeout: Optional[float] = None,
        request_id: Optional[str] = None,
    ) -> ExecutionResult:
        """Execute notebook cell code statefully inside the bound PythonRuntime worker."""
        if self.status != SessionStatus.ACTIVE:
            raise SessionNotActiveError(self.session_id, self.status.value)

        # Check underlying runtime health
        if not await self.runtime.is_alive():
            self.status = SessionStatus.FAILED
            self.updated_at = datetime.now(timezone.utc)
            raise SessionExecutionError(
                self.session_id, "Underlying Python runtime is no longer alive."
            )

        req_id = request_id or str(uuid.uuid4())

        # Serialize cell executions against the stateful Python namespace using asyncio.Lock
        async with self._lock:
            try:
                res = await self.runtime.execute_code(code, timeout=timeout)
                self.updated_at = datetime.now(timezone.utc)
                return ExecutionResult(
                    session_id=self.session_id,
                    request_id=req_id,
                    cell_id=cell_id,
                    status=res.get("status", "ok"),
                    stdout=res.get("stdout", ""),
                    stderr=res.get("stderr", ""),
                    traceback=res.get("traceback"),
                    execution_time_ms=res.get("execution_time_ms", 0.0),
                )
            except Exception as exc:
                if not await self.runtime.is_alive():
                    self.status = SessionStatus.FAILED
                    self.updated_at = datetime.now(timezone.utc)
                raise SessionExecutionError(self.session_id, str(exc)) from exc

    async def reset(self) -> None:
        """Reset the session Python namespace by restarting the underlying worker runtime."""
        async with self._lock:
            if self.status != SessionStatus.ACTIVE:
                raise SessionNotActiveError(self.session_id, self.status.value)

            await self.runtime.stop()
            await self.runtime.start()
            self.updated_at = datetime.now(timezone.utc)

    async def stop(self) -> None:
        """Orchestrate graceful termination of the execution session and its bound worker runtime."""
        if self.status in (SessionStatus.STOPPING, SessionStatus.STOPPED):
            return

        self.status = SessionStatus.STOPPING
        self.updated_at = datetime.now(timezone.utc)

        try:
            await self.runtime.stop()
        except Exception:
            pass

        self.status = SessionStatus.STOPPED
        self.updated_at = datetime.now(timezone.utc)
