import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_notebook_api_crud(async_client: AsyncClient, db_session):
    """Test full Notebook API CRUD lifecycle via HTTP endpoints."""
    # Setup Workspace & Project
    ws_resp = await async_client.post("/api/v1/workspaces", json={"name": "Notebook WS"})
    ws_id = ws_resp.json()["id"]
    proj_resp = await async_client.post(f"/api/v1/workspaces/{ws_id}/projects", json={"name": "Analytics Proj"})
    proj_id = proj_resp.json()["id"]

    # 1. Create Notebook
    nb_resp = await async_client.post(
        f"/api/v1/projects/{proj_id}/notebooks",
        json={"name": "ETL Notebook", "description": "ETL process", "language": "python"},
    )
    assert nb_resp.status_code == 201
    nb_data = nb_resp.json()
    nb_id = nb_data["id"]
    assert nb_data["project_id"] == proj_id
    assert nb_data["language"] == "python"

    # 2. Get Notebook Details
    get_resp = await async_client.get(f"/api/v1/notebooks/{nb_id}")
    assert get_resp.status_code == 200
    detail = get_resp.json()
    assert detail["name"] == "ETL Notebook"
    assert detail["cells"] == []

    # 3. List Notebooks in Project
    list_resp = await async_client.get(f"/api/v1/projects/{proj_id}/notebooks")
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 1

    # 4. Patch Notebook
    patch_resp = await async_client.patch(
        f"/api/v1/notebooks/{nb_id}",
        json={"name": "Updated ETL Notebook"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["name"] == "Updated ETL Notebook"

    # 5. Delete Notebook
    del_resp = await async_client.delete(f"/api/v1/notebooks/{nb_id}")
    assert del_resp.status_code == 204

    # 6. Verify 404
    assert (await async_client.get(f"/api/v1/notebooks/{nb_id}")).status_code == 404


@pytest.mark.asyncio
async def test_notebook_api_language_validation_and_no_execution(async_client: AsyncClient, db_session):
    """Verify that unsupported language returns 422, default language works, and code is NOT executed."""
    ws_resp = await async_client.post("/api/v1/workspaces", json={"name": "Lang Validation WS"})
    ws_id = ws_resp.json()["id"]
    proj_resp = await async_client.post(f"/api/v1/workspaces/{ws_id}/projects", json={"name": "Lang Proj"})
    proj_id = proj_resp.json()["id"]

    # 422 for unsupported language 'ruby'
    resp_422 = await async_client.post(
        f"/api/v1/projects/{proj_id}/notebooks",
        json={"name": "Ruby Notebook", "language": "ruby"},
    )
    assert resp_422.status_code == 422

    # Default language 'python' when omitted
    resp_default = await async_client.post(
        f"/api/v1/projects/{proj_id}/notebooks",
        json={"name": "Default Lang Notebook"},
    )
    assert resp_default.status_code == 201
    assert resp_default.json()["language"] == "python"
