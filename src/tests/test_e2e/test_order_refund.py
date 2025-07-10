import pytest


@pytest.mark.e2e
async def test_order_refund_flow(
    client,
    activated_user,
    pending_order,
    payment_service_fake
):
    """Test complete order refund workflow."""
    headers = {"Authorization": f"Bearer {activated_user['access_token']}"}

    order_resp = await client.get(
        f"/api/v1/ecommerce/orders/{pending_order.id}/",
        headers=headers
    )
    order_data = order_resp.json()
    assert order_data["status"] == "pending"

    payment_intent_data = {"order_id": pending_order.id}

    resp = await client.post(
        "/api/v1/ecommerce/payments/create-intent/",
        json=payment_intent_data,
        headers=headers
    )
    intent_response = resp.json()
    payment_intent_id = intent_response["id"]

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
    await client.post(
        "/api/v1/ecommerce/payments/process/",
        json=payment_process_data,
        headers=headers
    )

    order_resp = await client.get(
        f"/api/v1/ecommerce/orders/{pending_order.id}/",
        headers=headers
    )
    order_data = order_resp.json()
    assert order_data["status"] == "paid"

    refund_resp = await client.post(
        f"/api/v1/ecommerce/orders/{pending_order.id}/refund/",
        json={"reason": "requested_by_customer"},
        headers=headers
    )
    assert refund_resp.status_code == 200

    order_resp = await client.get(
        f"/api/v1/ecommerce/orders/{pending_order.id}/",
        headers=headers
    )
    order_data = order_resp.json()
    assert order_data["status"] == "canceled"


@pytest.mark.e2e
async def test_order_refund_validation_flow(client, activated_user):
    """Test order refund validation workflow."""
    headers = {"Authorization": f"Bearer {activated_user['access_token']}"}

    refund_resp = await client.post(
        "/api/v1/ecommerce/orders/99999/refund/",
        json={"reason": "requested_by_customer"},
        headers=headers
    )
    assert refund_resp.status_code in (404, 400)
