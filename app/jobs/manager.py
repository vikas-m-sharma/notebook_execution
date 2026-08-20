import uuid
from datetime import datetime, timezone
from typing import Any, Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.execution import ExecutionManager
from app.jobs.enums import (
    ConcurrencyPolicy,
    JobExecutionStatus,
    JobStatus,
    ScheduleType,
    TriggerType,
)
from app.jobs.exceptions import (
    JobCancellationError,
    JobConcurrencyError,
    JobError,
    JobExecutionError,
    JobNotFoundError,
    JobValidationError,
    ScheduleValidationError,
)
from app.jobs.schedule_utils import calculate_next_run, validate_cron_expression, validate_timezone
from app.models.job import Job, JobExecution
from app.repositories.job import JobExecutionRepository, JobRepository
from app.repositories.notebook import NotebookRepository
from app.repositories.notebook_cell import NotebookCellRepository


class JobManager:
    """Manager orchestrating Job CRUD, schedule calculation, manual/scheduled trigger execution, and execution history."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.job_repo = JobRepository(db)
        self.history_repo = JobExecutionRepository(db)
        self.notebook_repo = NotebookRepository(db)
        self.cell_repo = NotebookCellRepository(db)
        self.exec_manager = ExecutionManager()

    async def create_job(
        self,
        name: str,
        notebook_id: uuid.UUID,
        workspace_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
        description: Optional[str] = None,
        schedule_type: str = ScheduleType.ONE_TIME.value,
        cron_expression: Optional[str] = None,
        tz_name: str = "UTC",
        concurrency_policy: str = ConcurrencyPolicy.PREVENT_OVERLAP.value,
        max_retries: int = 0,
        retry_delay_seconds: int = 60,
        parameters: Optional[dict[str, Any]] = None,
    ) -> Job:
        """Validate and create a new Job definition."""
        # 1. Validate notebook exists
        nb = await self.notebook_repo.get_by_id(notebook_id)
        if not nb:
            raise JobValidationError(f"Notebook '{notebook_id}' does not exist.")

        # 2. Validate timezone
        if not validate_timezone(tz_name):
            raise ScheduleValidationError(f"Invalid timezone identifier '{tz_name}'.")

        # 3. Validate schedule type & cron syntax
        next_run = None
        if schedule_type == ScheduleType.CRON.value:
            if not cron_expression:
                raise ScheduleValidationError("Cron expression is required for CRON schedule type.")
            if not validate_cron_expression(cron_expression):
                raise ScheduleValidationError(f"Invalid 5-field cron expression '{cron_expression}'.")
            next_run = calculate_next_run(cron_expression, tz_name)

        # 4. Check name uniqueness
        existing = await self.job_repo.get_by_name(name)
        if existing:
            raise JobValidationError(f"A job with name '{name}' already exists.")

        # 5. Persist job
        return await self.job_repo.create(
            name=name,
            notebook_id=notebook_id,
            workspace_id=workspace_id or nb.workspace_id,
            project_id=project_id or nb.project_id,
            description=description,
            schedule_type=schedule_type.upper(),
            cron_expression=cron_expression,
            timezone=tz_name,
            concurrency_policy=concurrency_policy.upper(),
            max_retries=max_retries,
            retry_delay_seconds=retry_delay_seconds,
            parameters=parameters or {},
            status=JobStatus.ACTIVE.value,
            next_run_at=next_run,
        )

    async def get_job(self, job_id: uuid.UUID) -> Job:
        """Get job definition by UUID."""
        job = await self.job_repo.get_by_id(job_id)
        if not job:
            raise JobNotFoundError(str(job_id))
        return job

    async def list_jobs(
        self,
        workspace_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
        notebook_id: Optional[uuid.UUID] = None,
    ) -> Sequence[Job]:
        """List jobs filtered by hierarchy."""
        return await self.job_repo.list_all(
            workspace_id=workspace_id,
            project_id=project_id,
            notebook_id=notebook_id,
        )

    async def update_job(
        self,
        job_id: uuid.UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        schedule_type: Optional[str] = None,
        cron_expression: Optional[str] = None,
        tz_name: Optional[str] = None,
        concurrency_policy: Optional[str] = None,
        max_retries: Optional[int] = None,
        retry_delay_seconds: Optional[int] = None,
        parameters: Optional[dict[str, Any]] = None,
    ) -> Job:
        """Update job configuration and recalculate schedule times."""
        job = await self.get_job(job_id)

        target_tz = tz_name or job.timezone
        if not validate_timezone(target_tz):
            raise ScheduleValidationError(f"Invalid timezone identifier '{target_tz}'.")

        target_schedule = schedule_type or job.schedule_type
        target_cron = cron_expression if cron_expression is not None else job.cron_expression

        next_run = job.next_run_at
        if target_schedule == ScheduleType.CRON.value:
            if not target_cron:
                raise ScheduleValidationError("Cron expression is required for CRON schedule type.")
            if not validate_cron_expression(target_cron):
                raise ScheduleValidationError(f"Invalid 5-field cron expression '{target_cron}'.")
            next_run = calculate_next_run(target_cron, target_tz)

        updated = await self.job_repo.update(
            job_id=job_id,
            name=name,
            description=description,
            schedule_type=target_schedule,
            cron_expression=target_cron,
            timezone=target_tz,
            concurrency_policy=concurrency_policy,
            max_retries=max_retries,
            retry_delay_seconds=retry_delay_seconds,
            parameters=parameters,
            next_run_at=next_run,
        )
        return updated  # type: ignore

    async def delete_job(self, job_id: uuid.UUID) -> bool:
        """Delete a job definition."""
        await self.get_job(job_id)
        return await self.job_repo.delete(job_id)

    async def pause_job(self, job_id: uuid.UUID) -> Job:
        """Pause job scheduling."""
        await self.get_job(job_id)
        updated = await self.job_repo.update(
            job_id=job_id,
            status=JobStatus.PAUSED.value,
            clear_next_run=True,
        )
        return updated  # type: ignore

    async def resume_job(self, job_id: uuid.UUID) -> Job:
        """Resume job scheduling and recalculate next run timestamp."""
        job = await self.get_job(job_id)
        next_run = None
        if job.schedule_type == ScheduleType.CRON.value and job.cron_expression:
            next_run = calculate_next_run(job.cron_expression, job.timezone)

        updated = await self.job_repo.update(
            job_id=job_id,
            status=JobStatus.ACTIVE.value,
            next_run_at=next_run,
        )
        return updated  # type: ignore

    async def trigger_job_execution(
        self,
        job_id: uuid.UUID,
        trigger_type: str = TriggerType.MANUAL.value,
    ) -> JobExecution:
        """Trigger job notebook execution via ExecutionManager, enforcing concurrency policies and recording history."""
        job = await self.get_job(job_id)

        if job.status in (JobStatus.PAUSED.value, JobStatus.DISABLED.value):
            raise JobValidationError(f"Cannot trigger job '{job.name}' because it is in state {job.status}.")

        # Enforce PREVENT_OVERLAP concurrency policy
        if job.concurrency_policy == ConcurrencyPolicy.PREVENT_OVERLAP.value:
            history = await self.history_repo.list_by_job_id(job_id)
            for h in history:
                if h.status in (JobExecutionStatus.RUNNING.value, JobExecutionStatus.QUEUED.value):
                    raise JobConcurrencyError(str(job_id))

        # Get or create execution session
        session_id = f"job-{job.id}"
        try:
            await self.exec_manager.session_manager.get_session(session_id)
        except Exception:
            await self.exec_manager.session_manager.create_session(
                notebook_id=job.notebook_id,
                session_id=session_id,
            )

        cells = await self.cell_repo.list_by_notebook(job.notebook_id)
        code_cells = [c for c in cells if c.cell_type == "code"]
        execution_id = f"exec-{uuid.uuid4()}"

        if code_cells:
            for cell in code_cells:
                task = await self.exec_manager.submit_execution({
                    "session_id": session_id,
                    "notebook_id": job.notebook_id,
                    "cell_id": str(cell.id),
                    "code": cell.code_content or "",
                })
                execution_id = task.execution_id
        else:
            task = await self.exec_manager.submit_execution({
                "session_id": session_id,
                "notebook_id": job.notebook_id,
                "code": "# Job execution",
            })
            execution_id = task.execution_id

        # Record JobExecution history
        now = datetime.now(timezone.utc)
        history_rec = await self.history_repo.create(
            job_id=job.id,
            execution_id=execution_id,
            trigger_type=trigger_type,
            status=JobExecutionStatus.RUNNING.value,
            started_at=now,
        )

        await self.job_repo.update(job_id=job.id, last_run_at=now)
        return history_rec

    async def cancel_job_execution(self, job_id: uuid.UUID, execution_id: str) -> JobExecution:
        """Cancel a running job execution run."""
        await self.get_job(job_id)

        try:
            await self.exec_manager.cancel_execution(execution_id)
        except Exception as err:
            raise JobCancellationError(str(job_id), str(err)) from err

        now = datetime.now(timezone.utc)
        updated = await self.history_repo.update_status(
            execution_id=execution_id,
            status=JobExecutionStatus.CANCELLED.value,
            finished_at=now,
        )
        if not updated:
            raise JobNotFoundError(execution_id)
        return updated

    async def list_job_executions(self, job_id: uuid.UUID) -> Sequence[JobExecution]:
        """Retrieve execution history for a job."""
        await self.get_job(job_id)
        return await self.history_repo.list_by_job_id(job_id)
