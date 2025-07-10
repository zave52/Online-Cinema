import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_add_comment_to_nonexistent_movie(client, activated_user):
    headers = activated_user["headers"]
    movie_id = 9999
    comment_data = {"content": "Test comment"}
    resp = await client.post(
        f"/api/v1/cinema/movies/{movie_id}/comments/",
        json=comment_data,
        headers=headers
    )
    assert resp.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_add_comment_unauthorized(client):
    movie_id = 1
    comment_data = {"content": "Test comment"}
    resp = await client.post(
        f"/api/v1/cinema/movies/{movie_id}/comments/",
        json=comment_data
    )
    assert resp.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_delete_nonexistent_comment(client, activated_user):
    headers = activated_user["headers"]
    resp = await client.delete(
        "/api/v1/cinema/movies/1/comments/9999/",
        headers=headers
    )
    assert resp.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_comment_actions(client, activated_user):
    headers = activated_user["headers"]
    movie_id = 1
    comment_data = {"content": "Test comment"}
    add_resp = await client.post(
        f"/api/v1/cinema/movies/{movie_id}/comments/",
        json=comment_data,
        headers=headers
    )
    comment_id = add_resp.json().get("id")
    del_resp = await client.delete(
        f"/api/v1/cinema/movies/{movie_id}/comments/{comment_id}/",
        headers=headers
    )
    assert del_resp.status_code == 204


@pytest.mark.integration
@pytest.mark.asyncio
async def test_add_valid_comment(client, activated_user):
    headers = activated_user["headers"]
    movie_id = 1
    comment_data = {"content": "Test comment"}
    resp = await client.post(
        f"/api/v1/cinema/movies/{movie_id}/comments/",
        json=comment_data,
        headers=headers
    )
    assert resp.status_code == 201


@pytest.mark.integration
@pytest.mark.asyncio
async def test_add_invalid_comment(client, activated_user):
    headers = activated_user["headers"]
    movie_id = 1
    comment_data = {}
    resp = await client.post(
        f"/api/v1/cinema/movies/{movie_id}/comments/",
        json=comment_data,
        headers=headers
    )
    assert resp.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_reply_to_comment(client, activated_user):
    headers = activated_user["headers"]
    movie_id = 1
    comment_data = {"content": "Parent comment"}
    add_resp = await client.post(
        f"/api/v1/cinema/movies/{movie_id}/comments/",
        json=comment_data,
        headers=headers
    )
    comment_id = add_resp.json().get("id")
    reply_data = {"content": "Reply"}
    reply_resp = await client.post(
        f"/api/v1/cinema/movies/{movie_id}/comments/{comment_id}/replies/",
        json=reply_data,
        headers=headers
    )
    assert reply_resp.status_code == 201


@pytest.mark.integration
@pytest.mark.asyncio
async def test_delete_others_comment(client, activated_user, admin_token):
    headers1 = activated_user["headers"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    movie_id = 1
    comment_data = {"content": "Test comment"}
    add_resp = await client.post(
        f"/api/v1/cinema/movies/{movie_id}/comments/",
        json=comment_data,
        headers=admin_headers
    )

    comment_id = add_resp.json().get("id")
    del_resp = await client.delete(
        f"/api/v1/cinema/movies/{movie_id}/comments/{comment_id}/",
        headers=headers1
    )
    assert del_resp.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_comment_from_movie(client, activated_user):
    headers = activated_user["headers"]
    movie_id = 1
    comment_data = {"content": "Test comment"}
    resp = await client.post(
        f"/api/v1/cinema/movies/{movie_id}/comments/",
        json=comment_data,
        headers=headers
    )
    comment_id = resp.json()["id"]

    movie_resp = await client.get(
        f"/api/v1/cinema/movies/{movie_id}/",
        headers=headers
    )

    comments = movie_resp.json()["comments"]
    comments_ids = [comment["id"] for comment in comments]

    assert comment_id in comments_ids


@pytest.mark.integration
@pytest.mark.asyncio
async def test_comment_schema_fields_and_types(client, activated_user):
    headers = activated_user["headers"]
    movie_id = 1
    comment_data = {"content": "Test comment"}
    add_resp = await client.post(
        f"/api/v1/cinema/movies/{movie_id}/comments/",
        json=comment_data,
        headers=headers
    )

    comment = add_resp.json()
    assert isinstance(comment["id"], int)
    assert isinstance(comment["content"], str)
    assert "created_at" in comment


@pytest.mark.integration
@pytest.mark.asyncio
async def test_comments_invalid_http_method(client):
    movie_id = 1
    resp = await client.put(f"/api/v1/cinema/movies/{movie_id}/comments/")
    assert resp.status_code == 405


@pytest.mark.integration
@pytest.mark.asyncio
async def test_comment_error_message_format(client, activated_user):
    headers = activated_user["headers"]
    movie_id = 1
    resp = await client.post(
        f"/api/v1/cinema/movies/{movie_id}/comments/",
        json={},
        headers=headers
    )
    assert resp.status_code == 422
    data = resp.json()
    assert "detail" in data
