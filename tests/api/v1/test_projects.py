import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_project_api_crud(async_client: AsyncClient, db_session):
    """Test full Project API CRUD lifecycle via HTTP endpoints."""
    # 1. Create Workspace
    ws_resp = await async_client.post("/api/v1/workspaces", json={"name": "Project Parent WS"})
    ws_id = ws_resp.json()["id"]

    # 2. Create Project
    proj_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects",
        json={"name": "ML Pipelines", "description": "Machine learning pipelines"},
    )
    assert proj_resp.status_code == 201
    proj_data = proj_resp.json()
    proj_id = proj_data["id"]
    assert proj_data["workspace_id"] == ws_id
    assert proj_data["name"] == "ML Pipelines"

    # 3. Get Project
    get_resp = await async_client.get(f"/api/v1/projects/{proj_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "ML Pipelines"

    # 4. List Projects in Workspace
    list_resp = await async_client.get(f"/api/v1/workspaces/{ws_id}/projects")
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 1

    # 5. Patch Project
    patch_resp = await async_client.patch(
        f"/api/v1/projects/{proj_id}",
        json={"name": "Renamed ML Pipelines"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["name"] == "Renamed ML Pipelines"

    # 6. Delete Project
    del_resp = await async_client.delete(f"/api/v1/projects/{proj_id}")
    assert del_resp.status_code == 204

    # 7. Verify 404
    assert (await async_client.get(f"/api/v1/projects/{proj_id}")).status_code == 404


@pytest.mark.asyncio
async def test_project_api_negative_cases(async_client: AsyncClient, db_session):
    """Test negative cases: 404 missing workspace, 409 duplicate project name in workspace."""
    fake_ws_id = str(uuid.uuid4())
    # 404 for creation in non-existent workspace
    resp_404 = await async_client.post(
        f"/api/v1/workspaces/{fake_ws_id}/projects",
        json={"name": "Orphan Project"},
    )
    assert resp_404.status_code == 404

    # Create workspace and project
    ws_resp = await async_client.post("/api/v1/workspaces", json={"name": "WS Unique Proj"})
    ws_id = ws_resp.json()["id"]
    await async_client.post(f"/api/v1/workspaces/{ws_id}/projects", json={"name": "Dup Project"})

    # 409 for duplicate project name in same workspace
    resp_409 = await async_client.post(f"/api/v1/workspaces/{ws_id}/projects", json={"name": "Dup Project"})
    assert resp_409.status_code == 409
