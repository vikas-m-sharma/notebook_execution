import asyncio
import uuid
import pytest
from app.execution.enums import ExecutionStatus
from app.execution.exceptions import (
    ExecutionManagerError,
    InvalidExecutionStateError,
)
from app.execution.manager import ExecutionManager
from app.execution.models import ExecutionRequestPayload
from app.execution.session.manager import SessionManager


@pytest.mark.asyncio
async def test_execution_manager_basic_flow():
    """Test standard execution lifecycle through ExecutionManager: QUEUED -> VALIDATING -> RUNNING -> SUCCEEDED."""
    session_mgr = SessionManager()
    session = await session_mgr.create_session(notebook_id=uuid.uuid4())
    exec_mgr = ExecutionManager(session_manager=session_mgr)

    try:
        req = ExecutionRequestPayload(
            session_id=session.session_id,
            code="print('Hello ExecutionManager')",
        )
        task = await exec_mgr.submit_execution(req)

        assert task.status == ExecutionStatus.SUCCEEDED
        assert task.stdout.strip() == "Hello ExecutionManager"
        assert task.started_at is not None
        assert task.completed_at is not None
        assert task.execution_time_ms > 0

        # Retrieve result payload
        result_payload = await exec_mgr.get_execution_result(task.execution_id)
        assert result_payload.status == ExecutionStatus.SUCCEEDED
        assert result_payload.stdout.strip() == "Hello ExecutionManager"
    finally:
        await session_mgr.stop_session(session.session_id)


@pytest.mark.asyncio
async def test_execution_manager_stateful_ordering():
    """Test that ExecutionManager routes cells statefully and preserves execution order across multiple cells."""
    session_mgr = SessionManager()
    session = await session_mgr.create_session(notebook_id=uuid.uuid4())
    exec_mgr = ExecutionManager(session_manager=session_mgr)

    try:
        t1 = await exec_mgr.submit_execution({"session_id": session.session_id, "code": "x = 10"})
        assert t1.status == ExecutionStatus.SUCCEEDED

        t2 = await exec_mgr.submit_execution({"session_id": session.session_id, "code": "x = x + 20"})
        assert t2.status == ExecutionStatus.SUCCEEDED

        t3 = await exec_mgr.submit_execution({"session_id": session.session_id, "code": "print(x)"})
        assert t3.status == ExecutionStatus.SUCCEEDED
        assert t3.stdout.strip() == "30"
    finally:
        await session_mgr.stop_session(session.session_id)


@pytest.mark.asyncio
async def test_execution_manager_multi_session_concurrency():
    """Verify that ExecutionManager supports concurrent executions across different sessions."""
    session_mgr = SessionManager()
    nb_id = uuid.uuid4()
    sess_a = await session_mgr.create_session(notebook_id=nb_id)
    sess_b = await session_mgr.create_session(notebook_id=nb_id)
    exec_mgr = ExecutionManager(session_manager=session_mgr)

    try:
        t_a = asyncio.create_task(
            exec_mgr.submit_execution({"session_id": sess_a.session_id, "code": "print('Session A')"})
        )
        t_b = asyncio.create_task(
            exec_mgr.submit_execution({"session_id": sess_b.session_id, "code": "print('Session B')"})
        )

        res_a, res_b = await asyncio.gather(t_a, t_b)
        assert res_a.status == ExecutionStatus.SUCCEEDED
        assert res_a.stdout.strip() == "Session A"
        assert res_b.status == ExecutionStatus.SUCCEEDED
        assert res_b.stdout.strip() == "Session B"
    finally:
        await session_mgr.stop_session(sess_a.session_id)
        await session_mgr.stop_session(sess_b.session_id)


@pytest.mark.asyncio
async def test_execution_manager_validation_failure():
    """Verify that ExecutionManager rejects execution requests for non-existent sessions during VALIDATING state."""
    exec_mgr = ExecutionManager()

    with pytest.raises(ExecutionManagerError):
        await exec_mgr.submit_execution({"session_id": "session-invalid-id", "code": "print('test')"})

    # Check task was registered as FAILED
    tasks = await exec_mgr.list_executions("session-invalid-id")
    assert len(tasks) == 1
    assert tasks[0].status == ExecutionStatus.FAILED


