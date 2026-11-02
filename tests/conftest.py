"""Test fixtures and configuration for DisputeSentry AI test suite."""

from collections.abc import AsyncGenerator, Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.config import AppConfig, get_config
from app.main import create_app


@pytest.fixture
def app_config() -> AppConfig:
    """Fixture providing loaded application configuration."""
    return get_config()


@pytest.fixture
def app() -> FastAPI:
    """Fixture providing FastAPI application instance."""
    return create_app()


@pytest.fixture
def client(app: FastAPI) -> Generator[TestClient, None, None]:
    """Synchronous test client fixture."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def async_client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Asynchronous test client fixture using ASGITransport."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
