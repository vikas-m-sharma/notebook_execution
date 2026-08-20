import uuid
import pytest
from httpx import AsyncClient

from app.models.dependency import DependencyOperation
from app.models.notebook import Notebook
from app.models.project import Project
from app.models.workspace import Workspace


@pytest.mark.asyncio
async def test_dependency_api_crud_and_operations(async_client: AsyncClient, db_session):
    """Test REST API endpoints for notebook dependency CRUD and operation status retrieval."""
    # Seed DB hierarchy
    ws = Workspace(name="API Dep WS")
    db_session.add(ws)
    await db_session.flush()

    proj = Project(workspace_id=ws.id, name="API Dep Proj")
    db_session.add(proj)
    await db_session.flush()

    nb = Notebook(project_id=proj.id, name="API Dep Notebook")
    db_session.add(nb)
    await db_session.commit()

    # 1. POST /notebooks/{notebook_id}/dependencies — Create dependency
    payload = {"package_name": "requests", "version_specifier": ">=2.31"}
    res1 = await async_client.post(f"/api/v1/notebooks/{nb.id}/dependencies", json=payload)
    assert res1.status_code == 201
    dep_data = res1.json()
    assert dep_data["package_name"] == "requests"
    assert dep_data["version_specifier"] == ">=2.31"
    dep_id = dep_data["id"]

    # 2. GET /notebooks/{notebook_id}/dependencies — List dependencies
    res2 = await async_client.get(f"/api/v1/notebooks/{nb.id}/dependencies")
    assert res2.status_code == 200
    list_data = res2.json()
    assert list_data["total"] == 1
    assert list_data["items"][0]["id"] == dep_id

    # 3. PATCH /notebooks/{notebook_id}/dependencies/{dependency_id} — Update dependency
    res3 = await async_client.patch(
        f"/api/v1/notebooks/{nb.id}/dependencies/{dep_id}",
        json={"version_specifier": "==2.31.0"},
    )
    assert res3.status_code == 200
    assert res3.json()["version_specifier"] == "==2.31.0"

    # 4. POST with invalid package name — 400 Bad Request
    res_bad = await async_client.post(
        f"/api/v1/notebooks/{nb.id}/dependencies",
        json={"package_name": "pandas; rm -rf /"},
    )
    assert res_bad.status_code == 400

    # 5. GET /dependency-operations/{operation_id}
    op_id = "op-api-test-999"
    op_rec = DependencyOperation(
        operation_id=op_id,
        notebook_id=nb.id,
        status="READY",
        packages=[{"package_name": "requests", "version_specifier": "==2.31.0"}],
        resolved_versions={"requests": "2.31.0"},
    )
    db_session.add(op_rec)
    await db_session.commit()

    res_op = await async_client.get(f"/api/v1/dependency-operations/{op_id}")
    assert res_op.status_code == 200
    op_data = res_op.json()
    assert op_data["operation_id"] == op_id
    assert op_data["status"] == "READY"
    assert op_data["resolved_versions"] == {"requests": "2.31.0"}

    # 6. DELETE /notebooks/{notebook_id}/dependencies/{dependency_id}
    res_del = await async_client.delete(f"/api/v1/notebooks/{nb.id}/dependencies/{dep_id}")
    assert res_del.status_code == 204
