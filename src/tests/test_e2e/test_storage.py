import io

import pytest
from PIL import Image


def create_test_image() -> bytes:
    """Create a minimal valid JPEG image for testing."""
    img = Image.new('RGB', (1, 1), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    return img_bytes.getvalue()


@pytest.mark.e2e
async def test_storage_file_upload_flow(client, activated_user):
    """Test complete file upload storage workflow."""
    headers = {"Authorization": f"Bearer {activated_user['access_token']}"}
    user_id = activated_user["user_id"]

    profile_data = {
        "first_name": "John",
        "last_name": "Doe",
        "gender": "MAN",
        "date_of_birth": "1990-01-01",
        "info": "Test user"
    }

    files = {"avatar": ("avatar.jpg", create_test_image(), "image/jpeg")}

    upload_resp = await client.post(
        f"/api/v1/profiles/users/{user_id}/profile/",
        data=profile_data,
        files=files,
        headers=headers
    )

    assert upload_resp.status_code == 201


@pytest.mark.e2e
async def test_storage_file_validation_flow(client, activated_user):
    """Test file upload validation workflow."""
    headers = {"Authorization": f"Bearer {activated_user['access_token']}"}
    user_id = activated_user["user_id"]

    profile_data = {
        "first_name": "John",
        "last_name": "Doe",
        "gender": "MAN",
        "date_of_birth": "1990-01-01",
        "info": "Test user"
    }

    invalid_files = {
        "avatar": ("document.pdf", b"fake pdf content", "application/pdf")
    }

    invalid_resp = await client.post(
        f"/api/v1/profiles/users/{user_id}/profile/",
        data=profile_data,
        files=invalid_files,
        headers=headers
    )
    assert invalid_resp.status_code in (400, 422)

    large_files = {
        "avatar": ("large.jpg", b"x" * (10 * 1024 * 1024), "image/jpeg")
    }

    large_resp = await client.post(
        f"/api/v1/profiles/users/{user_id}/profile/",
        data=profile_data,
        files=large_files,
        headers=headers
    )
    assert large_resp.status_code in (400, 413, 422)


@pytest.mark.e2e
async def test_file_upload_returns_dummy_url(client, activated_user):
    headers = {"Authorization": f"Bearer {activated_user['access_token']}"}
    user_id = activated_user["user_id"]

    profile_data = {
        "first_name": "John",
        "last_name": "Doe",
        "gender": "MAN",
        "date_of_birth": "1990-01-01",
        "info": "Test user"
    }

    files = {"avatar": ("avatar.jpg", create_test_image(), "image/jpeg")}

    resp = await client.post(
        f"/api/v1/profiles/users/{user_id}/profile/",
        data=profile_data,
        files=files,
        headers=headers
    )

    assert resp.status_code == 201
    data = resp.json()
    assert "avatar" in data
    assert data["avatar"].startswith("https://fake-bucket.s3.amazonaws.com/")
