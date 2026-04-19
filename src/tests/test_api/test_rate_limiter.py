from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from security.rate_limiter import get_redis_client


@pytest.fixture
def mock_redis_rate_limit(app: FastAPI):
    mock = AsyncMock()
    app.dependency_overrides[get_redis_client] = lambda: mock
    yield mock


@pytest.mark.api
@pytest.mark.asyncio
async def test_anonymous_user_rate_limit_not_exceeded(
    client: AsyncClient,
    mock_redis_rate_limit,
    settings
):
    mock_redis_rate_limit.zcard.return_value = settings.RATE_LIMIT_ANONYMOUS - 1

    response = await client.get("/api/v1/cinema/movies/")
    assert response.status_code == 200


@pytest.mark.api
@pytest.mark.asyncio
async def test_anonymous_user_rate_limit_exceeded(
    client: AsyncClient,
    mock_redis_rate_limit,
    settings
):
    mock_redis_rate_limit.zcard.return_value = settings.RATE_LIMIT_ANONYMOUS + 1

    response = await client.get("/api/v1/cinema/movies/")
    assert response.status_code == 429
    assert response.json()["detail"] == "Too many requests"


@pytest.mark.api
@pytest.mark.asyncio
async def test_authenticated_user_rate_limit_not_exceeded(
    client: AsyncClient,
    activated_user,
    mock_redis_rate_limit,
    settings
):
    mock_redis_rate_limit.zcard.return_value = settings.RATE_LIMIT_AUTHENTICATED - 1

    headers = activated_user["headers"]
    response = await client.get("/api/v1/cinema/movies/", headers=headers)
    assert response.status_code == 200


@pytest.mark.api
@pytest.mark.asyncio
async def test_authenticated_user_rate_limit_exceeded(
    client: AsyncClient,
    activated_user,
    mock_redis_rate_limit,
    settings
):
    mock_redis_rate_limit.zcard.return_value = settings.RATE_LIMIT_AUTHENTICATED + 1

    headers = activated_user["headers"]
    response = await client.get("/api/v1/cinema/movies/", headers=headers)
    assert response.status_code == 429
    assert response.json()["detail"] == "Too many requests"
