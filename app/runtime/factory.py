import uuid
from typing import Type

from app.runtime.base import BaseRuntime
from app.runtime.config import RuntimeConfig
from app.runtime.enums import RuntimeStatus, RuntimeType
from app.runtime.exceptions import UnsupportedRuntimeTypeError
from app.runtime.python_runtime import PythonRuntime


class SQLRuntimeStub(BaseRuntime):
    """Phase 4 architectural extension point for SQL runtime lifecycle orchestration."""

    def __init__(
        self,
        config: RuntimeConfig | None = None,
        runtime_id: uuid.UUID | None = None,
    ) -> None:
        super().__init__(
            runtime_type=RuntimeType.SQL,
            config=config,
            runtime_id=runtime_id,
        )

    async def start(self) -> None:
        self.status = RuntimeStatus.STARTING
        # SQL engine connection startup sequence
        self.status = RuntimeStatus.RUNNING

    async def stop(self) -> None:
        self.status = RuntimeStatus.TERMINATING
        # SQL engine connection shutdown sequence
        self.status = RuntimeStatus.TERMINATED


class RuntimeFactory:
    """Factory responsible for instantiating execution runtimes based on RuntimeType."""

    _registry: dict[RuntimeType, Type[BaseRuntime]] = {
        RuntimeType.PYTHON: PythonRuntime,
        RuntimeType.SQL: SQLRuntimeStub,
    }

    @classmethod
    def create_runtime(
        cls,
        runtime_type: RuntimeType | str,
        config: RuntimeConfig | None = None,
        runtime_id: uuid.UUID | None = None,
    ) -> BaseRuntime:
        """Instantiate a runtime instance for the specified RuntimeType."""
        try:
            r_type = RuntimeType(runtime_type) if isinstance(runtime_type, str) else runtime_type
        except ValueError as exc:
            raise UnsupportedRuntimeTypeError(str(runtime_type)) from exc

        runtime_class = cls._registry.get(r_type)
        if runtime_class is None:
            raise UnsupportedRuntimeTypeError(str(r_type))

        return runtime_class(config=config, runtime_id=runtime_id)
