import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.core.database import get_db
from app.main import app
from app.models.base import Base


@pytest.fixture
def override_settings():
    """Fixture providing clean test configuration overrides."""
    return Settings(
        APP_NAME="Precision Data Platform - Test Environment",
        ENVIRONMENT="testing",
        DEBUG=True,
        LOG_LEVEL="DEBUG",
    )


@pytest_asyncio.fixture
async def db_session():
    """AsyncSession fixture configured with an in-memory database for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    # Enable foreign key constraint enforcement for SQLite
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession):
    """Async HTTP client fixture for testing FastAPI endpoints with db_session dependency override."""
    async def _get_db_override():
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()
