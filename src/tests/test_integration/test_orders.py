import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_orders_empty(client, activated_user):
    resp = await client.get(
        "/api/v1/ecommerce/orders/",
        headers=activated_user["headers"]
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["orders"] == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_order_unauthorized(client, seed_movies):
    resp = await client.post("/api/v1/ecommerce/orders/", json={})
    assert resp.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_order_missing_data(client, activated_user):
    resp = await client.post(
        "/api/v1/ecommerce/orders/",
        json={},
        headers=activated_user["headers"]
    )
    assert resp.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_order_empty_items(client, activated_user):
    """Test creating order with empty items list."""
    order_data = {"items": []}

    resp = await client.post(
        "/api/v1/ecommerce/orders/",
        json=order_data,
        headers=activated_user["headers"]
    )
    assert resp.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cancel_order(client, activated_user, pending_order):
    """Test order cancellation."""
    resp = await client.delete(
        f"/api/v1/ecommerce/orders/{pending_order['order_id']}/",
        headers=activated_user["headers"]
    )
    assert resp.status_code == 204


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_user_orders(client, activated_user, pending_order):
    """Test getting user's orders."""
    resp = await client.get(
        "/api/v1/ecommerce/orders/",
        headers=activated_user["headers"]
    )
    assert resp.status_code == 200

    orders = resp.json()["orders"]
    assert isinstance(orders, list)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_specific_order(client, activated_user, pending_order):
    """Test getting specific order by ID."""
    resp = await client.get(
        f"/api/v1/ecommerce/orders/{pending_order['order_id']}/",
        headers=activated_user["headers"]
    )
    assert resp.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_orders_unauthorized(client, pending_order):
    """Test getting orders without authentication."""
    resp = await client.get("/api/v1/ecommerce/orders/")
    assert resp.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_order_pagination(client, activated_user):
    """Test order list pagination."""
    resp = await client.get(
        "/api/v1/ecommerce/orders/?page=1&per_page=10",
        headers=activated_user["headers"]
    )
    assert resp.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_order_duplicate_items(client, activated_user, seed_movies):
    """Test creating order with duplicate items."""
    cart_item_data = {"movie_id": seed_movies[0]["id"]}
    cart_resp = await client.post(
        "/api/v1/ecommerce/cart/items/",
        json=cart_item_data,
        headers=activated_user["headers"]
    )
    assert cart_resp.status_code == 200
    cart_item_id = cart_resp.json()["cart_item_id"]

    order_data = {"cart_item_ids": [cart_item_id, cart_item_id]}

    resp = await client.post(
        "/api/v1/ecommerce/orders/",
        json=order_data,
        headers=activated_user["headers"]
    )
    assert resp.status_code == 400


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_order_not_found(client, activated_user, pending_order):
    resp = await client.get(
        "/api/v1/ecommerce/orders/9999/",
        headers=activated_user["headers"]
    )
    assert resp.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_valid_order(client, activated_user, seed_movies):
    headers = activated_user["headers"]
    cart_item_data = {"movie_id": seed_movies[0]["id"]}
    cart_resp = await client.post(
        "/api/v1/ecommerce/cart/items/",
        json=cart_item_data,
        headers=headers
    )
    assert cart_resp.status_code == 200
    cart_item_id = cart_resp.json()["cart_item_id"]

    order_data = {"cart_item_ids": [cart_item_id]}
    resp = await client.post(
        "/api/v1/ecommerce/orders/",
        json=order_data,
        headers=headers
    )
    assert resp.status_code == 201


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_order_schema_fields_and_types(
    client,
    activated_user,
    seed_movies
):
    cart_item_data = {"movie_id": seed_movies[0]["id"]}
    cart_resp = await client.post(
        "/api/v1/ecommerce/cart/items/",
        json=cart_item_data,
        headers=activated_user["headers"]
    )
    assert cart_resp.status_code == 200
    cart_item_id = cart_resp.json()["cart_item_id"]

    order_data = {"cart_item_ids": [cart_item_id]}
    resp = await client.post(
        "/api/v1/ecommerce/orders/",
        json=order_data,
        headers=activated_user["headers"]
    )
    order = resp.json()
    assert isinstance(order["id"], int)
    assert isinstance(order["user_id"], int)
    assert isinstance(order["total_amount"], str)
    assert "created_at" in order


@pytest.mark.integration
@pytest.mark.asyncio
async def test_order_status_pending(client, activated_user, seed_movies):
    """Test order status after creating"""
    movie_data = seed_movies[0]
    cart_item_resp = await client.post(
        "/api/v1/ecommerce/cart/items/",
        json={"movie_id": movie_data["id"]},
        headers=activated_user["headers"]
    )
    cart_item_id = cart_item_resp.json()["cart_item_id"]
    create_resp = await client.post(
        "/api/v1/ecommerce/orders/",
        json={"cart_item_ids": [cart_item_id]},
        headers=activated_user["headers"]
    )

    order = create_resp.json()
    assert order["status"] == "pending"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_order_invalid(client, activated_user, pending_order):
    """Test updating order with invalid data"""
    resp = await client.patch(
        f"/api/v1/ecommerce/orders/{pending_order['order_id']}/",
        json={"invalid_field": "value"},
        headers=activated_user["headers"]
    )
    assert resp.status_code == 405


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_order_schema_fields_and_types(
    client,
    activated_user,
    pending_order
):
    resp = await client.get(
        f"/api/v1/ecommerce/orders/{pending_order['order_id']}/",
        headers=activated_user["headers"]
    )
    assert resp.status_code == 200
    order = resp.json()
    assert isinstance(order["id"], int)
    assert isinstance(order["status"], str)
    assert isinstance(order["created_at"], str)
    assert "items" in order and isinstance(order["items"], list)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_orders_invalid_http_method(client, pending_order):
    resp = await client.put("/api/v1/ecommerce/orders/")
    assert resp.status_code == 405


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_order_error_message_format(client, activated_user):
    resp = await client.post(
        "/api/v1/ecommerce/orders/",
        json={},
        headers=activated_user["headers"]
    )
    assert resp.status_code == 422
    data = resp.json()
    assert "detail" in data
