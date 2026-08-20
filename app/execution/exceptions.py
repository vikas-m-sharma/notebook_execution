class ExecutionManagerError(Exception):
    """Base exception for Execution Manager errors."""

    pass


class ExecutionTaskNotFoundError(ExecutionManagerError):
    """Raised when an execution task is not found in the registry."""

    def __init__(self, execution_id: str) -> None:
        self.execution_id = execution_id
        super().__init__(f"Execution task '{execution_id}' not found.")


class InvalidExecutionStateError(ExecutionManagerError):
    """Raised when an operation is invalid for the execution task's current state."""

    def __init__(self, execution_id: str, current_status: str, action: str) -> None:
        self.execution_id = execution_id
        self.current_status = current_status
        self.action = action
        super().__init__(
            f"Cannot perform '{action}' on execution '{execution_id}' in state '{current_status}'."
        )


class ExecutionTimeoutError(ExecutionManagerError):
    """Raised when cell execution exceeds configured timeout."""

    def __init__(self, execution_id: str, timeout_seconds: float) -> None:
        self.execution_id = execution_id
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"Execution '{execution_id}' timed out after {timeout_seconds} seconds."
        )


class ExecutionCancelledError(ExecutionManagerError):
    """Raised when cell execution is cancelled."""

    def __init__(self, execution_id: str) -> None:
        self.execution_id = execution_id
        super().__init__(f"Execution '{execution_id}' was cancelled.")
