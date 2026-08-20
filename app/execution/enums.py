from enum import Enum


class ExecutionStatus(str, Enum):
    """Lifecycle status states of a notebook cell execution."""

    QUEUED = "queued"
    VALIDATING = "validating"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
