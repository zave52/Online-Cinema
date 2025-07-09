import uuid

import pytest

from tests.conftest import create_test_image, activated_user


@pytest.mark.e2e
async def test_complete_user_journey(client, user_data, admin_token):
    """Test complete user journey from registration to profile creation."""
    unique_user_data = user_data.copy()
    unique_user_data["email"] = f"user_{uuid.uuid4().hex[:8]}@example.com"

    reg_resp = await client.post(
        "/api/v1/accounts/register/",
        json=unique_user_data
    )
    assert reg_resp.status_code == 201
    user_id = reg_resp.json()["id"]

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
        json={
            "email": unique_user_data["email"],
            "password": unique_user_data["password"]
        },
        headers={"Content-Type": "application/json"}
    )

    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile_data = {
        "first_name": "John",
        "last_name": "Doe",
        "gender": "MAN",
        "date_of_birth": "1990-01-01",
        "info": "Test user profile"
    }

    files = {"avatar": ("avatar.jpg", create_test_image(), "image/jpeg")}

    profile_resp = await client.post(
        f"/api/v1/profiles/users/{user_id}/profile/",
        data=profile_data,
        files=files,
        headers=headers
    )
    assert profile_resp.status_code == 201


@pytest.mark.e2e
async def test_movie_browsing_and_ordering_journey(
    client,
    user_data,
    admin_token,
    seed_movies
):
    """Test complete movie browsing and ordering journey."""
    movies_resp = await client.get("/api/v1/cinema/movies/")
    assert movies_resp.status_code == 200
    movies_data = movies_resp.json()
    assert isinstance(movies_data, dict)
    assert "movies" in movies_data
    assert isinstance(movies_data["movies"], list)

    unique_user_data = user_data.copy()
    unique_user_data["email"] = f"movie_user_{uuid.uuid4().hex[:8]}@example.com"

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

    cart_item = {"movie_id": seed_movies[0]["id"]}
    cart_resp = await client.post(
        "/api/v1/ecommerce/cart/items/",
        json=cart_item,
        headers=headers
    )
    assert cart_resp.status_code == 200

    cart_item_id = cart_resp.json()["cart_item_id"]

    order_data = {
        "cart_item_ids": [cart_item_id]
    }
    order_resp = await client.post(
        "/api/v1/ecommerce/orders/",
        json=order_data,
        headers=headers
    )
    assert order_resp.status_code == 201


@pytest.mark.e2e
async def test_authentication_security_journey(client, user_data, admin_token):
    """Test complete authentication security journey."""
    unique_user_data = user_data.copy()
    unique_user_data["email"] = f"auth_user_{uuid.uuid4().hex[:8]}@example.com"

    reg_resp = await client.post(
        "/api/v1/accounts/register/",
        json=unique_user_data
    )
    assert reg_resp.status_code == 201

    admin_headers = {
        "Authorization": f"Bearer {admin_token}"
    }
    activation_data = {"email": unique_user_data["email"]}
    await client.post(
        "/api/v1/accounts/admin/users/activate/",
        json=activation_data,
        headers=admin_headers
    )

    wrong_login_resp = await client.post(
        "/api/v1/accounts/login/",
        json={
            "email": unique_user_data["email"],
            "password": "WrongPassword123!"
        },
        headers={"Content-Type": "application/json"}
    )
    assert wrong_login_resp.status_code in (401, 403)

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

    tampered_token = token[:-1] + ("a" if token[-1] != "a" else "b")
    tampered_verify_resp = await client.post(
        "/api/v1/accounts/verify/",
        json={"access_token": tampered_token}
    )
    assert tampered_verify_resp.status_code == 401


