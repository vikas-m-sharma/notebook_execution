import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.router import health_probe_router, router as v1_router
from app.core.config import get_settings
from app.core.database import close_db, init_db
from app.core.logging import setup_logging
from app.core.rate_limiter import limiter
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
    settings = get_settings()
    _warn_insecure_defaults(settings)
    await init_db()
    await scheduler.start()
    yield
    # Shutdown actions
    logger.info("Shutting down FastAPI application...")
    await scheduler.stop()
    await close_db()


def _warn_insecure_defaults(settings) -> None:
    """SEC-005: Warn loudly if default database credentials are in use outside development."""
    if (
        settings.ENVIRONMENT not in ("development", "testing")
        and "postgres:postgres" in settings.DATABASE_URL
    ):
        logger.critical(
            "SECURITY WARNING (SEC-005): The DATABASE_URL contains default credentials "
            "'postgres:postgres'. This MUST be overridden via the DATABASE_URL environment "
            "variable before deploying to any non-development environment."
        )


settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description="Precision Data Platform - Notebook Execution & Management Backend Control Plane API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT not in ("production",) else None,
    redoc_url="/redoc" if settings.ENVIRONMENT not in ("production",) else None,
)

# SEC-007: CORS policy — explicit origin allowlist; no wildcard
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key"],
)

# SEC-008: Rate limiting middleware
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# SEC-020: Register health probe router at root (no auth, safe for liveness probes)
app.include_router(health_probe_router, prefix="", tags=["health"])

# Register protected API router ONLY at /api/v1 (not duplicated at root)
app.include_router(v1_router, prefix="/api/v1", tags=["v1"])


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler preventing stack trace or internal credential leaks."""
    # SEC-011: Log exception class name only in message; reserve full traceback for DEBUG
    logger.error(
        "Unhandled %s on %s %s",
        exc.__class__.__name__,
        request.method,
        request.url.path,
        exc_info=settings.DEBUG,  # SEC-009/SEC-011: full traceback only in debug mode
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred."},
    )
