import pytest


@pytest.mark.anyio
async def test_admin_movie_moderation_flow(client, admin_token):
    """Test admin movie moderation workflow."""
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    movie_data = {
        "name": "Admin Test Movie",
        "year": 2024,
        "time": 120,
        "imdb": 8.5,
        "votes": 1000,
        "meta_score": 50,
        "gross": 10,
        "description": "A movie created by admin.",
        "price": 9.99,
        "certification": "PG-13",
        "genres": ["test"],
        "stars": ["test"],
        "directors": ["test"]
    }

    create_resp = await client.post(
        "/api/v1/cinema/movies/",
        json=movie_data,
        headers=admin_headers
    )
    print(create_resp.content)

    assert create_resp.status_code == 201

    moderate_resp = await client.patch(
        f"/api/v1/cinema/movies/{create_resp.json()['id']}/",
        json={"price": 10.99},
        headers=admin_headers
    )
    assert moderate_resp.status_code == 200


@pytest.mark.anyio
async def test_admin_user_role_management_flow(client, user_data, admin_token):
    """Test admin user role management workflow."""
    await client.post(
        "/api/v1/accounts/register/",
        json=user_data
    )

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    activate_data = {"email": user_data["email"]}
    await client.post(
        "/api/v1/accounts/admin/users/activate/",
        json=activate_data,
        headers=admin_headers
    )

    role_change_resp = await client.post(
        "/api/v1/accounts/admin/users/1/change-group/",
        json={"group_name": "moderator"},
        headers=admin_headers
    )
    assert role_change_resp.status_code == 200
