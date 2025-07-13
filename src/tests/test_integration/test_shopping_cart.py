import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_add_invalid_item_to_cart(client, activated_user, seed_movies):
    resp = await client.post(
        "/api/v1/ecommerce/cart/items/",
        json={"movie_id": 9999},
        headers=activated_user["headers"]
    )
    assert resp.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_remove_nonexistent_item_from_cart(
    client,
    activated_user
):
    resp = await client.delete(
        "/api/v1/ecommerce/cart/items/9999/",
        headers=activated_user["headers"]
    )
    assert resp.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_add_valid_item_to_cart(client, activated_user, seed_movies):
    movie_data = seed_movies[0]
    resp = await client.post(
        "/api/v1/ecommerce/cart/items/",
        json={"movie_id": movie_data["id"]},
        headers=activated_user["headers"]
    )
    assert resp.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_cart_contents(client, activated_user, seed_movies):
    movie_data = seed_movies[0]
    await client.post(
        "/api/v1/ecommerce/cart/items/",
        json={"movie_id": movie_data["id"]},
        headers=activated_user["headers"]
    )
    resp = await client.get(
        "/api/v1/ecommerce/cart/",
        headers=activated_user["headers"]
    )
    assert resp.status_code == 200
    cart = resp.json()
    assert "movies" in cart
    assert len(cart["movies"]) >= 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_remove_valid_item_from_cart(client, activated_user, seed_movies):
    movie_data = seed_movies[0]
    add_resp = await client.post(
        "/api/v1/ecommerce/cart/items/",
        json={"movie_id": movie_data["id"]},
        headers=activated_user["headers"]
    )
    cart_item_id = add_resp.json()["cart_item_id"]

    resp = await client.delete(
        f"/api/v1/ecommerce/cart/items/{cart_item_id}/",
        headers=activated_user["headers"]
    )
    assert resp.status_code == 204


@pytest.mark.integration
@pytest.mark.asyncio
async def test_shopping_cart_empty(client, activated_user):
    """Test getting empty shopping cart."""
    resp = await client.get(
        "/api/v1/ecommerce/cart/",
        headers=activated_user["headers"]
    )
    assert resp.status_code == 200

    cart = resp.json()
    assert isinstance(cart, dict)
    assert cart.get("items", []) == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_add_movie_to_cart_unauthorized(client, seed_movies):
    """Test adding movie to cart without authentication."""
    movie_data = seed_movies[0]
    resp = await client.post(
        "/api/v1/ecommerce/cart/items/",
        json={"movie_id": movie_data["id"]}
    )
    assert resp.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_clear_cart(client, activated_user):
    """Test clearing cart."""
    clear_resp = await client.delete(
        "/api/v1/ecommerce/cart/",
        headers=activated_user["headers"]
    )
    assert clear_resp.status_code == 204


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cart_checkout(client, activated_user, seed_movies):
    """Test cart checkout."""
    movie_data = seed_movies[0]

    await client.post(
        "/api/v1/ecommerce/cart/items/",
        json={"movie_id": movie_data["id"]},
        headers=activated_user["headers"]
    )

    checkout_resp = await client.post(
        "/api/v1/ecommerce/cart/checkout/",
        headers=activated_user["headers"]
    )
    assert checkout_resp.status_code == 200
