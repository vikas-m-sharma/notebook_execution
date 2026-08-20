import uuid
import pytest

from app.models.notebook import Notebook
from app.models.project import Project
from app.models.workspace import Workspace
from app.repositories.job import JobExecutionRepository, JobRepository


@pytest.mark.asyncio
async def test_job_repository_crud(db_session):
    """Test JobRepository creation, retrieval, filtering, updating, and deletion."""
    # Create parent hierarchy
    ws = Workspace(name="WS-Jobs")
    db_session.add(ws)
    await db_session.flush()

    proj = Project(name="PROJ-Jobs", workspace_id=ws.id)
    db_session.add(proj)
    await db_session.flush()

    nb = Notebook(name="NB-Jobs", project_id=proj.id)
    db_session.add(nb)
    await db_session.flush()

    repo = JobRepository(db_session)

    # 1. Create job
    job = await repo.create(
        name="job-sales-report",
        notebook_id=nb.id,
        workspace_id=ws.id,
        project_id=proj.id,
        description="Daily sales summary report",
        schedule_type="CRON",
        cron_expression="0 2 * * *",
        timezone="Asia/Kolkata",
    )
    assert job.name == "job-sales-report"
    assert job.status == "ACTIVE"

    # 2. Get by ID and Name
    by_id = await repo.get_by_id(job.id)
    assert by_id is not None
    assert by_id.name == "job-sales-report"

    by_name = await repo.get_by_name("job-sales-report")
    assert by_name is not None

    # 3. List all
    all_jobs = await repo.list_all(workspace_id=ws.id)
    assert len(all_jobs) == 1

    # 4. Update status
    updated = await repo.update_status(job.id, "PAUSED")
    assert updated.status == "PAUSED"

    # 5. Delete job
    deleted = await repo.delete(job.id)
    assert deleted is True


@pytest.mark.asyncio
async def test_job_execution_repository_crud(db_session):
    """Test JobExecutionRepository history recording and updates."""
    job_id = uuid.uuid4()
    exec_id = "exec-test-123"

    repo = JobExecutionRepository(db_session)
    history = await repo.create(
        job_id=job_id,
        execution_id=exec_id,
        trigger_type="MANUAL",
        status="RUNNING",
    )
    assert history.execution_id == exec_id
    assert history.status == "RUNNING"

    # List history
    history_list = await repo.list_by_job_id(job_id)
    assert len(history_list) == 1

    # Update status
    updated = await repo.update_status(
        execution_id=exec_id,
        status="SUCCESS",
        duration_ms=150.0,
    )
    assert updated.status == "SUCCESS"
    assert updated.duration_ms == 150.0
