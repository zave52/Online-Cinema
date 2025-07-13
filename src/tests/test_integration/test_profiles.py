import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_profile(client, user_with_profile):
    """Test getting user profile."""
    resp = await client.get(
        f"/api/v1/profiles/users/{user_with_profile['user_id']}/profile/",
        headers=user_with_profile["headers"]
    )
    assert resp.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_profile(client, activated_user, mock_avatar):
    """Test creating user profile."""
    profile_data = {
        "first_name": "Test",
        "last_name": "User",
        "gender": "MAN",
        "date_of_birth": "1990-01-01",
        "info": "Test user"
    }

    files = {
        "avatar": (
            mock_avatar.filename,
            mock_avatar.file,
            mock_avatar.content_type
        )
    }

    resp = await client.post(
        f"/api/v1/profiles/users/{activated_user['user_id']}/profile/",
        data=profile_data,
        files=files,
        headers=activated_user["headers"]
    )
    assert resp.status_code == 201


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_profile_patch(client, user_with_profile):
    """Test updating user profile with PATCH."""
    profile_data = {"info": "Test info"}
    resp = await client.patch(
        f"/api/v1/profiles/users/{user_with_profile['user_id']}/profile/",
        data=profile_data,
        headers=user_with_profile["headers"]
    )
    assert resp.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_profile_unauthorized(client, user_with_profile):
    """Test accessing profile without authentication."""
    resp = await client.get(
        f"/api/v1/profiles/users/{user_with_profile['user_id']}/profile/"
    )
    assert resp.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_profile_invalid_data(client, user_with_profile):
    """Test updating profile with invalid data."""
    resp = await client.patch(
        f"/api/v1/profiles/users/{user_with_profile['user_id']}/profile/",
        data={"first_name": 123},
        headers=user_with_profile["headers"]
    )
    assert resp.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_avatar_upload_valid(client, user_with_profile, mock_avatar):
    """Test valid avatar upload."""
    files = {
        "avatar": (mock_avatar.filename, mock_avatar.file,
                   mock_avatar.content_type)
    }

    resp = await client.patch(
        f"/api/v1/profiles/users/{user_with_profile['user_id']}/profile/",
        files=files,
        headers=user_with_profile["headers"]
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "avatar" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_avatar_upload_invalid_file(client, user_with_profile):
    """Test avatar upload with an invalid file type."""
    invalid_file_content = b"this is not an image"
    files = {"avatar": ("test.txt", invalid_file_content, "text/plain")}

    resp = await client.patch(
        f"/api/v1/profiles/users/{user_with_profile['user_id']}/profile/",
        files=files,
        headers=user_with_profile["headers"]
    )
    assert resp.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_another_users_profile(
    client,
    user_with_profile,
    another_user
):
    """Test updating another user's profile."""
    update_data = {
        "first_name": "Another",
        "last_name": "User",
        "bio": "Trying to update."
    }

    resp = await client.patch(
        f"/api/v1/profiles/users/{user_with_profile['user_id']}/profile/",
        data=update_data,
        headers=another_user["headers"]
    )
    assert resp.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_profile_duplicate(client, activated_user, mock_avatar):
    """Test creating duplicate profile for the same user."""
    profile_data = {
        "first_name": "Test",
        "last_name": "User",
        "gender": "MAN",
        "date_of_birth": "1990-01-01",
        "info": "Test user"
    }
    files = {
        "avatar": (
            mock_avatar.filename,
            mock_avatar.file,
            mock_avatar.content_type
        )
    }

    resp1 = await client.post(
        f"/api/v1/profiles/users/{activated_user['user_id']}/profile/",
        data=profile_data,
        files=files,
        headers=activated_user["headers"]
    )
    assert resp1.status_code == 201

    resp2 = await client.post(
        f"/api/v1/profiles/users/{activated_user['user_id']}/profile/",
        data=profile_data,
        files=files,
        headers=activated_user["headers"]
    )
    assert resp2.status_code == 400


@pytest.mark.integration
@pytest.mark.asyncio
async def test_profile_invalid_gender(client, activated_user, mock_avatar):
    """Test profile creation with invalid gender."""
    profile_data = {
        "first_name": "Test",
        "last_name": "User",
        "gender": "INVALID_GENDER",
        "date_of_birth": "1990-01-01",
        "info": "Test user"
    }
    files = {
        "avatar": (
            mock_avatar.filename,
            mock_avatar.file,
            mock_avatar.content_type
        )
    }

    resp = await client.post(
        f"/api/v1/profiles/users/{activated_user['user_id']}/profile/",
        data=profile_data,
        files=files,
        headers=activated_user["headers"]
    )
    assert resp.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_profile_invalid_date_format(client, activated_user, mock_avatar):
    """Test profile creation with invalid date format."""
    profile_data = {
        "first_name": "Test",
        "last_name": "User",
        "gender": "MAN",
        "date_of_birth": "invalid-date",
        "info": "Test user"
    }
    files = {
        "avatar": (
            mock_avatar.filename,
            mock_avatar.file,
            mock_avatar.content_type
        )
    }
    resp = await client.post(
        f"/api/v1/profiles/users/{activated_user['user_id']}/profile/",
        data=profile_data,
        files=files,
        headers=activated_user["headers"]
    )
    assert resp.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_profile_missing_required_fields(
    client,
    activated_user,
    mock_avatar
):
    """Test profile creation with missing required fields."""
    incomplete_data = {"first_name": "John"}
    files = {
        "avatar": (
            mock_avatar.filename,
            mock_avatar.file,
            mock_avatar.content_type
        )
    }
    resp = await client.post(
        f"/api/v1/profiles/users/{activated_user['user_id']}/profile/",
        data=incomplete_data,
        files=files,
        headers=activated_user["headers"]
    )
    assert resp.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_profile_future_birth_date(client, activated_user, mock_avatar):
    """Test profile creation with future birth date."""
    profile_data = {
        "first_name": "Test",
        "last_name": "User",
        "gender": "MAN",
        "date_of_birth": "2099-01-01",
        "info": "Test user"
    }
    files = {
        "avatar": (
            mock_avatar.filename,
            mock_avatar.file,
            mock_avatar.content_type
        )
    }

    resp = await client.post(
        f"/api/v1/profiles/users/{activated_user['user_id']}/profile/",
        data=profile_data,
        files=files,
        headers=activated_user["headers"]
    )
    assert resp.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_profile_large_avatar_file(client, activated_user):
    """Test profile creation with large avatar file."""
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
        f"/api/v1/profiles/users/{activated_user['user_id']}/profile/",
        data=profile_data,
        files=files,
        headers=activated_user["headers"]
    )
    assert resp.status_code == 422
