import pytest


@pytest.mark.api
@pytest.mark.asyncio
async def test_list_movies_success(client):
    """Test successful movie listing."""
    resp = await client.get("/api/v1/cinema/movies/")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert "movies" in data
    assert isinstance(data["movies"], list)


@pytest.mark.api
@pytest.mark.asyncio
async def test_get_movie_by_id_success(client, seed_movies):
    """Test getting movie by ID."""
    if seed_movies:
        movie_id = seed_movies[0]["id"]
        resp = await client.get(f"/api/v1/cinema/movies/{movie_id}/")
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert "name" in data
        assert "year" in data
        assert "time" in data
        assert "imdb" in data
        assert "votes" in data
        assert "meta_score" in data
        assert "gross" in data
        assert "description" in data
        assert "price" in data
        assert "genres" in data
        assert "stars" in data
        assert "directors" in data
        assert "certification" in data
        assert "likes" in data
        assert "favorites" in data
        assert "average_rating" in data
        assert "comments" in data


@pytest.mark.api
@pytest.mark.asyncio
async def test_get_movie_not_found(client):
    """Test getting non-existent movie."""
    resp = await client.get("/api/v1/cinema/movies/99999/")
    assert resp.status_code == 404
    assert "detail" in resp.json()


@pytest.mark.api
@pytest.mark.asyncio
async def test_get_movie_invalid_id_format(client):
    """Test getting movie with invalid ID format."""
    resp = await client.get("/api/v1/cinema/movies/invalid-id/")
    assert resp.status_code == 422


@pytest.mark.api
@pytest.mark.asyncio
async def test_create_movie_unauthorized(client):
    """Test creating movie without authentication."""
    movie_data = {
        "name": "Test Movie",
        "year": 2024,
        "time": 120,
        "imdb": 8.0,
        "votes": 1000,
        "description": "Test description",
        "price": 9.99,
        "certification": "G"
    }
    resp = await client.post("/api/v1/cinema/movies/", json=movie_data)
    assert resp.status_code in (401, 403)


@pytest.mark.api
@pytest.mark.asyncio
async def test_create_movie_invalid_data(client, admin_token):
    """Test creating movie with invalid data."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    invalid_movies = [
        {},
        {"name": ""},
        {"name": "Test", "year": "invalid"},
        {"name": "Test", "year": 2024, "time": -1},
        {"name": "Test", "year": 2024, "time": 120, "imdb": 11.0},
    ]

    for invalid_data in invalid_movies:
        resp = await client.post(
            "/api/v1/cinema/movies/",
            json=invalid_data,
            headers=headers
        )
        assert resp.status_code in (400, 422)


@pytest.mark.api
@pytest.mark.asyncio
async def test_movies_pagination(client):
    """Test movies pagination."""
    resp = await client.get("/api/v1/cinema/movies/?page=1&size=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "movies" in data
    assert "prev_page" in data
    assert "next_page" in data
    assert "total_pages" in data
    assert "total_items" in data


@pytest.mark.api
@pytest.mark.asyncio
async def test_movies_filtering(client):
    """Test movies filtering by genre."""
    resp = await client.get("/api/v1/cinema/movies/?genre=action")
    assert resp.status_code == 200
    data = resp.json()
    assert "movies" in data


@pytest.mark.api
@pytest.mark.asyncio
async def test_movies_search(client):
    """Test movies search functionality."""
    resp = await client.get("/api/v1/cinema/movies/?search=test")
    assert resp.status_code == 200
    data = resp.json()
    assert "movies" in data


@pytest.mark.api
@pytest.mark.asyncio
async def test_movies_sort(client):
    """Test movie sorting."""
    sort_fields = ["year", "imdb", "name", "price"]

    for field in sort_fields:
        resp = await client.get(f"/api/v1/cinema/movies/?sort_by={field}")
        assert resp.status_code == 200


@pytest.mark.api
@pytest.mark.asyncio
async def test_movies_multiple_filters(client):
    """Test combining multiple filters."""
    resp = await client.get(
        "/api/v1/cinema/movies/?year=2024&imdb_min=7&search=action"
    )  # Added trailing slash
    assert resp.status_code == 200


@pytest.mark.api
@pytest.mark.asyncio
async def test_update_movie_unauthorized(client):
    """Test updating movie without authentication."""
    resp = await client.patch(
        "/api/v1/cinema/movies/1/",
        json={"name": "Updated"}
    )
    assert resp.status_code in (401, 403)


@pytest.mark.api
@pytest.mark.asyncio
async def test_delete_movie_unauthorized(client):
    """Test deleting movie without authentication."""
    resp = await client.delete("/api/v1/cinema/movies/1/")
    assert resp.status_code in (401, 403)


@pytest.mark.api
@pytest.mark.asyncio
async def test_movies_malformed_json(client, admin_token):
    """Test malformed JSON in movie creation."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    resp = await client.post(
        "/api/v1/cinema/movies/",
        data="invalid json",
        headers=headers
    )
    assert resp.status_code in (400, 422)


@pytest.mark.api
@pytest.mark.asyncio
async def test_movies_invalid_http_method(client):
    """Test invalid HTTP methods."""
    resp = await client.patch("/api/v1/cinema/movies/")
    assert resp.status_code == 405
