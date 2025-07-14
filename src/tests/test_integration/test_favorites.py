import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_favorite_nonexistent_movie(client, activated_user):
    resp = await client.post(
        "/api/v1/cinema/movies/9999/favorites/",
        headers=activated_user["headers"]
    )
    assert resp.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_favorite_unauthorized(client, seed_movies):
    movie_data = seed_movies[0]
    resp = await client.post(
        f"/api/v1/cinema/movies/{movie_data['id']}/favorites/"
    )
    assert resp.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_double_favorite_movie(client, activated_user, seed_movies):
    movie_data = seed_movies[0]
    await client.post(
        f"/api/v1/cinema/movies/{movie_data['id']}/favorites/",
        headers=activated_user["headers"]
    )
    resp = await client.post(
        f"/api/v1/cinema/movies/{movie_data['id']}/favorites/",
        headers=activated_user["headers"]
    )
    assert resp.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_unfavorite_not_favorited_movie(
    client,
    activated_user,
    seed_movies
):
    movie_data = seed_movies[0]
    resp = await client.delete(
        f"/api/v1/cinema/movies/{movie_data['id']}/favorites/",
        headers=activated_user["headers"]
    )
    assert resp.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_favorite_valid_movie(client, activated_user, seed_movies):
    movie_data = seed_movies[0]
    resp = await client.post(
        f"/api/v1/cinema/movies/{movie_data['id']}/favorites/",
        headers=activated_user["headers"]
    )
    assert resp.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_remove_favorite_valid(client, activated_user, seed_movies):
    movie_data = seed_movies[0]
    await client.post(
        f"/api/v1/cinema/movies/{movie_data['id']}/favorites/",
        headers=activated_user["headers"]
    )
    resp = await client.delete(
        f"/api/v1/cinema/movies/{movie_data['id']}/favorites/",
        headers=activated_user["headers"]
    )
    assert resp.status_code == 204


@pytest.mark.integration
@pytest.mark.asyncio
async def test_remove_favorite_unauthorized(client, seed_movies):
    movie_data = seed_movies[0]
    resp = await client.delete(
        f"/api/v1/cinema/movies/{movie_data['id']}/favorites/"
    )
    assert resp.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_favorites_list_count(client, activated_user, seed_movies):
    movie_data = seed_movies[0]
    await client.post(
        f"/api/v1/cinema/movies/{movie_data['id']}/favorites/",
        headers=activated_user["headers"]
    )
    resp = await client.get(
        f"/api/v1/cinema/movies/favorites/",
        headers=activated_user["headers"]
    )
    assert resp.status_code == 200
    favorites = resp.json()
    assert isinstance(favorites, dict)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_favorite_schema_fields_and_types(
    client,
    activated_user,
    seed_movies
):
    movie_data = seed_movies[0]
    resp = await client.post(
        f"/api/v1/cinema/movies/{movie_data['id']}/favorites/",
        headers=activated_user["headers"]
    )
    data = resp.json()
    assert "message" in data
