import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_like_nonexistent_movie(client, activated_user):
    headers = activated_user["headers"]
    resp = await client.post(
        "/api/v1/cinema/movies/9999/likes/",
        headers=headers
    )
    assert resp.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_like_unauthorized(client):
    resp = await client.post("/api/v1/cinema/movies/1/likes/")
    assert resp.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_double_like_movie(client, activated_user):
    headers = activated_user["headers"]
    await client.post("/api/v1/cinema/movies/1/likes/", headers=headers)
    resp = await client.post("/api/v1/cinema/movies/1/likes/", headers=headers)
    assert resp.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_unlike_not_liked_movie(client, activated_user):
    headers = activated_user["headers"]
    resp = await client.delete(
        "/api/v1/cinema/movies/1/likes/",
        headers=headers
    )
    assert resp.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_like_valid_movie(client, activated_user):
    headers = activated_user["headers"]
    resp = await client.post("/api/v1/cinema/movies/1/likes/", headers=headers)
    assert resp.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_remove_like_valid(client, activated_user):
    headers = activated_user["headers"]
    await client.post("/api/v1/cinema/movies/1/likes/", headers=headers)
    resp = await client.delete(
        "/api/v1/cinema/movies/1/likes/",
        headers=headers
    )
    assert resp.status_code == 204


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_likes_list_count(client, activated_user):
    headers = activated_user["headers"]
    resp = await client.get("/api/v1/cinema/movies/likes/", headers=headers)
    assert resp.status_code == 200
    likes = resp.json()
    assert isinstance(likes, dict)
    assert "movies" in likes


@pytest.mark.integration
@pytest.mark.asyncio
async def test_like_schema_fields_and_types(client, activated_user):
    headers = activated_user["headers"]
    resp = await client.post("/api/v1/cinema/movies/1/likes/", headers=headers)
    data = resp.json()
    assert "message" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_likes_invalid_http_method(client):
    resp = await client.put("/api/v1/cinema/movies/1/likes/")
    assert resp.status_code == 405


@pytest.mark.integration
@pytest.mark.asyncio
async def test_like_error_message_format(client, activated_user):
    headers = activated_user["headers"]
    resp = await client.post(
        "/api/v1/cinema/movies/invalid/likes/",
        headers=headers
    )
    assert resp.status_code == 422
    data = resp.json()
    assert "detail" in data
