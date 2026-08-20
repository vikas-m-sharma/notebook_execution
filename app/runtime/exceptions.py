import uuid


class RuntimeManagerError(Exception):
    """Base exception for Runtime Manager domain errors."""

    pass


class RuntimeNotFoundError(RuntimeManagerError):
    """Raised when a requested runtime instance is not found."""

    def __init__(self, runtime_id: uuid.UUID) -> None:
        self.runtime_id = runtime_id
        super().__init__(f"Runtime instance '{runtime_id}' not found.")


class RuntimeStartupError(RuntimeManagerError):
    """Raised when a runtime instance fails during startup orchestration."""

    def __init__(self, runtime_id: uuid.UUID, reason: str) -> None:
        self.runtime_id = runtime_id
        self.reason = reason
        super().__init__(f"Failed to start runtime '{runtime_id}': {reason}")


class RuntimeAlreadyRunningError(RuntimeManagerError):
    """Raised when attempting to start a runtime instance that is already running."""

    def __init__(self, runtime_id: uuid.UUID) -> None:
        self.runtime_id = runtime_id
        super().__init__(f"Runtime '{runtime_id}' is already running.")


class UnsupportedRuntimeTypeError(RuntimeManagerError):
    """Raised when requesting an unsupported or un-implemented runtime type."""

    def __init__(self, runtime_type: str) -> None:
        self.runtime_type = runtime_type
        super().__init__(
            f"Unsupported runtime type '{runtime_type}'. Supported types: ['python', 'sql']."
        )
