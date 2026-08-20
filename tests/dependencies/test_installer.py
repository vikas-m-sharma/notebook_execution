import pytest

from app.runtime.python_runtime import PythonRuntime


@pytest.mark.asyncio
async def test_python_runtime_package_verification_and_installation():
    """Test package verification and installation inside isolated PythonRuntime worker process."""
    runtime = PythonRuntime()
    await runtime.start()

    try:
        # 1. Verify standard built-in / installed package (e.g. pytest or sys/pip)
        verify_res = await runtime.verify_packages([{"package_name": "pytest"}])
        assert verify_res.get("status") == "ok"
        assert verify_res.get("satisfied") is True

        # 2. Execute code using installed package in worker process
        exec_res = await runtime.execute_code("import pytest; print(pytest.__name__)")
        assert exec_res.get("status") == "ok"
        assert "pytest" in exec_res.get("stdout")

        # 3. Nonexistent package installation attempt
        install_res = await runtime.install_packages(["nonexistent-package-xyz1239999"], timeout=10.0)
        assert install_res.get("status") == "error"

    finally:
        await runtime.stop()
