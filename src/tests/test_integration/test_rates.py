import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rate_nonexistent_movie(client, activated_user, seed_movies):
    resp = await client.post(
        "/api/v1/cinema/movies/9999/rates/",
        json={"rate": 8},
        headers=activated_user["headers"]
    )
    assert resp.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rate_unauthorized(client, seed_movies):
    movie_data = seed_movies[0]
    resp = await client.post(
        f"/api/v1/cinema/movies/{movie_data['id']}/rates/",
        json={"rate": 8}
    )
    assert resp.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_double_rate_movie(client, activated_user, seed_movies):
    movie_data = seed_movies[0]
    resp1 = await client.post(
        f"/api/v1/cinema/movies/{movie_data['id']}/rates/",
        json={"rate": 8},
        headers=activated_user["headers"]
    )
    resp2 = await client.post(
        f"/api/v1/cinema/movies/{movie_data['id']}/rates/",
        json={"rate": 9},
        headers=activated_user["headers"]
    )
    assert resp1.status_code == 200
    assert resp2.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rate_valid_movie(client, activated_user, seed_movies):
    movie_data = seed_movies[0]
    resp = await client.post(
        f"/api/v1/cinema/movies/{movie_data['id']}/rates/",
        json={"rate": 8},
        headers=activated_user["headers"]
    )
    assert resp.status_code == 200
