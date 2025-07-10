import asyncio

import pytest


@pytest.mark.integration
async def test_list_movies_empty(client):
    """Test listing movies when database has movies."""
    response = await client.get("/api/v1/cinema/movies/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "movies" in data
    assert isinstance(data["movies"], list)


@pytest.mark.integration
async def test_create_and_list_movies(client, admin_token):
    """Test creating and listing movies with admin privileges."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    movie_data = {
        "name": "Test Movie",
        "year": 2022,
        "time": 120,
        "imdb": 8.5,
        "votes": 1000,
        "description": "A test movie.",
        "price": 9.99,
        "meta_score": 50,
        "gross": 5,
        "certification": "G",
        "genres": ["Action"],
        "stars": ["Test Star"],
        "directors": ["Test Director"]
    }
    create_resp = await client.post(
        "/api/v1/cinema/movies/",
        json=movie_data,
        headers=headers
    )
    assert create_resp.status_code == 201

    list_resp = await client.get("/api/v1/cinema/movies/")
    assert list_resp.status_code == 200
    movies = list_resp.json()["movies"]
    assert any(m["name"] == "Test Movie" for m in movies)


@pytest.mark.integration
async def test_movie_not_found(client):
    """Test getting non-existent movie."""
    resp = await client.get("/api/v1/cinema/movies/9999/")
    assert resp.status_code == 404


@pytest.mark.integration
async def test_create_movie_missing_fields(client, admin_token):
    """Test creating movie with missing required fields."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await client.post(
        "/api/v1/cinema/movies/",
        json={"name": "Incomplete Movie"},
        headers=headers
    )
    assert resp.status_code == 422


@pytest.mark.integration
async def test_filter_movies_no_results(client):
    """Test filtering movies with no results."""
    resp = await client.get("/api/v1/cinema/movies/?genre=NonExistentGenre")
    assert resp.status_code == 200
    data = resp.json()
    assert data["movies"] == []


@pytest.mark.integration
async def test_get_movie_invalid_id_format(client):
    """Test getting movie with invalid ID format."""
    resp = await client.get("/api/v1/cinema/movies/not-an-id/")
    assert resp.status_code == 422


@pytest.mark.integration
async def test_list_movies_empty_database(client):
    """Test listing movies from empty database."""
    resp = await client.get("/api/v1/cinema/movies/")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["movies"], list)


@pytest.mark.integration
async def test_movies_default_pagination(client, seed_movies):
    """Test movies list with default pagination."""
    resp = await client.get("/api/v1/cinema/movies/")
    assert resp.status_code == 200
    data = resp.json()
    assert "movies" in data
    assert "prev_page" in data
    assert "next_page" in data
    assert "total_items" in data
    assert "total_pages" in data


@pytest.mark.integration
async def test_movies_custom_pagination(client, seed_movies):
    """Test movies list with custom pagination."""
    resp = await client.get("/api/v1/cinema/movies/?per_page=1&page=2")
    assert resp.status_code == 200
    data = resp.json()
    assert "movies" in data
    assert len(data["movies"]) == 1


@pytest.mark.integration
@pytest.mark.parametrize(
    "page, per_page",
    [(-1, 10), (0, 10), (1, -1), (1, 0), (1, 101)]
)
async def test_movies_invalid_pagination_params(client, page, per_page):
    """Test movies list with invalid pagination parameters."""
    resp = await client.get(
        f"/api/v1/cinema/movies/?page={page}&per_page={per_page}"
    )
    assert resp.status_code == 422


@pytest.mark.integration
async def test_movies_invalid_query_types(client):
    """Test movies list with invalid query parameter types."""
    resp = await client.get("/api/v1/cinema/movies/?page=abc&per_page=xyz")
    assert resp.status_code == 422


@pytest.mark.integration
async def test_movies_sort_by_year(client):
    """Test movies list sorted by year."""
    resp = await client.get("/api/v1/cinema/movies/?sort_by=year")
    assert resp.status_code == 200


@pytest.mark.integration
async def test_movies_sort_by_imdb(client):
    """Test movies list sorted by IMDB rating."""
    resp = await client.get("/api/v1/cinema/movies/?sort_by=imdb")
    assert resp.status_code == 200


@pytest.mark.integration
async def test_movies_sort_invalid_field(client):
    """Test movies list sorted by invalid field."""
    resp = await client.get("/api/v1/cinema/movies/?sort_by=invalid_field")
    assert resp.status_code == 200


@pytest.mark.integration
async def test_movies_filter_by_year(client):
    """Test movies list filtered by year."""
    resp = await client.get("/api/v1/cinema/movies/?year=2020")
    assert resp.status_code == 200


@pytest.mark.integration
async def test_movies_filter_by_year_range(client):
    """Test movies list filtered by year range."""
    resp = await client.get(
        "/api/v1/cinema/movies/?year_from=2020&year_to=2023"
    )
    assert resp.status_code == 200


