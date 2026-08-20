from enum import Enum


class JobStatus(str, Enum):
    """Lifecycle status for a scheduled or manual Job definition."""

    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    DISABLED = "DISABLED"
    ERROR = "ERROR"


class JobExecutionStatus(str, Enum):
    """Execution status for a Job execution run."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"


class ScheduleType(str, Enum):
    """Scheduling strategy for a job."""

    ONE_TIME = "ONE_TIME"
    CRON = "CRON"


class TriggerType(str, Enum):
    """Source trigger of a job execution."""

    MANUAL = "MANUAL"
    SCHEDULED = "SCHEDULED"


class ConcurrencyPolicy(str, Enum):
    """Policy for handling concurrent executions of the same job."""

    ALLOW_CONCURRENT = "ALLOW_CONCURRENT"
    PREVENT_OVERLAP = "PREVENT_OVERLAP"
