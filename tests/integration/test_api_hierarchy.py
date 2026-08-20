import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_full_api_hierarchy_and_cascade_deletion(async_client: AsyncClient, db_session):
    """Full API integration test verifying Workspace -> Project -> Notebook -> Cell -> Metadata creation, retrieval, and cascade deletion via HTTP."""
    # 1. Create Workspace
    ws_resp = await async_client.post(
        "/api/v1/workspaces",
        json={"name": "Production API Workspace", "description": "Production environment"},
    )
    assert ws_resp.status_code == 201
    ws_id = ws_resp.json()["id"]

    # 2. Create Project
    proj_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects",
        json={"name": "Analytics Pipeline", "description": "End-to-end data pipeline"},
    )
    assert proj_resp.status_code == 201
    proj_id = proj_resp.json()["id"]

    # 3. Create Notebook
    nb_resp = await async_client.post(
        f"/api/v1/projects/{proj_id}/notebooks",
        json={"name": "Sales Forecast", "language": "python"},
    )
    assert nb_resp.status_code == 201
    nb_id = nb_resp.json()["id"]

    # 4. Create Cells (out of position order)
    c2_resp = await async_client.post(
        f"/api/v1/notebooks/{nb_id}/cells",
        json={"position": 2, "cell_type": "code", "source": "print(df.summary())"},
    )
    c0_resp = await async_client.post(
        f"/api/v1/notebooks/{nb_id}/cells",
        json={"position": 0, "cell_type": "code", "source": "import pandas as pd"},
    )
    c1_resp = await async_client.post(
        f"/api/v1/notebooks/{nb_id}/cells",
        json={"position": 1, "cell_type": "markdown", "source": "## Analysis Section"},
    )
    assert c2_resp.status_code == 201
    assert c0_resp.status_code == 201
    assert c1_resp.status_code == 201

    # 5. Patch Metadata
    meta_resp = await async_client.patch(
        f"/api/v1/notebooks/{nb_id}/metadata",
        json={"configuration": {"timeout_seconds": 1200, "libraries": ["pandas"]}},
    )
    assert meta_resp.status_code == 200

    # 6. Retrieve Full Notebook Detail via HTTP GET
    get_detail = await async_client.get(f"/api/v1/notebooks/{nb_id}")
    assert get_detail.status_code == 200
    detail_data = get_detail.json()
    assert detail_data["name"] == "Sales Forecast"
    assert len(detail_data["cells"]) == 3
    assert [c["position"] for c in detail_data["cells"]] == [0, 1, 2]
    assert detail_data["cells"][0]["source"] == "import pandas as pd"
    assert detail_data["cells"][1]["cell_type"] == "markdown"
    assert detail_data["metadata"]["configuration"]["timeout_seconds"] == 1200

    # 7. Delete Workspace via HTTP DELETE
    del_ws = await async_client.delete(f"/api/v1/workspaces/{ws_id}")
    assert del_ws.status_code == 204

    # 8. Verify all child endpoints return 404
    assert (await async_client.get(f"/api/v1/workspaces/{ws_id}")).status_code == 404
    assert (await async_client.get(f"/api/v1/projects/{proj_id}")).status_code == 404
    assert (await async_client.get(f"/api/v1/notebooks/{nb_id}")).status_code == 404
    assert (await async_client.get(f"/api/v1/notebooks/{nb_id}/cells")).status_code == 404
    assert (await async_client.get(f"/api/v1/notebooks/{nb_id}/metadata")).status_code == 404
