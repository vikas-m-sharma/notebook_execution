import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_connector_api_endpoints_crud_and_test(async_client: AsyncClient, db_session):
    """Test REST API endpoints for Connector management and connection testing without secret leaks."""
    # 1. POST /connectors — Create connector
    payload = {
        "name": "api-test-s3-bucket",
        "connector_type": "s3",
        "category": "OBJECT_STORAGE",
        "configuration": {"bucket": "prod-data-bucket", "region": "us-west-2"},
        "secret_payload": {"aws_access_key_id": "AKIA123", "aws_secret_access_key": "secret456"},
    }
    res1 = await async_client.post("/api/v1/connectors", json=payload)
    assert res1.status_code == 201
    conn_data = res1.json()
    assert conn_data["name"] == "api-test-s3-bucket"
    # Verify secrets are NOT in response
    assert "aws_secret_access_key" not in res1.text
    assert "secret456" not in res1.text
    conn_id = conn_data["id"]

    # 2. GET /connectors — List connectors
    res2 = await async_client.get("/api/v1/connectors")
    assert res2.status_code == 200
    list_data = res2.json()
    assert list_data["total"] >= 1

    # 3. GET /connectors/{connector_id} — Get connector
    res3 = await async_client.get(f"/api/v1/connectors/{conn_id}")
    assert res3.status_code == 200
    assert res3.json()["id"] == conn_id

    # 4. POST /connectors/{connector_id}/test — Test connector
    res_test = await async_client.post(f"/api/v1/connectors/{conn_id}/test")
    assert res_test.status_code == 200
    test_data = res_test.json()
    assert test_data["status"] == "AVAILABLE"
    assert test_data["capabilities"]["supports_object_storage"] is True

    # 5. DELETE /connectors/{connector_id}
    res_del = await async_client.delete(f"/api/v1/connectors/{conn_id}")
    assert res_del.status_code == 204
