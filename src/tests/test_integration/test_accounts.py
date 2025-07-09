import uuid

import pytest


@pytest.mark.integration
async def test_register_success(client, user_data):
    """Test successful user registration."""
    unique_user_data = user_data.copy()
    unique_user_data[
        "email"] = f"integration_{uuid.uuid4().hex[:8]}@example.com"

    response = await client.post(
        "/api/v1/accounts/register/",
        json=unique_user_data
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["email"] == unique_user_data["email"]


@pytest.mark.integration
async def test_register_invalid_email(client, user_data):
    """Test registration with an invalid email address."""
    bad_data = user_data.copy()
    bad_data["email"] = "not-an-email"
    response = await client.post("/api/v1/accounts/register/", json=bad_data)
    assert response.status_code == 422


@pytest.mark.integration
@pytest.mark.anyio
async def test_login_success(client, user_data, admin_token):
    """Test successful login after registration."""
    unique_user_data = user_data.copy()
    unique_user_data["email"] = f"login_test_{uuid.uuid4().hex[:8]}@example.com"

    await client.post("/api/v1/accounts/register/", json=unique_user_data)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    activation_data = {"email": unique_user_data["email"]}
    await client.post(
        "/api/v1/accounts/admin/users/activate/",
        json=activation_data,
        headers=admin_headers
    )
    response = await client.post(
        "/api/v1/accounts/login/",
        json={
            "email": unique_user_data["email"],
            "password": unique_user_data["password"]
        },
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.integration
async def test_login_wrong_password(client, user_data, admin_token):
    """Test login with wrong password."""
    unique_user_data = user_data.copy()
    unique_user_data["email"] = f"wrong_pass_{uuid.uuid4().hex[:8]}@example.com"

    await client.post("/api/v1/accounts/register/", json=unique_user_data)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    activation_data = {"email": unique_user_data["email"]}
    await client.post(
        "/api/v1/accounts/admin/users/activate/",
        json=activation_data,
        headers=admin_headers
    )
    response = await client.post(
        "/api/v1/accounts/login/",
        json={
            "email": unique_user_data["email"],
            "password": "WrongPassword123!"
        },
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 401


@pytest.mark.integration
async def test_profile_me(client, user_data, admin_token):
    """Test getting user's own profile."""
    unique_user_data = user_data.copy()
    unique_user_data["email"] = f"profile_me_{uuid.uuid4().hex[:8]}@example.com"

    reg_resp = await client.post(
        "/api/v1/accounts/register/",
        json=unique_user_data
    )
    user_id = reg_resp.json()["id"]

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    activation_data = {"email": unique_user_data["email"]}
    await client.post(
        "/api/v1/accounts/admin/users/activate/",
        json=activation_data,
        headers=admin_headers
    )

    login_resp = await client.post(
        "/api/v1/accounts/login/",
        json={
            "email": unique_user_data["email"],
            "password": unique_user_data["password"]
        },
        headers={"Content-Type": "application/json"}
    )

    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile_resp = await client.get(
        f"/api/v1/profiles/users/{user_id}/profile/",
        headers=headers
    )
    assert profile_resp.status_code == 404


@pytest.mark.integration
async def test_register_duplicate_email(client, user_data):
    """Test registration with duplicate email."""
    unique_user_data = user_data.copy()
    unique_user_data["email"] = f"duplicate_{uuid.uuid4().hex[:8]}@example.com"

    await client.post(
        "/api/v1/accounts/register/",
        json=unique_user_data
    )

    duplicate_data = unique_user_data.copy()

    resp = await client.post(
        "/api/v1/accounts/register/",
        json=duplicate_data
    )
    assert resp.status_code == 409


@pytest.mark.integration
async def test_register_weak_password(client, user_data):
    """Test registration with a weak password."""
    weak_data = user_data.copy()
    weak_data["password"] = "123"
    resp = await client.post(
        "/api/v1/accounts/register/",
        json=weak_data
    )
    assert resp.status_code == 422


@pytest.mark.integration
async def test_login_inactive_user(client, user_data):
    """Test login for an inactive user (if activation is required)."""
    unique_user_data = user_data.copy()
    unique_user_data["email"] = f"inactive_{uuid.uuid4().hex[:8]}@example.com"

    await client.post(
        "/api/v1/accounts/register/",
        json=unique_user_data
    )
    resp = await client.post(
        "/api/v1/accounts/login/",
        json={
            "email": unique_user_data["email"],
            "password": unique_user_data["password"]
        },
        headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 403


@pytest.mark.integration
async def test_profile_jwt_tampering(client, user_data, admin_token):
    """Test accessing profile with a tampered JWT token."""
    unique_user_data = user_data.copy()
    unique_user_data["email"] = f"jwt_tamper_{uuid.uuid4().hex[:8]}@example.com"

    reg_resp = await client.post(
        "/api/v1/accounts/register/",
        json=unique_user_data
    )
    user_id = reg_resp.json()["id"]

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    activation_data = {"email": unique_user_data["email"]}
    await client.post(
        "/api/v1/accounts/admin/users/activate/",
        json=activation_data,
        headers=admin_headers
    )

    login_resp = await client.post(
        "/api/v1/accounts/login/",
        json={
            "email": unique_user_data["email"],
            "password": unique_user_data["password"]
        },
        headers={"Content-Type": "application/json"}
    )
    token = login_resp.json()["access_token"]
    tampered_token = token[:-1] + ("a" if token[-1] != "a" else "b")
    headers = {"Authorization": f"Bearer {tampered_token}"}
    resp = await client.get(
        f"/api/v1/profiles/users/{user_id}/profile/",
        headers=headers
    )
    assert resp.status_code == 401


@pytest.mark.integration
async def test_register_missing_fields(client):
    """Test registration with missing required fields."""
    resp = await client.post(
        "/api/v1/accounts/register/",
        json={"email": "user@example.com"}
    )
    assert resp.status_code == 422


@pytest.mark.integration
async def test_login_nonexistent_user(client):
    """Test login with a non-existent user."""
    resp = await client.post(
        "/api/v1/accounts/login/",
        json={"email": "nouser@example.com", "password": "StrongPassword123!"},
        headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 401


@pytest.mark.integration
async def test_login_missing_fields(client):
    """Test login with missing required fields."""
    resp = await client.post(
        "/api/v1/accounts/login/",
        json={"email": "user@example.com"},
        headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 422


@pytest.mark.integration
async def test_profile_invalid_update(client, user_data, admin_token):
    """Test updating the user's profile with invalid data."""
    unique_user_data = user_data.copy()
    unique_user_data["email"] = f"partial_{uuid.uuid4().hex[:8]}@example.com"

    reg_resp = await client.post(
        "/api/v1/accounts/register/",
        json=unique_user_data
    )
    user_id = reg_resp.json()["id"]

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    activation_data = {"email": unique_user_data["email"]}
    await client.post(
        "/api/v1/accounts/admin/users/activate/",
        json=activation_data,
        headers=admin_headers
    )

    login_resp = await client.post(
        "/api/v1/accounts/login/",
        json={
            "email": unique_user_data["email"],
            "password": unique_user_data["password"]
        },
        headers={"Content-Type": "application/json"}
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.patch(
        f"/api/v1/profiles/users/{user_id}/profile/",
        json={"first_name": "Partial"}, headers=headers
    )
    assert resp.status_code == 404


@pytest.mark.integration
async def test_profile_unauthorized_update(client):
    """Test unauthorized update of the user's profile."""
    resp = await client.patch(
        "/api/v1/profiles/users/1/profile/",
        json={"first_name": "NoAuth"}
    )
    assert resp.status_code in (401, 403)


@pytest.mark.integration
async def test_profile_access_another_user(client, activated_user):
    """Test that a user cannot access another user's profile (if not allowed)."""
    headers1 = activated_user["headers"]

    user2_data = {
        "email": f"user2_{uuid.uuid4().hex[:8]}@example.com",
        "password": "StrongPass123!"
    }
    reg_resp2 = await client.post("/api/v1/accounts/register/", json=user2_data)
    user_id2 = reg_resp2.json()["id"]

    resp = await client.get(
        f"/api/v1/profiles/users/{user_id2}/profile/",
        headers=headers1
    )
    assert resp.status_code == 403


@pytest.mark.integration
async def test_profile_missing_jwt(client):
    """Test accessing the user's profile without a JWT token."""
    resp = await client.get("/api/v1/profiles/users/1/profile/")
    assert resp.status_code == 403


@pytest.mark.integration
async def test_password_reset_invalid_email(client):
    """Test password reset with an invalid email address."""
    resp = await client.post(
        "/api/v1/accounts/password-reset/request/",
        json={"email": "nonexistent@example.com"}
    )
    assert resp.status_code == 200


@pytest.mark.integration
async def test_password_change_wrong_old_password(client, activated_user):
    """Test password change with a wrong old password."""
    headers = activated_user["headers"]

    resp = await client.post(
        "/api/v1/accounts/password-change/",
        json={
            "old_password": "wrongpassword",
            "new_password": "NewPassword123!"
        },
        headers=headers
    )
    assert resp.status_code == 401


@pytest.mark.integration
async def test_profile_update_another_user_forbidden(client, activated_user):
    """Test that a user cannot update another user's profile."""
    user_id1 = activated_user["user_id"]
    headers1 = activated_user["headers"]

    user2_data = {
        "email": f"user2_{uuid.uuid4().hex[:8]}@example.com",
        "password": "StrongPass123!"
    }
    reg_resp2 = await client.post("/api/v1/accounts/register/", json=user2_data)
    user_id2 = reg_resp2.json()["id"]

    resp = await client.patch(
        f"/api/v1/profiles/users/{user_id2}/profile/",
        json={"first_name": "Forbidden"}, headers=headers1
    )
    assert resp.status_code == 403


@pytest.mark.integration
async def test_password_reset_with_invalid_token(
    client,
    user_data,
    admin_token
):
    """Test password reset with an invalid or expired token."""
    await client.post("/api/v1/accounts/register/", json=user_data)

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    activation_data = {"email": user_data["email"]}
    await client.post(
        "/api/v1/accounts/admin/users/activate/",
        json=activation_data,
        headers=admin_headers
    )

    resp = await client.post(
        "/api/v1/accounts/password-reset/complete/",
        json={
            "email": user_data["email"],
            "password": "NewPassword123!",
            "token": "definitely_invalid_token"
        }
    )
    assert resp.status_code == 400


@pytest.mark.integration
async def test_register_empty_password(client, user_data):
    """Test registration with empty password."""
    bad_data = user_data.copy()
    bad_data["password"] = ""
    resp = await client.post("/api/v1/accounts/register/", json=bad_data)
    assert resp.status_code == 422


@pytest.mark.integration
async def test_register_empty_email(client, user_data):
    """Test registration with empty email."""
    bad_data = user_data.copy()
    bad_data["email"] = ""
    resp = await client.post("/api/v1/accounts/register/", json=bad_data)
    assert resp.status_code == 422


@pytest.mark.integration
async def test_register_very_long_email(client, user_data):
    """Test registration with very long email."""
    bad_data = user_data.copy()
    bad_data["email"] = "a" * 300 + "@example.com"
    resp = await client.post("/api/v1/accounts/register/", json=bad_data)
    assert resp.status_code == 422


@pytest.mark.integration
async def test_register_sql_injection_attempt(client, user_data):
    """Test registration with SQL injection attempt."""
    bad_data = user_data.copy()
    bad_data["email"] = "admin@example.com'; DROP TABLE users; --"
    resp = await client.post("/api/v1/accounts/register/", json=bad_data)
    assert resp.status_code == 422


@pytest.mark.integration
async def test_login_case_insensitive_email(client, user_data, admin_token):
    """Test login with different case email."""
    unique_user_data = user_data.copy()
    unique_user_data["email"] = f"login_test_{uuid.uuid4().hex[:8]}@example.com"

    await client.post("/api/v1/accounts/register/", json=unique_user_data)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    activation_data = {"email": unique_user_data["email"]}
    await client.post(
        "/api/v1/accounts/admin/users/activate/",
        json=activation_data,
        headers=admin_headers
    )
    resp = await client.post(
        "/api/v1/accounts/login/",
        json={
            "email": unique_user_data["email"].upper(),
            "password": unique_user_data["password"]
        },
        headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 200


@pytest.mark.integration
async def test_token_verification(client, user_data, admin_token):
    """Test token verification endpoint."""
    unique_user_data = user_data.copy()
    unique_user_data["email"] = f"login_test_{uuid.uuid4().hex[:8]}@example.com"

    await client.post("/api/v1/accounts/register/", json=unique_user_data)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    activation_data = {"email": unique_user_data["email"]}
    await client.post(
        "/api/v1/accounts/admin/users/activate/",
        json=activation_data,
        headers=admin_headers
    )
    login_resp = await client.post(
        "/api/v1/accounts/login/",
        json={
            "email": unique_user_data["email"],
            "password": unique_user_data["password"]
        },
        headers={"Content-Type": "application/json"}
    )

    token = login_resp.json()["access_token"]

    verify_resp = await client.post(
        "/api/v1/accounts/verify/",
        json={"access_token": token}
    )
    assert verify_resp.status_code == 200


@pytest.mark.integration
async def test_token_verification_invalid(client):
    """Test token verification with invalid token."""
    resp = await client.post(
        "/api/v1/accounts/verify/",
        json={"access_token": "invalid_token"}
    )
    assert resp.status_code == 401


@pytest.mark.integration
async def test_refresh_token_flow(client, user_data, admin_token):
    """Test refresh token flow."""
    unique_user_data = user_data.copy()
    unique_user_data["email"] = f"login_test_{uuid.uuid4().hex[:8]}@example.com"

    await client.post("/api/v1/accounts/register/", json=unique_user_data)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    activation_data = {"email": unique_user_data["email"]}
    await client.post(
        "/api/v1/accounts/admin/users/activate/",
        json=activation_data,
        headers=admin_headers
    )
    login_resp = await client.post(
        "/api/v1/accounts/login/",
        json={
            "email": unique_user_data["email"],
            "password": unique_user_data["password"]
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
async def test_refresh_token_invalid(client):
    """Test refresh token with invalid token."""
    resp = await client.post(
        "/api/v1/accounts/refresh/",
        json={"refresh_token": "invalid_refresh_token"}
    )
    assert resp.status_code == 400


@pytest.mark.integration
async def test_logout_flow(client, user_data, admin_token):
    """Test logout flow."""
    unique_user_data = user_data.copy()
    unique_user_data["email"] = f"login_test_{uuid.uuid4().hex[:8]}@example.com"

    await client.post("/api/v1/accounts/register/", json=unique_user_data)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    activation_data = {"email": unique_user_data["email"]}
    await client.post(
        "/api/v1/accounts/admin/users/activate/",
        json=activation_data,
        headers=admin_headers
    )

    login_resp = await client.post(
        "/api/v1/accounts/login/",
        json={
            "email": unique_user_data["email"],
            "password": unique_user_data["password"]
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
async def test_password_change_same_password(client, activated_user):
    """Test password change with same old and new password."""
    headers = activated_user["headers"]
    resp = await client.post(
        "/api/v1/accounts/password-change/",
        json={
            "old_password": activated_user["password"],
            "new_password": activated_user["password"]
        },
        headers=headers
    )
    assert resp.status_code == 400


@pytest.mark.integration
async def test_password_change_weak_new_password(client, activated_user):
    """Test password change with weak new password."""
    headers = activated_user["headers"]
    resp = await client.post(
        "/api/v1/accounts/password-change/",
        json={
            "old_password": activated_user["password"],
            "new_password": "123"
        },
        headers=headers
    )
    assert resp.status_code == 422


@pytest.mark.integration
async def test_concurrent_registration_same_email(client, user_data):
    """Test that duplicate email registration is properly handled."""
    base_email = f"duplicate_test_{uuid.uuid4().hex[:8]}@example.com"
    user_payload = {"email": base_email, "password": user_data["password"]}

    resp1 = await client.post("/api/v1/accounts/register/", json=user_payload)
    resp2 = await client.post("/api/v1/accounts/register/", json=user_payload)

    assert resp1.status_code == 201
    assert resp2.status_code == 409
