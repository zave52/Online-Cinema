import pytest


@pytest.mark.integration
async def test_rate_nonexistent_movie(client, activated_user):
    headers = activated_user["headers"]
    resp = await client.post(
        "/api/v1/cinema/movies/9999/rates/",
        json={"rate": 8},
        headers=headers
    )
    assert resp.status_code == 404


@pytest.mark.integration
async def test_rate_unauthorized(client):
    resp = await client.post(
        "/api/v1/cinema/movies/1/rates/",
        json={"rate": 8}
    )
    assert resp.status_code == 403


@pytest.mark.integration
async def test_double_rate_movie(client, activated_user):
    headers = activated_user["headers"]
    resp1 = await client.post(
        "/api/v1/cinema/movies/1/rates/",
        json={"rate": 8},
        headers=headers
    )
    resp2 = await client.post(
        "/api/v1/cinema/movies/1/rates/",
        json={"rate": 9},
        headers=headers
    )
    assert resp1.status_code == 200
    assert resp2.status_code == 200


@pytest.mark.integration
async def test_rate_valid_movie(client, activated_user):
    headers = activated_user["headers"]
    resp = await client.post(
        "/api/v1/cinema/movies/1/rates/",
        json={"rate": 8},
        headers=headers
    )
    assert resp.status_code == 200
