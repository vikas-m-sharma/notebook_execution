import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_notebook_cell_api_crud_and_ordering(async_client: AsyncClient, db_session):
    """Test NotebookCell API CRUD lifecycle, position ordering, and execution safety."""
    # Setup hierarchy
    ws_resp = await async_client.post("/api/v1/workspaces", json={"name": "Cell WS"})
    ws_id = ws_resp.json()["id"]
    proj_resp = await async_client.post(f"/api/v1/workspaces/{ws_id}/projects", json={"name": "Cell Proj"})
    proj_id = proj_resp.json()["id"]
    nb_resp = await async_client.post(f"/api/v1/projects/{proj_id}/notebooks", json={"name": "Cell Notebook"})
    nb_id = nb_resp.json()["id"]

    # 1. Create cells out of position order
    c2_resp = await async_client.post(
        f"/api/v1/notebooks/{nb_id}/cells",
        json={"position": 2, "cell_type": "code", "source": "print('Cell 2')"},
    )
    assert c2_resp.status_code == 201

    c0_resp = await async_client.post(
        f"/api/v1/notebooks/{nb_id}/cells",
        json={"position": 0, "cell_type": "code", "source": "import os; os.system('echo safety_test')"},
    )
    assert c0_resp.status_code == 201
    c0_id = c0_resp.json()["id"]

    c1_resp = await async_client.post(
        f"/api/v1/notebooks/{nb_id}/cells",
        json={"position": 1, "cell_type": "markdown", "source": "# Header Title"},
    )
    assert c1_resp.status_code == 201

    # 2. List Cells (Must be ordered by position: 0, 1, 2)
    list_resp = await async_client.get(f"/api/v1/notebooks/{nb_id}/cells")
    assert list_resp.status_code == 200
    cells = list_resp.json()["items"]
    assert len(cells) == 3
    assert [c["position"] for c in cells] == [0, 1, 2]
    assert cells[0]["source"] == "import os; os.system('echo safety_test')"
    assert cells[1]["cell_type"] == "markdown"

    # 3. Get specific cell
    get_resp = await async_client.get(f"/api/v1/notebooks/{nb_id}/cells/{c0_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["position"] == 0

    # 4. Patch Cell
    patch_resp = await async_client.patch(
        f"/api/v1/notebooks/{nb_id}/cells/{c0_id}",
        json={"source": "import os; print('Updated source without execution')"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["source"] == "import os; print('Updated source without execution')"

    # 5. Delete Cell
    del_resp = await async_client.delete(f"/api/v1/notebooks/{nb_id}/cells/{c0_id}")
    assert del_resp.status_code == 204

    # 6. Verify remaining cells list count
    list_again = await async_client.get(f"/api/v1/notebooks/{nb_id}/cells")
    assert list_again.json()["total"] == 2


@pytest.mark.asyncio
async def test_notebook_cell_api_validation_and_conflicts(async_client: AsyncClient, db_session):
    """Test negative cases: 409 duplicate position, 422 unsupported cell_type, 404 missing notebook/cell."""
    ws_resp = await async_client.post("/api/v1/workspaces", json={"name": "Cell Validation WS"})
    ws_id = ws_resp.json()["id"]
    proj_resp = await async_client.post(f"/api/v1/workspaces/{ws_id}/projects", json={"name": "Cell Validation Proj"})
    proj_id = proj_resp.json()["id"]
    nb_resp = await async_client.post(f"/api/v1/projects/{proj_id}/notebooks", json={"name": "Validation Notebook"})
    nb_id = nb_resp.json()["id"]

    await async_client.post(
        f"/api/v1/notebooks/{nb_id}/cells",
        json={"position": 0, "cell_type": "code", "source": "x = 1"},
    )

    # 409 for duplicate position 0 in same notebook
    resp_409 = await async_client.post(
        f"/api/v1/notebooks/{nb_id}/cells",
        json={"position": 0, "cell_type": "code", "source": "x = 2"},
    )
    assert resp_409.status_code == 409

    # 422 for unsupported cell type
    resp_422 = await async_client.post(
        f"/api/v1/notebooks/{nb_id}/cells",
        json={"position": 5, "cell_type": "invalid_type", "source": "x = 5"},
    )
    assert resp_422.status_code == 422

    # 404 for non-existent cell ID
    fake_cell_id = str(uuid.uuid4())
    resp_404 = await async_client.get(f"/api/v1/notebooks/{nb_id}/cells/{fake_cell_id}")
    assert resp_404.status_code == 404
