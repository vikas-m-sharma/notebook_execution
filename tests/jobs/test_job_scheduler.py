from datetime import datetime, timedelta, timezone
import pytest

from app.jobs.scheduler import JobScheduler
from app.models.notebook import Notebook
from app.models.project import Project
from app.models.workspace import Workspace
from app.repositories.job import JobRepository


@pytest.mark.asyncio
async def test_job_scheduler_due_job_evaluation(db_session):
    """Test JobScheduler evaluating due active jobs and triggering scheduled executions."""
    ws = Workspace(name="WS-Sched")
    db_session.add(ws)
    await db_session.flush()

    proj = Project(name="PROJ-Sched", workspace_id=ws.id)
    db_session.add(proj)
    await db_session.flush()

    nb = Notebook(name="NB-Sched", project_id=proj.id)
    db_session.add(nb)
    await db_session.flush()

    job_repo = JobRepository(db_session)
    now_utc = datetime.now(timezone.utc)
    due_time = now_utc - timedelta(minutes=5)

    # Create due job
    due_job = await job_repo.create(
        name="due-cron-job",
        notebook_id=nb.id,
        workspace_id=ws.id,
        project_id=proj.id,
        schedule_type="CRON",
        cron_expression="*/5 * * * *",
        timezone="UTC",
        status="ACTIVE",
        next_run_at=due_time,
    )
    await db_session.commit()

    job_id = due_job.id
    scheduler = JobScheduler(check_interval_seconds=0.1)
    await scheduler.evaluate_due_jobs(session=db_session)

    # Verify next_run_at was updated to future timestamp
    refreshed = await job_repo.get_by_id(job_id)
    refreshed_next = refreshed.next_run_at if refreshed.next_run_at.tzinfo else refreshed.next_run_at.replace(tzinfo=timezone.utc)
    assert refreshed_next > now_utc
    assert refreshed.last_run_at is not None
