import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_favorite_nonexistent_movie(client, activated_user):
    headers = activated_user["headers"]
    resp = await client.post(
        "/api/v1/cinema/movies/9999/favorites/",
        headers=headers
    )
    assert resp.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_favorite_unauthorized(client):
    resp = await client.post("/api/v1/cinema/movies/1/favorites/")
    assert resp.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_double_favorite_movie(client, activated_user):
    headers = activated_user["headers"]
    await client.post("/api/v1/cinema/movies/1/favorites/", headers=headers)
    resp = await client.post(
        "/api/v1/cinema/movies/1/favorites/",
        headers=headers
    )
    assert resp.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_unfavorite_not_favorited_movie(client, activated_user):
    headers = activated_user["headers"]
    resp = await client.delete(
        "/api/v1/cinema/movies/1/favorites/",
        headers=headers
    )
    assert resp.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_favorite_valid_movie(client, activated_user):
    headers = activated_user["headers"]
    resp = await client.post(
        "/api/v1/cinema/movies/1/favorites/",
        headers=headers
    )
    assert resp.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_remove_favorite_valid(client, activated_user):
    headers = activated_user["headers"]
    await client.post("/api/v1/cinema/movies/1/favorites/", headers=headers)
    resp = await client.delete(
        "/api/v1/cinema/movies/1/favorites/",
        headers=headers
    )
    assert resp.status_code == 204


@pytest.mark.integration
@pytest.mark.asyncio
async def test_remove_favorite_unauthorized(client):
    resp = await client.delete("/api/v1/cinema/movies/1/favorites/")
    assert resp.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_favorites_list_count(client, activated_user):
    headers = activated_user["headers"]
    resp = await client.get("/api/v1/cinema/movies/favorites/", headers=headers)
    assert resp.status_code == 200
    favorites = resp.json()
    assert isinstance(favorites, dict)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_favorite_schema_fields_and_types(client, activated_user):
    headers = activated_user["headers"]
    resp = await client.post(
        "/api/v1/cinema/movies/1/favorites/",
        headers=headers
    )
    data = resp.json()
    assert "message" in data
