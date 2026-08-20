import uuid
from datetime import datetime
from typing import Any, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job, JobExecution


class JobRepository:
    """Async repository for Job definition persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        name: str,
        notebook_id: uuid.UUID,
        workspace_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
        description: Optional[str] = None,
        schedule_type: str = "ONE_TIME",
        cron_expression: Optional[str] = None,
        timezone: str = "UTC",
        concurrency_policy: str = "PREVENT_OVERLAP",
        max_retries: int = 0,
        retry_delay_seconds: int = 60,
        parameters: Optional[dict[str, Any]] = None,
        status: str = "ACTIVE",
        next_run_at: Optional[datetime] = None,
    ) -> Job:
        """Create a new Job definition."""
        job = Job(
            name=name,
            notebook_id=notebook_id,
            workspace_id=workspace_id,
            project_id=project_id,
            description=description,
            schedule_type=schedule_type,
            cron_expression=cron_expression,
            timezone=timezone,
            concurrency_policy=concurrency_policy,
            max_retries=max_retries,
            retry_delay_seconds=retry_delay_seconds,
            parameters=parameters or {},
            status=status,
            next_run_at=next_run_at,
        )
        self.session.add(job)
        await self.session.flush()
        await self.session.refresh(job)
        return job

    async def get_by_id(self, job_id: uuid.UUID) -> Optional[Job]:
        """Retrieve a Job by UUID."""
        stmt = select(Job).where(Job.id == job_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Job]:
        """Retrieve a Job by unique string name."""
        stmt = select(Job).where(Job.name == name)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_all(
        self,
        workspace_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
        notebook_id: Optional[uuid.UUID] = None,
    ) -> Sequence[Job]:
        """List all Jobs optionally filtered by workspace, project, or notebook."""
        stmt = select(Job)
        if workspace_id:
            stmt = stmt.where(Job.workspace_id == workspace_id)
        if project_id:
            stmt = stmt.where(Job.project_id == project_id)
        if notebook_id:
            stmt = stmt.where(Job.notebook_id == notebook_id)

        stmt = stmt.order_by(Job.name.asc())
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def list_due_jobs(self, current_time: datetime) -> Sequence[Job]:
        """List ACTIVE jobs whose next_run_at timestamp is due (<= current_time)."""
        stmt = (
            select(Job)
            .where(Job.status == "ACTIVE")
            .where(Job.next_run_at.isnot(None))
            .where(Job.next_run_at <= current_time)
        )
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def update(
        self,
        job_id: uuid.UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        schedule_type: Optional[str] = None,
        cron_expression: Optional[str] = None,
        timezone: Optional[str] = None,
        concurrency_policy: Optional[str] = None,
        max_retries: Optional[int] = None,
        retry_delay_seconds: Optional[int] = None,
        parameters: Optional[dict[str, Any]] = None,
        status: Optional[str] = None,
        next_run_at: Optional[datetime] = None,
        last_run_at: Optional[datetime] = None,
        clear_next_run: bool = False,
    ) -> Optional[Job]:
        """Update Job properties."""
        job = await self.get_by_id(job_id)
        if not job:
            return None
        if name is not None:
            job.name = name
        if description is not None:
            job.description = description
        if schedule_type is not None:
            job.schedule_type = schedule_type
        if cron_expression is not None:
            job.cron_expression = cron_expression
        if timezone is not None:
            job.timezone = timezone
        if concurrency_policy is not None:
            job.concurrency_policy = concurrency_policy
        if max_retries is not None:
            job.max_retries = max_retries
        if retry_delay_seconds is not None:
            job.retry_delay_seconds = retry_delay_seconds
        if parameters is not None:
            job.parameters = parameters
        if status is not None:
            job.status = status
        if clear_next_run:
            job.next_run_at = None
        elif next_run_at is not None:
            job.next_run_at = next_run_at
        if last_run_at is not None:
            job.last_run_at = last_run_at

        await self.session.flush()
        await self.session.refresh(job)
        return job

    async def update_status(self, job_id: uuid.UUID, status: str) -> Optional[Job]:
        """Update job status lifecycle."""
        return await self.update(job_id, status=status)

    async def delete(self, job_id: uuid.UUID) -> bool:
        """Delete Job definition record."""
        job = await self.get_by_id(job_id)
        if not job:
            return False
        await self.session.delete(job)
        await self.session.flush()
        return True


class JobExecutionRepository:
    """Async repository for Job execution history records."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        job_id: uuid.UUID,
        execution_id: str,
        trigger_type: str = "MANUAL",
        status: str = "QUEUED",
        started_at: Optional[datetime] = None,
    ) -> JobExecution:
        """Create a new JobExecution history record."""
        exec_record = JobExecution(
            job_id=job_id,
            execution_id=execution_id,
            trigger_type=trigger_type,
            status=status,
            started_at=started_at or datetime.now(),
        )
        self.session.add(exec_record)
        await self.session.flush()
        await self.session.refresh(exec_record)
        return exec_record

    async def get_by_id(self, history_id: uuid.UUID) -> Optional[JobExecution]:
        """Retrieve JobExecution history by UUID."""
        stmt = select(JobExecution).where(JobExecution.id == history_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_execution_id(self, execution_id: str) -> Optional[JobExecution]:
        """Retrieve JobExecution history by execution_id string."""
        stmt = select(JobExecution).where(JobExecution.execution_id == execution_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_by_job_id(self, job_id: uuid.UUID) -> Sequence[JobExecution]:
        """List execution history records for a given job ordered by created_at descending."""
        stmt = (
            select(JobExecution)
            .where(JobExecution.job_id == job_id)
            .order_by(JobExecution.created_at.desc())
        )
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def update_status(
        self,
        execution_id: str,
        status: str,
        finished_at: Optional[datetime] = None,
        duration_ms: Optional[float] = None,
        error_message: Optional[str] = None,
        retry_count: Optional[int] = None,
    ) -> Optional[JobExecution]:
        """Update execution history status and timing details."""
        rec = await self.get_by_execution_id(execution_id)
        if not rec:
            return None

        rec.status = status
        if finished_at is not None:
            rec.finished_at = finished_at
        if duration_ms is not None:
            rec.duration_ms = duration_ms
        if error_message is not None:
            rec.error_message = error_message
        if retry_count is not None:
            rec.retry_count = retry_count

        await self.session.flush()
        await self.session.refresh(rec)
        return rec
