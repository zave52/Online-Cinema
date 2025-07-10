from io import BytesIO

import pytest
from PIL import Image
from fastapi import UploadFile

from validation.profiles import validate_name, validate_image


@pytest.mark.unit
def test_validate_name_accepts_english_letters():
    validate_name("John")
    validate_name("Alice")
    validate_name("")


@pytest.mark.unit
def test_validate_name_rejects_non_english():
    with pytest.raises(ValueError):
        validate_name("Иван")
    with pytest.raises(ValueError):
        validate_name("John123")
    with pytest.raises(ValueError):
        validate_name("John_Doe")
    with pytest.raises(ValueError):
        validate_name("John-Doe")
    with pytest.raises(ValueError):
        validate_name("John Doe")


@pytest.mark.unit
def make_upload_file(format="PNG", size=(10, 10), file_size=None):
    img = Image.new("RGB", size)
    buf = BytesIO()
    img.save(buf, format=format)
    data = buf.getvalue()
    if file_size:
        data = data + b"0" * (file_size - len(data))
    buf = BytesIO(data)
    buf.seek(0)
    return UploadFile(filename=f"test.{format.lower()}", file=buf)


@pytest.mark.unit
def test_validate_image_accepts_valid_png():
    file = make_upload_file(format="PNG")
    validate_image(file)


@pytest.mark.unit
def test_validate_image_accepts_valid_jpg():
    file = make_upload_file(format="JPEG")
    validate_image(file)


@pytest.mark.unit
def test_validate_image_rejects_large_file():
    file = make_upload_file(format="PNG", file_size=1024 * 1024 + 1)
    with pytest.raises(ValueError, match="Image size exceeds 1 MB"):
        validate_image(file)


@pytest.mark.unit
def test_validate_image_rejects_unsupported_format():
    file = make_upload_file(format="BMP")
    with pytest.raises(ValueError, match="Unsupported image format"):
        validate_image(file)


@pytest.mark.unit
def test_validate_image_rejects_invalid_image():
    buf = BytesIO(b"notanimage")
    file = UploadFile(filename="bad.png", file=buf)
    with pytest.raises(ValueError, match="Invalid image format"):
        validate_image(file)
