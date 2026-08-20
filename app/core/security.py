"""
app/core/security.py

SEC-001: API Key authentication dependency for FastAPI routes.

Authentication model:
- Client must include the header: X-API-Key: <key>
- The key is validated against settings.API_KEY.
- When settings.REQUIRE_AUTH is False (default for development/testing),
  authentication is skipped and all requests are allowed through.
- When settings.REQUIRE_AUTH is True, a missing or invalid key returns HTTP 401.

Usage in router:
    from app.core.security import verify_api_key
    router = APIRouter(dependencies=[Depends(verify_api_key)])
"""
import logging

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# X-API-Key header extractor — auto_error=False so we can produce a custom 401
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    api_key: str | None = Security(_api_key_header),
) -> None:
    """
    SEC-001: FastAPI dependency that enforces API key authentication.

    - When REQUIRE_AUTH=False: passes through (development/testing mode).
    - When REQUIRE_AUTH=True: validates X-API-Key header against settings.API_KEY.
    - Returns HTTP 401 if the key is missing or invalid.
    """
    settings = get_settings()

    if not settings.REQUIRE_AUTH:
        # Authentication disabled — development or testing environment
        return

    if not settings.API_KEY:
        # REQUIRE_AUTH=True but no API_KEY configured — safe-fail: deny all
        logger.critical(
            "SEC-001: REQUIRE_AUTH=True but API_KEY is not set. "
            "All requests are denied. Configure API_KEY in environment."
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service is not configured for authenticated access.",
        )

    if not api_key or api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
