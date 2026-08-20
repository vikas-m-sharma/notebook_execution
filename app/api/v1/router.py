from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from app.core.security import verify_api_key

from app.api.v1.routes.connectors import router as connectors_router
from app.api.v1.routes.dependencies import router as dependencies_router
from app.api.v1.routes.execution_outputs import router as execution_outputs_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.jobs import router as jobs_router
from app.api.v1.routes.notebook_cells import router as notebook_cells_router
from app.api.v1.routes.notebook_metadata import router as notebook_metadata_router
from app.api.v1.routes.notebooks import router as notebooks_router
from app.api.v1.routes.projects import router as projects_router
from app.api.v1.routes.workspaces import router as workspaces_router
from app.core.database import check_database_connection
from app.schemas.health import DatabaseHealthResponse, HealthResponse

# SEC-020: Separate health router (probe-safe, no auth) from protected API router.
# health_router is mounted at "/" in main.py; api_router is mounted at "/api/v1".
health_probe_router = APIRouter()


@health_probe_router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Check application control plane health status.",
)
async def health_check() -> HealthResponse:
    """Application health probe endpoint."""
    return HealthResponse(status="healthy")


@health_probe_router.get(
    "/health/db",
    response_model=DatabaseHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Database Health Check",
    description="Check PostgreSQL database connectivity status.",
)
async def db_health_check() -> JSONResponse:
    """Database connectivity health probe endpoint."""
    is_connected = await check_database_connection()
    if is_connected:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "healthy", "database": "connected"},
        )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "unhealthy", "database": "disconnected"},
    )


# Protected API router (mounted at /api/v1 in main.py)
# SEC-001: All routes inherit API key authentication requirement.
router = APIRouter(dependencies=[Depends(verify_api_key)])

# Mount API routes
router.include_router(workspaces_router, prefix="/workspaces", tags=["Workspaces"])
router.include_router(projects_router, tags=["Projects"])
router.include_router(notebooks_router, tags=["Notebooks"])
router.include_router(notebook_cells_router, tags=["Notebook Cells"])
router.include_router(notebook_metadata_router, tags=["Notebook Metadata"])
router.include_router(execution_outputs_router, tags=["Execution Outputs"])
router.include_router(dependencies_router, tags=["Dependencies"])
router.include_router(connectors_router, tags=["Connectors"])
router.include_router(jobs_router, tags=["Jobs"])
router.include_router(health_router, tags=["Production Health"])