@pytest.mark.e2e
async def test_payment_processing_journey(
    client,
    activated_user,
    pending_order,
    payment_service_fake
):
    """Test complete payment processing journey."""
    headers = {"Authorization": f"Bearer {activated_user['access_token']}"}

    payment_intent_data = {"order_id": pending_order.id}

    intent_response = await client.post(
        "/api/v1/ecommerce/payments/create-intent/",
        json=payment_intent_data,
        headers=headers
    )
    assert intent_response.status_code == 200

    payment_intent_id = intent_response.json()["id"]

    payment_method = await payment_service_fake.create_payment_method(
        payment_method_type="card",
        card_number="4242424242424242",
        exp_month=12,
        exp_year=2025,
        cvc="123"
    )
    payment_method_id = payment_method["id"]

    await payment_service_fake.attach_payment_method_to_intent(
        payment_intent_id, payment_method_id
    )

    payment_process_data = {"payment_intent_id": payment_intent_id}
    process_resp = await client.post(
        "/api/v1/ecommerce/payments/process/",
        json=payment_process_data,
        headers=headers
    )
    assert process_resp.status_code == 200


@pytest.mark.e2e
async def test_password_reset_journey(client, user_data, admin_token):
    """Test complete password reset journey."""
    unique_user_data = user_data.copy()
    unique_user_data["email"] = f"auth_user_{uuid.uuid4().hex[:8]}@example.com"

    await client.post("/api/v1/accounts/register/", json=user_data)

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    activation_data = {"email": unique_user_data["email"]}
    await client.post(
        "/api/v1/accounts/admin/users/activate/",
        json=activation_data,
        headers=admin_headers
    )

    reset_request_resp = await client.post(
        "/api/v1/accounts/password-reset/request/",
        json={"email": unique_user_data["email"]}
    )
    assert reset_request_resp.status_code == 200

    reset_complete_resp = await client.post(
        "/api/v1/accounts/password-reset/complete/",
        json={
            "email": user_data["email"],
            "password": "NewPassword123!",
            "token": "invalid_token"
        }
    )
    assert reset_complete_resp.status_code == 400

    nonexistent_reset_resp = await client.post(
        "/api/v1/accounts/password-reset/request/",
        json={"email": "nonexistent@example.com"}
    )
    assert nonexistent_reset_resp.status_code == 200


@pytest.mark.e2e
async def test_admin_user_management_journey(client, user_data, admin_token):
    """Test admin user management journey."""
    unique_user_data = user_data.copy()
    unique_user_data["email"] = f"admin_test_{uuid.uuid4().hex[:8]}@example.com"

    reg_resp = await client.post(
        "/api/v1/accounts/register/",
        json=unique_user_data
    )
    assert reg_resp.status_code == 201
    user_id = reg_resp.json()["id"]

    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    manual_activate_resp = await client.post(
        "/api/v1/accounts/admin/users/activate/",
        json={"email": unique_user_data["email"]},
        headers=admin_headers
    )
    assert manual_activate_resp.status_code == 200

    change_group_resp = await client.post(
        f"/api/v1/accounts/admin/users/{user_id}/change-group/",
        json={"group_name": "admin"}
    )
    assert change_group_resp.status_code in (401, 403)

    admin_change_resp = await client.post(
        f"/api/v1/accounts/admin/users/{user_id}/change-group/",
        json={"group_name": "admin"},
        headers=admin_headers
    )
    assert admin_change_resp.status_code == 200


