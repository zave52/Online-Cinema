import base64
from io import BytesIO

import aioboto3
import httpx
import pytest
from PIL import Image
from bs4 import BeautifulSoup


@pytest.mark.e2e
@pytest.mark.order(9)
async def test_avatar_upload_and_verification(
    e2e_client,
    e2e_db_session,
    settings,
    s3_client
):
    """End-to-end test for user profile creation with avatar upload and verification."""
    user_data = {
        "email": "storage.test@example.com",
        "password": "Password123!"
    }
    register_resp = await e2e_client.post(
        "/api/v1/accounts/register/",
        json=user_data
    )
    user_id = register_resp.json()["id"]

    mailhog_url = f"http://{settings.MAIL_SERVER}:8025/api/v2/messages"
    async with httpx.AsyncClient() as client:
        mailhog_response = await client.get(mailhog_url)
    messages = mailhog_response.json()["items"]
    activation_email = [
        m for m in messages
        if m["Content"]["Headers"]["To"][0] == user_data["email"]
    ][0]
    email_html = base64.b64decode(activation_email["MIME"]["Parts"][0]["Body"])
    soup = BeautifulSoup(email_html, "html.parser")
    activation_link = soup.find("a", id="link")["href"]
    token = activation_link.split("token=")[1]

    await e2e_client.post(
        "/api/v1/accounts/activate/",
        json={"email": user_data["email"], "token": token}
    )

    login_resp = await e2e_client.post(
        "/api/v1/accounts/login/",
        json=user_data
    )
    user_token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {user_token}"}

    img = Image.new("RGB", (100, 100), color="blue")
    img_bytes = BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)

    profile_data = {
        "first_name": "Storage",
        "last_name": "Test",
        "gender": "MAN",
        "date_of_birth": "1991-01-01",
        "info": "Testing storage.",
    }
    files = {"avatar": ("avatar.jpg", img_bytes, "image/jpeg")}

    profile_url = f"/api/v1/profiles/users/{user_id}/profile/"
    profile_response = await e2e_client.post(
        profile_url,
        headers=headers,
        data=profile_data,
        files=files
    )
    assert profile_response.status_code == 201, f"Profile creation failed: {profile_response.text}"

    profile_json = profile_response.json()
    assert "avatar" in profile_json
    avatar_key = f"avatars/{user_id}_avatar.jpg"
    expected_url = await s3_client.get_file_url(avatar_key)
    assert profile_json["avatar"] == expected_url

    session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url=settings.S3_STORAGE_ENDPOINT,
        aws_access_key_id=settings.S3_STORAGE_ACCESS_KEY,
        aws_secret_access_key=settings.S3_STORAGE_SECRET_KEY
    ) as s3:
        response = await s3.list_objects_v2(
            Bucket=settings.S3_BUCKET_NAME,
            Prefix=avatar_key
        )

    assert "Contents" in response, f"Avatar {avatar_key} not found in MinIO bucket."
