import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_payment_nonexistent_order(client, activated_user):
    """Test payment for non-existent order."""
    headers = activated_user["headers"]

    payment_data = {
        "order_id": 9999,
    }
    resp = await client.post(
        "/api/v1/ecommerce/payments/create-intent/",
        json=payment_data,
        headers=headers
    )
    assert resp.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_payment_unauthorized(client):
    """Test payment without authentication."""
    payment_data = {
        "order_id": 1,
    }
    resp = await client.post(
        "/api/v1/ecommerce/payments/create-intent/",
        json=payment_data
    )
    assert resp.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_double_payment_attempt(
    client,
    activated_user,
    pending_order,
    payment_service_fake
):
    """Test attempting to pay for the same order twice."""
    headers = activated_user["headers"]

    payment_intent_data = {"order_id": pending_order.id}
    intent_resp = await client.post(
        "/api/v1/ecommerce/payments/create-intent/",
        json=payment_intent_data,
        headers=headers
    )
    assert intent_resp.status_code == 200
    payment_intent_id = intent_resp.json().get("id")

    payment_method = await payment_service_fake.create_payment_method()
    await payment_service_fake.attach_payment_method_to_intent(
        payment_intent_id,
        payment_method["id"]
    )

    process_payment_data = {"payment_intent_id": payment_intent_id}
    resp1 = await client.post(
        "/api/v1/ecommerce/payments/process/",
        json=process_payment_data,
        headers=headers
    )
    assert resp1.status_code == 200

    resp2 = await client.post(
        "/api/v1/ecommerce/payments/process/",
        json=process_payment_data,
        headers=headers
    )
    assert resp2.status_code == 400


@pytest.mark.integration
@pytest.mark.asyncio
async def test_payment_missing_fields(client, activated_user):
    """Test payment with missing required fields."""
    headers = activated_user["headers"]
    resp = await client.post(
        "/api/v1/ecommerce/payments/create-intent/",
        json={},
        headers=headers
    )
    assert resp.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_payment_success_simulation(
    client,
    activated_user,
    pending_order,
    payment_service_fake
):
    """Test successful payment simulation."""
    headers = activated_user["headers"]

    payment_intent_data = {"order_id": pending_order.id}
    intent_resp = await client.post(
        "/api/v1/ecommerce/payments/create-intent/",
        json=payment_intent_data,
        headers=headers
    )
    assert intent_resp.status_code == 200
    payment_intent_id = intent_resp.json().get("id")

    payment_method = await payment_service_fake.create_payment_method()
    await payment_service_fake.attach_payment_method_to_intent(
        payment_intent_id,
        payment_method["id"]
    )

    process_payment_data = {"payment_intent_id": payment_intent_id}
    resp = await client.post(
        "/api/v1/ecommerce/payments/process/",
        json=process_payment_data,
        headers=headers
    )
    assert resp.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_payment_status_check(
    client,
    activated_user,
    pending_order,
    payment_service_fake
):
    """Test checking payments status."""
    headers = activated_user["headers"]

    resp = await client.get("/api/v1/ecommerce/payments/", headers=headers)
    assert resp.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_payment_list_user_payments(client, activated_user):
    """Test listing user's payments."""
    headers = activated_user["headers"]

    resp = await client.get("/api/v1/ecommerce/payments/", headers=headers)
    assert resp.status_code == 200

    payments = resp.json()
    assert isinstance(payments, dict)
    assert "payments" in payments
    assert isinstance(payments["payments"], list)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_payment_webhook_simulation(client):
    """Test payment webhook endpoint."""
    webhook_data = {
        "event_type": "payment.succeeded",
        "payment_id": "test_payment_123",
        "amount": 1000,
        "currency": "usd"
    }

    resp = await client.post(
        "/api/v1/ecommerce/payments/webhook/",
        json=webhook_data
    )
    assert resp.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_payment_sql_injection_attempt(client, activated_user):
    """Test SQL injection attempt in payment data."""
    headers = activated_user["headers"]

    malicious_payment = {
        "order_id": "1; DROP TABLE payments; --",
    }

    resp = await client.post(
        "/api/v1/ecommerce/payments/create-intent/",
        json=malicious_payment,
        headers=headers
    )
    assert resp.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_payment_negative_order_id(client, activated_user):
    """Test payment with negative order ID."""
    headers = activated_user["headers"]

    negative_payment = {
        "order_id": -1,
    }

    resp = await client.post(
        "/api/v1/ecommerce/payments/create-intent/",
        json=negative_payment,
        headers=headers
    )
    assert resp.status_code == 404
