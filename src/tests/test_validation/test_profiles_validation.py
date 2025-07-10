from datetime import date, timedelta
from io import BytesIO
from unittest.mock import MagicMock

import pytest
from PIL import Image
from fastapi import UploadFile, HTTPException

from schemas.profiles import (
    ProfileCreateRequestSchema,
    ProfileUpdateRequestSchema,
    ProfilePatchRequestSchema,
)


@pytest.fixture
def mock_avatar():
    """Fixture for a mock avatar file."""
    img = Image.new("RGB", (10, 10), color="red")
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)

    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "avatar.png"
    mock_file.content_type = "image/png"
    mock_file.file = img_byte_arr
    return mock_file


class TestProfileCreateRequestSchema:
    """Test ProfileCreateRequestSchema validation logic."""

    def test_valid_profile_create(self, mock_avatar):
        """Test valid profile creation data."""
        valid_data = {
            "first_name": "John",
            "last_name": "Doe",
            "gender": "man",
            "date_of_birth": date(2000, 1, 1),
            "info": "A bit about me.",
            "avatar": mock_avatar,
        }
        try:
            schema = ProfileCreateRequestSchema(**valid_data)
            assert schema.first_name == "john"
            assert schema.last_name == "doe"
        except HTTPException as e:
            pytest.fail(f"Validation failed unexpectedly: {e.detail}")

    def test_invalid_gender(self, mock_avatar):
        """Test invalid gender."""
        with pytest.raises(HTTPException):
            ProfileCreateRequestSchema(
                first_name="John",
                last_name="Doe",
                gender="other",
                date_of_birth=date(2000, 1, 1),
                info="A bit about me.",
                avatar=mock_avatar,
            )

    def test_invalid_date_of_birth(self, mock_avatar):
        """Test invalid date_of_birth."""
        with pytest.raises(HTTPException):
            ProfileCreateRequestSchema(
                first_name="John",
                last_name="Doe",
                gender="man",
                date_of_birth=date.today() + timedelta(days=1),
                info="A bit about me.",
                avatar=mock_avatar,
            )

    def test_empty_info(self, mock_avatar):
        """Test empty info field."""
        with pytest.raises(HTTPException):
            ProfileCreateRequestSchema(
                first_name="John",
                last_name="Doe",
                gender="man",
                date_of_birth=date(2000, 1, 1),
                info="  ",
                avatar=mock_avatar,
            )


class TestProfileUpdateRequestSchema:
    """Test ProfileUpdateRequestSchema validation logic."""

    def test_valid_profile_update(self, mock_avatar):
        """Test valid profile update data."""
        valid_data = {
            "first_name": "John",
            "last_name": "Doe",
            "gender": "man",
            "date_of_birth": date(2000, 1, 1),
            "info": "A bit about me.",
            "avatar": mock_avatar,
        }
        try:
            schema = ProfileUpdateRequestSchema(**valid_data)
            assert schema.first_name == "john"
        except HTTPException as e:
            pytest.fail(f"Validation failed unexpectedly: {e.detail}")

    def test_optional_avatar(self):
        """Test profile update with optional avatar."""
        valid_data = {
            "first_name": "John",
            "last_name": "Doe",
            "gender": "man",
            "date_of_birth": date(2000, 1, 1),
            "info": "A bit about me.",
            "avatar": None,
        }
        try:
            schema = ProfileUpdateRequestSchema(**valid_data)
            assert schema.avatar is None
        except HTTPException as e:
            pytest.fail(f"Validation failed unexpectedly: {e.detail}")


class TestProfilePatchRequestSchema:
    """Test ProfilePatchRequestSchema validation logic."""

    def test_valid_profile_patch(self):
        """Test valid profile patch data."""
        valid_data = {"first_name": "Johnny"}
        try:
            schema = ProfilePatchRequestSchema(**valid_data)
            assert schema.first_name == "johnny"
        except HTTPException as e:
            pytest.fail(f"Validation failed unexpectedly: {e.detail}")

    def test_patch_with_none_values(self):
        """Test that None values are handled correctly."""
        data = {
            "first_name": None,
            "last_name": None,
            "gender": None,
            "date_of_birth": None,
            "info": None,
            "avatar": None,
        }
        schema = ProfilePatchRequestSchema(**data)
        assert schema.first_name is None
        assert schema.last_name is None
