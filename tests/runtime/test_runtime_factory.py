import pytest
from app.runtime.enums import RuntimeStatus, RuntimeType
from app.runtime.exceptions import UnsupportedRuntimeTypeError
from app.runtime.factory import RuntimeFactory, SQLRuntimeStub
from app.runtime.python_runtime import PythonRuntime


@pytest.mark.asyncio
async def test_runtime_factory_python_creation():
    """Test RuntimeFactory creating real PythonRuntime instance."""
    runtime = RuntimeFactory.create_runtime(RuntimeType.PYTHON)
    assert isinstance(runtime, PythonRuntime)
    assert runtime.runtime_type == RuntimeType.PYTHON
    assert runtime.status == RuntimeStatus.STARTING

    await runtime.start()
    assert runtime.status == RuntimeStatus.RUNNING
    assert await runtime.is_alive() is True

    await runtime.stop()
    assert runtime.status == RuntimeStatus.TERMINATED
    assert await runtime.is_alive() is False


@pytest.mark.asyncio
async def test_runtime_factory_sql_creation():
    """Test RuntimeFactory creating SQL runtime instance (extension point)."""
    runtime = RuntimeFactory.create_runtime(RuntimeType.SQL)
    assert isinstance(runtime, SQLRuntimeStub)
    assert runtime.runtime_type == RuntimeType.SQL

    await runtime.start()
    assert runtime.status == RuntimeStatus.RUNNING

    await runtime.stop()
    assert runtime.status == RuntimeStatus.TERMINATED


def test_runtime_factory_unsupported_type():
    """Test RuntimeFactory with unsupported runtime type raising UnsupportedRuntimeTypeError."""
    with pytest.raises(UnsupportedRuntimeTypeError):
        RuntimeFactory.create_runtime("unsupported_type")
