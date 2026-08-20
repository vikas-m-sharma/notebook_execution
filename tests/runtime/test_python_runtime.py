import pytest
from app.runtime.enums import RuntimeStatus, RuntimeType
from app.runtime.manager import RuntimeManager
from app.runtime.python_runtime import PythonRuntime


@pytest.mark.asyncio
async def test_python_runtime_process_lifecycle():
    """Test PythonRuntime child worker process startup, health check, and termination."""
    runtime = PythonRuntime()

    # 1. Start worker process
    await runtime.start()
    assert runtime.status == RuntimeStatus.RUNNING
    assert await runtime.is_alive() is True
    assert runtime._process is not None
    assert runtime._process.is_alive() is True

    # 2. Stop worker process
    await runtime.stop()
    assert runtime.status == RuntimeStatus.TERMINATED
    assert await runtime.is_alive() is False
    assert runtime._process.is_alive() is False


@pytest.mark.asyncio
async def test_python_runtime_code_execution_and_stdout():
    """Test executing code inside child Python worker process and capturing stdout/stderr."""
    runtime = PythonRuntime()
    await runtime.start()

    try:
        res = await runtime.execute_code("a = 10\nb = 20\nprint('Result:', a + b)")
        assert res["status"] == "ok"
        assert res["stdout"].strip() == "Result: 30"
        assert res["stderr"] == ""
        assert res["traceback"] is None
        assert res["execution_time_ms"] > 0
    finally:
        await runtime.stop()


@pytest.mark.asyncio
async def test_python_runtime_state_persistence_across_executions():
    """Test that variables persist across multiple code execution requests within the same worker process."""
    runtime = PythonRuntime()
    await runtime.start()

    try:
        # Cell 1: Define variable
        r1 = await runtime.execute_code("counter = 100")
        assert r1["status"] == "ok"

        # Cell 2: Access and mutate variable
        r2 = await runtime.execute_code("counter += 50\nprint('Counter:', counter)")
        assert r2["status"] == "ok"
        assert r2["stdout"].strip() == "Counter: 150"
    finally:
        await runtime.stop()


@pytest.mark.asyncio
async def test_python_runtime_process_isolation_safety():
    """Verify strict process isolation: variables defined in child worker NEVER leak into main process namespace."""
    runtime = PythonRuntime()
    await runtime.start()

    try:
        r1 = await runtime.execute_code("secret_worker_var = 'ISOLATED_SECRET'")
        assert r1["status"] == "ok"

        # Verify secret_worker_var does NOT exist in main process
        assert "secret_worker_var" not in globals()
        assert "secret_worker_var" not in locals()
    finally:
        await runtime.stop()


@pytest.mark.asyncio
async def test_python_runtime_error_traceback_handling():
    """Test Exception traceback formatting when user code raises a runtime error inside worker process."""
    runtime = PythonRuntime()
    await runtime.start()

    try:
        res = await runtime.execute_code("1 / 0")
        assert res["status"] == "error"
        assert res["traceback"] is not None
        assert "ZeroDivisionError: division by zero" in res["traceback"]
    finally:
        await runtime.stop()


@pytest.mark.asyncio
async def test_python_runtime_manager_integration():
    """Test RuntimeManager orchestrating real PythonRuntime process worker."""
    manager = RuntimeManager()

    # Provision real Python runtime via manager
    rt = await manager.start_runtime(RuntimeType.PYTHON)
    assert isinstance(rt, PythonRuntime)
    assert await rt.is_alive() is True

    # Execute code
    res = await rt.execute_code("print('Hello from RuntimeManager!')")
    assert res["status"] == "ok"
    assert "Hello from RuntimeManager!" in res["stdout"]

    # Terminate all runtimes
    await manager.terminate_all()
    assert (await manager.list_runtimes()) == []
