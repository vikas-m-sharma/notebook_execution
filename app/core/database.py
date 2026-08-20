import logging
from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Global engine and sessionmaker instances
engine: AsyncEngine | None = None
AsyncSessionLocal: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Get or initialize the global AsyncEngine instance."""
    global engine
    if engine is None:
        settings = get_settings()
        engine = create_async_engine(
            settings.DATABASE_URL,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_timeout=settings.DATABASE_POOL_TIMEOUT,
            pool_recycle=settings.DATABASE_POOL_RECYCLE,
            echo=settings.DEBUG,
        )
    return engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Get or initialize the global async session factory."""
    global AsyncSessionLocal
    if AsyncSessionLocal is None:
        async_engine = get_engine()
        AsyncSessionLocal = async_sessionmaker(
            bind=async_engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return AsyncSessionLocal


async def init_db() -> None:
    """Initialize database infrastructure resources on application startup."""
    logger.info("Initializing database connection pool...")
    get_engine()
    get_sessionmaker()
    logger.info("Database connection pool initialized.")


async def close_db() -> None:
    """Dispose database engine resources gracefully on application shutdown."""
    global engine, AsyncSessionLocal
    if engine is not None:
        logger.info("Closing database connection pool...")
        await engine.dispose()
        engine = None
        AsyncSessionLocal = None
        logger.info("Database connection pool closed.")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency generator for providing an AsyncSession instance per request."""
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_database_connection() -> bool:
    """Execute a lightweight test query (SELECT 1) to verify database connectivity."""
    try:
        current_engine = get_engine()
        async with current_engine.connect() as connection:
            result = await connection.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as exc:
        logger.warning(f"Database connection check failed: {exc}")
        return False
