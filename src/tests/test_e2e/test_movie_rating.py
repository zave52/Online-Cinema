import pytest


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_movie_rating_flow(client, activated_user, seed_movies):
    """Test complete movie rating workflow."""
    headers = {"Authorization": f"Bearer {activated_user['access_token']}"}

    movie_id = seed_movies[0]["id"]

    rating_data = {"rate": 8}
    rate_resp = await client.post(
        f"/api/v1/cinema/movies/{movie_id}/rates/",
        json=rating_data,
        headers=headers
    )
    assert rate_resp.status_code == 200

    ratings_resp = await client.get(f"/api/v1/cinema/movies/{movie_id}/")
    data = ratings_resp.json()
    assert ratings_resp.status_code == 200
    assert "average_rating" in data


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_movie_like_flow(client, activated_user, seed_movies):
    """Test movie like/unlike workflow."""
    headers = {"Authorization": f"Bearer {activated_user['access_token']}"}

    movie_id = seed_movies[0]["id"]

    like_resp = await client.post(
        f"/api/v1/cinema/movies/{movie_id}/likes/",
        headers=headers
    )
    assert like_resp.status_code == 200

    unlike_resp = await client.delete(
        f"/api/v1/cinema/movies/{movie_id}/likes/",
        headers=headers
    )
    assert unlike_resp.status_code == 204
