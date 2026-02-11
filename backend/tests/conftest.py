"""Pytest fixtures for NutriMind backend tests."""

import asyncio
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings
from app.models import Base


@pytest_asyncio.fixture(scope="session")
async def test_engine() -> AsyncIterator[AsyncEngine]:
    """Create a test database engine.

    In CI / local dev without a real Postgres, tests that need a
    database should be marked with ``@pytest.mark.db``.  The health
    endpoint test works without a real database.
    """
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_size=2,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Provide a transactional database session that rolls back after each test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def app() -> FastAPI:
    """Create a FastAPI application instance for testing.

    Mocks Redis and database connections so that the health endpoint
    can be tested without infrastructure dependencies.
    """
    from app.main import app as application

    # Mock Redis
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.aclose = AsyncMock()

    # Mock DB engine and session factory
    mock_engine = MagicMock()
    mock_session_factory = MagicMock()

    application.state.redis = mock_redis
    application.state.db_engine = mock_engine
    application.state.db_session_factory = mock_session_factory

    return application


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Provide an async HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
