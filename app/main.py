import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api.v1.router import router as v1_router
from app.core.config import get_settings
from app.core.database import close_db, init_db
from app.core.logging import setup_logging
from app.jobs.scheduler import JobScheduler

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = JobScheduler(check_interval_seconds=5.0)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager handling startup and shutdown initialization."""
    # Startup actions
    setup_logging()
    logger.info("Starting up FastAPI application...")
    await init_db()
    await scheduler.start()
    yield
    # Shutdown actions
    logger.info("Shutting down FastAPI application...")
    await scheduler.stop()
    await close_db()


settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description="Precision Data Platform - Notebook Execution & Management Backend Control Plane API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
)

# Register API routers
app.include_router(v1_router, prefix="/api/v1", tags=["v1"])
# Also expose top-level health routes for root health probes
app.include_router(v1_router, prefix="", tags=["health"])


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler preventing stack trace or internal credential leaks."""
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred."},
    )
