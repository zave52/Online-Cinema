import pytest


@pytest.mark.anyio
async def test_create_payment_unauthorized(client):
    payment_data = {
        "order_id": 1
    }
    resp = await client.post(
        "/api/v1/ecommerce/payments/create-intent/",
        json=payment_data
    )
    assert resp.status_code in (401, 403)


@pytest.mark.anyio
async def test_create_payment_invalid_order(client, activated_user):
    """Test payment with invalid order id."""
    headers = {"Authorization": f"Bearer {activated_user['access_token']}"}

    payment_data = {"order_id": 1000}

    resp = await client.post(
        "/api/v1/ecommerce/payments/create-intent/",
        json=payment_data,
        headers=headers
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_create_payment_missing_fields(client, activated_user):
    """Test payment with missing required fields."""
    headers = {"Authorization": f"Bearer {activated_user['access_token']}"}

    resp = await client.post(
        "/api/v1/ecommerce/payments/create-intent/",
        json={},
        headers=headers
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_get_payment_status(
    client,
    activated_user,
    pending_order,
    payment_service_fake
):
    """Test full payment journey: create intent, create payment method, attach method, confirm payment, and check status."""
    headers = {"Authorization": f"Bearer {activated_user['access_token']}"}

    payment_intent_data = {"order_id": pending_order.id}

    resp = await client.post(
        "/api/v1/ecommerce/payments/create-intent/",
        json=payment_intent_data,
        headers=headers
    )
    assert resp.status_code == 200
    intent_response = resp.json()
    payment_intent_id = intent_response["id"]

    assert payment_intent_id.startswith("pi_test_")
    assert "client_secret" in intent_response
    assert intent_response["currency"] == "usd"

    payment_method = await payment_service_fake.create_payment_method(
        payment_method_type="card",
        card_number="4242424242424242",
        exp_month=12,
        exp_year=2025,
        cvc="123"
    )
    assert payment_method["id"].startswith("pm_test_")
    assert payment_method["type"] == "card"
    assert payment_method["card"]["brand"] == "visa"
    assert payment_method["card"]["last4"] == "4242"
    payment_method_id = payment_method["id"]

    attached_intent = await payment_service_fake.attach_payment_method_to_intent(
        payment_intent_id, payment_method_id
    )
    assert attached_intent["id"] == payment_intent_id
    assert attached_intent["payment_method"] == payment_method_id
    assert attached_intent["status"] == "requires_confirmation"

    payment_process_data = {"payment_intent_id": payment_intent_id}
    process_resp = await client.post(
        "/api/v1/ecommerce/payments/process/",
        json=payment_process_data,
        headers=headers
    )
    assert process_resp.status_code == 200

    resp = await client.get(
        "/api/v1/ecommerce/payments/1/",
        headers=headers
    )
    assert resp.status_code == 200
    payment_data = resp.json()
    assert payment_data["external_payment_id"] == payment_intent_id
    assert payment_data["status"] == "successful"


@pytest.mark.anyio
async def test_full_payment_journey_with_order_completion(
    client,
    activated_user,
    pending_order,
    payment_service_fake
):
    """Test complete payment journey including order status update."""
    headers = {"Authorization": f"Bearer {activated_user['access_token']}"}

    payment_intent_data = {"order_id": pending_order.id}

    resp = await client.post(
        "/api/v1/ecommerce/payments/create-intent/",
        json=payment_intent_data,
        headers=headers
    )
    assert resp.status_code == 200
    intent_response = resp.json()
    payment_intent_id = intent_response["id"]

    assert payment_intent_id.startswith("pi_test_")
    assert "client_secret" in intent_response
    assert intent_response["currency"] == "usd"

    payment_method = await payment_service_fake.create_payment_method()
    assert payment_method["id"].startswith("pm_test_")
    assert payment_method["type"] == "card"

    attached_intent = await payment_service_fake.attach_payment_method_to_intent(
        payment_intent_id, payment_method["id"]
    )
    assert attached_intent["id"] == payment_intent_id
    assert attached_intent["payment_method"] == payment_method["id"]
    assert attached_intent["status"] == "requires_confirmation"

    payment_process_data = {"payment_intent_id": payment_intent_id}
    process_resp = await client.post(
        "/api/v1/ecommerce/payments/process/",
        json=payment_process_data,
        headers=headers
    )
    assert process_resp.status_code == 200

    resp = await client.get(
        "/api/v1/ecommerce/payments/2/",
        headers=headers
    )
    assert resp.status_code == 200
    payment_data = resp.json()
    assert payment_data["external_payment_id"] == payment_intent_id
    assert payment_data["status"] == "successful"


@pytest.mark.anyio
async def test_payment_journey_with_different_card_types(
    client,
    activated_user,
    pending_order,
    payment_service_fake
):
    """Test payment journey with different card types."""
    headers = {"Authorization": f"Bearer {activated_user['access_token']}"}

    payment_intent_data = {"order_id": pending_order.id}
    resp = await client.post(
        "/api/v1/ecommerce/payments/create-intent/",
        json=payment_intent_data,
        headers=headers
    )
    assert resp.status_code == 200
    intent_response = resp.json()
    payment_intent_id = intent_response["id"]

    assert payment_intent_id.startswith("pi_test_")

    visa_method = await payment_service_fake.create_payment_method(
        card_number="4242424242424242",
        exp_month=12,
        exp_year=2025,
        cvc="123"
    )
    assert visa_method["card"]["brand"] == "visa"
    assert visa_method["card"]["last4"] == "4242"

    mastercard_method = await payment_service_fake.create_payment_method(
        card_number="5555555555554444",
        exp_month=12,
        exp_year=2025,
        cvc="123"
    )
    assert mastercard_method["card"]["brand"] == "mastercard"
    assert mastercard_method["card"]["last4"] == "4444"

    amex_method = await payment_service_fake.create_payment_method(
        card_number="378282246310005",
        exp_month=12,
        exp_year=2025,
        cvc="1234"
    )
    assert amex_method["card"]["brand"] == "amex"
    assert amex_method["card"]["last4"] == "0005"

    attached_intent = await payment_service_fake.attach_payment_method_to_intent(
        payment_intent_id, mastercard_method["id"]
    )
    assert attached_intent["payment_method"] == mastercard_method["id"]

    payment_process_data = {"payment_intent_id": payment_intent_id}
    process_resp = await client.post(
        "/api/v1/ecommerce/payments/process/",
        json=payment_process_data,
        headers=headers
    )
    assert process_resp.status_code == 200

    resp = await client.get(
        f"/api/v1/ecommerce/payments/3/",
        headers=headers
    )
    assert resp.status_code == 200
    status_data = resp.json()
    assert status_data["status"] == "successful"
