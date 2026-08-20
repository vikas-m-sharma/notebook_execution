import asyncio
import multiprocessing as mp
import time
import uuid
from typing import Any, Optional

from app.runtime.base import BaseRuntime
from app.runtime.config import RuntimeConfig
from app.runtime.enums import RuntimeStatus, RuntimeType
from app.runtime.exceptions import (
    RuntimeAlreadyRunningError,
    RuntimeStartupError,
)
from app.runtime.python_worker import run_python_worker


class PythonRuntime(BaseRuntime):
    """Isolated Python process execution runtime implementing BaseRuntime contract."""

    def __init__(
        self,
        config: RuntimeConfig | None = None,
        runtime_id: uuid.UUID | None = None,
    ) -> None:
        super().__init__(
            runtime_type=RuntimeType.PYTHON,
            config=config,
            runtime_id=runtime_id,
        )
        self._process: Optional[mp.Process] = None
        self._parent_conn: Optional[Any] = None
        self._child_conn: Optional[Any] = None

    async def start(self) -> None:
        """Spawn dedicated child Python worker process and establish IPC connection."""
        if self._process is not None and self._process.is_alive():
            raise RuntimeAlreadyRunningError(self.runtime_id)

        self.status = RuntimeStatus.STARTING

        try:
            ctx = mp.get_context("spawn")
            self._parent_conn, self._child_conn = ctx.Pipe()

            self._process = ctx.Process(
                target=run_python_worker,
                args=(self._child_conn,),
                name=f"python_worker_{self.runtime_id}",
                daemon=True,
            )
            self._process.start()

            # Poll briefly for worker process startup
            for _ in range(50):
                if self._process.is_alive():
                    break
                await asyncio.sleep(0.02)

            if not self._process.is_alive():
                raise RuntimeStartupError(self.runtime_id, "Worker process exited immediately.")

            self.status = RuntimeStatus.RUNNING
        except Exception as exc:
            self.status = RuntimeStatus.FAILED
            if self._process and self._process.is_alive():
                self._process.terminate()
            raise RuntimeStartupError(self.runtime_id, str(exc)) from exc

    async def execute_code(
        self, code: str, timeout: Optional[float] = None
    ) -> dict[str, Any]:
        """Send code execution request to isolated Python worker process via IPC."""
        if not await self.is_alive():
            raise RuntimeError(
                f"Python runtime '{self.runtime_id}' is not running (status: {self.status})."
            )

        req_id = str(uuid.uuid4())
        exec_timeout = timeout if timeout is not None else float(self.config.timeout_seconds)

        payload = {
            "command": "execute",
            "request_id": req_id,
            "code": code,
        }

        # Send execution payload over IPC
        await asyncio.to_thread(self._parent_conn.send, payload)

        # Await response asynchronously with timeout protection
        start_t = time.time()
        while time.time() - start_t < exec_timeout:
            if not self._process or not self._process.is_alive():
                self.status = RuntimeStatus.FAILED
                raise RuntimeError(
                    f"Python worker process '{self.runtime_id}' died during execution."
                )

            has_data = await asyncio.to_thread(self._parent_conn.poll, 0.05)
            if has_data:
                res = await asyncio.to_thread(self._parent_conn.recv)
                return res

            await asyncio.sleep(0.02)

        # Timeout reached: terminate worker
        self.status = RuntimeStatus.FAILED
        self._process.terminate()
        raise TimeoutError(f"Execution timed out after {exec_timeout} seconds.")

    async def install_packages(
        self, requirements: list[str], timeout: float = 120.0
    ) -> dict[str, Any]:
        """Send package installation request to child worker process via IPC."""
        if not await self.is_alive():
            raise RuntimeError(
                f"Python runtime '{self.runtime_id}' is not running (status: {self.status})."
            )

        req_id = str(uuid.uuid4())
        payload = {
            "command": "install_packages",
            "request_id": req_id,
            "requirements": requirements,
            "timeout": timeout,
        }

        await asyncio.to_thread(self._parent_conn.send, payload)

        start_t = time.time()
        while time.time() - start_t < (timeout + 5.0):
            if not self._process or not self._process.is_alive():
                self.status = RuntimeStatus.FAILED
                raise RuntimeError(f"Python worker process '{self.runtime_id}' died during package installation.")

            has_data = await asyncio.to_thread(self._parent_conn.poll, 0.05)
            if has_data:
                res = await asyncio.to_thread(self._parent_conn.recv)
                return res

            await asyncio.sleep(0.02)

        self.status = RuntimeStatus.FAILED
        self._process.terminate()
        raise TimeoutError(f"Package installation timed out after {timeout} seconds.")

    async def verify_packages(
        self, packages: list[dict[str, str]]
    ) -> dict[str, Any]:
        """Send package verification request to child worker process via IPC."""
        if not await self.is_alive():
            raise RuntimeError(
                f"Python runtime '{self.runtime_id}' is not running (status: {self.status})."
            )

        req_id = str(uuid.uuid4())
        payload = {
            "command": "verify_packages",
            "request_id": req_id,
            "packages": packages,
        }

        await asyncio.to_thread(self._parent_conn.send, payload)

        start_t = time.time()
        while time.time() - start_t < 10.0:
            if not self._process or not self._process.is_alive():
                self.status = RuntimeStatus.FAILED
                raise RuntimeError(f"Python worker process '{self.runtime_id}' died during package verification.")

            has_data = await asyncio.to_thread(self._parent_conn.poll, 0.05)
            if has_data:
                res = await asyncio.to_thread(self._parent_conn.recv)
                return res

            await asyncio.sleep(0.02)

        raise TimeoutError("Package verification timed out.")

    async def stop(self) -> None:
        """Orchestrate graceful shutdown of the child worker process."""
        if self.status in (RuntimeStatus.TERMINATING, RuntimeStatus.TERMINATED):
            return

        self.status = RuntimeStatus.TERMINATING

        if self._parent_conn and self._process and self._process.is_alive():
            try:
                await asyncio.to_thread(self._parent_conn.send, {"command": "stop"})
                await asyncio.to_thread(self._process.join, timeout=1.0)
            except Exception:
                pass

        if self._process and self._process.is_alive():
            self._process.terminate()
            await asyncio.to_thread(self._process.join, timeout=0.5)

        if self._parent_conn:
            try:
                self._parent_conn.close()
            except Exception:
                pass

        if self._child_conn:
            try:
                self._child_conn.close()
            except Exception:
                pass

        self.status = RuntimeStatus.TERMINATED
