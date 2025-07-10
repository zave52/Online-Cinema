import pytest


@pytest.mark.integration
async def test_add_invalid_item_to_cart(client, activated_user):
    headers = activated_user["headers"]
    resp = await client.post(
        "/api/v1/ecommerce/cart/items/",
        json={"movie_id": 9999},
        headers=headers
    )
    assert resp.status_code == 404


@pytest.mark.integration
async def test_remove_nonexistent_item_from_cart(client, activated_user):
    headers = activated_user["headers"]
    resp = await client.delete(
        "/api/v1/ecommerce/cart/items/9999/",
        headers=headers
    )
    assert resp.status_code == 404


@pytest.mark.integration
async def test_add_valid_item_to_cart(client, activated_user):
    headers = activated_user["headers"]
    resp = await client.post(
        "/api/v1/ecommerce/cart/items/",
        json={"movie_id": 1},
        headers=headers
    )
    assert resp.status_code == 200


@pytest.mark.integration
async def test_get_cart_contents(client, activated_user):
    headers = activated_user["headers"]
    await client.post(
        "/api/v1/ecommerce/cart/items/",
        json={"movie_id": 1},
        headers=headers
    )
    resp = await client.get("/api/v1/ecommerce/cart/", headers=headers)
    assert resp.status_code == 200
    cart = resp.json()
    assert "movies" in cart
    assert len(cart["movies"]) >= 1


@pytest.mark.integration
async def test_remove_valid_item_from_cart(client, activated_user):
    headers = activated_user["headers"]
    add_resp = await client.post(
        "/api/v1/ecommerce/cart/items/",
        json={"movie_id": 1},
        headers=headers
    )
    cart_item_id = add_resp.json().get("cart_item_id")

    resp = await client.delete(
        f"/api/v1/ecommerce/cart/items/{cart_item_id}/",
        headers=headers
    )
    assert resp.status_code == 204


@pytest.mark.integration
async def test_shopping_cart_empty(client, activated_user):
    """Test getting empty shopping cart."""
    headers = activated_user["headers"]

    resp = await client.get("/api/v1/ecommerce/cart/", headers=headers)
    assert resp.status_code in (200, 404)

    cart = resp.json()
    assert isinstance(cart, dict)
    assert cart.get("items", []) == []


@pytest.mark.integration
async def test_add_movie_to_cart_unauthorized(client, seed_movies):
    """Test adding movie to cart without authentication."""
    movie_id = seed_movies[0]["id"]
    cart_item = {"movie_id": movie_id}

    resp = await client.post(
        "/api/v1/ecommerce/cart/items/",
        json=cart_item
    )
    assert resp.status_code == 403


@pytest.mark.integration
async def test_clear_cart(client, activated_user):
    """Test clearing cart."""
    headers = activated_user["headers"]

    clear_resp = await client.delete("/api/v1/ecommerce/cart/", headers=headers)
    assert clear_resp.status_code == 204


@pytest.mark.integration
async def test_cart_checkout(client, activated_user, seed_movies):
    """Test cart checkout."""
    headers = activated_user["headers"]

    movie_id = seed_movies[0]["id"]

    await client.post(
        "/api/v1/ecommerce/cart/items/",
        json={"movie_id": movie_id},
        headers=headers
    )

    checkout_resp = await client.post(
        "/api/v1/ecommerce/cart/checkout/",
        headers=headers
    )
    assert checkout_resp.status_code == 200
