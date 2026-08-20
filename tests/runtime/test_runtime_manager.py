import uuid
import pytest
from app.runtime.config import RuntimeConfig
from app.runtime.enums import RuntimeStatus, RuntimeType
from app.runtime.exceptions import (
    RuntimeAlreadyRunningError,
    RuntimeNotFoundError,
)
from app.runtime.manager import RuntimeManager


@pytest.mark.asyncio
async def test_runtime_manager_lifecycle():
    """Test full RuntimeManager startup, retrieval, filtering, shutdown, and bulk termination lifecycle."""
    manager = RuntimeManager()

    # 1. Start Python runtime
    cfg = RuntimeConfig(timeout_seconds=300)
    rt_py = await manager.start_runtime(RuntimeType.PYTHON, config=cfg)
    assert rt_py.runtime_type == RuntimeType.PYTHON
    assert rt_py.status == RuntimeStatus.RUNNING
    assert await rt_py.is_alive() is True

    # 2. Get runtime by ID
    retrieved = await manager.get_runtime(rt_py.runtime_id)
    assert retrieved.runtime_id == rt_py.runtime_id

    # 3. Start SQL runtime
    rt_sql = await manager.start_runtime(RuntimeType.SQL)
    assert rt_sql.runtime_type == RuntimeType.SQL

    # 4. List active runtimes & filter by type
    all_rts = await manager.list_runtimes()
    assert len(all_rts) == 2

    py_rts = await manager.list_runtimes(RuntimeType.PYTHON)
    assert len(py_rts) == 1
    assert py_rts[0].runtime_id == rt_py.runtime_id

    # 5. Stop single runtime
    stopped = await manager.stop_runtime(rt_py.runtime_id)
    assert stopped.status == RuntimeStatus.TERMINATED
    assert await stopped.is_alive() is False

    # 6. Bulk terminate remaining runtimes
    await manager.terminate_all()
    remaining = await manager.list_runtimes()
    assert len(remaining) == 0


@pytest.mark.asyncio
async def test_runtime_manager_negative_cases():
    """Test RuntimeManager exceptions: RuntimeNotFoundError, RuntimeAlreadyRunningError."""
    manager = RuntimeManager()

    # RuntimeNotFoundError
    fake_id = uuid.uuid4()
    with pytest.raises(RuntimeNotFoundError):
        await manager.get_runtime(fake_id)

    with pytest.raises(RuntimeNotFoundError):
        await manager.stop_runtime(fake_id)

    # RuntimeAlreadyRunningError
    rt = await manager.start_runtime(RuntimeType.PYTHON)
    with pytest.raises(RuntimeAlreadyRunningError):
        await manager.start_runtime(RuntimeType.PYTHON, runtime_id=rt.runtime_id)
