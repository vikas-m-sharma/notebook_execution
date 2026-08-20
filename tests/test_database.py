from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import Settings, get_settings
from app.core.database import (
    check_database_connection,
    get_db,
    get_engine,
    get_sessionmaker,
)


def test_settings_load():
    """Verify application configuration loads cleanly with default parameters."""
    settings = get_settings()
    assert isinstance(settings, Settings)
    assert settings.APP_NAME == "Precision Data Platform - Notebook Backend"
    assert "postgresql+asyncpg" in settings.DATABASE_URL
    assert settings.DATABASE_POOL_SIZE == 10


def test_database_engine_initialization():
    """Verify async engine instance initialization."""
    engine = get_engine()
    assert isinstance(engine, AsyncEngine)
    assert engine.url.drivername == "postgresql+asyncpg"


def test_sessionmaker_initialization():
    """Verify async session factory initialization."""
    session_factory = get_sessionmaker()
    assert isinstance(session_factory, async_sessionmaker)


@pytest.mark.asyncio
async def test_get_db_generator():
    """Verify that get_db yields an AsyncSession instance and closes cleanly."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_factory = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session), __aexit__=AsyncMock()))

    with patch("app.core.database.get_sessionmaker", return_value=mock_factory):
        generator = get_db()
        session = await anext(generator)
        assert session == mock_session

        with pytest.raises(StopAsyncIteration):
            await anext(generator)


@pytest.mark.asyncio
async def test_check_database_connection_failure():
    """Verify check_database_connection returns False when connection raises an exception."""
    with patch("app.core.database.get_engine") as mock_get_engine:
        mock_engine = MagicMock()
        mock_engine.connect.side_effect = Exception("Connection refused")
        mock_get_engine.return_value = mock_engine

        result = await check_database_connection()
        assert result is False
