import asyncio
import uuid
import pytest
from app.execution.session.enums import SessionStatus
from app.execution.session.exceptions import SessionExecutionError
from app.execution.session.manager import SessionManager


@pytest.mark.asyncio
async def test_session_cell_exception_resilience():
    """Verify that runtime exceptions in a cell do not destroy the session or discard previous state."""
    manager = SessionManager()
    session = await manager.create_session(notebook_id=uuid.uuid4())

    try:
        # Cell 1: Define variable
        r1 = await session.execute_cell("x = 10")
        assert r1.status == "ok"

        # Cell 2: Runtime Exception (Division by Zero)
        r2 = await session.execute_cell("1 / 0")
        assert r2.status == "error"
        assert "ZeroDivisionError" in r2.traceback
        assert session.status == SessionStatus.ACTIVE  # Session remains active!

        # Cell 3: Access variable from Cell 1
        r3 = await session.execute_cell("print(x)")
        assert r3.status == "ok"
        assert r3.stdout.strip() == "10"
    finally:
        await manager.stop_session(session.session_id)


@pytest.mark.asyncio
async def test_session_cell_syntax_error_resilience():
    """Verify that syntax errors in a cell do not destroy the session."""
    manager = SessionManager()
    session = await manager.create_session(notebook_id=uuid.uuid4())

    try:
        # Cell 1: Define variable
        await session.execute_cell("val = 'alive'")

        # Cell 2: Syntax Error
        r2 = await session.execute_cell("if True")
        assert r2.status == "error"
        assert "SyntaxError" in r2.traceback
        assert session.status == SessionStatus.ACTIVE

        # Cell 3: Access variable
        r3 = await session.execute_cell("print(val)")
        assert r3.status == "ok"
        assert r3.stdout.strip() == "alive"
    finally:
        await manager.stop_session(session.session_id)


@pytest.mark.asyncio
async def test_session_reset_discards_namespace():
    """Verify that reset_session() discards in-memory namespace state."""
    manager = SessionManager()
    session = await manager.create_session(notebook_id=uuid.uuid4())

    try:
        # Define variable
        await session.execute_cell("temp_var = 999")

        # Reset session
        await manager.reset_session(session.session_id)

        # Attempt to access variable
        r2 = await session.execute_cell("print(temp_var)")
        assert r2.status == "error"
        assert "NameError: name 'temp_var' is not defined" in r2.traceback
    finally:
        await manager.stop_session(session.session_id)


@pytest.mark.asyncio
async def test_cross_session_isolation():
    """Verify that different execution sessions have strictly isolated Python worker namespaces."""
    manager = SessionManager()
    nb_id = uuid.uuid4()

    sess_a = await manager.create_session(notebook_id=nb_id)
    sess_b = await manager.create_session(notebook_id=nb_id)

    try:
        # Session A defines variable
        await sess_a.execute_cell("secret_a = 'SESSION_A_DATA'")

        # Session B attempts to read secret_a
        rb = await sess_b.execute_cell("print(secret_a)")
        assert rb.status == "error"
        assert "NameError: name 'secret_a' is not defined" in rb.traceback
    finally:
        await manager.stop_session(sess_a.session_id)
        await manager.stop_session(sess_b.session_id)


@pytest.mark.asyncio
async def test_same_notebook_new_session_is_fresh():
    """Verify that stopping a session and creating a new session for the same notebook starts with a fresh namespace."""
    manager = SessionManager()
    nb_id = uuid.uuid4()

    sess1 = await manager.create_session(notebook_id=nb_id)
    await sess1.execute_cell("shared_var = 12345")
    await manager.stop_session(sess1.session_id)

    sess2 = await manager.create_session(notebook_id=nb_id)
    try:
        r2 = await sess2.execute_cell("print(shared_var)")
        assert r2.status == "error"
        assert "NameError: name 'shared_var' is not defined" in r2.traceback
    finally:
        await manager.stop_session(sess2.session_id)


@pytest.mark.asyncio
async def test_session_concurrency_serialization():
    """Verify that concurrent execution requests against the same ExecutionSession are serialized cleanly."""
    manager = SessionManager()
    session = await manager.create_session(notebook_id=uuid.uuid4())

    try:
        await session.execute_cell("counter = 0")

        async def run_cell(increment):
            return await session.execute_cell(f"counter += {increment}")

        # Run 5 concurrent execution tasks
        results = await asyncio.gather(
            run_cell(1),
            run_cell(2),
            run_cell(3),
            run_cell(4),
            run_cell(5),
        )

        assert all(r.status == "ok" for r in results)

        final_res = await session.execute_cell("print(counter)")
        assert final_res.stdout.strip() == "15"
    finally:
        await manager.stop_session(session.session_id)


@pytest.mark.asyncio
async def test_session_worker_failure_handling():
    """Verify that worker process termination sets session status to FAILED and rejects subsequent requests."""
    manager = SessionManager()
    session = await manager.create_session(notebook_id=uuid.uuid4())

    try:
        await session.execute_cell("x = 1")

        # Simulate unexpected worker process termination
        if session.runtime._process and session.runtime._process.is_alive():
            session.runtime._process.terminate()
            session.runtime._process.join()

        # Attempt execution on dead worker
        with pytest.raises(SessionExecutionError):
            await session.execute_cell("print(x)")

        assert session.status == SessionStatus.FAILED
    finally:
        await manager.stop_session(session.session_id)
