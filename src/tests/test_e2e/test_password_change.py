import uuid

import pytest


@pytest.mark.e2e
async def test_password_change_flow(client, user_data, admin_token):
    """Test complete password change workflow."""
    unique_user_data = user_data.copy()
    unique_user_data["email"] = f"api_login_{uuid.uuid4().hex[:8]}@example.com"
    unique_user_data["username"] = f"api_login_{uuid.uuid4().hex[:8]}"

    await client.post("/api/v1/accounts/register/", json=user_data)

    admin_headers = {
        "Authorization": f"Bearer {admin_token}"
    }
    activation_data = {"email": unique_user_data["email"]}
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
    new_password = "NewPassword123!"

    change_resp = await client.post(
        "/api/v1/accounts/password-change/",
        json={
            "old_password": user_data["password"],
            "new_password": new_password
        },
        headers=headers
    )
    assert change_resp.status_code == 200

    old_login_resp = await client.post(
        "/api/v1/accounts/login/",
        json={"email": user_data["email"], "password": user_data["password"]},
        headers={"Content-Type": "application/json"}
    )
    assert old_login_resp.status_code == 401

    new_login_resp = await client.post(
        "/api/v1/accounts/login/",
        json={"email": user_data["email"], "password": user_data["password"]},
        headers={"Content-Type": "application/json"}
    )

    assert new_login_resp.status_code == 200
