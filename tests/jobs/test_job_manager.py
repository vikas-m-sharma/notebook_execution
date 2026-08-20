import uuid
import pytest

from app.jobs.enums import ConcurrencyPolicy, JobStatus
from app.jobs.exceptions import JobConcurrencyError, JobValidationError
from app.jobs.manager import JobManager
from app.models.notebook import Notebook
from app.models.project import Project
from app.models.workspace import Workspace


@pytest.mark.asyncio
async def test_job_manager_crud_pause_resume_trigger(db_session):
    """Test JobManager creation, pause/resume, manual execution trigger, and execution history persistence."""
    ws = Workspace(name="WS-JM")
    db_session.add(ws)
    await db_session.flush()

    proj = Project(name="PROJ-JM", workspace_id=ws.id)
    db_session.add(proj)
    await db_session.flush()

    nb = Notebook(name="NB-JM", project_id=proj.id)
    db_session.add(nb)
    await db_session.flush()

    manager = JobManager(db_session)

    # 1. Create job
    job = await manager.create_job(
        name="jm-analytics-job",
        notebook_id=nb.id,
        workspace_id=ws.id,
        project_id=proj.id,
        description="Analytics job",
        schedule_type="CRON",
        cron_expression="0 2 * * *",
        tz_name="UTC",
        concurrency_policy="PREVENT_OVERLAP",
    )
    assert job.name == "jm-analytics-job"
    assert job.status == JobStatus.ACTIVE.value
    assert job.next_run_at is not None

    # 2. Pause & Resume
    paused = await manager.pause_job(job.id)
    assert paused.status == JobStatus.PAUSED.value
    assert paused.next_run_at is None

    resumed = await manager.resume_job(job.id)
    assert resumed.status == JobStatus.ACTIVE.value
    assert resumed.next_run_at is not None

    # 3. Trigger manual execution
    exec_history = await manager.trigger_job_execution(job.id, trigger_type="MANUAL")
    assert exec_history.job_id == job.id
    assert exec_history.trigger_type == "MANUAL"
    assert exec_history.execution_id.startswith("exec-")

    # 4. Attempt second execution under PREVENT_OVERLAP policy
    with pytest.raises(JobConcurrencyError):
        await manager.trigger_job_execution(job.id, trigger_type="MANUAL")

    # 5. List job execution history
    history_records = await manager.list_job_executions(job.id)
    assert len(history_records) == 1
    assert history_records[0].execution_id == exec_history.execution_id