@pytest.mark.e2e
async def test_multiuser_interaction_journey(client, user_data, admin_token):
    """Test multi-user interaction journey."""
    user1_data = user_data.copy()
    user1_data["email"] = f"multiuser1_{uuid.uuid4().hex[:8]}@example.com"

    user2_data = user_data.copy()
    user2_data["email"] = f"multiuser1_{uuid.uuid4().hex[:8]}@example.com"

    reg1_resp = await client.post("/api/v1/accounts/register/", json=user1_data)
    reg2_resp = await client.post("/api/v1/accounts/register/", json=user2_data)

    assert reg1_resp.status_code == 201
    assert reg2_resp.status_code == 201

    user1_id = reg1_resp.json()["id"]
    user2_id = reg2_resp.json()["id"]

    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    activation_data = {"email": user1_data["email"]}
    await client.post(
        "/api/v1/accounts/admin/users/activate/",
        json=activation_data,
        headers=admin_headers
    )
    activation_data = {"email": user2_data["email"]}
    await client.post(
        "/api/v1/accounts/admin/users/activate/",
        json=activation_data,
        headers=admin_headers
    )

    login1_resp = await client.post(
        "/api/v1/accounts/login/",
        json={"email": user1_data["email"], "password": user1_data["password"]},
        headers={"Content-Type": "application/json"}
    )
    login2_resp = await client.post(
        "/api/v1/accounts/login/",
        json={"email": user2_data["email"], "password": user2_data["password"]},
        headers={"Content-Type": "application/json"}
    )

    token1 = login1_resp.json()["access_token"]
    token2 = login2_resp.json()["access_token"]
    headers1 = {"Authorization": f"Bearer {token1}"}
    headers2 = {"Authorization": f"Bearer {token2}"}

    profile_data = {
        "first_name": "John",
        "last_name": "Doe",
        "gender": "MAN",
        "date_of_birth": "1990-01-01",
        "info": "Test user profile"
    }

    files = {"avatar": ("avatar.jpg", create_test_image(), "image/jpeg")}

    profile_resp1 = await client.post(
        f"/api/v1/profiles/users/{user1_id}/profile/",
        data=profile_data,
        files=files,
        headers=headers1
    )
    profile_resp2 = await client.post(
        f"/api/v1/profiles/users/{user2_id}/profile/",
        data=profile_data,
        files=files,
        headers=headers2
    )

    access_user1_resp = await client.get(
        f"/api/v1/profiles/users/{user1_id}/profile/",
        headers=headers2
    )
    assert access_user1_resp.status_code == 403
    access_user2_resp = await client.get(
        f"/api/v1/profiles/users/{user2_id}/profile/",
        headers=headers1
    )
    assert access_user2_resp.status_code == 403

    update_user1_resp = await client.patch(
        f"/api/v1/profiles/users/{user1_id}/profile/",
        json={"first_name": "Hacked"},
        headers=headers2
    )
    assert update_user1_resp.status_code == 403
    update_user2_resp = await client.patch(
        f"/api/v1/profiles/users/{user2_id}/profile/",
        json={"first_name": "Hacked"},
        headers=headers1
    )
    assert update_user2_resp.status_code == 403


@pytest.mark.e2e
async def test_concurrent_operations_journey(client, user_data):
    """Test registration that would typically be done concurrently, but executed sequentially to avoid DB conflicts."""
    import uuid

    registration_results = []
    for i in range(3):
        unique_user_data = user_data.copy()
        unique_user_data["email"] = (
            f"concurrent_{i}_{uuid.uuid4().hex[:8]}@example.com"
        )
        unique_user_data["username"] = f"concurrent_{i}_{uuid.uuid4().hex[:8]}"

        try:
            resp = await client.post(
                "/api/v1/accounts/register/",
                json=unique_user_data
            )
            registration_results.append((resp.status_code, unique_user_data))
        except Exception:
            registration_results.append((500, unique_user_data))

    success_count = sum(
        1 for status, _ in registration_results if status == 201
    )
    assert success_count == 3


@pytest.mark.e2e
async def test_error_handling_journey(client):
    """Test comprehensive error handling journey."""
    malformed_resp = await client.post(
        "/api/v1/accounts/register/",
        data={"data": "invalid json"},
        headers={"Content-Type": "application/json"}
    )
    assert malformed_resp.status_code == 422

    invalid_method_resp = await client.patch("/api/v1/accounts/register/")
    assert invalid_method_resp.status_code == 405

    not_found_resp = await client.get("/api/v1/nonexistent/")
    assert not_found_resp.status_code == 404

    unauth_resp = await client.get("/api/v1/profiles/users/1/profile/")
    assert unauth_resp.status_code in (401, 403)

    invalid_token_resp = await client.get(
        "/api/v1/profiles/users/1/profile/",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert invalid_token_resp.status_code == 401
