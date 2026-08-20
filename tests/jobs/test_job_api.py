import pytest
from httpx import AsyncClient

from app.models.notebook import Notebook
from app.models.project import Project
from app.models.workspace import Workspace


@pytest.mark.asyncio
async def test_job_api_endpoints(async_client: AsyncClient, db_session):
    """Test REST API endpoints for Job management, manual triggers, pause/resume, and execution history."""
    ws = Workspace(name="WS-JobAPI")
    db_session.add(ws)
    await db_session.flush()

    proj = Project(name="PROJ-JobAPI", workspace_id=ws.id)
    db_session.add(proj)
    await db_session.flush()

    nb = Notebook(name="NB-JobAPI", project_id=proj.id)
    db_session.add(nb)
    await db_session.flush()
    await db_session.commit()

    # 1. POST /jobs — Create job
    create_payload = {
        "name": "daily-etl-pipeline",
        "notebook_id": str(nb.id),
        "workspace_id": str(ws.id),
        "project_id": str(proj.id),
        "description": "Daily ETL data pipeline job",
        "schedule_type": "CRON",
        "cron_expression": "0 1 * * *",
        "timezone": "Asia/Kolkata",
        "concurrency_policy": "PREVENT_OVERLAP",
        "max_retries": 2,
        "retry_delay_seconds": 30,
        "parameters": {"env": "production"},
    }
    res1 = await async_client.post("/api/v1/jobs", json=create_payload)
    assert res1.status_code == 201
    job_data = res1.json()
    assert job_data["name"] == "daily-etl-pipeline"
    job_id = job_data["id"]

    # 2. GET /jobs — List jobs
    res2 = await async_client.get("/api/v1/jobs")
    assert res2.status_code == 200
    assert res2.json()["total"] >= 1

    # 3. GET /jobs/{job_id} — Get job details
    res3 = await async_client.get(f"/api/v1/jobs/{job_id}")
    assert res3.status_code == 200
    assert res3.json()["id"] == job_id

    # 4. POST /jobs/{job_id}/run — Trigger manual run
    res_run = await async_client.post(f"/api/v1/jobs/{job_id}/run")
    assert res_run.status_code == 200
    history_data = res_run.json()
    assert history_data["job_id"] == job_id
    assert history_data["trigger_type"] == "MANUAL"

    # 5. GET /jobs/{job_id}/executions — List execution history
    res_execs = await async_client.get(f"/api/v1/jobs/{job_id}/executions")
    assert res_execs.status_code == 200
    assert res_execs.json()["total"] == 1

    # 6. POST /jobs/{job_id}/pause
    res_pause = await async_client.post(f"/api/v1/jobs/{job_id}/pause")
    assert res_pause.status_code == 200
    assert res_pause.json()["status"] == "PAUSED"

    # 7. POST /jobs/{job_id}/resume
    res_resume = await async_client.post(f"/api/v1/jobs/{job_id}/resume")
    assert res_resume.status_code == 200
    assert res_resume.json()["status"] == "ACTIVE"

    # 8. DELETE /jobs/{job_id}
    res_del = await async_client.delete(f"/api/v1/jobs/{job_id}")
    assert res_del.status_code == 204