@pytest.mark.asyncio
async def test_execution_manager_user_code_exception():
    """Verify that user code exceptions transition task to FAILED without destroying session usability."""
    session_mgr = SessionManager()
    session = await session_mgr.create_session(notebook_id=uuid.uuid4())
    exec_mgr = ExecutionManager(session_manager=session_mgr)

    try:
        await exec_mgr.submit_execution({"session_id": session.session_id, "code": "val = 'alive'"})

        t_err = await exec_mgr.submit_execution({"session_id": session.session_id, "code": "raise ValueError('test error')"})
        assert t_err.status == ExecutionStatus.FAILED
        assert "ValueError: test error" in t_err.traceback

        t_ok = await exec_mgr.submit_execution({"session_id": session.session_id, "code": "print(val)"})
        assert t_ok.status == ExecutionStatus.SUCCEEDED
        assert t_ok.stdout.strip() == "alive"
    finally:
        await session_mgr.stop_session(session.session_id)


@pytest.mark.asyncio
async def test_execution_manager_timeout():
    """Verify that cell execution exceeding configured timeout transitions task to TIMED_OUT."""
    session_mgr = SessionManager()
    session = await session_mgr.create_session(notebook_id=uuid.uuid4())
    exec_mgr = ExecutionManager(session_manager=session_mgr)

    try:
        req = ExecutionRequestPayload(
            session_id=session.session_id,
            code="import time\ntime.sleep(5)",
            timeout=0.5,
        )
        task = await exec_mgr.submit_execution(req)

        assert task.status == ExecutionStatus.TIMED_OUT
        assert "timed out after 0.5" in task.error_message
    finally:
        await session_mgr.stop_session(session.session_id)


@pytest.mark.asyncio
async def test_execution_manager_cancellation():
    """Verify explicit execution cancellation transition: RUNNING -> CANCELLING -> CANCELLED."""
    session_mgr = SessionManager()
    session = await session_mgr.create_session(notebook_id=uuid.uuid4())
    exec_mgr = ExecutionManager(session_manager=session_mgr)

    try:
        async def submit_slow():
            return await exec_mgr.submit_execution(
                ExecutionRequestPayload(
                    session_id=session.session_id,
                    code="import time\ntime.sleep(5)",
                    timeout=10.0,
                )
            )

        submit_task = asyncio.create_task(submit_slow())

        # Wait briefly for task to start running
        for _ in range(20):
            tasks = await exec_mgr.list_executions(session.session_id)
            if tasks and tasks[0].status == ExecutionStatus.RUNNING:
                break
            await asyncio.sleep(0.05)

        running_tasks = await exec_mgr.list_executions(session.session_id)
        assert len(running_tasks) == 1
        exec_id = running_tasks[0].execution_id

        # Cancel execution
        cancelled_task = await exec_mgr.cancel_execution(exec_id)
        assert cancelled_task.status in (ExecutionStatus.CANCELLING, ExecutionStatus.CANCELLED)

        # Await submitted task
        task_res = await submit_task
        assert task_res.status == ExecutionStatus.CANCELLED
    finally:
        await session_mgr.stop_session(session.session_id)


@pytest.mark.asyncio
async def test_execution_manager_cancellation_invalid_state():
    """Verify that cancelling an already completed execution raises InvalidExecutionStateError."""
    session_mgr = SessionManager()
    session = await session_mgr.create_session(notebook_id=uuid.uuid4())
    exec_mgr = ExecutionManager(session_manager=session_mgr)

    try:
        t = await exec_mgr.submit_execution({"session_id": session.session_id, "code": "x = 1"})
        assert t.status == ExecutionStatus.SUCCEEDED

        with pytest.raises(InvalidExecutionStateError):
            await exec_mgr.cancel_execution(t.execution_id)
    finally:
        await session_mgr.stop_session(session.session_id)


@pytest.mark.asyncio
async def test_execution_manager_architectural_boundary():
    """Verify control plane execution boundary: ExecutionManager does NOT execute Python code directly."""
    session_mgr = SessionManager()
    session = await session_mgr.create_session(notebook_id=uuid.uuid4())
    exec_mgr = ExecutionManager(session_manager=session_mgr)

    try:
        t = await exec_mgr.submit_execution(
            {"session_id": session.session_id, "code": "exec_mgr_var = 'CONTROL_PLANE_SAFE'"}
        )
        assert t.status == ExecutionStatus.SUCCEEDED

        # Verify exec_mgr_var does NOT exist in globals() of current test/control-plane process
        assert "exec_mgr_var" not in globals()
        assert "exec_mgr_var" not in locals()
    finally:
        await session_mgr.stop_session(session.session_id)
