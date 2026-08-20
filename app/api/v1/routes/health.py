from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.database import check_database_connection

router = APIRouter()


class LivenessResponse(BaseModel):
    """Schema for application liveness health probe."""

    status: str = "alive"


class ReadinessResponse(BaseModel):
    """Schema for application readiness probe."""

    status: str
    database: str


@router.get(
    "/health/live",
    response_model=LivenessResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness Probe",
    description="Check if the application control plane process is alive.",
)
async def liveness_probe() -> LivenessResponse:
    """Liveness probe endpoint."""
    return LivenessResponse(status="alive")


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness Probe",
    description="Check if required PostgreSQL database infrastructure is ready for serving requests.",
)
async def readiness_probe() -> JSONResponse:
    """Readiness probe endpoint."""
    is_connected = await check_database_connection()
    if is_connected:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "ready", "database": "connected"},
        )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "not_ready", "database": "disconnected"},
    )
