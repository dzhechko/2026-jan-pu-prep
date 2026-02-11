"""Tests for the /api/health endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_ok(client: AsyncClient) -> None:
    """GET /api/health should return 200 with status ok."""
    response = await client.get("/api/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_health_contains_version(client: AsyncClient) -> None:
    """GET /api/health should include the application version."""
    response = await client.get("/api/health")
    data = response.json()
    assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_health_ready_with_mocked_services(client: AsyncClient) -> None:
    """GET /api/health/ready should return 200 when DB and Redis mocks succeed.

    Note: This test uses the mocked app fixture from conftest.py,
    so it does not require actual Postgres or Redis connections.
    """
    # The mock session factory needs to support async context manager
    from unittest.mock import AsyncMock, MagicMock
    from app.main import app

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=MagicMock())
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    app.state.db_session_factory = MagicMock(return_value=mock_session)

    response = await client.get("/api/health/ready")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