@pytest.mark.integration
async def test_movies_filter_by_imdb_rating(client):
    """Test movies list filtered by IMDB rating."""
    resp = await client.get("/api/v1/cinema/movies/?imdb_min=7.0")
    assert resp.status_code == 200


@pytest.mark.integration
async def test_movies_filter_by_price_range(client):
    """Test movies list filtered by price range."""
    resp = await client.get(
        "/api/v1/cinema/movies/?price_min=5.0&price_max=15.0"
    )
    assert resp.status_code == 200


@pytest.mark.integration
async def test_movies_search_by_name(client):
    """Test movies list with name search."""
    resp = await client.get("/api/v1/cinema/movies/?search=Action")
    assert resp.status_code == 200


@pytest.mark.integration
async def test_movies_search_case_insensitive(client):
    """Test movies list with case insensitive search."""
    resp = await client.get("/api/v1/cinema/movies/?search=ACTION")
    assert resp.status_code == 200


@pytest.mark.integration
async def test_movies_search_partial_match(client):
    """Test movies list with partial match search."""
    resp = await client.get("/api/v1/cinema/movies/?search=Act")
    assert resp.status_code == 200


@pytest.mark.integration
async def test_create_movie_unauthorized(client):
    """Test creating movie without authentication."""
    movie_data = {
        "name": "Unauthorized Movie",
        "year": 2022,
        "time": 120,
        "imdb": 8.5,
        "votes": 1000,
        "description": "Should not be created.",
        "price": 9.99,
        "meta_score": 50,
        "gross": 5,
        "certification": "PG-13",
        "genres": ["Test Genre"],
        "stars": ["Test Star"],
        "directors": ["Test Director"]
    }

    resp = await client.post("/api/v1/cinema/movies/", json=movie_data)
    assert resp.status_code == 403


@pytest.mark.integration
async def test_create_movie_invalid_data_types(client, user_data):
    """Test creating movie with invalid data types."""
    await client.post("/api/v1/accounts/register/", json=user_data)
    login_resp = await client.post(
        "/api/v1/accounts/login/",
        json={"email": user_data["email"], "password": user_data["password"]},
        headers={"Content-Type": "application/json"}
    )

    if login_resp.status_code == 200:
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        invalid_movie_data = {
            "name": 123,
            "year": "not_a_year",
            "time": -10,
            "imdb": "invalid_rating",
            "votes": -100,
            "description": None,
            "price": "free",
            "meta_score": 50,
            "gross": 5,
            "certification": 1,
            "genres": ["Test Genre"],
            "stars": ["Test Star"],
            "directors": ["Test Director"]
        }

        resp = await client.post(
            "/api/v1/cinema/movies/",
            json=invalid_movie_data,
            headers=headers
        )
        assert resp.status_code == 422


@pytest.mark.integration
async def test_create_movie_boundary_values(client, admin_token):
    """Test creating movie with boundary values."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    boundary_movie_data = {
        "name": "A" * 1000,
        "year": 1900,
        "time": 1,
        "imdb": 0.0,
        "votes": 0,
        "description": "",
        "price": 0.01,
        "meta_score": 50,
        "gross": 5,
        "certification": "G",
        "genres": ["Test Genre"],
        "stars": ["Test Star"],
        "directors": ["Test Director"]
    }

    resp = await client.post(
        "/api/v1/cinema/movies/",
        json=boundary_movie_data,
        headers=headers
    )
    assert resp.status_code == 422


@pytest.mark.integration
async def test_update_movie_success(client, admin_token, seed_movies):
    """Test successful movie update."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    movie_id = seed_movies[0]["id"]
    update_data = {
        "name": "Updated Movie Name",
        "description": "Updated description"
    }

    resp = await client.patch(
        f"/api/v1/cinema/movies/{movie_id}/",
        json=update_data,
        headers=headers
    )
    assert resp.status_code == 200


@pytest.mark.integration
async def test_update_movie_not_found(client, admin_token):
    """Test updating non-existent movie."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    update_data = {"name": "Should Not Update"}
    resp = await client.patch(
        "/api/v1/cinema/movies/9999/",
        json=update_data,
        headers=headers
    )
    assert resp.status_code == 404


@pytest.mark.integration
async def test_delete_movie_success(client, admin_token, seed_movies):
    """Test successful movie deletion."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    movie_data = {
        "name": "Test Movie",
        "year": 2010,
        "time": 120,
        "imdb": 8.5,
        "votes": 1000,
        "description": "Test movie",
        "price": 9.99,
        "meta_score": 50,
        "gross": 5,
        "certification": "G",
        "genres": ["Test Genre"],
        "stars": ["Test Star"],
        "directors": ["Test Director"]
    }
    movie_resp = await client.post(
        "/api/v1/cinema/movies/",
        json=movie_data,
        headers=headers
    )

    movie_id = movie_resp.json()["id"]
    resp = await client.delete(
        f"/api/v1/cinema/movies/{movie_id}/",
        headers=headers
    )
    assert resp.status_code == 200


