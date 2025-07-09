import pytest


@pytest.mark.anyio
async def test_invalid_http_method(client):
    resp = await client.put("/api/v1/accounts/register/", json={})
    assert resp.status_code == 405


@pytest.mark.anyio
async def test_invalid_missing_fields(client):
    resp = await client.post("/api/v1/accounts/register/", json={})
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_unauthorized_access(client):
    resp = await client.get("/api/v1/ecommerce/orders/")
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_forbidden_access(client, activated_user):
    """Test that a normal user cannot access an admin/moderator-only endpoint."""
    headers = activated_user["headers"]
    resp = await client.get(
        "/api/v1/ecommerce/admin/payments/",
        headers=headers
    )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_error_handling_not_found(client):
    resp = await client.get("/api/v1/nonexistent-endpoint/")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_advanced_search_filter(client, activated_user):
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


@pytest.mark.anyio
async def test_error_message_format_general(client):
    resp = await client.post("/api/v1/accounts/register/", json={})
    assert resp.status_code == 422
    data = resp.json()
    assert "detail" in data


@pytest.mark.anyio
async def test_permissions_forbidden_access(client, activated_user):
    """Test that a normal user cannot access an admin/moderator-only endpoint (permissions check)."""
    headers = activated_user["headers"]
    resp = await client.get(
        "/api/v1/ecommerce/admin/payments/",
        headers=headers
    )
    assert resp.status_code == 403
