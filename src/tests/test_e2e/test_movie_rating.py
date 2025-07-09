import pytest


@pytest.mark.anyio
async def test_movie_rating_flow(client, user_data, admin_token, seed_movies):
    """Test complete movie rating workflow."""
    await client.post("/api/v1/accounts/register/", json=user_data)

    admin_headers = {
        "Authorization": f"Bearer {admin_token}"
    }
    activation_data = {"email": user_data["email"]}
    await client.post(
        "/api/v1/accounts/admin/users/activate/",
        json=activation_data,
        headers=admin_headers
    )

    login_resp = await client.post(
        "/api/v1/accounts/login/",
        json={"email": user_data["email"], "password": user_data["password"]},
        headers={"Content-Type": "application/json"}
    )

    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
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


@pytest.mark.anyio
async def test_movie_like_flow(client, user_data, admin_token, seed_movies):
    """Test movie like/unlike workflow."""
    await client.post("/api/v1/accounts/register/", json=user_data)

    admin_headers = {
        "Authorization": f"Bearer {admin_token}"
    }
    activation_data = {"email": user_data["email"]}
    await client.post(
        "/api/v1/accounts/admin/users/activate/",
        json=activation_data,
        headers=admin_headers
    )

    login_resp = await client.post(
        "/api/v1/accounts/login/",
        json={"email": user_data["email"], "password": user_data["password"]},
        headers={"Content-Type": "application/json"}
    )

    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
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
