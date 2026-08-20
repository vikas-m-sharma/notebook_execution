from enum import Enum


class RuntimeType(str, Enum):
    """Execution runtime types supported by the platform."""

    PYTHON = "python"
    SQL = "sql"


class RuntimeStatus(str, Enum):
    """Lifecycle status states of an execution runtime instance."""

    STARTING = "starting"
    RUNNING = "running"
    TERMINATING = "terminating"
    TERMINATED = "terminated"
    FAILED = "failed"
