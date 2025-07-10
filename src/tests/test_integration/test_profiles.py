import pytest

from tests.conftest import create_test_image


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_profile(client, activated_user):
    """Test getting user profile."""
    headers = activated_user["headers"]
    user_id = activated_user["user_id"]

    resp = await client.get(
        f"/api/v1/profiles/users/{user_id}/profile/",
        headers=headers
    )
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        data = resp.json()
        assert data["email"] == activated_user["email"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_profile(client, activated_user):
    """Test creating user profile."""
    headers = activated_user["headers"]
    user_id = activated_user["user_id"]

    profile_data = {
        "first_name": "Test",
        "last_name": "User",
        "gender": "MAN",
        "date_of_birth": "1990-01-01",
        "info": "Test user"
    }

    files = {"avatar": ("avatar.jpg", create_test_image(), "image/jpeg")}

    resp = await client.post(
        f"/api/v1/profiles/users/{user_id}/profile/",
        data=profile_data,
        files=files,
        headers=headers
    )
    assert resp.status_code == 201


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_profile_patch(client, activated_user):
    """Test updating user profile with PATCH."""
    headers = activated_user["headers"]
    user_id = activated_user["user_id"]

    profile_data = {
        "first_name": "Test",
        "last_name": "User",
        "gender": "MAN",
        "date_of_birth": "1990-01-01",
        "info": "Test user"
    }

    files = {"avatar": ("avatar.jpg", create_test_image(), "image/jpeg")}

    await client.post(
        f"/api/v1/profiles/users/{user_id}/profile/",
        data=profile_data,
        files=files,
        headers=headers
    )

    profile_data = {
        "info": "Test info"
    }
    resp = await client.patch(
        f"/api/v1/profiles/users/{user_id}/profile/",
        data=profile_data,
        headers=headers
    )
    assert resp.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_profile_unauthorized(client):
    """Test accessing profile without authentication."""
    resp = await client.get("/api/v1/profiles/users/1/profile/")
    assert resp.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_profile_forbidden(client, activated_user):
    """Test accessing another user's profile."""
    headers = activated_user["headers"]
    user_id = activated_user["user_id"]

    resp = await client.get(
        f"/api/v1/profiles/users/{user_id + 1}/profile/",
        headers=headers
    )
    assert resp.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_profile_invalid_data(client, activated_user):
    """Test updating profile with invalid data."""
    headers = activated_user["headers"]
    user_id = activated_user["user_id"]

    resp = await client.patch(
        f"/api/v1/profiles/users/{user_id}/profile/",
        data={"first_name": 123},
        headers=headers
    )
    assert resp.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_avatar_upload_valid(client, activated_user):
    """Test valid avatar upload."""
    headers = activated_user["headers"]
    user_id = activated_user["user_id"]
    profile_data = {
        "first_name": "Test",
        "last_name": "User",
        "gender": "MAN",
        "date_of_birth": "1990-01-01",
        "info": "Test user"
    }

    files = {"avatar": ("avatar.jpg", create_test_image(), "image/jpeg")}

    await client.post(
        f"/api/v1/profiles/users/{user_id}/profile/",
        data=profile_data,
        files=files,
        headers=headers
    )

    files = {"avatar": ("test.jpg", create_test_image(), "image/jpeg")}

    resp = await client.patch(
        f"/api/v1/profiles/users/{user_id}/profile/",
        files=files,
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "avatar" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_avatar_upload_invalid_file(client, activated_user):
    """Test avatar upload with an invalid file type."""
    headers = activated_user["headers"]
    user_id = activated_user["user_id"]

    invalid_file_content = b"this is not an image"
    files = {"avatar": ("test.txt", invalid_file_content, "text/plain")}

    resp = await client.patch(
        f"/api/v1/profiles/users/{user_id}/profile/",
        headers=headers,
        files=files
    )
    assert resp.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_another_users_profile(client, activated_user, user_data):
    """Test updating another user's profile."""
    headers = activated_user["headers"]
    another_user_id = activated_user["user_id"] + 1

    update_data = {
        "first_name": "Another",
        "last_name": "User",
        "bio": "Trying to update."
    }

    resp = await client.patch(
        f"/api/v1/profiles/users/{another_user_id}/profile/",
        headers=headers,
        data=update_data
    )
    assert resp.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_profile_duplicate(client, activated_user):
    """Test creating duplicate profile for the same user."""
    headers = activated_user["headers"]
    user_id = activated_user["user_id"]

    profile_data = {
        "first_name": "Test",
        "last_name": "User",
        "gender": "MAN",
        "date_of_birth": "1990-01-01",
        "info": "Test user"
    }
    files = {"avatar": ("avatar.jpg", create_test_image(), "image/jpeg")}

    resp1 = await client.post(
        f"/api/v1/profiles/users/{user_id}/profile/",
        data=profile_data,
        files=files,
        headers=headers
    )
    assert resp1.status_code == 201

    resp2 = await client.post(
        f"/api/v1/profiles/users/{user_id}/profile/",
        data=profile_data,
        files=files,
        headers=headers
    )
    assert resp2.status_code == 400


@pytest.mark.integration
@pytest.mark.asyncio
async def test_profile_invalid_gender(client, activated_user):
    """Test profile creation with invalid gender."""
    headers = activated_user["headers"]
    user_id = activated_user["user_id"]

    profile_data = {
        "first_name": "Test",
        "last_name": "User",
        "gender": "INVALID_GENDER",
        "date_of_birth": "1990-01-01",
        "info": "Test user"
    }
    files = {"avatar": ("avatar.jpg", create_test_image(), "image/jpeg")}

    resp = await client.post(
        f"/api/v1/profiles/users/{user_id}/profile/",
        data=profile_data,
        files=files,
        headers=headers
    )
    assert resp.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_profile_invalid_date_format(client, activated_user):
    """Test profile creation with invalid date format."""
    headers = activated_user["headers"]
    user_id = activated_user["user_id"]

    profile_data = {
        "first_name": "Test",
        "last_name": "User",
        "gender": "MAN",
        "date_of_birth": "invalid-date",
        "info": "Test user"
    }
    files = {"avatar": ("avatar.jpg", create_test_image(), "image/jpeg")}

    resp = await client.post(
        f"/api/v1/profiles/users/{user_id}/profile/",
        data=profile_data,
        files=files,
        headers=headers
    )
    assert resp.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_profile_missing_required_fields(client, activated_user):
    """Test profile creation with missing required fields."""
    headers = activated_user["headers"]
    user_id = activated_user["user_id"]

    incomplete_data = {"first_name": "John"}
    files = {"avatar": ("avatar.jpg", create_test_image(), "image/jpeg")}

    resp = await client.post(
        f"/api/v1/profiles/users/{user_id}/profile/",
        data=incomplete_data,
        files=files,
        headers=headers
    )
    assert resp.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_profile_future_birth_date(client, activated_user):
    """Test profile creation with future birth date."""
    headers = activated_user["headers"]
    user_id = activated_user["user_id"]

    profile_data = {
        "first_name": "Test",
        "last_name": "User",
        "gender": "MAN",
        "date_of_birth": "2099-01-01",
        "info": "Test user"
    }
    files = {"avatar": ("avatar.jpg", create_test_image(), "image/jpeg")}

    resp = await client.post(
        f"/api/v1/profiles/users/{user_id}/profile/",
        data=profile_data,
        files=files,
        headers=headers
    )
    assert resp.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_profile_large_avatar_file(client, activated_user):
    """Test profile creation with large avatar file."""
    headers = activated_user["headers"]
    user_id = activated_user["user_id"]

    profile_data = {
        "first_name": "Test",
        "last_name": "User",
        "gender": "MAN",
        "date_of_birth": "1990-01-01",
        "info": "Test user"
    }
    large_content = b"x" * (10 * 1024 * 1024)
    files = {"avatar": ("large_avatar.jpg", large_content, "image/jpeg")}

    resp = await client.post(
        f"/api/v1/profiles/users/{user_id}/profile/",
        data=profile_data,
        files=files,
        headers=headers
    )
    assert resp.status_code == 422
