class JobError(Exception):
    """Base exception for all Job Manager operations."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class JobNotFoundError(JobError):
    """Raised when a requested Job ID does not exist."""

    def __init__(self, job_id: str) -> None:
        super().__init__(f"Job '{job_id}' not found.")
        self.job_id = job_id


class JobValidationError(JobError):
    """Raised when job configuration, parameters, or workspace/project/notebook hierarchy is invalid."""

    def __init__(self, details: str) -> None:
        super().__init__(f"Job validation failed: {details}")
        self.details = details


class ScheduleValidationError(JobError):
    """Raised when cron expression or timezone specification is invalid."""

    def __init__(self, details: str) -> None:
        super().__init__(f"Schedule validation failed: {details}")
        self.details = details


class JobExecutionError(JobError):
    """Raised when job execution initiation or orchestration fails."""

    def __init__(self, job_id: str, details: str) -> None:
        super().__init__(f"Execution failed for job '{job_id}': {details}")
        self.job_id = job_id
        self.details = details


class JobConcurrencyError(JobError):
    """Raised when job execution violates the PREVENT_OVERLAP concurrency policy."""

    def __init__(self, job_id: str) -> None:
        super().__init__(f"Job '{job_id}' is already running and PREVENT_OVERLAP concurrency policy is active.")
        self.job_id = job_id


class JobCancellationError(JobError):
    """Raised when job execution cancellation request fails."""

    def __init__(self, job_id: str, details: str) -> None:
        super().__init__(f"Failed to cancel job '{job_id}': {details}")
        self.job_id = job_id
        self.details = details
