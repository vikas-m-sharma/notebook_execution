import uuid
from typing import Sequence

from app.runtime.base import BaseRuntime
from app.runtime.config import RuntimeConfig
from app.runtime.enums import RuntimeStatus, RuntimeType
from app.runtime.exceptions import (
    RuntimeAlreadyRunningError,
    RuntimeNotFoundError,
    RuntimeStartupError,
)
from app.runtime.factory import RuntimeFactory


class RuntimeManager:
    """Orchestrator for managing runtime instances, lifecycle transitions, and active registry."""

    def __init__(self) -> None:
        self._runtimes: dict[uuid.UUID, BaseRuntime] = {}

    async def start_runtime(
        self,
        runtime_type: RuntimeType | str = RuntimeType.PYTHON,
        config: RuntimeConfig | None = None,
        runtime_id: uuid.UUID | None = None,
    ) -> BaseRuntime:
        """Provision, select, and orchestrate the startup of a new execution runtime."""
        target_id = runtime_id or uuid.uuid4()
        if target_id in self._runtimes:
            existing = self._runtimes[target_id]
            if await existing.is_alive():
                raise RuntimeAlreadyRunningError(target_id)

        runtime = RuntimeFactory.create_runtime(
            runtime_type=runtime_type,
            config=config,
            runtime_id=target_id,
        )

        try:
            await runtime.start()
        except Exception as exc:
            runtime.status = RuntimeStatus.FAILED
            self._runtimes[target_id] = runtime
            raise RuntimeStartupError(target_id, str(exc)) from exc

        self._runtimes[target_id] = runtime
        return runtime

    async def get_runtime(self, runtime_id: uuid.UUID) -> BaseRuntime:
        """Retrieve an active runtime instance by UUID or raise RuntimeNotFoundError."""
        runtime = self._runtimes.get(runtime_id)
        if runtime is None:
            raise RuntimeNotFoundError(runtime_id)
        return runtime

    async def list_runtimes(
        self, runtime_type: RuntimeType | str | None = None
    ) -> Sequence[BaseRuntime]:
        """List all active runtime instances, optionally filtered by RuntimeType."""
        runtimes = list(self._runtimes.values())
        if runtime_type is not None:
            t_enum = RuntimeType(runtime_type) if isinstance(runtime_type, str) else runtime_type
            runtimes = [r for r in runtimes if r.runtime_type == t_enum]
        return runtimes

    async def stop_runtime(self, runtime_id: uuid.UUID) -> BaseRuntime:
        """Orchestrate graceful shutdown of an active runtime instance."""
        runtime = await self.get_runtime(runtime_id)
        await runtime.stop()
        return runtime

    async def terminate_all(self) -> None:
        """Orchestrate bulk shutdown of all active runtime instances."""
        for runtime in list(self._runtimes.values()):
            if runtime.status in (RuntimeStatus.STARTING, RuntimeStatus.RUNNING):
                await runtime.stop()
        self._runtimes.clear()
