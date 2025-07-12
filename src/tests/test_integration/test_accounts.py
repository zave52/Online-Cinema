import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_success(client, seed_user_groups):
    """Test successful user registration."""
    user_data = {
        "email": "test@gmail.com",
        "password": "StrongPassword123!"
    }

    response = await client.post(
        "/api/v1/accounts/register/",
        json=user_data
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["email"] == user_data["email"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_invalid_email(client, seed_user_groups):
    """Test registration with an invalid email address."""
    bad_data = {
        "email": "not-an-email",
        "password": "StrongPassword123!"
    }
    response = await client.post("/api/v1/accounts/register/", json=bad_data)
    assert response.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_success(client, activated_user):
    """Test successful login after registration."""
    response = await client.post(
        "/api/v1/accounts/login/",
        json={
            "email": activated_user["email"],
            "password": activated_user["password"]
        },
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_wrong_password(client, activated_user):
    """Test login with wrong password."""
    response = await client.post(
        "/api/v1/accounts/login/",
        json={
            "email": activated_user["email"],
            "password": "WrongPassword123!"
        },
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_profile_me(client, activated_user):
    """Test getting user's own profile."""
    login_resp = await client.post(
        "/api/v1/accounts/login/",
        json={
            "email": activated_user["email"],
            "password": activated_user["password"]
        },
        headers={"Content-Type": "application/json"}
    )

    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile_resp = await client.get(
        f"/api/v1/profiles/users/{activated_user['user_id']}/profile/",
        headers=headers
    )
    assert profile_resp.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_duplicate_email(client, seed_user_groups):
    """Test registration with duplicate email."""
    user_data = {
        "email": "test@gmail.com",
        "password": "StrongPassword123!"
    }
    await client.post(
        "/api/v1/accounts/register/",
        json=user_data
    )

    duplicate_data = user_data.copy()

    resp = await client.post(
        "/api/v1/accounts/register/",
        json=duplicate_data
    )
    assert resp.status_code == 409


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_weak_password(client, seed_user_groups):
    """Test registration with a weak password."""
    weak_data = {
        "email": "test@gmail.com",
        "password": "123"
    }
    resp = await client.post(
        "/api/v1/accounts/register/",
        json=weak_data
    )
    assert resp.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_inactive_user(client, seed_user_groups):
    """Test login for an inactive user (if activation is required)."""
    user_data = {
        "email": "test@gmail.com",
        "password": "StrongPassword123!"
    }
    await client.post(
        "/api/v1/accounts/register/",
        json=user_data
    )
    resp = await client.post(
        "/api/v1/accounts/login/",
        json={
            "email": user_data["email"],
            "password": user_data["password"]
        },
        headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_profile_jwt_tampering(client, activated_user):
    """Test accessing profile with a tampered JWT token."""
    login_resp = await client.post(
        "/api/v1/accounts/login/",
        json={
            "email": activated_user["email"],
            "password": activated_user["password"]
        },
        headers={"Content-Type": "application/json"}
    )
    token = login_resp.json()["access_token"]
    tampered_token = token[:-2] + ("aa" if token[-1] != "a" else "bb")
    headers = {"Authorization": f"Bearer {tampered_token}"}
    resp = await client.get(
        f"/api/v1/profiles/users/{activated_user['user_id']}/profile/",
        headers=headers
    )
    assert resp.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_missing_fields(client, seed_user_groups):
    """Test registration with missing required fields."""
    resp = await client.post(
        "/api/v1/accounts/register/",
        json={"email": "user@example.com"}
    )
    assert resp.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_nonexistent_user(client, seed_user_groups):
    """Test login with a non-existent user."""
    resp = await client.post(
        "/api/v1/accounts/login/",
        json={"email": "nouser@example.com", "password": "StrongPassword123!"},
        headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_missing_fields(client, activated_user):
    """Test login with missing required fields."""
    resp = await client.post(
        "/api/v1/accounts/login/",
        json={"email": activated_user["email"]},
        headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_profile_invalid_update(client, user_with_profile):
    """Test updating the user's profile with invalid data."""
    resp = await client.patch(
        f"/api/v1/profiles/users/{user_with_profile['user_id']}/profile/",
        data={"date_of_birth": "Invalid"}, headers=user_with_profile["headers"]
    )

    assert resp.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_profile_unauthorized_update(client, user_with_profile):
    """Test unauthorized update of the user's profile."""
    resp = await client.patch(
        f"/api/v1/profiles/users/{user_with_profile['user_id']}/profile/",
        data={"first_name": "NoAuth"}
    )
    assert resp.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_profile_access_another_user(
    client,
    user_with_profile,
    another_user
):
    """Test that a user cannot access another user's profile (if not allowed)."""
    resp = await client.get(
        f"/api/v1/profiles/users/{user_with_profile['user_id']}/profile/",
        headers=another_user["headers"]
    )
    assert resp.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_profile_missing_jwt(client, user_with_profile):
    """Test accessing the user's profile without a JWT token."""
    resp = await client.get(
        f"/api/v1/profiles/users/{user_with_profile['user_id']}/profile/"
    )
    assert resp.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_password_reset_invalid_email(client, activated_user):
    """Test password reset with an invalid email address."""
    resp = await client.post(
        "/api/v1/accounts/password-reset/request/",
        json={"email": "nonexistent@example.com"}
    )
    assert resp.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_password_change_wrong_old_password(client, activated_user):
    """Test password change with a wrong old password."""
    resp = await client.post(
        "/api/v1/accounts/password-change/",
        json={
            "old_password": "wrongpassword",
            "new_password": "NewPassword123!"
        },
        headers=activated_user["headers"]
    )
    assert resp.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_profile_update_another_user_forbidden(
    client,
    user_with_profile,
    another_user
):
    """Test that a user cannot update another user's profile."""
    resp = await client.patch(
        f"/api/v1/profiles/users/{user_with_profile['user_id']}/profile/",
        data={"first_name": "Forbidden"}, headers=another_user["headers"]
    )
    assert resp.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_password_reset_with_invalid_token(
    client,
    activated_user
):
    """Test password reset with an invalid or expired token."""
    resp = await client.post(
        "/api/v1/accounts/password-reset/complete/",
        json={
            "email": activated_user["email"],
            "password": "NewPassword123!",
            "token": "definitely_invalid_token"
        }
    )
    assert resp.status_code == 400


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_empty_password(client, seed_user_groups):
    """Test registration with empty password."""
    bad_data = {
        "email": "testuser@gmail.com",
        "password": ""
    }
    resp = await client.post("/api/v1/accounts/register/", json=bad_data)
    assert resp.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_empty_email(client, seed_user_groups):
    """Test registration with empty email."""
    bad_data = {
        "email": "",
        "password": "StrongPassword123!"
    }
    resp = await client.post("/api/v1/accounts/register/", json=bad_data)
    assert resp.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_very_long_email(client, seed_user_groups):
    """Test registration with very long email."""
    bad_data = {
        "email": "a" * 300 + "@gmail.com",
        "password": "StrongPasssword123!"
    }
    resp = await client.post("/api/v1/accounts/register/", json=bad_data)
    assert resp.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_sql_injection_attempt(client, seed_user_groups):
    """Test registration with SQL injection attempt."""
    bad_data = {
        "email": "admin@example.com'; DROP TABLE users; --",
        "password": "StrongPassword123!"
    }
    resp = await client.post("/api/v1/accounts/register/", json=bad_data)
    assert resp.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_case_insensitive_email(client, activated_user):
    """Test login with different case email."""
    resp = await client.post(
        "/api/v1/accounts/login/",
        json={
            "email": activated_user["email"].upper(),
            "password": activated_user["password"]
        },
        headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_token_verification(client, activated_user):
    """Test token verification endpoint."""
    verify_resp = await client.post(
        "/api/v1/accounts/verify/",
        json={"access_token": activated_user["access_token"]}
    )
    assert verify_resp.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_token_verification_invalid(client, activated_user):
    """Test token verification with invalid token."""
    resp = await client.post(
        "/api/v1/accounts/verify/",
        json={"access_token": "invalid_token"}
    )
    assert resp.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_refresh_token_flow(client, activated_user):
    """Test refresh token flow."""
    login_resp = await client.post(
        "/api/v1/accounts/login/",
        json={
            "email": activated_user["email"],
            "password": activated_user["password"]
        },
        headers={"Content-Type": "application/json"}
    )

    refresh_token = login_resp.json()["refresh_token"]

    refresh_resp = await client.post(
        "/api/v1/accounts/refresh/",
        json={"refresh_token": refresh_token}
    )
    assert refresh_resp.status_code == 200
    assert "access_token" in refresh_resp.json()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_refresh_token_invalid(client, activated_user):
    """Test refresh token with invalid token."""
    resp = await client.post(
        "/api/v1/accounts/refresh/",
        json={"refresh_token": "invalid_refresh_token"}
    )
    assert resp.status_code == 400


@pytest.mark.integration
@pytest.mark.asyncio
async def test_logout_flow(client, activated_user):
    """Test logout flow."""
    login_resp = await client.post(
        "/api/v1/accounts/login/",
        json={
            "email": activated_user["email"],
            "password": activated_user["password"]
        },
        headers={"Content-Type": "application/json"}
    )

    tokens = login_resp.json()
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    logout_resp = await client.post(
        "/api/v1/accounts/logout/",
        json={"refresh_token": refresh_token},
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert logout_resp.status_code == 200

    resp = await client.post(
        "/api/v1/accounts/refresh/",
        json={"refresh_token": refresh_token}
    )
    assert resp.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_password_change_same_password(client, activated_user):
    """Test password change with same old and new password."""
    resp = await client.post(
        "/api/v1/accounts/password-change/",
        json={
            "old_password": activated_user["password"],
            "new_password": activated_user["password"]
        },
        headers=activated_user["headers"]
    )
    assert resp.status_code == 400


@pytest.mark.integration
@pytest.mark.asyncio
async def test_password_change_weak_new_password(client, activated_user):
    """Test password change with weak new password."""
    resp = await client.post(
        "/api/v1/accounts/password-change/",
        json={
            "old_password": activated_user["password"],
            "new_password": "123"
        },
        headers=activated_user["headers"]
    )
    assert resp.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_registration_same_email(client, seed_user_groups):
    """Test that duplicate email registration is properly handled."""
    user_data = {
        "email": "testuser@gmail.com",
        "password": "StrongPassword123!"
    }
    resp1 = await client.post("/api/v1/accounts/register/", json=user_data)
    resp2 = await client.post("/api/v1/accounts/register/", json=user_data)

    assert resp1.status_code == 201
    assert resp2.status_code == 409
