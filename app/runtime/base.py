import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from app.runtime.config import RuntimeConfig
from app.runtime.enums import RuntimeStatus, RuntimeType


class BaseRuntime(ABC):
    """Abstract base class defining the execution runtime contract."""

    def __init__(
        self,
        runtime_type: RuntimeType,
        config: RuntimeConfig | None = None,
        runtime_id: uuid.UUID | None = None,
    ) -> None:
        self.runtime_id: uuid.UUID = runtime_id or uuid.uuid4()
        self.runtime_type: RuntimeType = runtime_type
        self.config: RuntimeConfig = config or RuntimeConfig()
        self.status: RuntimeStatus = RuntimeStatus.STARTING
        self.created_at: datetime = datetime.now(timezone.utc)
        self.updated_at: datetime = datetime.now(timezone.utc)

    @abstractmethod
    async def start(self) -> None:
        """Orchestrate runtime startup sequence."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Orchestrate runtime graceful shutdown sequence."""
        pass

    async def get_status(self) -> RuntimeStatus:
        """Retrieve current status of the runtime instance."""
        return self.status

    async def is_alive(self) -> bool:
        """Check if the runtime is active and running."""
        return self.status == RuntimeStatus.RUNNING
