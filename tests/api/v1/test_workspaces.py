import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_workspace_api_crud(async_client: AsyncClient, db_session):
    """Test full Workspace API CRUD lifecycle via HTTP endpoints."""
    # 1. Create Workspace
    create_resp = await async_client.post(
        "/api/v1/workspaces",
        json={"name": "Engineering Workspace", "description": "Backend platform engineering"},
    )
    assert create_resp.status_code == 201
    data = create_resp.json()
    ws_id = data["id"]
    assert data["name"] == "Engineering Workspace"
    assert data["description"] == "Backend platform engineering"

    # 2. Get Workspace
    get_resp = await async_client.get(f"/api/v1/workspaces/{ws_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Engineering Workspace"

    # 3. List Workspaces
    list_resp = await async_client.get("/api/v1/workspaces")
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1

    # 4. Patch Workspace
    patch_resp = await async_client.patch(
        f"/api/v1/workspaces/{ws_id}",
        json={"name": "Renamed Engineering Workspace"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["name"] == "Renamed Engineering Workspace"

    # 5. Delete Workspace
    del_resp = await async_client.delete(f"/api/v1/workspaces/{ws_id}")
    assert del_resp.status_code == 204

    # 6. Verify 404 after deletion
    get_again = await async_client.get(f"/api/v1/workspaces/{ws_id}")
    assert get_again.status_code == 404


@pytest.mark.asyncio
async def test_workspace_api_negative_cases(async_client: AsyncClient, db_session):
    """Test negative cases: 404 missing, 409 conflict, 422 validation."""
    # 404 for non-existent workspace
    fake_id = str(uuid.uuid4())
    resp_404 = await async_client.get(f"/api/v1/workspaces/{fake_id}")
    assert resp_404.status_code == 404

    # 422 for empty name
    resp_422 = await async_client.post("/api/v1/workspaces", json={"name": ""})
    assert resp_422.status_code == 422

    # 409 for duplicate name
    await async_client.post("/api/v1/workspaces", json={"name": "Unique WS"})
    resp_409 = await async_client.post("/api/v1/workspaces", json={"name": "Unique WS"})
    assert resp_409.status_code == 409
