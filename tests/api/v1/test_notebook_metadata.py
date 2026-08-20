import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_notebook_metadata_api(async_client: AsyncClient, db_session):
    """Test NotebookMetadata GET and PATCH HTTP endpoints."""
    # Setup hierarchy
    ws_resp = await async_client.post("/api/v1/workspaces", json={"name": "Metadata WS"})
    ws_id = ws_resp.json()["id"]
    proj_resp = await async_client.post(f"/api/v1/workspaces/{ws_id}/projects", json={"name": "Metadata Proj"})
    proj_id = proj_resp.json()["id"]
    nb_resp = await async_client.post(f"/api/v1/projects/{proj_id}/notebooks", json={"name": "Metadata Notebook"})
    nb_id = nb_resp.json()["id"]

    # 1. GET metadata before setting returns 404
    get_before = await async_client.get(f"/api/v1/notebooks/{nb_id}/metadata")
    assert get_before.status_code == 404

    # 2. PATCH metadata
    patch_resp = await async_client.patch(
        f"/api/v1/notebooks/{nb_id}/metadata",
        json={"configuration": {"timeout_seconds": 600, "environment": "py310"}},
    )
    assert patch_resp.status_code == 200
    meta_data = patch_resp.json()
    assert meta_data["notebook_id"] == nb_id
    assert meta_data["configuration"]["timeout_seconds"] == 600

    # 3. GET metadata after setting returns 200
    get_after = await async_client.get(f"/api/v1/notebooks/{nb_id}/metadata")
    assert get_after.status_code == 200
    assert get_after.json()["configuration"]["environment"] == "py310"

    # 4. 404 for non-existent notebook metadata
    fake_nb_id = str(uuid.uuid4())
    assert (await async_client.get(f"/api/v1/notebooks/{fake_nb_id}/metadata")).status_code == 404
