import uuid
from typing import Optional, Sequence

from app.execution.session.enums import SessionStatus
from app.execution.session.exceptions import (
    SessionNotFoundError,
)
from app.execution.session.models import ExecutionResult, SessionInfo
from app.execution.session.session import ExecutionSession
from app.runtime.config import RuntimeConfig
from app.runtime.enums import RuntimeType
from app.runtime.manager import RuntimeManager


class SessionManager:
    """Manager and registry for active Execution Session instances."""

    def __init__(self, runtime_manager: Optional[RuntimeManager] = None) -> None:
        self.runtime_manager: RuntimeManager = runtime_manager or RuntimeManager()
        self._sessions: dict[str, ExecutionSession] = {}

    async def create_session(
        self,
        notebook_id: uuid.UUID,
        config: Optional[RuntimeConfig] = None,
        session_id: Optional[str] = None,
    ) -> ExecutionSession:
        """Create and start a new Execution Session bound to a fresh PythonRuntime."""
        target_session_id = session_id or f"session-{uuid.uuid4().hex[:12]}"

        # Start a dedicated PythonRuntime worker process via RuntimeManager
        runtime = await self.runtime_manager.start_runtime(
            runtime_type=RuntimeType.PYTHON,
            config=config,
        )

        session = ExecutionSession(
            notebook_id=notebook_id,
            runtime=runtime,
            session_id=target_session_id,
        )

        await session.start()
        self._sessions[target_session_id] = session
        return session

    async def get_session(self, session_id: str) -> ExecutionSession:
        """Retrieve an active ExecutionSession by session_id or raise SessionNotFoundError."""
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionNotFoundError(session_id)
        return session

    async def get_session_info(self, session_id: str) -> SessionInfo:
        """Retrieve SessionInfo model for a session."""
        session = await self.get_session(session_id)
        return SessionInfo(
            session_id=session.session_id,
            notebook_id=session.notebook_id,
            runtime_id=session.runtime.runtime_id,
            status=session.status,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )

    async def list_sessions(
        self, notebook_id: Optional[uuid.UUID] = None
    ) -> Sequence[ExecutionSession]:
        """List active Execution Sessions, optionally filtered by notebook_id."""
        sessions = list(self._sessions.values())
        if notebook_id is not None:
            sessions = [s for s in sessions if s.notebook_id == notebook_id]
        return sessions

    async def execute_in_session(
        self,
        session_id: str,
        code: str,
        cell_id: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> ExecutionResult:
        """Route code execution request to the target ExecutionSession."""
        session = await self.get_session(session_id)
        return await session.execute_cell(code=code, cell_id=cell_id, timeout=timeout)

    async def reset_session(self, session_id: str) -> ExecutionSession:
        """Reset the target ExecutionSession's Python namespace."""
        session = await self.get_session(session_id)
        await session.reset()
        return session

    async def stop_session(self, session_id: str) -> ExecutionSession:
        """Stop an active ExecutionSession and release its bound PythonRuntime worker."""
        session = await self.get_session(session_id)
        await session.stop()
        return session

    async def terminate_all_sessions(self) -> None:
        """Orchestrate bulk termination of all active Execution Sessions."""
        for session in list(self._sessions.values()):
            if session.status in (SessionStatus.STARTING, SessionStatus.ACTIVE):
                await session.stop()
        self._sessions.clear()
        await self.runtime_manager.terminate_all()
