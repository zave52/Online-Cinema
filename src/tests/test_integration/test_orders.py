import pytest

from tests.conftest import activated_user


@pytest.mark.integration
async def test_list_orders_empty(client, activated_user):
    headers = activated_user["headers"]
    resp = await client.get("/api/v1/ecommerce/orders/", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["orders"] == []


@pytest.mark.integration
async def test_create_order_unauthorized(client):
    resp = await client.post("/api/v1/ecommerce/orders/", json={})
    assert resp.status_code == 403


@pytest.mark.integration
async def test_create_order_missing_data(client, activated_user):
    headers = activated_user["headers"]
    resp = await client.post(
        "/api/v1/ecommerce/orders/",
        json={},
        headers=headers
    )
    assert resp.status_code == 422


@pytest.mark.integration
async def test_create_order_empty_items(client, activated_user):
    """Test creating order with empty items list."""
    headers = activated_user["headers"]

    order_data = {"items": []}

    resp = await client.post(
        "/api/v1/ecommerce/orders/",
        json=order_data,
        headers=headers
    )
    assert resp.status_code == 422


@pytest.mark.integration
async def test_cancel_order(client, activated_user, seed_movies):
    """Test order cancellation."""
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
    order_id = resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/ecommerce/orders/{order_id}/",
        headers=headers
    )
    assert resp.status_code == 204


@pytest.mark.integration
async def test_get_user_orders(client, activated_user):
    """Test getting user's orders."""
    headers = activated_user["headers"]

    resp = await client.get("/api/v1/ecommerce/orders/", headers=headers)
    assert resp.status_code == 200

    orders = resp.json()["orders"]
    assert isinstance(orders, list)


@pytest.mark.integration
async def test_get_specific_order(client, activated_user, seed_movies):
    """Test getting specific order by ID."""
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
    order_id = resp.json()["id"]

    resp = await client.get(
        f"/api/v1/ecommerce/orders/{order_id}/",
        headers=headers
    )
    assert resp.status_code == 200


@pytest.mark.integration
async def test_get_orders_unauthorized(client):
    """Test getting orders without authentication."""
    resp = await client.get("/api/v1/ecommerce/orders/")
    assert resp.status_code == 403


@pytest.mark.integration
async def test_order_pagination(client, activated_user):
    """Test order list pagination."""
    headers = activated_user["headers"]

    resp = await client.get(
        "/api/v1/ecommerce/orders/?page=1&per_page=10",
        headers=headers
    )
    assert resp.status_code == 200


@pytest.mark.integration
async def test_order_duplicate_items(client, activated_user, seed_movies):
    """Test creating order with duplicate items."""
    headers = activated_user["headers"]

    cart_item_data = {"movie_id": seed_movies[0]["id"]}
    cart_resp = await client.post(
        "/api/v1/ecommerce/cart/items/",
        json=cart_item_data,
        headers=headers
    )
    assert cart_resp.status_code == 200
    cart_item_id = cart_resp.json()["cart_item_id"]

    order_data = {"cart_item_ids": [cart_item_id, cart_item_id]}

    resp = await client.post(
        "/api/v1/ecommerce/orders/",
        json=order_data,
        headers=headers
    )
    assert resp.status_code == 400


@pytest.mark.integration
async def test_get_order_not_found(client, activated_user):
    headers = activated_user["headers"]
    resp = await client.get("/api/v1/ecommerce/orders/9999/", headers=headers)
    assert resp.status_code == 404


@pytest.mark.integration
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
async def test_order_schema_fields_and_types(
    client,
    activated_user,
    seed_movies
):
    headers = activated_user["headers"]
    cart_item_data = {"movie_id": seed_movies[0]["id"]}
    cart_resp = await client.post(
        "/api/v1/ecommerce/cart/items/",
        json=cart_item_data,
        headers=headers
    )
    assert cart_resp.status_code == 201
    cart_item_id = cart_resp.json().get("id")

    order_data = {"cart_item_ids": [cart_item_id]}
    resp = await client.post(
        "/api/v1/ecommerce/orders/",
        json=order_data,
        headers=headers
    )
    order = resp.json()
    assert isinstance(order["id"], int)
    assert isinstance(order["user_id"], int)
    assert isinstance(order["total_price"], (int, float))
    assert "created_at" in order


@pytest.mark.integration
async def test_order_status_pending(client, activated_user):
    """Test order status after creating"""
    headers = activated_user["headers"]

    cart_item_resp = await client.post(
        "/api/v1/ecommerce/cart/items/",
        json={"movie_id": 1},
        headers=headers
    )
    cart_item_id = cart_item_resp.json()["cart_item_id"]
    create_resp = await client.post(
        "/api/v1/ecommerce/orders/",
        json={"cart_item_ids": [cart_item_id]},
        headers=headers
    )

    order = create_resp.json()
    assert order["status"] == "pending"


@pytest.mark.integration
async def test_update_order_invalid(client, activated_user):
    """Test updating order with invalid data"""
    headers = activated_user["headers"]
    resp = await client.patch(
        "/api/v1/ecommerce/orders/1/",
        json={"invalid_field": "value"},
        headers=headers
    )
    assert resp.status_code == 405


@pytest.mark.integration
async def test_order_schema_fields_and_types(client, activated_user):
    headers = activated_user["headers"]

    cart_item_resp = await client.post(
        "/api/v1/ecommerce/cart/items/",
        json={"movie_id": 1},
        headers=headers
    )
    cart_item_id = cart_item_resp.json()["cart_item_id"]

    order_resp = await client.post(
        "/api/v1/ecommerce/orders/",
        json={"cart_item_ids": [cart_item_id]},
        headers=headers
    )

    order_id = order_resp.json().get("id")
    resp = await client.get(
        f"/api/v1/ecommerce/orders/{order_id}/",
        headers=headers
    )
    assert resp.status_code == 200
    order = resp.json()
    assert isinstance(order["id"], int)
    assert isinstance(order["status"], str)
    assert isinstance(order["created_at"], str)
    assert "items" in order and isinstance(order["items"], list)


@pytest.mark.integration
async def test_orders_invalid_http_method(client):
    resp = await client.put("/api/v1/ecommerce/orders/")
    assert resp.status_code == 405


@pytest.mark.integration
async def test_create_order_error_message_format(client, activated_user):
    headers = activated_user["headers"]
    resp = await client.post(
        "/api/v1/ecommerce/orders/",
        json={},
        headers=headers
    )
    assert resp.status_code == 422
    data = resp.json()
    assert "detail" in data
