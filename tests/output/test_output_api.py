import uuid
import pytest
from httpx import AsyncClient

from app.output.enums import OutputType
from app.repositories.output import ExecutionOutputRepository
from app.schemas.output import OutputEventSchema


@pytest.mark.asyncio
async def test_execution_outputs_api_endpoints(async_client: AsyncClient, db_session):
    """Test HTTP API endpoints: GET /api/v1/executions/{execution_id}/outputs and GET /api/v1/notebooks/{notebook_id}/cells/{cell_id}/outputs."""
    repo = ExecutionOutputRepository(db_session)
    exec_id = "exec-api-test-100"
    cell_id = "cell-api-test-200"
    nb_id = uuid.uuid4()

    # Seed execution outputs in database
    ev1 = OutputEventSchema(
        execution_id=exec_id,
        session_id="session-api",
        notebook_id=None,
        cell_id=cell_id,
        output_type=OutputType.STDOUT,
        content="API test output\n",
        sequence=1,
    )
    await repo.create(ev1)
    await db_session.commit()

    # 1. GET /api/v1/executions/{execution_id}/outputs
    res1 = await async_client.get(f"/api/v1/executions/{exec_id}/outputs")
    assert res1.status_code == 200
    data1 = res1.json()
    assert len(data1) == 1
    assert data1[0]["execution_id"] == exec_id
    assert data1[0]["content"] == "API test output\n"
    assert data1[0]["sequence"] == 1

    # 2. GET /api/v1/notebooks/{notebook_id}/cells/{cell_id}/outputs
    res2 = await async_client.get(f"/api/v1/notebooks/{nb_id}/cells/{cell_id}/outputs")
    assert res2.status_code == 200
    data2 = res2.json()
    assert len(data2) == 1
    assert data2[0]["cell_id"] == cell_id
    assert data2[0]["content"] == "API test output\n"
