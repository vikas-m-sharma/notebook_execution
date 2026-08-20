import uuid
import pytest
from app.execution.session.enums import SessionStatus
from app.execution.session.exceptions import (
    SessionNotActiveError,
    SessionNotFoundError,
)
from app.execution.session.manager import SessionManager


@pytest.mark.asyncio
async def test_session_lifecycle_and_manager():
    """Test ExecutionSession lifecycle: creation, active status, retrieval, listing, stopping, and cleanup."""
    manager = SessionManager()
    notebook_id = uuid.uuid4()

    # 1. Create Session
    session = await manager.create_session(notebook_id=notebook_id)
    assert session.status == SessionStatus.ACTIVE
    assert session.notebook_id == notebook_id
    assert session.session_id.startswith("session-")

    # 2. Get Session Info
    info = await manager.get_session_info(session.session_id)
    assert info.session_id == session.session_id
    assert info.status == SessionStatus.ACTIVE
    assert info.notebook_id == notebook_id

    # 3. List Sessions
    sessions = await manager.list_sessions(notebook_id=notebook_id)
    assert len(sessions) == 1
    assert sessions[0].session_id == session.session_id

    # 4. Stop Session
    stopped_sess = await manager.stop_session(session.session_id)
    assert stopped_sess.status == SessionStatus.STOPPED

    # 5. Verify execution in stopped session raises SessionNotActiveError
    with pytest.raises(SessionNotActiveError):
        await stopped_sess.execute_cell("print('test')")

    # 6. Bulk terminate sessions
    await manager.terminate_all_sessions()


@pytest.mark.asyncio
async def test_session_lifecycle_negative_cases():
    """Test SessionManager exceptions for invalid session IDs."""
    manager = SessionManager()

    with pytest.raises(SessionNotFoundError):
        await manager.get_session("session-invalid-id")

    with pytest.raises(SessionNotFoundError):
        await manager.execute_in_session("session-invalid-id", "x = 1")
