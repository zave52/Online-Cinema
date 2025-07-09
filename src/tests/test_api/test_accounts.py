import uuid

import pytest


@pytest.mark.anyio
async def test_register_success(client, user_data):
    """Test successful user registration."""
    unique_user_data = user_data.copy()
    unique_user_data["email"] = f"api_test_{uuid.uuid4().hex[:8]}@example.com"
    unique_user_data["username"] = f"api_test_{uuid.uuid4().hex[:8]}"

    resp = await client.post(
        "/api/v1/accounts/register/",
        json=unique_user_data
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["email"] == unique_user_data["email"]


@pytest.mark.anyio
async def test_register_duplicate(client, user_data):
    """Test duplicate registration."""
    unique_user_data = user_data.copy()
    unique_user_data["email"] = f"api_dup_{uuid.uuid4().hex[:8]}@example.com"
    unique_user_data["username"] = f"api_dup_{uuid.uuid4().hex[:8]}"

    await client.post("/api/v1/accounts/register/", json=unique_user_data)
    resp = await client.post(
        "/api/v1/accounts/register/",
        json=unique_user_data
    )
    assert resp.status_code == 409
    assert "detail" in resp.json()


@pytest.mark.anyio
async def test_login_success(client, user_data, admin_token):
    """Test successful login."""
    unique_user_data = user_data.copy()
    unique_user_data["email"] = f"api_login_{uuid.uuid4().hex[:8]}@example.com"
    unique_user_data["username"] = f"api_login_{uuid.uuid4().hex[:8]}"

    await client.post("/api/v1/accounts/register/", json=unique_user_data)

    admin_headers = {
        "Authorization": f"Bearer {admin_token}"
    }
    activation_data = {"email": unique_user_data["email"]}
    await client.post(
        "/api/v1/accounts/admin/users/activate/",
        json=activation_data,
        headers=admin_headers
    )

    resp = await client.post(
        "/api/v1/accounts/login/",
        json={
            "email": unique_user_data["email"],
            "password": unique_user_data["password"]
        },
        headers={"Content-Type": "application/json"}
    )

    data = resp.json()

    assert resp.status_code == 200
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.anyio
async def test_login_invalid_password(client, user_data, admin_token):
    """Test login with invalid password."""
    unique_user_data = user_data.copy()
    unique_user_data["email"] = (
        f"api_invalid_{uuid.uuid4().hex[:8]}@example.com"
    )
    unique_user_data["username"] = f"api_invalid_{uuid.uuid4().hex[:8]}"

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
            "email": unique_user_data["email"],
            "password": "WrongPassword123!"
        },
        headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 401
    assert "detail" in resp.json()


@pytest.mark.anyio
async def test_login_nonexistent_user(client):
    """Test login with non-existent user."""
    resp = await client.post(
        "/api/v1/accounts/login/",
        json={
            "email": "nonexistent@example.com",
            "password": "ValidPassword123!"
        },
        headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_register_invalid_email_format(client, user_data):
    """Test registration with invalid email format."""
    invalid_data = user_data.copy()
    invalid_data["email"] = "not-an-email"
    resp = await client.post("/api/v1/accounts/register/", json=invalid_data)
    assert resp.status_code == 422
    error_data = resp.json()
    assert "detail" in error_data


@pytest.mark.anyio
async def test_register_weak_password(client, user_data):
    """Test registration with weak password."""
    weak_data = user_data.copy()
    weak_data["password"] = "123"
    resp = await client.post("/api/v1/accounts/register/", json=weak_data)
    assert resp.status_code == 422
    error_data = resp.json()
    assert "detail" in error_data


@pytest.mark.anyio
async def test_register_missing_fields(client):
    """Test registration with missing required fields."""
    resp = await client.post("/api/v1/accounts/register/", json={})
    assert resp.status_code == 422
    error_data = resp.json()
    assert "detail" in error_data


@pytest.mark.anyio
async def test_token_verification_valid(client, user_data, admin_token):
    """Test token verification with valid token."""
    await client.post("/api/v1/accounts/register/", json=user_data)

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
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

    if login_resp.status_code == 200:
        token = login_resp.json()["access_token"]
        verify_resp = await client.post(
            "/api/v1/accounts/verify/",
            json={"access_token": token}
        )
        assert verify_resp.status_code == 200


@pytest.mark.anyio
async def test_token_verification_invalid(client):
    """Test token verification with invalid token."""
    resp = await client.post(
        "/api/v1/accounts/verify/",
        json={"access_token": "invalid_token"}
    )
    assert resp.status_code == 401