@pytest.mark.integration
async def test_delete_movie_unauthorized(client, seed_movies):
    """Test deleting movie without authentication."""
    movie_id = seed_movies[0]["id"]
    resp = await client.delete(f"/api/v1/cinema/movies/{movie_id}/")
    assert resp.status_code == 403


@pytest.mark.integration
async def test_movies_concurrent_access(client):
    """Test concurrent access to movies endpoint."""
    tasks = [
        client.get("/api/v1/cinema/movies/")
        for _ in range(5)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)
    status_codes = [
        r.status_code if hasattr(r, 'status_code') else 500 for r in results
    ]

    assert all(code == 200 for code in status_codes)


@pytest.mark.integration
async def test_movies_sql_injection_attempt(client):
    """Test SQL injection attempt in movies search."""
    malicious_search = "'; DROP TABLE movies; --"
    resp = await client.get(f"/api/v1/cinema/movies/?search={malicious_search}")
    assert resp.status_code == 200


@pytest.mark.integration
async def test_movies_xss_prevention(client):
    """Test XSS prevention in movie responses."""
    xss_payload = "<script>alert('xss')</script>"
    resp = await client.get(f"/api/v1/cinema/movies/?search={xss_payload}")
    assert resp.status_code == 200

    response_text = resp.text
    assert "<script>" not in response_text


@pytest.mark.integration
async def test_movies_large_request_payload(client, admin_token):
    """Test handling of large request payload."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    large_movie_data = {
        "name": "Test Movie",
        "year": 2020,
        "time": 120,
        "imdb": 8.5,
        "votes": 1000,
        "description": "A" * 100000,
        "price": 9.99,
        "meta_score": 50,
        "gross": 5,
        "certification": "G",
        "genres": ["Test Genre"],
        "stars": ["Test Star"],
        "directors": ["Test Director"]
    }

    resp = await client.post(
        "/api/v1/cinema/movies/",
        json=large_movie_data,
        headers=headers
    )

    assert resp.status_code == 201


@pytest.mark.integration
async def test_movies_invalid_http_methods(client):
    """Test invalid HTTP methods on movies endpoint."""
    resp = await client.patch("/api/v1/cinema/movies/")
    assert resp.status_code == 405


@pytest.mark.integration
async def test_movies_content_type_validation(client, admin_token):
    """Test content type validation for movie creation."""
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "text/plain"
    }

    movie_data = "not json data"
    resp = await client.post(
        "/api/v1/cinema/movies/",
        data=movie_data,
        headers=headers
    )
    assert resp.status_code == 422


@pytest.mark.integration
async def test_movie_filtering_integration(client, admin_token):
    """Test movie filtering integration."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    movie_data_1 = {
        "name": "Action Movie Test",
        "year": 2023,
        "time": 120,
        "imdb": 7.5,
        "votes": 500,
        "description": "An action-packed movie.",
        "price": 12.99,
        "meta_score": 50,
        "gross": 5,
        "certification": "PG-13",
        "genres": ["Action"],
        "stars": ["Action Star"],
        "directors": ["Action Director"]
    }

    movie_data_2 = {
        "name": "Comedy Movie Test",
        "year": 2022,
        "time": 90,
        "imdb": 6.0,
        "votes": 300,
        "description": "A hilarious comedy.",
        "price": 8.99,
        "meta_score": 50,
        "gross": 5,
        "certification": "PG",
        "genres": ["Comedy"],
        "stars": ["Comedy Star"],
        "directors": ["Comedy Director"]
    }

    action_resp = await client.post(
        "/api/v1/cinema/movies/",
        json=movie_data_1,
        headers=headers
    )
    assert action_resp.status_code == 201

    comedy_resp = await client.post(
        "/api/v1/cinema/movies/",
        json=movie_data_2,
        headers=headers
    )
    assert comedy_resp.status_code == 201

    resp = await client.get("/api/v1/cinema/movies/?genre=Action")
    assert resp.status_code == 200
    movies = resp.json()["movies"]
    assert len(movies) > 0

    assert all(
        any(genre["name"] == "Action" for genre in m["genres"]) for m in movies
    )

    resp = await client.get("/api/v1/cinema/movies/?imdb_min=7.0")
    assert resp.status_code == 200
    movies = resp.json()["movies"]
    assert len(movies) > 0
    assert all(m["imdb"] >= 7.0 for m in movies)

    resp = await client.get("/api/v1/cinema/movies/?genre=Action&&imdb_min=7.0")
    assert resp.status_code == 200
    movies = resp.json()["movies"]
    assert len(movies) > 0
    assert all(
        any(
            genre["name"] == "Action"
            for genre in m["genres"]
        ) and m["imdb"] >= 7.0
        for m in movies
    )
