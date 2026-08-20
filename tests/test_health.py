from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient):
    """Verify that root /health endpoint returns HTTP 200 and healthy status."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_api_v1_health_endpoint(async_client: AsyncClient):
    """Verify that /api/v1/health endpoint returns HTTP 200 and healthy status."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_database_health_endpoint_connected(async_client: AsyncClient):
    """Verify database health endpoint response when database is connected."""
    with patch(
        "app.api.v1.router.check_database_connection",
        new_callable=AsyncMock,
        return_value=True,
    ):
        response = await async_client.get("/health/db")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy", "database": "connected"}


@pytest.mark.asyncio
async def test_database_health_endpoint_disconnected(async_client: AsyncClient):
    """Verify database health endpoint response when database is disconnected."""
    with patch(
        "app.api.v1.router.check_database_connection",
        new_callable=AsyncMock,
        return_value=False,
    ):
        response = await async_client.get("/health/db")
        assert response.status_code == 503
        assert response.json() == {"status": "unhealthy", "database": "disconnected"}
