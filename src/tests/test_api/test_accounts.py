import pytest


@pytest.mark.api
@pytest.mark.asyncio
async def test_register_success(client, seed_user_groups):
    """Test successful user registration."""
    user_data = {
        "email": "test@gmail.com",
        "password": "StrongPassword123!"
    }

    resp = await client.post(
        "/api/v1/accounts/register/",
        json=user_data
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["email"] == user_data["email"]


@pytest.mark.api
@pytest.mark.asyncio
async def test_register_duplicate(client, seed_user_groups):
    """Test duplicate registration."""
    user_data = {
        "email": "test@gmail.com",
        "password": "StrongPassword123!"
    }

    await client.post("/api/v1/accounts/register/", json=user_data)
    resp = await client.post(
        "/api/v1/accounts/register/",
        json=user_data
    )
    assert resp.status_code == 409
    assert "detail" in resp.json()


@pytest.mark.api
@pytest.mark.asyncio
async def test_login_success(client, activated_user):
    """Test successful login."""
    resp = await client.post(
        "/api/v1/accounts/login/",
        json={
            "email": activated_user["email"],
            "password": activated_user["password"]
        },
        headers={"Content-Type": "application/json"}
    )

    data = resp.json()

    assert resp.status_code == 200
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.api
@pytest.mark.asyncio
async def test_login_invalid_password(client, activated_user):
    """Test login with invalid password."""
    resp = await client.post(
        "/api/v1/accounts/login/",
        json={
            "email": activated_user["email"],
            "password": "WrongPassword123!"
        },
        headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 401
    assert "detail" in resp.json()


@pytest.mark.api
@pytest.mark.asyncio
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


@pytest.mark.api
@pytest.mark.asyncio
async def test_register_invalid_email_format(client):
    """Test registration with invalid email format."""
    user_data = {
        "email": "not-an-email",
        "password": "StrongPassword123!"
    }
    resp = await client.post("/api/v1/accounts/register/", json=user_data)
    assert resp.status_code == 422
    error_data = resp.json()
    assert "detail" in error_data


@pytest.mark.api
@pytest.mark.asyncio
async def test_register_weak_password(client):
    """Test registration with weak password."""
    user_data = {
        "email": "test@gmail.com",
        "password": "123"
    }
    resp = await client.post("/api/v1/accounts/register/", json=user_data)
    assert resp.status_code == 422
    error_data = resp.json()
    assert "detail" in error_data


@pytest.mark.api
@pytest.mark.asyncio
async def test_register_missing_fields(client):
    """Test registration with missing required fields."""
    resp = await client.post("/api/v1/accounts/register/", json={})
    assert resp.status_code == 422
    error_data = resp.json()
    assert "detail" in error_data


@pytest.mark.api
@pytest.mark.asyncio
async def test_token_verification_valid(client, activated_user):
    """Test token verification with valid token."""
    token = activated_user["access_token"]
    verify_resp = await client.post(
        "/api/v1/accounts/verify/",
        json={"access_token": token}
    )
    assert verify_resp.status_code == 200


@pytest.mark.api
@pytest.mark.asyncio
async def test_token_verification_invalid(client):
    """Test token verification with invalid token."""
    resp = await client.post(
        "/api/v1/accounts/verify/",
        json={"access_token": "invalid_token"}
    )
    assert resp.status_code == 401
