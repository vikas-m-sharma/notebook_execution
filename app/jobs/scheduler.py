import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_sessionmaker
from app.jobs.schedule_utils import calculate_next_run

logger = logging.getLogger(__name__)


class JobScheduler:
    """Async background task scheduler evaluating active job schedules and triggering executions."""

    def __init__(self, check_interval_seconds: float = 5.0) -> None:
        self.check_interval_seconds = check_interval_seconds
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start the background scheduler evaluation loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"JobScheduler background loop started (interval={self.check_interval_seconds}s).")

    async def stop(self) -> None:
        """Gracefully stop the background scheduler evaluation loop."""
        if not self._running:
            return
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("JobScheduler background loop stopped.")

    async def _run_loop(self) -> None:
        """Evaluation loop checking due jobs periodically."""
        while self._running:
            try:
                await self.evaluate_due_jobs()
            except Exception as exc:
                logger.error(f"Error during JobScheduler evaluation: {exc}", exc_info=True)

            try:
                await asyncio.sleep(self.check_interval_seconds)
            except asyncio.CancelledError:
                break

    async def evaluate_due_jobs(self, session: Optional[AsyncSession] = None) -> None:
        """Query database for due jobs and trigger executions."""
        if session is not None:
            await self._evaluate_session_jobs(session)
        else:
            try:
                session_factory = get_sessionmaker()
                async with session_factory() as db_session:
                    await self._evaluate_session_jobs(db_session)
            except Exception as exc:
                logger.error(f"Error creating DB session for scheduler evaluation: {exc}")

    async def _evaluate_session_jobs(self, session: AsyncSession) -> None:
        """Process due jobs within a given AsyncSession."""
        from app.jobs.enums import TriggerType
        from app.jobs.manager import JobManager
        from app.repositories.job import JobRepository

        try:
            now_utc = datetime.now(timezone.utc)
            job_repo = JobRepository(session)
            due_jobs = await job_repo.list_due_jobs(now_utc)

            if not due_jobs:
                return

            manager = JobManager(session)
            for job in due_jobs:
                logger.info(f"Triggering scheduled execution for job '{job.name}' ({job.id}).")
                try:
                    await manager.trigger_job_execution(
                        job_id=job.id,
                        trigger_type=TriggerType.SCHEDULED.value,
                    )
                    next_run = None
                    if job.schedule_type == "CRON" and job.cron_expression:
                        next_run = calculate_next_run(job.cron_expression, job.timezone, now_utc)

                    await job_repo.update(
                        job_id=job.id,
                        next_run_at=next_run,
                        last_run_at=now_utc,
                    )
                    await session.commit()
                except Exception as err:
                    await session.rollback()
                    logger.error(f"Failed scheduled trigger for job '{job.name}': {err}")

        except Exception as outer_err:
            logger.error(f"Error in _evaluate_session_jobs: {outer_err}")
