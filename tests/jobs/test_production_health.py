from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_production_health_probes(async_client: AsyncClient):
    """Test Liveness probe (/health/live) and Readiness probe (/health/ready)."""
    # Liveness probe
    res_live = await async_client.get("/api/v1/health/live")
    assert res_live.status_code == 200
    assert res_live.json()["status"] == "alive"

    # Readiness probe (connected)
    with patch("app.api.v1.routes.health.check_database_connection", new_callable=AsyncMock, return_value=True):
        res_ready = await async_client.get("/api/v1/health/ready")
        assert res_ready.status_code == 200
        assert res_ready.json()["status"] == "ready"
        assert res_ready.json()["database"] == "connected"

    # Readiness probe (disconnected)
    with patch("app.api.v1.routes.health.check_database_connection", new_callable=AsyncMock, return_value=False):
        res_unready = await async_client.get("/api/v1/health/ready")
        assert res_unready.status_code == 503
        assert res_unready.json()["status"] == "not_ready"
