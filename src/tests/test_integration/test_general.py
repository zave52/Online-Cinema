import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_invalid_http_method(client, seed_user_groups):
    resp = await client.put("/api/v1/accounts/register/", json={})
    assert resp.status_code == 405


@pytest.mark.integration
@pytest.mark.asyncio
async def test_invalid_missing_fields(client, seed_user_groups):
    resp = await client.post("/api/v1/accounts/register/", json={})
    assert resp.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_unauthorized_access(client, activated_user):
    resp = await client.get("/api/v1/ecommerce/orders/")
    assert resp.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_forbidden_access(client, activated_user):
    """Test that a normal user cannot access an admin/moderator-only endpoint."""
    resp = await client.get(
        "/api/v1/ecommerce/admin/payments/",
        headers=activated_user["headers"]
    )
    assert resp.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling_not_found(client, seed_user_groups):
    resp = await client.get("/api/v1/nonexistent-endpoint/")
    assert resp.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_advanced_search_filter(client, seed_movies):
    """Test advanced search and filtering capabilities"""
    resp = await client.get(
        "/api/v1/cinema/movies/?year_from=2020&year_to=2023&imdb_min=7&genre=Action"
    )
    assert resp.status_code == 200

    resp = await client.get("/api/v1/cinema/movies/?search=Action & Adventure")
    assert resp.status_code == 200

    resp = await client.get(
        "/api/v1/cinema/movies/?search=NonExistentMovie12345"
    )
    assert resp.status_code == 200
    data = resp.json()
    if isinstance(data, dict) and "movies" in data:
        assert len(data["movies"]) == 0
    else:
        assert len(data) == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_message_format_general(client, seed_user_groups):
    resp = await client.post("/api/v1/accounts/register/", json={})
    assert resp.status_code == 422
    data = resp.json()
    assert "detail" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_permissions_forbidden_access(client, activated_user):
    """Test that a normal user cannot access an admin/moderator-only endpoint (permissions check)."""
    resp = await client.get(
        "/api/v1/ecommerce/admin/payments/",
        headers=activated_user["headers"]
    )
    assert resp.status_code == 403
